"""
shared_state.py
===============
Provides a thread-safe mechanism to share state (like video frames) 
between the main OpenCV thread and the Flask web server thread.
"""

import threading

class SharedState:
    _lock = threading.Lock()
    _latest_frame = None

    @classmethod
    def set_frame(cls, frame):
        """Safely set the latest processed OpenCV frame."""
        with cls._lock:
            if frame is not None:
                # We copy the frame so the web server has a stable snapshot
                cls._latest_frame = frame.copy()

    @classmethod
    def get_frame(cls):
        """Safely retrieve the latest frame."""
        with cls._lock:
            return cls._latest_frame
