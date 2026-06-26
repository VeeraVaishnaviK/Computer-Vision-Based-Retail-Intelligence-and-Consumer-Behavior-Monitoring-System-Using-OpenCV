"""
counter.py
==========
Entry/Exit people counter using virtual line crossing detection.

Two horizontal lines are drawn across the frame:
    - ENTRY LINE (y = 400): Person crossing downward → counted as ENTRY
    - EXIT LINE  (y = 420): Person crossing upward   → counted as EXIT

Algorithm:
    For each tracked person (by ID), we store their previous centroid Y.
    Each frame, we check if the centroid crossed either line by comparing
    the previous Y with the current Y:

    - Entry:  previous_y < entry_line AND current_y >= entry_line → ENTRY
    - Exit:   previous_y > exit_line AND current_y <= exit_line  → EXIT

    The direction of crossing determines entry vs exit:
    - Downward crossing of entry line = entering the store
    - Upward crossing of exit line = leaving the store

Occupancy:
    occupancy = total_entries - total_exits (clamped to >= 0)

Usage:
    counter = PeopleCounter()
    counter.update(tracked_objects)  # called every frame
    entries, exits, occupancy = counter.get_counts()
"""

from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class PeopleCounter:
    """
    Counts people entering and exiting by detecting line crossings.

    Attributes:
        entry_line_y:     Y-coordinate of the entry line.
        exit_line_y:      Y-coordinate of the exit line.
        total_entries:    Cumulative entry count.
        total_exits:      Cumulative exit count.
        previous_centroids: Dict {id: (cx, cy)} from the previous frame.
        counted_ids:      Dict {id: set} tracking which lines each ID crossed
                          (prevents double-counting).
        entry_log:        List of entry events with timestamps.
        exit_log:         List of exit events with timestamps.
    """

    def __init__(self, entry_line_y=None, exit_line_y=None):
        """
        Initialize the people counter.

        Args:
            entry_line_y: Y-coordinate of the entry line.
                          Default from config.ENTRY_LINE_Y.
            exit_line_y:  Y-coordinate of the exit line.
                          Default from config.EXIT_LINE_Y.
        """
        self.entry_line_y = entry_line_y or config.ENTRY_LINE_Y
        self.exit_line_y = exit_line_y or config.EXIT_LINE_Y

        self.total_entries = 0
        self.total_exits = 0
        self.previous_centroids = {}  # {id: (cx, cy)}
        self.counted_ids = {}         # {id: {"entry", "exit"}}

        # Event logs for CSV/DB storage
        self.entry_log = []   # [(id, timestamp), ...]
        self.exit_log = []    # [(id, timestamp), ...]

        # Track entry times for duration calculation
        self.entry_times = {}  # {id: datetime}

        print(f"[COUNTER] Initialized")
        print(f"[COUNTER] Entry line Y={self.entry_line_y}, "
              f"Exit line Y={self.exit_line_y}")

    def update(self, tracked_objects):
        """
        Check all tracked objects for line crossings.

        Must be called every frame with the current tracked objects
        from the CentroidTracker.

        Args:
            tracked_objects: OrderedDict {id: (cx, cy)} from tracker.

        Returns:
            Tuple (new_entries, new_exits) — lists of IDs that just
            crossed a line in this frame. Empty lists if no crossings.
        """
        new_entries = []
        new_exits = []

        for object_id, centroid in tracked_objects.items():
            cx, cy = centroid

            # Initialize tracking for new IDs
            if object_id not in self.counted_ids:
                self.counted_ids[object_id] = set()

            # Need a previous position to detect crossing
            if object_id in self.previous_centroids:
                prev_cx, prev_cy = self.previous_centroids[object_id]

                # =============================================
                # CHECK ENTRY: crossing downward past entry line
                # =============================================
                if ("entry" not in self.counted_ids[object_id] and
                        prev_cy < self.entry_line_y and
                        cy >= self.entry_line_y):

                    self.total_entries += 1
                    self.counted_ids[object_id].add("entry")

                    now = datetime.now()
                    self.entry_times[object_id] = now
                    self.entry_log.append({
                        "track_id": object_id,
                        "timestamp": now.isoformat(),
                        "type": "entry",
                    })
                    new_entries.append(object_id)
                    print(f"[COUNTER] ENTRY detected — ID:{object_id} "
                          f"at {now.strftime('%H:%M:%S')}")

                # =============================================
                # CHECK EXIT: crossing upward past exit line
                # =============================================
                if ("exit" not in self.counted_ids[object_id] and
                        prev_cy > self.exit_line_y and
                        cy <= self.exit_line_y):

                    self.total_exits += 1
                    self.counted_ids[object_id].add("exit")

                    now = datetime.now()
                    duration = None
                    if object_id in self.entry_times:
                        duration = (now - self.entry_times[object_id]) \
                            .total_seconds()

                    self.exit_log.append({
                        "track_id": object_id,
                        "timestamp": now.isoformat(),
                        "type": "exit",
                        "duration": duration,
                    })
                    new_exits.append(object_id)
                    print(f"[COUNTER] EXIT detected — ID:{object_id} "
                          f"at {now.strftime('%H:%M:%S')} "
                          f"(duration: {duration:.1f}s)"
                          if duration else
                          f"[COUNTER] EXIT detected — ID:{object_id}")

            # Store current centroid for next frame comparison
            self.previous_centroids[object_id] = centroid

        # Clean up old IDs that are no longer tracked
        active_ids = set(tracked_objects.keys())
        stale_ids = set(self.previous_centroids.keys()) - active_ids
        for stale_id in stale_ids:
            self.previous_centroids.pop(stale_id, None)

        return new_entries, new_exits

    def get_counts(self):
        """
        Get current counting statistics.

        Returns:
            Tuple (entries, exits, occupancy) where:
            - entries:   Total number of people who entered.
            - exits:     Total number of people who exited.
            - occupancy: Current estimated occupancy (entries - exits, >= 0).
        """
        occupancy = max(0, self.total_entries - self.total_exits)
        return self.total_entries, self.total_exits, occupancy

    def get_entry_log(self):
        """
        Get the list of entry events.

        Returns:
            List of dicts: [{"track_id": int, "timestamp": str, "type": str}]
        """
        return self.entry_log

    def get_exit_log(self):
        """
        Get the list of exit events with durations.

        Returns:
            List of dicts with track_id, timestamp, type, and duration.
        """
        return self.exit_log

    def get_entry_time(self, object_id):
        """
        Get the entry time for a specific person.

        Args:
            object_id: Tracker-assigned ID.

        Returns:
            datetime object or None if not found.
        """
        return self.entry_times.get(object_id, None)

    def reset(self):
        """Reset all counters and logs to zero."""
        self.total_entries = 0
        self.total_exits = 0
        self.previous_centroids.clear()
        self.counted_ids.clear()
        self.entry_log.clear()
        self.exit_log.clear()
        self.entry_times.clear()
        print("[COUNTER] All counters reset to zero")
