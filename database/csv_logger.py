"""
csv_logger.py
=============
CSV logging module for persisting real-time analytics data.

Creates and appends to CSV log files in the data/logs/ directory.
Each log type (visitors, movement, behavior, queue) has its own
file with a predefined schema.

This module is used in Phases 1-6 before SQLite integration.
After Phase 7, the database module replaces this for primary storage,
but CSV export remains available for reporting.
"""

import os
import csv
from datetime import datetime


class CSVLogger:
    """
    Manages CSV log files for all analytics modules.

    Creates log files with headers on first write, then appends
    subsequent rows. Thread-safe for single-process use.

    Attributes:
        logs_dir:   Path to the logs directory.
        files:      Dict mapping log names to file paths.
    """

    def __init__(self, logs_dir):
        """
        Initialize the CSV logger.

        Args:
            logs_dir: Path to the directory where CSV files are stored.
                      Created automatically if it doesn't exist.
        """
        self.logs_dir = logs_dir
        os.makedirs(logs_dir, exist_ok=True)

        # Define file paths
        self.files = {
            "visitor":  os.path.join(logs_dir, "visitor_log.csv"),
            "movement": os.path.join(logs_dir, "movement_log.csv"),
            "behavior": os.path.join(logs_dir, "behavior_log.csv"),
            "queue":    os.path.join(logs_dir, "queue_log.csv"),
        }

        # Define headers for each log type
        self.headers = {
            "visitor": [
                "visitor_id", "track_id", "entry_time", "exit_time",
                "duration_seconds", "status"
            ],
            "movement": [
                "visitor_id", "track_id", "x", "y",
                "normalized_x", "normalized_y", "timestamp", "speed"
            ],
            "behavior": [
                "visitor_id", "track_id", "zone_name",
                "enter_time", "exit_time", "dwell_time_seconds",
                "visit_number"
            ],
            "queue": [
                "timestamp", "queue_length", "estimated_wait_seconds",
                "crowd_level", "alert_triggered"
            ],
        }

        # Initialize files with headers if they don't exist
        self._initialize_files()

    def _initialize_files(self):
        """Create CSV files with headers if they don't already exist."""
        for log_name, filepath in self.files.items():
            if not os.path.exists(filepath):
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(self.headers[log_name])
                print(f"[CSV] Created: {filepath}")

    def log_visitor(self, track_id, entry_time, exit_time=None,
                    duration=None, status="ACTIVE"):
        """
        Log a visitor entry or exit event.

        Args:
            track_id:    Tracker-assigned ID.
            entry_time:  ISO timestamp string of entry.
            exit_time:   ISO timestamp string of exit (None if still active).
            duration:    Duration in seconds (None if still active).
            status:      "ACTIVE" or "EXITED".
        """
        row = [
            self._get_next_id("visitor"),
            track_id,
            entry_time,
            exit_time or "",
            round(duration, 2) if duration else "",
            status,
        ]
        self._append_row("visitor", row)

    def log_movement(self, visitor_id, track_id, x, y,
                     norm_x, norm_y, speed=0.0):
        """
        Log a movement data point for a tracked person.

        Args:
            visitor_id: Database visitor ID.
            track_id:   Tracker-assigned ID.
            x, y:       Pixel coordinates.
            norm_x, norm_y: Normalized coordinates (0.0 - 1.0).
            speed:      Speed in pixels/second.
        """
        row = [
            visitor_id,
            track_id,
            round(x, 1),
            round(y, 1),
            round(norm_x, 4),
            round(norm_y, 4),
            datetime.now().isoformat(),
            round(speed, 2),
        ]
        self._append_row("movement", row)

    def log_behavior(self, visitor_id, track_id, zone_name,
                     enter_time, exit_time=None, dwell_time=0.0,
                     visit_number=1):
        """
        Log a zone visit event.

        Args:
            visitor_id:   Database visitor ID.
            track_id:     Tracker-assigned ID.
            zone_name:    Name of the zone visited.
            enter_time:   ISO timestamp of zone entry.
            exit_time:    ISO timestamp of zone exit (None if still inside).
            dwell_time:   Time spent in zone in seconds.
            visit_number: Which visit this is (1st, 2nd, etc.).
        """
        row = [
            visitor_id,
            track_id,
            zone_name,
            enter_time,
            exit_time or "",
            round(dwell_time, 2),
            visit_number,
        ]
        self._append_row("behavior", row)

    def log_queue(self, queue_length, estimated_wait, crowd_level,
                  alert_triggered):
        """
        Log a queue status snapshot.

        Args:
            queue_length:     Number of people in the queue ROI.
            estimated_wait:   Estimated wait time in seconds.
            crowd_level:      "LOW", "MEDIUM", "HIGH", or "CRITICAL".
            alert_triggered:  Boolean — whether an alert was triggered.
        """
        row = [
            datetime.now().isoformat(),
            queue_length,
            round(estimated_wait, 2),
            crowd_level,
            int(alert_triggered),
        ]
        self._append_row("queue", row)

    def _append_row(self, log_name, row):
        """
        Append a single row to the specified CSV log file.

        Args:
            log_name: Key name ("visitor", "movement", "behavior", "queue").
            row:      List of values to write.
        """
        filepath = self.files[log_name]
        try:
            with open(filepath, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)
        except IOError as e:
            print(f"[CSV ERROR] Failed to write to {filepath}: {e}")

    def _get_next_id(self, log_name):
        """
        Get the next auto-increment ID by counting existing rows.

        Args:
            log_name: Key name of the log file.

        Returns:
            Integer — next available ID (1-indexed).
        """
        filepath = self.files[log_name]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                row_count = sum(1 for _ in reader) - 1  # Subtract header
                return max(1, row_count + 1)
        except (IOError, StopIteration):
            return 1

    def get_log_path(self, log_name):
        """
        Get the file path for a specific log.

        Args:
            log_name: "visitor", "movement", "behavior", or "queue".

        Returns:
            String — absolute file path.
        """
        return self.files.get(log_name, "")
