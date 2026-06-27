"""
queue_manager.py
================
Queue detection and crowd management module.

Monitors the Billing zone (queue ROI) and provides:
    1. Queue Length    — Number of people in the billing ROI
    2. Wait Time      — Estimated wait time based on queue length
    3. Crowd Level    — LOW / MEDIUM / HIGH / CRITICAL classification
    4. Alerts         — Triggered when crowd level exceeds threshold
    5. Queue History  — Time-series data for trend analysis

The queue manager is called every frame with the current person-zone
mapping. It counts people in the Billing zone and uses configurable
thresholds to classify crowd density.

Wait Time Estimation:
    estimated_wait = queue_length × AVG_SERVICE_TIME
    This is a simplified model assuming single-server FIFO queue.
    AVG_SERVICE_TIME is configurable (default: 30 seconds).

Usage:
    queue_mgr = QueueManager(csv_logger)
    queue_mgr.update(person_zones, zone_counts)
    status = queue_mgr.get_status()
"""

import time
from datetime import datetime
from collections import deque
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class QueueManager:
    """
    Monitors queue in the Billing zone and detects overcrowding.

    Attributes:
        queue_zone:       Name of the zone used as queue ROI.
        crowd_thresholds: Dict mapping crowd level names to person counts.
        avg_service_time: Estimated seconds per customer served.
        current_length:   Current number of people in the queue.
        current_level:    Current crowd level string.
        current_wait:     Current estimated wait in seconds.
        alert_active:     Whether an alert is currently active.
        alert_message:    Current alert message text.
        history:          Deque of recent queue snapshots for trends.
        peak_length:      Maximum queue length observed in this session.
        csv_logger:       CSVLogger instance for data persistence.
        db:               DatabaseManager instance for data persistence.
        log_interval:     Minimum seconds between CSV writes.
    """

    def __init__(self, csv_logger=None, db=None, queue_zone="Billing",
                 log_interval=2.0):
        """
        Initialize the queue manager.

        Args:
            csv_logger:   CSVLogger instance. If None, CSV logging disabled.
            db:           DatabaseManager instance. If None, DB logging disabled.
            queue_zone:   Name of the zone to monitor as queue.
            log_interval: Seconds between log entries.
        """
        self.queue_zone = queue_zone
        self.crowd_thresholds = config.CROWD_THRESHOLDS
        self.avg_service_time = config.AVG_SERVICE_TIME

        # Current state
        self.current_length = 0
        self.current_level = "LOW"
        self.current_wait = 0.0
        self.alert_active = False
        self.alert_message = ""

        # History for trend analysis (last 300 snapshots)
        self.history = deque(maxlen=300)
        self.peak_length = 0
        self.total_alerts = 0

        # People currently in queue (track IDs)
        self.people_in_queue = set()

        # Per-person queue entry times for individual wait tracking
        self.queue_entry_times = {}  # {person_id: entry_timestamp}

        # CSV and DB logging
        self.csv_logger = csv_logger
        self.db = db
        self.log_interval = log_interval
        self._last_log_time = 0.0

        print(f"[QUEUE] Queue manager initialized")
        print(f"[QUEUE] Monitoring zone: {queue_zone}")
        print(f"[QUEUE] Thresholds: {self.crowd_thresholds}")
        print(f"[QUEUE] Avg service time: {self.avg_service_time}s")

    def update(self, person_zones, zone_counts):
        """
        Update queue status based on current frame data.

        Args:
            person_zones: Dict {person_id: zone_name or None} from ZoneManager.
            zone_counts:  Dict {zone_name: int} from ZoneManager.

        Returns:
            Dict with current queue status.
        """
        current_time = time.time()

        # =====================================================
        # Count people in the queue zone
        # =====================================================
        self.current_length = zone_counts.get(self.queue_zone, 0)

        # Track which people are in the queue
        new_queue_people = set()
        for person_id, zone in person_zones.items():
            if zone == self.queue_zone:
                new_queue_people.add(person_id)

                # Record queue entry time for new arrivals
                if person_id not in self.queue_entry_times:
                    self.queue_entry_times[person_id] = current_time

        # Clean up people who left the queue
        left_queue = self.people_in_queue - new_queue_people
        for pid in left_queue:
            self.queue_entry_times.pop(pid, None)

        self.people_in_queue = new_queue_people

        # Update peak
        if self.current_length > self.peak_length:
            self.peak_length = self.current_length

        # =====================================================
        # Estimate wait time
        # =====================================================
        self.current_wait = self.current_length * self.avg_service_time

        # =====================================================
        # Classify crowd level
        # =====================================================
        self.current_level = self._classify_crowd(self.current_length)

        # =====================================================
        # Check for alerts
        # =====================================================
        prev_alert = self.alert_active
        self.alert_active = self.current_level in ("HIGH", "CRITICAL")

        if self.alert_active:
            if self.current_level == "CRITICAL":
                self.alert_message = (
                    f"OVERCROWDING! {self.current_length} people in "
                    f"{self.queue_zone} — Estimated wait: "
                    f"{self._format_time(self.current_wait)}"
                )
            else:
                self.alert_message = (
                    f"High crowd density in {self.queue_zone}: "
                    f"{self.current_length} people — Wait: "
                    f"{self._format_time(self.current_wait)}"
                )

            # Count new alert triggers
            if not prev_alert:
                self.total_alerts += 1
                print(f"[QUEUE ALERT] {self.alert_message}")
        else:
            self.alert_message = ""

        # =====================================================
        # Record history snapshot
        # =====================================================
        snapshot = {
            "timestamp": current_time,
            "queue_length": self.current_length,
            "wait_estimate": self.current_wait,
            "crowd_level": self.current_level,
            "alert": self.alert_active,
        }
        self.history.append(snapshot)

        # =====================================================
        # Log to CSV/DB at controlled intervals
        # =====================================================
        if current_time - self._last_log_time >= self.log_interval:
            now_iso = datetime.now().isoformat()
            
            if self.csv_logger is not None:
                self.csv_logger.log_queue(
                    queue_length=self.current_length,
                    estimated_wait=self.current_wait,
                    crowd_level=self.current_level,
                    alert_triggered=self.alert_active,
                )
            
            if self.db is not None:
                self.db.insert_queue(
                    queue_length=self.current_length,
                    estimated_wait=self.current_wait,
                    crowd_level=self.current_level,
                    alert_triggered=int(self.alert_active)
                )
            self._last_log_time = current_time

        return self.get_status()

    def _classify_crowd(self, count):
        """
        Classify crowd density based on person count and thresholds.

        Thresholds (default):
            LOW:      0-1 people
            MEDIUM:   2-3 people
            HIGH:     4-5 people
            CRITICAL: 6+ people

        Args:
            count: Number of people in the queue zone.

        Returns:
            String: "LOW", "MEDIUM", "HIGH", or "CRITICAL".
        """
        if count >= self.crowd_thresholds.get("CRITICAL", 8):
            return "CRITICAL"
        elif count >= self.crowd_thresholds.get("HIGH", 6):
            return "HIGH"
        elif count >= self.crowd_thresholds.get("MEDIUM", 4):
            return "MEDIUM"
        else:
            return "LOW"

    def _format_time(self, seconds):
        """
        Format seconds into a human-readable time string.

        Args:
            seconds: Time in seconds.

        Returns:
            String like "2m 30s" or "45s".
        """
        if seconds >= 60:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        return f"{int(seconds)}s"

    def get_status(self):
        """
        Get the current queue status.

        Returns:
            Dict with queue_length, wait_estimate, crowd_level,
            alert_active, alert_message, peak_length.
        """
        return {
            "queue_length": self.current_length,
            "wait_estimate": round(self.current_wait, 1),
            "wait_formatted": self._format_time(self.current_wait),
            "crowd_level": self.current_level,
            "alert_active": self.alert_active,
            "alert_message": self.alert_message,
            "peak_length": self.peak_length,
            "total_alerts": self.total_alerts,
            "people_ids": list(self.people_in_queue),
        }

    def get_person_wait_time(self, person_id):
        """
        Get how long a specific person has been waiting in the queue.

        Args:
            person_id: Tracker-assigned person ID.

        Returns:
            Float seconds, or 0.0 if person not in queue.
        """
        if person_id in self.queue_entry_times:
            return time.time() - self.queue_entry_times[person_id]
        return 0.0

    def get_trend_data(self, last_n=60):
        """
        Get recent queue length history for trend plotting.

        Args:
            last_n: Number of recent snapshots to return.

        Returns:
            List of dicts with timestamp and queue_length.
        """
        recent = list(self.history)[-last_n:]
        return [{"timestamp": s["timestamp"],
                 "queue_length": s["queue_length"]}
                for s in recent]

    def get_statistics(self):
        """
        Get aggregate queue statistics for the session.

        Returns:
            Dict with peak, average, and total alert count.
        """
        if not self.history:
            return {
                "peak_queue_length": 0,
                "avg_queue_length": 0.0,
                "total_alerts": 0,
                "alert_percentage": 0.0,
            }

        lengths = [s["queue_length"] for s in self.history]
        alerts = [s["alert"] for s in self.history]

        return {
            "peak_queue_length": self.peak_length,
            "avg_queue_length": round(sum(lengths) / len(lengths), 1),
            "total_alerts": self.total_alerts,
            "alert_percentage": round(
                sum(1 for a in alerts if a) / len(alerts) * 100, 1
            ) if alerts else 0.0,
        }
