"""
behavior_analyzer.py
====================
Analyzes customer interaction with virtual store zones.

Tracks per-person, per-zone:
    1. Zone entry time — when a person enters a zone
    2. Zone exit time  — when a person leaves a zone
    3. Dwell time      — how long a person stayed in a zone
    4. Revisit count   — how many times a person re-entered a zone
    5. Favorite zone   — the zone where a person spent the most time

The analyzer is called every frame with the person-zone mapping
from the ZoneManager. It detects transitions (enter/leave) by
comparing the current zone to the previous zone for each person.

Usage:
    analyzer = BehaviorAnalyzer(csv_logger)
    analyzer.update(person_zones, tracked_objects)
    metrics = analyzer.get_dashboard_metrics()
"""

import time
from datetime import datetime
from collections import defaultdict
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class BehaviorAnalyzer:
    """
    Tracks and analyzes customer behavior across virtual store zones.

    Attributes:
        previous_zones:   Dict {person_id: zone_name} — last frame's zone.
        zone_entries:     Dict {(person_id, zone): enter_timestamp}.
        dwell_times:      Dict {(person_id, zone): [durations]}.
        visit_counts:     Dict {(person_id, zone): int} — visit counter.
        active_visits:    Dict {(person_id, zone): enter_time} — ongoing visits.
        total_zone_time:  Dict {zone: total_seconds} — aggregate time.
        total_zone_visits: Dict {zone: total_visit_count}.
        csv_logger:       CSVLogger for persisting behavior data.
    """

    def __init__(self, csv_logger=None, db=None):
        """
        Initialize the behavior analyzer.

        Args:
            csv_logger: CSVLogger instance. If None, CSV logging is disabled.
            db: DatabaseManager instance. If None, DB logging is disabled.
        """
        self.previous_zones = {}          # {person_id: zone_name or None}
        self.active_visits = {}           # {(person_id, zone): enter_time_float}
        self.dwell_times = defaultdict(list)   # {(person_id, zone): [seconds]}
        self.visit_counts = defaultdict(int)   # {(person_id, zone): count}

        # Aggregate statistics
        self.total_zone_time = defaultdict(float)    # {zone: total_seconds}
        self.total_zone_visits = defaultdict(int)     # {zone: visit_count}

        # Per-person aggregate
        self.person_total_time = defaultdict(lambda: defaultdict(float))
        # {person_id: {zone: total_seconds}}

        self.csv_logger = csv_logger
        self.db = db
        self._logged_visits = set()  # Track which visits have been logged

        print("[BEHAVIOR] Behavior analyzer initialized")

    def update(self, person_zones, tracked_objects):
        """
        Update behavior analysis with current frame's person-zone data.

        Detects zone transitions by comparing current zones to previous
        zones for each person. Records entry/exit events and calculates
        dwell times.

        Args:
            person_zones:    Dict {person_id: zone_name or None} from ZoneManager.
            tracked_objects: OrderedDict {person_id: (cx, cy)} from tracker.

        Returns:
            Dict with events: {"entries": [...], "exits": [...]}
        """
        current_time = time.time()
        events = {"entries": [], "exits": []}

        for person_id in tracked_objects:
            current_zone = person_zones.get(person_id, None)
            previous_zone = self.previous_zones.get(person_id, None)

            # =====================================================
            # CASE 1: Person entered a new zone
            # =====================================================
            if current_zone is not None and current_zone != previous_zone:
                # If they were in a different zone, close that visit first
                if previous_zone is not None:
                    self._close_visit(person_id, previous_zone, current_time)
                    events["exits"].append({
                        "person_id": person_id,
                        "zone": previous_zone,
                        "time": current_time,
                    })

                # Open a new visit
                self._open_visit(person_id, current_zone, current_time)
                events["entries"].append({
                    "person_id": person_id,
                    "zone": current_zone,
                    "time": current_time,
                })

            # =====================================================
            # CASE 2: Person left a zone (now in no zone)
            # =====================================================
            elif current_zone is None and previous_zone is not None:
                self._close_visit(person_id, previous_zone, current_time)
                events["exits"].append({
                    "person_id": person_id,
                    "zone": previous_zone,
                    "time": current_time,
                })

            # =====================================================
            # CASE 3: Person still in the same zone — accumulate time
            # =====================================================
            elif current_zone is not None and current_zone == previous_zone:
                key = (person_id, current_zone)
                if key in self.active_visits:
                    elapsed = current_time - self.active_visits[key]
                    self.person_total_time[person_id][current_zone] = \
                        sum(self.dwell_times.get(key, [])) + elapsed

            # Update previous zone
            self.previous_zones[person_id] = current_zone

        # Clean up persons that are no longer tracked
        active_ids = set(tracked_objects.keys())
        stale_ids = set(self.previous_zones.keys()) - active_ids
        for stale_id in stale_ids:
            prev_zone = self.previous_zones.get(stale_id)
            if prev_zone is not None:
                self._close_visit(stale_id, prev_zone, current_time)
            self.previous_zones.pop(stale_id, None)

        return events

    def _open_visit(self, person_id, zone_name, timestamp):
        """
        Record the start of a zone visit.

        Args:
            person_id: Tracker-assigned person ID.
            zone_name: Name of the zone entered.
            timestamp: Time of entry (float, from time.time()).
        """
        key = (person_id, zone_name)
        self.active_visits[key] = timestamp
        self.visit_counts[key] += 1
        self.total_zone_visits[zone_name] += 1

    def _close_visit(self, person_id, zone_name, timestamp):
        """
        Record the end of a zone visit and calculate dwell time.

        Args:
            person_id: Tracker-assigned person ID.
            zone_name: Name of the zone exited.
            timestamp: Time of exit (float, from time.time()).
        """
        key = (person_id, zone_name)

        if key in self.active_visits:
            enter_time = self.active_visits[key]
            dwell_time = timestamp - enter_time

            # Store dwell time
            self.dwell_times[key].append(dwell_time)
            self.total_zone_time[zone_name] += dwell_time
            self.person_total_time[person_id][zone_name] += dwell_time

            # Log to CSV
            if self.csv_logger is not None:
                visit_num = self.visit_counts.get(key, 1)
                visit_key = (person_id, zone_name, visit_num)
                if visit_key not in self._logged_visits:
                    self.csv_logger.log_behavior(
                        visitor_id=person_id,
                        track_id=person_id,
                        zone_name=zone_name,
                        enter_time=datetime.fromtimestamp(enter_time).isoformat(),
                        exit_time=datetime.fromtimestamp(timestamp).isoformat(),
                        dwell_time=round(dwell_time, 2),
                        visit_number=visit_num,
                    )
                    
                    if hasattr(self, 'db') and self.db is not None:
                        self.db.insert_behavior(
                            track_id=person_id,
                            zone_name=zone_name,
                            enter_time=datetime.fromtimestamp(enter_time).isoformat(),
                            exit_time=datetime.fromtimestamp(timestamp).isoformat(),
                            dwell_time=round(dwell_time, 2),
                            visit_number=visit_num
                        )
                        
                    self._logged_visits.add(visit_key)

            # Remove from active visits
            del self.active_visits[key]

    def get_zone_dwell_summary(self):
        """
        Get total dwell time per zone across all visitors.

        Returns:
            Dict {zone_name: total_seconds}.
        """
        summary = {}
        for zone_name in config.ZONES:
            total = self.total_zone_time.get(zone_name, 0.0)

            # Add ongoing visits
            for (pid, zn), enter_time in self.active_visits.items():
                if zn == zone_name:
                    total += time.time() - enter_time

            summary[zone_name] = round(total, 1)
        return summary

    def get_zone_visit_counts(self):
        """
        Get total visit count per zone.

        Returns:
            Dict {zone_name: total_visits}.
        """
        counts = {}
        for zone_name in config.ZONES:
            counts[zone_name] = self.total_zone_visits.get(zone_name, 0)
        return counts

    def get_most_visited_zone(self):
        """
        Get the zone with the highest total visit count.

        Returns:
            Tuple (zone_name, visit_count) or ("None", 0) if no visits.
        """
        counts = self.get_zone_visit_counts()
        if not counts or max(counts.values()) == 0:
            return ("None", 0)
        most = max(counts, key=counts.get)
        return (most, counts[most])

    def get_most_time_zone(self):
        """
        Get the zone where customers spent the most total time.

        Returns:
            Tuple (zone_name, total_seconds) or ("None", 0.0).
        """
        dwell = self.get_zone_dwell_summary()
        if not dwell or max(dwell.values()) == 0:
            return ("None", 0.0)
        most = max(dwell, key=dwell.get)
        return (most, dwell[most])

    def get_person_favorite_zone(self, person_id):
        """
        Get the zone where a specific person spent the most time.

        Args:
            person_id: Tracker-assigned person ID.

        Returns:
            Tuple (zone_name, total_seconds) or ("None", 0.0).
        """
        person_times = self.person_total_time.get(person_id, {})
        if not person_times:
            return ("None", 0.0)
        fav = max(person_times, key=person_times.get)
        return (fav, round(person_times[fav], 1))

    def get_person_zone_history(self, person_id):
        """
        Get a person's complete zone visit history.

        Args:
            person_id: Tracker-assigned person ID.

        Returns:
            List of dicts with zone_name, visit_count, total_time.
        """
        history = []
        for zone_name in config.ZONES:
            key = (person_id, zone_name)
            visits = self.visit_counts.get(key, 0)
            total_time = sum(self.dwell_times.get(key, []))

            # Add ongoing visit time
            if key in self.active_visits:
                total_time += time.time() - self.active_visits[key]

            if visits > 0:
                history.append({
                    "zone": zone_name,
                    "visits": visits,
                    "total_time": round(total_time, 1),
                })
        return history

    def get_dashboard_metrics(self):
        """
        Get all metrics needed for the dashboard display.

        Returns:
            Dict with most_visited_zone, most_time_zone,
            zone_visits, zone_dwell_times.
        """
        most_visited = self.get_most_visited_zone()
        most_time = self.get_most_time_zone()
        visits = self.get_zone_visit_counts()
        dwell = self.get_zone_dwell_summary()

        return {
            "most_visited_zone": most_visited[0],
            "most_visited_count": most_visited[1],
            "most_time_zone": most_time[0],
            "most_time_seconds": round(most_time[1], 1),
            "zone_visits": visits,
            "zone_dwell": dwell,
        }

    def get_active_zone_label(self, person_id):
        """
        Get a display-ready string for a person's current zone.

        Args:
            person_id: Person ID.

        Returns:
            String like "Electronics (12.3s)" or "—" if not in a zone.
        """
        current_zone = self.previous_zones.get(person_id, None)
        if current_zone is None:
            return "—"

        key = (person_id, current_zone)
        if key in self.active_visits:
            elapsed = time.time() - self.active_visits[key]
            return f"{current_zone} ({elapsed:.1f}s)"
        return current_zone
