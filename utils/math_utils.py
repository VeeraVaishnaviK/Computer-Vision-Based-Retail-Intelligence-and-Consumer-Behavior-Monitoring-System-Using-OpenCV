"""
math_utils.py
=============
Mathematical utility functions used across the system.

Functions:
    - calculate_centroid: Get center point of a bounding box
    - calculate_distance: Euclidean distance between two points
    - point_in_rect: Check if a point lies inside a rectangle
    - normalize_point: Normalize pixel coordinates to 0-1 range
"""

import math


def calculate_centroid(bbox):
    """
    Calculate the centroid (center point) of a bounding box.

    Args:
        bbox: Tuple (x, y, w, h) where:
              x, y = top-left corner coordinates
              w, h = width and height of the bounding box

    Returns:
        Tuple (cx, cy) — the center coordinates as integers.

    Example:
        >>> calculate_centroid((100, 200, 50, 80))
        (125, 240)
    """
    x, y, w, h = bbox
    cx = int(x + w / 2)
    cy = int(y + h / 2)
    return (cx, cy)


def calculate_distance(point1, point2):
    """
    Calculate the Euclidean distance between two 2D points.

    Args:
        point1: Tuple (x1, y1)
        point2: Tuple (x2, y2)

    Returns:
        Float — Euclidean distance in pixels.

    Example:
        >>> calculate_distance((0, 0), (3, 4))
        5.0
    """
    return math.sqrt(
        (point1[0] - point2[0]) ** 2 +
        (point1[1] - point2[1]) ** 2
    )


def point_in_rect(point, rect):
    """
    Check if a 2D point lies inside a rectangle.

    Args:
        point: Tuple (px, py) — the point to test.
        rect:  Tuple (x1, y1, x2, y2) — top-left and bottom-right corners.

    Returns:
        Boolean — True if the point is inside (inclusive of edges).

    Example:
        >>> point_in_rect((150, 100), (100, 50, 300, 230))
        True
        >>> point_in_rect((50, 100), (100, 50, 300, 230))
        False
    """
    px, py = point
    x1, y1, x2, y2 = rect
    return x1 <= px <= x2 and y1 <= py <= y2


def normalize_point(point, frame_width, frame_height):
    """
    Normalize pixel coordinates to the range [0.0, 1.0].

    Useful for storing coordinates that are resolution-independent,
    making heatmaps and movement data comparable across different
    camera resolutions.

    Args:
        point: Tuple (px, py) — pixel coordinates.
        frame_width:  Integer — frame width in pixels.
        frame_height: Integer — frame height in pixels.

    Returns:
        Tuple (nx, ny) — normalized coordinates as floats.

    Example:
        >>> normalize_point((320, 240), 640, 480)
        (0.5, 0.5)
    """
    px, py = point
    nx = round(px / frame_width, 4)
    ny = round(py / frame_height, 4)
    return (nx, ny)


def clamp(value, min_val, max_val):
    """
    Clamp a numeric value between a minimum and maximum.

    Args:
        value:   The value to clamp.
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.

    Returns:
        The clamped value.

    Example:
        >>> clamp(-5, 0, 100)
        0
        >>> clamp(150, 0, 100)
        100
    """
    return max(min_val, min(value, max_val))
