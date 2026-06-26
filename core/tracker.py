"""
tracker.py
==========
Centroid-based multi-object tracker.

This is a classical computer vision tracker that:
    1. Takes bounding box detections from the detector
    2. Computes centroid (center point) of each detection
    3. Matches new centroids to existing tracked objects using
       minimum Euclidean distance
    4. Assigns persistent unique IDs to each person
    5. Handles new entries (register) and disappearances (deregister)

Algorithm (per frame):
    - If no existing objects: register all detections as new
    - If existing objects exist:
        a) Build pairwise distance matrix (existing vs new centroids)
        b) Use greedy minimum-distance matching
        c) If distance < MAX_DISTANCE → update existing object
        d) Unmatched new detections → register as new objects
        e) Unmatched existing objects → increment disappeared counter
        f) If disappeared > MAX_DISAPPEARED → deregister

This approach is purely classical — no deep learning re-identification.
It works well for moderate person counts (1-15 people) typical in
retail store demos.

Usage:
    tracker = CentroidTracker(max_disappeared=40, max_distance=80)
    objects = tracker.update(detections)
    # objects = {0: (cx, cy), 1: (cx, cy), ...}
"""

import numpy as np
from collections import OrderedDict
from scipy.spatial import distance as dist
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class CentroidTracker:
    """
    Multi-object tracker using centroid distance matching.

    Attributes:
        next_object_id:  Next unique ID to assign.
        objects:         OrderedDict {id: centroid} of currently tracked objects.
        disappeared:     OrderedDict {id: count} of consecutive missed frames.
        bbox:            OrderedDict {id: (x,y,w,h)} of current bounding boxes.
        trails:          Dict {id: [(x,y), ...]} of position history.
        max_disappeared: Frames to wait before deregistering.
        max_distance:    Max pixel distance for matching.
    """

    def __init__(self, max_disappeared=None, max_distance=None):
        """
        Initialize the centroid tracker.

        Args:
            max_disappeared: Max frames an object can be missing before
                             being deregistered. Default from config.
            max_distance:    Max Euclidean distance (pixels) to consider
                             a match. Default from config.
        """
        self.next_object_id = 0
        self.objects = OrderedDict()       # {id: centroid}
        self.disappeared = OrderedDict()   # {id: missed_frame_count}
        self.bbox = OrderedDict()          # {id: (x, y, w, h)}
        self.trails = {}                   # {id: [(x, y), ...]}

        self.max_disappeared = max_disappeared or config.MAX_DISAPPEARED
        self.max_distance = max_distance or config.MAX_DISTANCE

        # Statistics
        self.total_registered = 0
        self.total_deregistered = 0

    def register(self, centroid, bbox):
        """
        Register a new tracked object with a unique ID.

        Args:
            centroid: Tuple (cx, cy) — center of the bounding box.
            bbox:     Tuple (x, y, w, h) — bounding box dimensions.

        Returns:
            Integer — the assigned unique ID.
        """
        object_id = self.next_object_id
        self.objects[object_id] = centroid
        self.disappeared[object_id] = 0
        self.bbox[object_id] = bbox
        self.trails[object_id] = [centroid]

        self.next_object_id += 1
        self.total_registered += 1

        return object_id

    def deregister(self, object_id):
        """
        Remove a tracked object (person left the frame or disappeared
        for too many frames).

        Args:
            object_id: The unique ID to remove.
        """
        del self.objects[object_id]
        del self.disappeared[object_id]
        del self.bbox[object_id]
        # Keep trails for a bit for drawing, then clean up
        if object_id in self.trails:
            del self.trails[object_id]

        self.total_deregistered += 1

    def update(self, detections):
        """
        Update tracker with new detections from the current frame.

        This is the main method called every frame. It performs the
        centroid matching algorithm and returns updated object positions.

        Args:
            detections: List of (x, y, w, h, confidence) tuples from
                       the detector. Can be empty.

        Returns:
            OrderedDict {id: centroid} of all currently tracked objects.
        """
        # =====================================================
        # CASE 1: No detections in this frame
        # =====================================================
        if len(detections) == 0:
            # Mark all existing objects as disappeared
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1

                # Deregister if disappeared for too long
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)

            return self.objects

        # =====================================================
        # Extract centroids and bounding boxes from detections
        # =====================================================
        input_centroids = []
        input_bboxes = []

        for det in detections:
            x, y, w, h = det[0], det[1], det[2], det[3]
            cx = int(x + w / 2)
            cy = int(y + h / 2)
            input_centroids.append((cx, cy))
            input_bboxes.append((x, y, w, h))

        input_centroids = np.array(input_centroids)

        # =====================================================
        # CASE 2: No existing objects — register all detections
        # =====================================================
        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                self.register(tuple(input_centroids[i]), input_bboxes[i])
            return self.objects

        # =====================================================
        # CASE 3: Match existing objects to new detections
        # =====================================================
        object_ids = list(self.objects.keys())
        object_centroids = list(self.objects.values())
        object_centroids = np.array(object_centroids)

        # Compute pairwise Euclidean distance matrix
        # Rows = existing objects, Columns = new detections
        D = dist.cdist(object_centroids, input_centroids)

        # Find minimum distance assignments
        # Sort rows by their minimum column value
        rows = D.min(axis=1).argsort()
        # For each row, find the column with minimum distance
        cols = D.argmin(axis=1)[rows]

        # Track which rows and columns have been matched
        used_rows = set()
        used_cols = set()

        for (row, col) in zip(rows, cols):
            # Skip if already used
            if row in used_rows or col in used_cols:
                continue

            # Skip if distance exceeds threshold (not a valid match)
            if D[row, col] > self.max_distance:
                continue

            # Update the matched object
            object_id = object_ids[row]
            new_centroid = tuple(input_centroids[col])

            self.objects[object_id] = new_centroid
            self.bbox[object_id] = input_bboxes[col]
            self.disappeared[object_id] = 0

            # Append to trail
            if object_id in self.trails:
                self.trails[object_id].append(new_centroid)
                # Limit trail length to prevent memory growth
                if len(self.trails[object_id]) > 200:
                    self.trails[object_id] = self.trails[object_id][-100:]

            used_rows.add(row)
            used_cols.add(col)

        # =====================================================
        # Handle unmatched existing objects (disappeared)
        # =====================================================
        unused_rows = set(range(D.shape[0])) - used_rows
        for row in unused_rows:
            object_id = object_ids[row]
            self.disappeared[object_id] += 1

            if self.disappeared[object_id] > self.max_disappeared:
                self.deregister(object_id)

        # =====================================================
        # Handle unmatched new detections (new objects)
        # =====================================================
        unused_cols = set(range(D.shape[1])) - used_cols
        for col in unused_cols:
            self.register(tuple(input_centroids[col]), input_bboxes[col])

        return self.objects

    def get_trails(self):
        """
        Get the movement trails for all tracked objects.

        Returns:
            Dict {object_id: [(x, y), ...]} of position histories.
        """
        return self.trails

    def get_bboxes(self):
        """
        Get current bounding boxes for all tracked objects.

        Returns:
            OrderedDict {object_id: (x, y, w, h)}.
        """
        return self.bbox

    def get_active_count(self):
        """
        Get the number of currently tracked objects.

        Returns:
            Integer — number of active tracked objects.
        """
        return len(self.objects)

    def get_stats(self):
        """
        Get tracker statistics.

        Returns:
            Dict with total registered, deregistered, and currently active.
        """
        return {
            "total_registered": self.total_registered,
            "total_deregistered": self.total_deregistered,
            "currently_active": len(self.objects),
        }
