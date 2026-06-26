"""
zone_manager.py
===============
Manages virtual store zones and detects person-zone interactions.

The webcam frame is divided into 4 virtual retail zones:
    - Zone A: Electronics  (top-left)
    - Zone B: Grocery      (top-right)
    - Zone C: Fashion      (bottom-left)
    - Zone D: Billing      (bottom-right)

Each zone is a rectangular region defined by (x1, y1, x2, y2).
The ZoneManager checks every tracked person's centroid against
all zones each frame and reports which zone each person is in.

Usage:
    zone_manager = ZoneManager(zones_dict)
    zone_map = zone_manager.get_person_zones(tracked_objects)
    # zone_map = {person_id: "Electronics", ...}
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.math_utils import point_in_rect


class ZoneManager:
    """
    Manages virtual store zones and person-zone membership.

    Attributes:
        zones:        Dict {zone_name: (x1, y1, x2, y2)} — zone definitions.
        zone_colors:  Dict {zone_name: (B, G, R)} — display colors.
        person_zones: Dict {person_id: zone_name or None} — current zone per person.
        zone_counts:  Dict {zone_name: int} — current people count per zone.
    """

    def __init__(self, zones=None, zone_colors=None):
        """
        Initialize the zone manager.

        Args:
            zones:       Dict of zone definitions. Default from config.
            zone_colors: Dict of zone colors. Default from config.
        """
        self.zones = zones or config.ZONES
        self.zone_colors = zone_colors or config.ZONE_COLORS
        self.person_zones = {}    # {person_id: zone_name or None}
        self.zone_counts = {name: 0 for name in self.zones}

        print(f"[ZONES] Initialized {len(self.zones)} zones:")
        for name, coords in self.zones.items():
            print(f"[ZONES]   {name}: {coords}")

    def get_person_zones(self, tracked_objects):
        """
        Determine which zone each tracked person is currently in.

        Checks each person's centroid against all zone rectangles
        using point-in-rectangle tests.

        Args:
            tracked_objects: OrderedDict {person_id: (cx, cy)} from tracker.

        Returns:
            Dict {person_id: zone_name} for persons inside a zone.
            Persons not in any zone are mapped to None.
        """
        self.person_zones = {}
        self.zone_counts = {name: 0 for name in self.zones}

        for person_id, centroid in tracked_objects.items():
            zone_name = self._find_zone(centroid)
            self.person_zones[person_id] = zone_name

            if zone_name is not None:
                self.zone_counts[zone_name] += 1

        return self.person_zones

    def _find_zone(self, centroid):
        """
        Find which zone a centroid point belongs to.

        Args:
            centroid: Tuple (cx, cy).

        Returns:
            String zone name, or None if not in any zone.
        """
        for zone_name, rect in self.zones.items():
            if point_in_rect(centroid, rect):
                return zone_name
        return None

    def get_zone_counts(self):
        """
        Get the current number of people in each zone.

        Returns:
            Dict {zone_name: count}.
        """
        return self.zone_counts.copy()

    def get_zone_names(self):
        """
        Get the list of zone names.

        Returns:
            List of zone name strings.
        """
        return list(self.zones.keys())

    def get_zone_rect(self, zone_name):
        """
        Get the rectangle coordinates for a specific zone.

        Args:
            zone_name: Name of the zone.

        Returns:
            Tuple (x1, y1, x2, y2) or None if zone not found.
        """
        return self.zones.get(zone_name, None)

    def get_zone_color(self, zone_name):
        """
        Get the display color for a specific zone.

        Args:
            zone_name: Name of the zone.

        Returns:
            Tuple (B, G, R) or (200, 200, 200) as default.
        """
        return self.zone_colors.get(zone_name, (200, 200, 200))
