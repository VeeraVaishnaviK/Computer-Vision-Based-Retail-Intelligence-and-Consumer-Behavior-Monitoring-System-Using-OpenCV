"""
heatmap_generator.py
====================
Generates spatial heatmaps from customer movement tracking data.

Creates a visual representation of where customers spend the most
time in the store. High-traffic areas appear as warm colors (red/yellow),
while low-traffic areas appear as cool colors (blue/green).

Two modes of operation:
    1. LIVE MODE:   Accumulates centroid positions in real-time during
                    the webcam session. Generates heatmap on demand.
    2. OFFLINE MODE: Reads movement_log.csv and generates heatmap from
                     historical data.

Algorithm:
    1. Create a 2D accumulator matrix (same size as frame)
    2. For each centroid position, increment a Gaussian-weighted
       area around that point (simulates person's area of influence)
    3. Normalize the matrix to 0-255
    4. Apply OpenCV colormap (COLORMAP_JET) for visualization
    5. Optionally blend with a reference frame or zone overlay

Usage:
    # Live mode (during webcam session):
    heatmap_gen = HeatmapGenerator(640, 480)
    heatmap_gen.add_point(320, 240)  # called every frame per person
    heatmap_image = heatmap_gen.generate()

    # Offline mode (from CSV):
    heatmap_gen = HeatmapGenerator(640, 480)
    heatmap_gen.generate_from_csv("data/logs/movement_log.csv")
"""

import cv2
import numpy as np
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class HeatmapGenerator:
    """
    Generates spatial heatmaps from movement coordinates.

    Attributes:
        width:        Frame width in pixels.
        height:       Frame height in pixels.
        accumulator:  2D numpy array accumulating position weights.
        point_count:  Total number of points added.
        radius:       Gaussian spread radius for each point.
        colormap:     OpenCV colormap ID (default: COLORMAP_JET).
    """

    def __init__(self, width=None, height=None, radius=25):
        """
        Initialize the heatmap generator.

        Args:
            width:  Frame width. Default from config.
            height: Frame height. Default from config.
            radius: Gaussian spread radius in pixels. Larger values
                    create smoother, more spread-out heatmaps.
        """
        self.width = width or config.FRAME_WIDTH
        self.height = height or config.FRAME_HEIGHT
        self.radius = radius
        self.colormap = config.HEATMAP_COLORMAP  # cv2.COLORMAP_JET = 11

        # 2D accumulator — float32 for precision during accumulation
        self.accumulator = np.zeros((self.height, self.width), dtype=np.float32)
        self.point_count = 0

        # Pre-compute Gaussian kernel for efficiency
        self._kernel = self._create_gaussian_kernel(radius)

        print(f"[HEATMAP] Initialized ({self.width}x{self.height}, "
              f"radius={radius})")

    def _create_gaussian_kernel(self, radius):
        """
        Create a 2D Gaussian kernel for point spreading.

        The kernel simulates a person's "area of influence" —
        the center of their position gets the highest weight,
        with influence falling off in a bell curve pattern.

        Args:
            radius: Kernel half-size in pixels.

        Returns:
            2D numpy array (2*radius+1 × 2*radius+1).
        """
        size = 2 * radius + 1
        kernel = np.zeros((size, size), dtype=np.float32)

        for y in range(size):
            for x in range(size):
                # Distance from center
                dx = x - radius
                dy = y - radius
                dist_sq = dx * dx + dy * dy

                # Gaussian falloff: exp(-d²/2σ²), σ = radius/2
                sigma = radius / 2.0
                kernel[y, x] = np.exp(-dist_sq / (2 * sigma * sigma))

        return kernel

    def add_point(self, x, y, weight=1.0):
        """
        Add a single centroid position to the heatmap accumulator.

        Applies the Gaussian kernel centered at (x, y) to the
        accumulator matrix. Handles edge clipping automatically.

        Args:
            x:      X pixel coordinate.
            y:      Y pixel coordinate.
            weight: Multiplier for this point (default 1.0).
                    Use higher weights for stationary people.
        """
        x, y = int(x), int(y)
        r = self.radius

        # Calculate kernel placement bounds (clip to frame edges)
        # Kernel region
        kx_start = max(0, r - x)
        ky_start = max(0, r - y)
        kx_end = min(2 * r + 1, self.width - x + r)
        ky_end = min(2 * r + 1, self.height - y + r)

        # Accumulator region
        ax_start = max(0, x - r)
        ay_start = max(0, y - r)
        ax_end = min(self.width, x + r + 1)
        ay_end = min(self.height, y + r + 1)

        # Validate dimensions match
        k_h = ky_end - ky_start
        k_w = kx_end - kx_start
        a_h = ay_end - ay_start
        a_w = ax_end - ax_start

        # Use the minimum dimensions to ensure they match
        h = min(k_h, a_h)
        w = min(k_w, a_w)

        if h > 0 and w > 0:
            self.accumulator[ay_start:ay_start + h, ax_start:ax_start + w] += \
                self._kernel[ky_start:ky_start + h, kx_start:kx_start + w] * weight

        self.point_count += 1

    def add_points_batch(self, points, weight=1.0):
        """
        Add multiple points at once.

        Args:
            points: List of (x, y) tuples.
            weight: Weight multiplier for all points.
        """
        for x, y in points:
            self.add_point(x, y, weight)

    def generate(self, apply_colormap=True):
        """
        Generate the heatmap image from the accumulated data.

        Args:
            apply_colormap: If True, apply OpenCV colormap.
                            If False, return grayscale.

        Returns:
            BGR image (numpy array, uint8) — the heatmap visualization.
            Returns black image if no points have been added.
        """
        if self.point_count == 0:
            blank = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            cv2.putText(blank, "No movement data",
                        (self.width // 4, self.height // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1,
                        (128, 128, 128), 2, cv2.LINE_AA)
            return blank

        # Normalize to 0-255
        max_val = self.accumulator.max()
        if max_val > 0:
            normalized = (self.accumulator / max_val * 255).astype(np.uint8)
        else:
            normalized = np.zeros_like(self.accumulator, dtype=np.uint8)

        if apply_colormap:
            # Apply colormap (JET: blue→green→yellow→red)
            heatmap = cv2.applyColorMap(normalized, self.colormap)
        else:
            # Grayscale
            heatmap = cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR)

        return heatmap

    def generate_overlay(self, background_frame=None, alpha=0.5):
        """
        Generate a heatmap blended with a background frame.

        Creates a semi-transparent overlay where the heatmap
        is visible on top of the actual store layout / zones.

        Args:
            background_frame: BGR frame to overlay on. If None,
                              uses a black background.
            alpha:            Blend factor (0.0=only background,
                              1.0=only heatmap).

        Returns:
            BGR blended image (numpy array, uint8).
        """
        heatmap = self.generate()

        if background_frame is None:
            background = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            background[:] = (30, 30, 30)  # Dark gray background
        else:
            background = cv2.resize(background_frame,
                                    (self.width, self.height))

        # Only overlay where there's actual heatmap data
        # (avoid coloring areas with no movement)
        gray = cv2.cvtColor(heatmap, cv2.COLOR_BGR2GRAY)
        mask = gray > 5  # Threshold to ignore near-zero areas

        blended = background.copy()
        blended[mask] = cv2.addWeighted(
            heatmap, alpha, background, 1 - alpha, 0
        )[mask]

        return blended

    def generate_with_zones(self, zones=None, zone_colors=None):
        """
        Generate a heatmap with zone boundaries overlaid.

        Useful for understanding which parts of which zones
        have the most foot traffic.

        Args:
            zones:       Dict {zone_name: (x1,y1,x2,y2)}. Default from config.
            zone_colors: Dict {zone_name: (B,G,R)}. Default from config.

        Returns:
            BGR image with heatmap + zone outlines + labels.
        """
        zones = zones or config.ZONES
        zone_colors = zone_colors or config.ZONE_COLORS

        heatmap = self.generate()

        # Draw zone rectangles and labels
        for zone_name, (x1, y1, x2, y2) in zones.items():
            color = zone_colors.get(zone_name, (200, 200, 200))
            cv2.rectangle(heatmap, (x1, y1), (x2, y2), color, 2)
            cv2.putText(heatmap, zone_name,
                        (x1 + 5, y1 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (255, 255, 255), 2, cv2.LINE_AA)

        # Add title
        cv2.putText(heatmap, "CUSTOMER MOVEMENT HEATMAP",
                    (10, self.height - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (255, 255, 255), 2, cv2.LINE_AA)

        # Add color scale legend
        self._draw_color_legend(heatmap)

        return heatmap

    def _draw_color_legend(self, image):
        """
        Draw a vertical color scale legend on the right side of the image.

        Args:
            image: BGR image to draw on (modified in-place).
        """
        legend_x = self.width - 40
        legend_y_start = 20
        legend_height = 150
        legend_width = 20

        # Create gradient bar
        for i in range(legend_height):
            value = int(255 * (1 - i / legend_height))
            color_bar = np.array([[value]], dtype=np.uint8)
            color = cv2.applyColorMap(color_bar, self.colormap)[0][0]
            color = tuple(int(c) for c in color)
            cv2.line(image,
                     (legend_x, legend_y_start + i),
                     (legend_x + legend_width, legend_y_start + i),
                     color, 1)

        # Border
        cv2.rectangle(image,
                      (legend_x, legend_y_start),
                      (legend_x + legend_width, legend_y_start + legend_height),
                      (255, 255, 255), 1)

        # Labels
        cv2.putText(image, "High",
                    (legend_x - 5, legend_y_start - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                    (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(image, "Low",
                    (legend_x - 5, legend_y_start + legend_height + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                    (255, 255, 255), 1, cv2.LINE_AA)

    def save(self, filepath=None, with_zones=True):
        """
        Save the heatmap image to a file.

        Args:
            filepath:   Output path. Default: data/reports/heatmap.png
            with_zones: If True, include zone overlays.

        Returns:
            String — the saved file path.
        """
        if filepath is None:
            filepath = os.path.join(config.REPORTS_DIR, "heatmap.png")

        if with_zones:
            image = self.generate_with_zones()
        else:
            image = self.generate()

        cv2.imwrite(filepath, image)
        print(f"[HEATMAP] Saved: {filepath} ({self.point_count} points)")
        return filepath

    def generate_from_csv(self, csv_path=None, save=True):
        """
        Generate a heatmap from a movement_log.csv file.

        Reads all recorded positions and builds the heatmap
        in one batch. Useful for offline analysis.

        Args:
            csv_path: Path to movement_log.csv. Default from config.
            save:     If True, save the result to heatmap.png.

        Returns:
            BGR heatmap image (numpy array).
        """
        if csv_path is None:
            csv_path = os.path.join(config.LOGS_DIR, "movement_log.csv")

        if not os.path.exists(csv_path):
            print(f"[HEATMAP] CSV not found: {csv_path}")
            return self.generate()

        try:
            df = pd.read_csv(csv_path)
            if df.empty or 'x' not in df.columns or 'y' not in df.columns:
                print("[HEATMAP] No coordinate data in CSV")
                return self.generate()

            # Reset accumulator for clean offline generation
            self.accumulator = np.zeros((self.height, self.width),
                                        dtype=np.float32)
            self.point_count = 0

            # Add all points from CSV
            for _, row in df.iterrows():
                x = float(row['x'])
                y = float(row['y'])
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.add_point(x, y)

            print(f"[HEATMAP] Loaded {self.point_count} points from CSV")

            if save:
                self.save()

            return self.generate_with_zones()

        except Exception as e:
            print(f"[HEATMAP] Error reading CSV: {e}")
            return self.generate()

    def reset(self):
        """Reset the accumulator to zero."""
        self.accumulator = np.zeros((self.height, self.width), dtype=np.float32)
        self.point_count = 0
        print("[HEATMAP] Accumulator reset")


# =====================================================
# Standalone execution: python -m analytics.heatmap_generator
# =====================================================
if __name__ == "__main__":
    print("=" * 50)
    print("  HEATMAP GENERATOR — Offline Mode")
    print("=" * 50)
    generator = HeatmapGenerator()
    generator.generate_from_csv()
    print("Done.")
