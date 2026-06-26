"""
video_utils.py
==============
Webcam and video capture utilities.

Handles:
    - Opening the webcam or a video file
    - Setting frame dimensions
    - Preprocessing frames (resize, optional denoising)
    - Safely releasing the capture resource

This module abstracts away all OpenCV VideoCapture details
so that the rest of the system works with clean frames.
"""

import cv2
import sys


def get_video_capture(source=0, width=640, height=480):
    """
    Open a video capture source (webcam or video file).

    Args:
        source: Integer (camera index) or String (path to video file).
                Default is 0 (built-in webcam).
        width:  Desired frame width in pixels.
        height: Desired frame height in pixels.

    Returns:
        cv2.VideoCapture object, ready to read frames.

    Raises:
        SystemExit: If the capture source cannot be opened.

    Example:
        >>> cap = get_video_capture(0, 640, 480)
        >>> ret, frame = cap.read()
    """
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[ERROR] Cannot open video source: {source}")
        print("        Check your webcam connection or file path.")
        sys.exit(1)

    # Set resolution (only effective for webcams, ignored for video files)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    # Read actual resolution (may differ from requested)
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"[INFO] Video source opened: {source}")
    print(f"[INFO] Resolution: {actual_w}x{actual_h}, FPS: {actual_fps:.1f}")

    return cap


def preprocess_frame(frame, target_width=640, target_height=480):
    """
    Preprocess a raw frame for detection.

    Steps:
        1. Resize to target dimensions (if different)
        2. Apply slight Gaussian blur to reduce noise

    Args:
        frame:         Raw BGR frame from cv2.VideoCapture.
        target_width:  Desired output width.
        target_height: Desired output height.

    Returns:
        Preprocessed BGR frame (numpy array).
    """
    h, w = frame.shape[:2]

    # Resize if dimensions don't match
    if w != target_width or h != target_height:
        frame = cv2.resize(frame, (target_width, target_height),
                           interpolation=cv2.INTER_LINEAR)

    # Light Gaussian blur to reduce webcam noise (3x3 kernel)
    frame = cv2.GaussianBlur(frame, (3, 3), 0)

    return frame


def release_capture(cap):
    """
    Safely release a VideoCapture object and close all OpenCV windows.

    Args:
        cap: cv2.VideoCapture object to release.
    """
    if cap is not None and cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Video capture released. All windows closed.")
