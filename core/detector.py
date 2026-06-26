"""
detector.py
============
Person detection module using YOLOv4-tiny (primary) and HOG+SVM (fallback).

Architecture:
    - Primary:  YOLOv4-tiny loaded via cv2.dnn.readNetFromDarknet()
                This is still 100% OpenCV — uses OpenCV's built-in DNN module.
                ~23MB model, runs at 15-25 FPS on CPU.

    - Fallback: OpenCV HOG descriptor with default people detector.
                Pure classical CV. Lower accuracy but zero external files.

The detector filters all YOLO detections to only return 'person' class
(COCO class ID 0), applies Non-Maximum Suppression (NMS) to remove
duplicate overlapping boxes, and returns clean bounding boxes.

Usage:
    detector = PersonDetector(backend="yolo")
    detections = detector.detect(frame)
    # detections = [(x, y, w, h, confidence), ...]
"""

import cv2
import numpy as np
import os
import sys

# Add project root to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class PersonDetector:
    """
    Detects people in video frames using YOLOv4-tiny or HOG.

    Attributes:
        backend:    "yolo" or "hog" — which detector to use.
        net:        cv2.dnn.Net object (YOLO) or None (HOG).
        hog:        cv2.HOGDescriptor object (HOG) or None (YOLO).
        conf_thresh: Minimum confidence to accept a detection.
        nms_thresh:  NMS threshold for suppressing overlapping boxes.
    """

    def __init__(self, backend="yolo"):
        """
        Initialize the person detector.

        Args:
            backend: "yolo" for YOLOv4-tiny (recommended)
                     "hog" for classical HOG+SVM (fallback)

        Raises:
            FileNotFoundError: If YOLO model files are missing.
        """
        self.backend = backend
        self.net = None
        self.hog = None
        self.output_layers = None
        self.conf_thresh = config.CONFIDENCE_THRESHOLD
        self.nms_thresh = config.NMS_THRESHOLD

        if backend == "yolo":
            self._load_yolo()
        else:
            self._load_hog()

        print(f"[DETECTOR] Initialized with backend: {backend}")

    def _load_yolo(self):
        """
        Load YOLOv4-tiny model using OpenCV's DNN module.

        Reads the .cfg (architecture) and .weights (trained parameters)
        files. Sets the preferable backend to CPU (no GPU required).

        Raises:
            FileNotFoundError: If cfg or weights file is missing.
        """
        cfg_path = config.YOLO_CFG
        weights_path = config.YOLO_WEIGHTS

        # Check that model files exist
        if not os.path.exists(cfg_path):
            print(f"[ERROR] YOLO config not found: {cfg_path}")
            print("        Run 'python download_models.py' to download.")
            print("        Falling back to HOG detector...")
            self.backend = "hog"
            self._load_hog()
            return

        if not os.path.exists(weights_path):
            print(f"[ERROR] YOLO weights not found: {weights_path}")
            print("        Run 'python download_models.py' to download.")
            print("        Falling back to HOG detector...")
            self.backend = "hog"
            self._load_hog()
            return

        # Load network
        self.net = cv2.dnn.readNetFromDarknet(cfg_path, weights_path)

        # Use CPU backend (works everywhere, no GPU needed)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        # Get output layer names
        layer_names = self.net.getLayerNames()
        unconnected = self.net.getUnconnectedOutLayers()

        # Handle both OpenCV 4.x formats (flat array or nested array)
        if len(unconnected.shape) == 1:
            self.output_layers = [layer_names[i - 1] for i in unconnected]
        else:
            self.output_layers = [layer_names[i[0] - 1]
                                  for i in unconnected]

        print(f"[DETECTOR] YOLOv4-tiny loaded successfully")
        print(f"[DETECTOR] Output layers: {self.output_layers}")

    def _load_hog(self):
        """
        Load the HOG (Histogram of Oriented Gradients) people detector.

        Uses OpenCV's pre-trained SVM classifier for pedestrian detection.
        This is pure classical computer vision — no neural networks.

        Limitations:
        - Higher false positive rate (~30-40%)
        - Struggles with partial occlusion
        - Slower than YOLO for multi-person scenes
        """
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        print("[DETECTOR] HOG+SVM people detector loaded (fallback mode)")

    def detect(self, frame):
        """
        Detect all people in a frame.

        Dispatches to the appropriate backend (YOLO or HOG),
        applies confidence filtering and NMS, and returns
        clean bounding boxes.

        Args:
            frame: BGR frame (numpy array), expected 640x480.

        Returns:
            List of tuples: [(x, y, w, h, confidence), ...]
            where (x, y) is the top-left corner, (w, h) is width/height,
            and confidence is 0.0-1.0.
            Returns empty list if no people detected.
        """
        if self.backend == "yolo" and self.net is not None:
            return self._detect_yolo(frame)
        else:
            return self._detect_hog(frame)

    def _detect_yolo(self, frame):
        """
        Run YOLOv4-tiny detection on a frame.

        Pipeline:
            1. Convert frame to blob (416x416, normalized)
            2. Forward pass through network
            3. Filter detections: keep only 'person' class
            4. Apply confidence threshold
            5. Apply Non-Maximum Suppression (NMS)
            6. Return final bounding boxes

        Args:
            frame: BGR frame (numpy array).

        Returns:
            List of (x, y, w, h, confidence) tuples.
        """
        height, width = frame.shape[:2]

        # Step 1: Create blob — resize to 416x416, normalize to 0-1
        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=1 / 255.0,
            size=config.INPUT_SIZE,
            swapRB=True,    # BGR to RGB
            crop=False
        )

        # Step 2: Forward pass
        self.net.setInput(blob)
        outputs = self.net.forward(self.output_layers)

        # Step 3-4: Filter detections
        boxes = []
        confidences = []

        for output in outputs:
            for detection in output:
                # detection format: [cx, cy, w, h, obj_conf, class1, class2, ...]
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = float(scores[class_id])

                # Only keep 'person' class with sufficient confidence
                if class_id == config.PERSON_CLASS_ID and \
                   confidence > self.conf_thresh:

                    # YOLO outputs center coordinates normalized to 0-1
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)

                    # Convert center coords to top-left corner
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    # Clamp to frame boundaries
                    x = max(0, x)
                    y = max(0, y)
                    w = min(w, width - x)
                    h = min(h, height - y)

                    boxes.append([x, y, w, h])
                    confidences.append(confidence)

        # Step 5: Non-Maximum Suppression
        detections = []
        if len(boxes) > 0:
            indices = cv2.dnn.NMSBoxes(
                boxes, confidences,
                self.conf_thresh,
                self.nms_thresh
            )

            # Handle both OpenCV 4.x formats
            if len(indices) > 0:
                # Flatten if necessary
                if isinstance(indices, np.ndarray):
                    indices = indices.flatten()

                for i in indices:
                    x, y, w, h = boxes[i]
                    conf = confidences[i]
                    detections.append((x, y, w, h, conf))

        return detections

    def _detect_hog(self, frame):
        """
        Run HOG+SVM pedestrian detection on a frame.

        The HOG detector uses a sliding window approach with
        Histogram of Oriented Gradients features classified
        by a pre-trained Support Vector Machine.

        Args:
            frame: BGR frame (numpy array).

        Returns:
            List of (x, y, w, h, confidence) tuples.
        """
        # detectMultiScale returns (rects, weights)
        # winStride and padding affect speed vs accuracy
        rects, weights = self.hog.detectMultiScale(
            frame,
            winStride=(8, 8),
            padding=(4, 4),
            scale=1.05
        )

        detections = []
        for i, (x, y, w, h) in enumerate(rects):
            confidence = float(weights[i]) if i < len(weights) else 0.5
            # HOG weights are not true probabilities, normalize roughly
            confidence = min(1.0, max(0.0, confidence / 2.0))
            if confidence > self.conf_thresh:
                detections.append((int(x), int(y), int(w), int(h), confidence))

        return detections

    def get_backend_info(self):
        """
        Return information about the current detection backend.

        Returns:
            Dict with backend name, model size, and expected FPS.
        """
        if self.backend == "yolo":
            return {
                "backend": "YOLOv4-tiny (OpenCV DNN)",
                "model_size": "~23 MB",
                "expected_fps": "15-25 FPS (CPU)",
                "accuracy": "High (COCO-trained)",
            }
        else:
            return {
                "backend": "HOG+SVM (Classical CV)",
                "model_size": "Built-in (~3 MB)",
                "expected_fps": "5-15 FPS",
                "accuracy": "Moderate (higher false positives)",
            }
