"""
drawing_utils.py
================
OpenCV drawing utilities for rendering visual overlays on frames.

All drawing functions modify the frame in-place and return it,
enabling method chaining. Colors are in BGR format (OpenCV standard).

Functions:
    - draw_bounding_box: Draw a detection box with person ID label
    - draw_entry_exit_lines: Draw the counting lines
    - draw_zones: Draw virtual store zone overlays
    - draw_info_panel: Draw the right-side metrics panel
    - draw_trail: Draw a person's movement trail
    - draw_alert: Draw a flashing alert banner
"""

import cv2
import numpy as np


def draw_bounding_box(frame, bbox, person_id, color=(0, 255, 0)):
    """
    Draw a bounding box around a detected person with their ID label.

    Args:
        frame:     BGR frame (numpy array).
        bbox:      Tuple (x, y, w, h) — top-left corner + dimensions.
        person_id: Integer — unique tracker-assigned ID.
        color:     BGR color tuple. Default: green.

    Returns:
        Modified frame.
    """
    x, y, w, h = [int(v) for v in bbox]

    # Draw rectangle
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

    # Draw ID label with background
    label = f"ID:{person_id}"
    label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    label_w, label_h = label_size

    # Label background
    cv2.rectangle(frame,
                  (x, y - label_h - 10),
                  (x + label_w + 10, y),
                  color, -1)

    # Label text
    cv2.putText(frame, label,
                (x + 5, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (0, 0, 0), 1, cv2.LINE_AA)

    return frame


def draw_centroid(frame, centroid, person_id, color=(0, 255, 0)):
    """
    Draw a small filled circle at a person's centroid position.

    Args:
        frame:     BGR frame.
        centroid:  Tuple (cx, cy).
        person_id: Integer — unique ID (used for color variation).
        color:     BGR color tuple.

    Returns:
        Modified frame.
    """
    cx, cy = [int(v) for v in centroid]
    cv2.circle(frame, (cx, cy), 5, color, -1)
    return frame


def draw_entry_exit_lines(frame, entry_y, exit_y, width,
                          entry_color=(0, 255, 0),
                          exit_color=(0, 0, 255)):
    """
    Draw horizontal entry and exit counting lines across the frame.

    Args:
        frame:       BGR frame.
        entry_y:     Y-coordinate of the entry line.
        exit_y:      Y-coordinate of the exit line.
        width:       Frame width (line spans full width).
        entry_color: BGR color for entry line. Default: green.
        exit_color:  BGR color for exit line. Default: red.

    Returns:
        Modified frame.
    """
    # Entry line (dashed effect using thick line)
    cv2.line(frame, (0, entry_y), (width, entry_y),
             entry_color, 2, cv2.LINE_AA)
    cv2.putText(frame, "ENTRY LINE",
                (10, entry_y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                entry_color, 1, cv2.LINE_AA)

    # Exit line
    cv2.line(frame, (0, exit_y), (width, exit_y),
             exit_color, 2, cv2.LINE_AA)
    cv2.putText(frame, "EXIT LINE",
                (10, exit_y + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                exit_color, 1, cv2.LINE_AA)

    return frame


def draw_zones(frame, zones, zone_colors, alpha=0.25):
    """
    Draw semi-transparent colored rectangles for virtual store zones.

    Each zone is rendered as a colored overlay with a label.

    Args:
        frame:       BGR frame.
        zones:       Dict of {zone_name: (x1, y1, x2, y2)}.
        zone_colors: Dict of {zone_name: (B, G, R)}.
        alpha:       Transparency factor (0.0 = invisible, 1.0 = opaque).

    Returns:
        Modified frame.
    """
    overlay = frame.copy()

    for zone_name, (x1, y1, x2, y2) in zones.items():
        color = zone_colors.get(zone_name, (200, 200, 200))

        # Draw filled rectangle on overlay
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)

        # Draw border on original
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Zone label
        cv2.putText(frame, zone_name,
                    (x1 + 5, y1 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (255, 255, 255), 2, cv2.LINE_AA)

    # Blend overlay with frame for transparency
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    return frame


def draw_info_panel(frame, metrics, panel_width=280):
    """
    Draw an information panel on the right side of the frame
    displaying real-time metrics.

    Args:
        frame:       BGR frame.
        metrics:     Dict of {label: value} pairs to display.
        panel_width: Width of the info panel in pixels.

    Returns:
        New wider frame with panel attached.
    """
    h, w = frame.shape[:2]

    # Create dark panel
    panel = np.zeros((h, panel_width, 3), dtype=np.uint8)
    panel[:] = (40, 40, 40)  # Dark gray background

    # Title
    cv2.putText(panel, "RETAIL INTELLIGENCE",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (0, 200, 255), 2, cv2.LINE_AA)

    # Horizontal separator
    cv2.line(panel, (10, 45), (panel_width - 10, 45),
             (100, 100, 100), 1)

    # Draw each metric
    y_offset = 75
    line_spacing = 30

    for label, value in metrics.items():
        # Label (gray)
        cv2.putText(panel, str(label),
                    (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                    (180, 180, 180), 1, cv2.LINE_AA)

        # Value (bright white, bold)
        cv2.putText(panel, str(value),
                    (10, y_offset + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (255, 255, 255), 2, cv2.LINE_AA)

        y_offset += line_spacing + 15

    # Concatenate frame and panel side by side
    combined = np.hstack([frame, panel])

    return combined


def draw_trail(frame, trail_points, color=(255, 255, 0), max_points=30):
    """
    Draw a movement trail (connected line segments) for a tracked person.

    Args:
        frame:        BGR frame.
        trail_points: List of (x, y) tuples — recent centroid positions.
        color:        BGR color for the trail. Default: cyan.
        max_points:   Maximum trail points to draw (most recent).

    Returns:
        Modified frame.
    """
    # Use only the most recent points
    points = trail_points[-max_points:]

    if len(points) < 2:
        return frame

    for i in range(1, len(points)):
        # Fade effect: older points are dimmer
        alpha = i / len(points)
        thickness = max(1, int(alpha * 3))
        pt1 = (int(points[i - 1][0]), int(points[i - 1][1]))
        pt2 = (int(points[i][0]), int(points[i][1]))

        # Scale color by alpha for fading effect
        faded_color = tuple(int(c * alpha) for c in color)
        cv2.line(frame, pt1, pt2, faded_color, thickness, cv2.LINE_AA)

    return frame


def draw_fps(frame, fps):
    """
    Draw FPS counter in the top-left corner of the frame.

    Args:
        frame: BGR frame.
        fps:   Float — current frames per second.

    Returns:
        Modified frame.
    """
    fps_text = f"FPS: {fps:.1f}"
    cv2.putText(frame, fps_text,
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (0, 255, 0), 2, cv2.LINE_AA)
    return frame


def draw_alert(frame, message, color=(0, 0, 255)):
    """
    Draw a prominent alert banner at the top of the frame.

    Args:
        frame:   BGR frame.
        message: Alert text string.
        color:   BGR color for the banner. Default: red.

    Returns:
        Modified frame.
    """
    h, w = frame.shape[:2]

    # Semi-transparent red banner
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 40), color, -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    # Alert text
    cv2.putText(frame, f"ALERT: {message}",
                (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (255, 255, 255), 2, cv2.LINE_AA)

    return frame


def draw_movement_label(frame, centroid, person_id, distance, speed):
    """
    Draw movement stats (distance and speed) below a person's centroid.

    Displays a small semi-transparent label showing:
        ID:X | Dist: 1234px | Spd: 56px/s

    Args:
        frame:     BGR frame.
        centroid:  Tuple (cx, cy) — person's center position.
        person_id: Integer — tracker-assigned ID.
        distance:  Float — total distance travelled in pixels.
        speed:     Float — current speed in pixels/second.

    Returns:
        Modified frame.
    """
    cx, cy = int(centroid[0]), int(centroid[1])

    label = f"ID:{person_id} D:{int(distance)}px S:{int(speed)}px/s"
    label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
    label_w, label_h = label_size

    # Position below the centroid
    lx = max(0, cx - label_w // 2)
    ly = cy + 20

    # Background rectangle
    overlay = frame.copy()
    cv2.rectangle(overlay,
                  (lx - 2, ly - label_h - 4),
                  (lx + label_w + 4, ly + 4),
                  (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Text
    cv2.putText(frame, label,
                (lx, ly),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                (0, 255, 255), 1, cv2.LINE_AA)

    return frame


def draw_zone_people_count(frame, zones, zone_counts, zone_colors):
    """
    Draw a person count badge inside each zone.

    Displays a small circle with the count of people currently
    inside each zone, positioned at the zone's center.

    Args:
        frame:       BGR frame.
        zones:       Dict {zone_name: (x1, y1, x2, y2)}.
        zone_counts: Dict {zone_name: int}.
        zone_colors: Dict {zone_name: (B, G, R)}.

    Returns:
        Modified frame.
    """
    for zone_name, (x1, y1, x2, y2) in zones.items():
        count = zone_counts.get(zone_name, 0)
        color = zone_colors.get(zone_name, (200, 200, 200))

        # Badge position: center-bottom of zone
        badge_x = (x1 + x2) // 2
        badge_y = y2 - 20

        # Draw badge circle
        badge_color = (0, 0, 200) if count > 0 else (100, 100, 100)
        cv2.circle(frame, (badge_x, badge_y), 16, badge_color, -1)
        cv2.circle(frame, (badge_x, badge_y), 16, (255, 255, 255), 1)

        # Draw count text
        count_text = str(count)
        text_size, _ = cv2.getTextSize(count_text, cv2.FONT_HERSHEY_SIMPLEX,
                                       0.5, 2)
        text_x = badge_x - text_size[0] // 2
        text_y = badge_y + text_size[1] // 2
        cv2.putText(frame, count_text,
                    (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 255, 255), 2, cv2.LINE_AA)

    return frame


def draw_zone_label(frame, centroid, zone_label):
    """
    Draw a person's current zone and dwell time above their centroid.

    Args:
        frame:      BGR frame.
        centroid:   Tuple (cx, cy).
        zone_label: String like "Electronics (5.2s)" or "—".

    Returns:
        Modified frame.
    """
    if zone_label == "—":
        return frame

    cx, cy = int(centroid[0]), int(centroid[1])

    label_size, _ = cv2.getTextSize(zone_label, cv2.FONT_HERSHEY_SIMPLEX,
                                    0.4, 1)
    lx = max(0, cx - label_size[0] // 2)
    ly = cy - 30

    # Background
    cv2.rectangle(frame,
                  (lx - 2, ly - label_size[1] - 4),
                  (lx + label_size[0] + 4, ly + 4),
                  (0, 100, 0), -1)

    # Text
    cv2.putText(frame, zone_label,
                (lx, ly),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                (255, 255, 255), 1, cv2.LINE_AA)

    return frame
