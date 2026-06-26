"""
movement_analyzer.py
====================
Analyzes customer movement patterns from tracking data.

This module sits on top of the CentroidTracker and provides:
    1. Per-person distance calculation (total pixels travelled)
    2. Per-person speed calculation (pixels per second)
    3. Movement path storage for trail visualization
    4. Movement data logging to CSV
    5. Movement statistics (avg speed, total distance, time in store)

The movement analyzer is called every frame with the current
tracked objects and their centroids. It maintains a history
of positions per person ID and computes metrics from that history.

Usage:
    analyzer = MovementAnalyzer(csv_logger, frame_width=640, frame_height=480)
    analyzer.update(tracked_objects, current_time)
    stats = analyzer.get_person_stats(person_id)
"""

import time
import math
from datetime import datetime
from collections import defaultdict
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.math_utils import calculate_distance, normalize_point


class MovementAnalyzer:
    """
    Tracks and analyzes movement patterns for each detected person.

    Attributes:
        positions:       Dict {id: [(x, y, timestamp), ...]} — full history.
        distances:       Dict {id: float} — total distance in pixels.
        speeds:          Dict {id: float} — current speed in px/sec.
        first_seen:      Dict {id: float} — first detection time.
        last_seen:       Dict {id: float} — most recent detection time.
        frame_width:     Frame width for coordinate normalization.
        frame_height:    Frame height for coordinate normalization.
        csv_logger:      CSVLogger instance for persisting movement data.
        log_interval:    Minimum seconds between CSV log writes per person.
        _last_log_time:  Dict {id: float} — last CSV write time per person.
    """

    def __init__(self, csv_logger=None, frame_width=640, frame_height=480,
                 log_interval=0.5):
        """
        Initialize the movement analyzer.

        Args:
            csv_logger:    CSVLogger instance. If None, logging is disabled.
            frame_width:   Frame width in pixels (for normalization).
            frame_height:  Frame height in pixels (for normalization).
            log_interval:  Minimum seconds between CSV writes per person.
                           Prevents flooding the CSV at 30 FPS.
        """
        self.positions = defaultdict(list)     # {id: [(x, y, time), ...]}
        self.distances = defaultdict(float)    # {id: total_distance_px}
        self.speeds = defaultdict(float)       # {id: current_speed_px_per_sec}
        self.first_seen = {}                   # {id: timestamp}
        self.last_seen = {}                    # {id: timestamp}

        self.frame_width = frame_width
        self.frame_height = frame_height
        self.csv_logger = csv_logger
        self.log_interval = log_interval
        self._last_log_time = defaultdict(float)

        # Global statistics
        self.total_distance_all = 0.0

        print("[MOVEMENT] Movement analyzer initialized")

    def update(self, tracked_objects):
        """
        Update movement data for all currently tracked persons.

        Called every frame with the current tracked objects from
        the CentroidTracker. Computes per-frame displacement,
        accumulates total distance, and calculates instantaneous speed.

        Args:
            tracked_objects: OrderedDict {id: (cx, cy)} from tracker.
        """
        current_time = time.time()

        for object_id, centroid in tracked_objects.items():
            cx, cy = centroid

            # Record first seen time
            if object_id not in self.first_seen:
                self.first_seen[object_id] = current_time

            # Calculate displacement from last position
            if len(self.positions[object_id]) > 0:
                prev_x, prev_y, prev_time = self.positions[object_id][-1]
                prev_point = (prev_x, prev_y)
                curr_point = (cx, cy)

                # Euclidean distance in pixels
                displacement = calculate_distance(prev_point, curr_point)

                # Filter out noise: ignore tiny movements < 2 pixels
                if displacement > 2.0:
                    self.distances[object_id] += displacement
                    self.total_distance_all += displacement

                    # Calculate speed (pixels per second)
                    time_delta = current_time - prev_time
                    if time_delta > 0:
                        self.speeds[object_id] = displacement / time_delta
                    else:
                        self.speeds[object_id] = 0.0
                else:
                    # Person is stationary
                    self.speeds[object_id] = 0.0
            else:
                self.speeds[object_id] = 0.0

            # Store position with timestamp
            self.positions[object_id].append((cx, cy, current_time))
            self.last_seen[object_id] = current_time

            # Limit position history to prevent memory growth
            if len(self.positions[object_id]) > 500:
                self.positions[object_id] = self.positions[object_id][-300:]

            # Log to CSV at controlled intervals
            if self.csv_logger is not None:
                time_since_last_log = current_time - self._last_log_time[object_id]
                if time_since_last_log >= self.log_interval:
                    norm_x, norm_y = normalize_point(
                        (cx, cy), self.frame_width, self.frame_height
                    )
                    self.csv_logger.log_movement(
                        visitor_id=object_id,
                        track_id=object_id,
                        x=cx,
                        y=cy,
                        norm_x=norm_x,
                        norm_y=norm_y,
                        speed=self.speeds[object_id],
                    )
                    self._last_log_time[object_id] = current_time

        # Clean up data for deregistered persons
        active_ids = set(tracked_objects.keys())
        stored_ids = set(self.positions.keys())
        for stale_id in stored_ids - active_ids:
            # Don't delete immediately — keep for a short time for trail drawing
            if stale_id in self.last_seen:
                elapsed = current_time - self.last_seen[stale_id]
                if elapsed > 5.0:  # Keep data for 5 seconds after disappearing
                    # Keep distances and first/last seen for final stats
                    self.positions.pop(stale_id, None)
                    self.speeds.pop(stale_id, None)

    def get_person_stats(self, object_id):
        """
        Get movement statistics for a specific person.

        Args:
            object_id: Tracker-assigned person ID.

        Returns:
            Dict with distance, speed, duration, and position count.
            Returns None if person not found.
        """
        if object_id not in self.first_seen:
            return None

        current_time = time.time()
        first = self.first_seen[object_id]
        last = self.last_seen.get(object_id, current_time)
        duration = last - first

        return {
            "person_id": object_id,
            "total_distance_px": round(self.distances.get(object_id, 0.0), 1),
            "current_speed_px_s": round(self.speeds.get(object_id, 0.0), 1),
            "duration_seconds": round(duration, 1),
            "position_count": len(self.positions.get(object_id, [])),
        }

    def get_all_stats(self):
        """
        Get movement statistics for all known persons.

        Returns:
            List of stat dicts (same format as get_person_stats).
        """
        stats = []
        all_ids = set(self.first_seen.keys())
        for oid in all_ids:
            stat = self.get_person_stats(oid)
            if stat is not None:
                stats.append(stat)
        return stats

    def get_trail_points(self, object_id, max_points=50):
        """
        Get recent position history for drawing a trail.

        Args:
            object_id:  Person ID.
            max_points: Maximum number of points to return.

        Returns:
            List of (x, y) tuples (most recent last).
        """
        if object_id not in self.positions:
            return []

        points = self.positions[object_id][-max_points:]
        return [(p[0], p[1]) for p in points]

    def get_all_positions_flat(self):
        """
        Get all recorded positions as a flat list.
        Useful for heatmap generation.

        Returns:
            List of (x, y) tuples from all persons.
        """
        all_points = []
        for positions in self.positions.values():
            for px, py, _ in positions:
                all_points.append((px, py))
        return all_points

    def get_summary_metrics(self):
        """
        Get aggregate movement metrics across all persons.

        Returns:
            Dict with avg_distance, avg_speed, total_tracked, etc.
        """
        all_ids = set(self.first_seen.keys())
        if not all_ids:
            return {
                "total_persons_tracked": 0,
                "avg_distance_px": 0.0,
                "avg_speed_px_s": 0.0,
                "max_distance_px": 0.0,
                "total_distance_px": 0.0,
            }

        distances = [self.distances.get(oid, 0.0) for oid in all_ids]
        speeds = [self.speeds.get(oid, 0.0) for oid in all_ids
                  if oid in self.speeds]

        return {
            "total_persons_tracked": len(all_ids),
            "avg_distance_px": round(sum(distances) / len(distances), 1)
            if distances else 0.0,
            "avg_speed_px_s": round(sum(speeds) / len(speeds), 1)
            if speeds else 0.0,
            "max_distance_px": round(max(distances), 1) if distances else 0.0,
            "total_distance_px": round(sum(distances), 1),
        }

    def get_active_person_display_info(self, tracked_objects):
        """
        Get display-ready movement info for all currently visible persons.

        Args:
            tracked_objects: OrderedDict {id: (cx, cy)} from tracker.

        Returns:
            List of dicts with id, centroid, distance, speed for display.
        """
        info_list = []
        for object_id, centroid in tracked_objects.items():
            info = {
                "id": object_id,
                "centroid": centroid,
                "distance": round(self.distances.get(object_id, 0.0), 0),
                "speed": round(self.speeds.get(object_id, 0.0), 0),
            }
            info_list.append(info)
        return info_list
