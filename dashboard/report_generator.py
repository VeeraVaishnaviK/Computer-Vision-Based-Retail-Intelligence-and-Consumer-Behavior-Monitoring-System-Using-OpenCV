"""
report_generator.py
===================
Generates a text-based summary report from CSV analytics data.

Creates a formatted report with:
    - Session overview (timestamps, duration)
    - Visitor statistics
    - Zone analysis
    - Queue metrics
    - Movement summary
    - Recommendations based on data

The report is saved as a text file and also printed to console.

Usage:
    from dashboard.report_generator import ReportGenerator
    report = ReportGenerator()
    report.generate()
"""

import os
import sys
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class ReportGenerator:
    """
    Generates text-based analytics reports from CSV data.

    Attributes:
        logs_dir:    Path to CSV log files.
        reports_dir: Path to save the report.
    """

    def __init__(self, logs_dir=None, reports_dir=None):
        """
        Initialize the report generator.

        Args:
            logs_dir:    Path to CSV logs. Default from config.
            reports_dir: Path to save report. Default from config.
        """
        self.logs_dir = logs_dir or config.LOGS_DIR
        self.reports_dir = reports_dir or config.REPORTS_DIR
        os.makedirs(self.reports_dir, exist_ok=True)

    def _load_csv(self, filename):
        """Safely load a CSV file."""
        filepath = os.path.join(self.logs_dir, filename)
        if os.path.exists(filepath):
            try:
                return pd.read_csv(filepath)
            except Exception:
                return pd.DataFrame()
        return pd.DataFrame()

    def generate(self, print_to_console=True):
        """
        Generate the full analytics report.

        Args:
            print_to_console: If True, also print the report.

        Returns:
            String — the complete report text.
        """
        visitor_df = self._load_csv("visitor_log.csv")
        movement_df = self._load_csv("movement_log.csv")
        behavior_df = self._load_csv("behavior_log.csv")
        queue_df = self._load_csv("queue_log.csv")

        lines = []
        sep = "=" * 60

        # Header
        lines.append(sep)
        lines.append("  RETAIL INTELLIGENCE SYSTEM — ANALYTICS REPORT")
        lines.append(sep)
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # --- Visitor Statistics ---
        lines.append(f"  {'─' * 40}")
        lines.append("  VISITOR STATISTICS")
        lines.append(f"  {'─' * 40}")

        if not visitor_df.empty:
            total = len(visitor_df)
            active = len(visitor_df[visitor_df['status'] == 'ACTIVE']) \
                if 'status' in visitor_df.columns else 0
            exited = len(visitor_df[visitor_df['status'] == 'EXITED']) \
                if 'status' in visitor_df.columns else 0

            lines.append(f"  Total Visitors:       {total}")
            lines.append(f"  Currently Active:     {active}")
            lines.append(f"  Exited:               {exited}")

            if 'duration_seconds' in visitor_df.columns:
                durations = pd.to_numeric(
                    visitor_df['duration_seconds'], errors='coerce'
                ).dropna()
                if len(durations) > 0:
                    lines.append(f"  Avg Stay Duration:    {durations.mean():.1f}s")
                    lines.append(f"  Max Stay Duration:    {durations.max():.1f}s")
                    lines.append(f"  Min Stay Duration:    {durations.min():.1f}s")
        else:
            lines.append("  No visitor data available.")
        lines.append("")

        # --- Zone Analysis ---
        lines.append(f"  {'─' * 40}")
        lines.append("  ZONE ANALYSIS")
        lines.append(f"  {'─' * 40}")

        if not behavior_df.empty:
            lines.append(f"  {'Zone':<16} {'Visits':<10} "
                         f"{'Total Dwell':<14} {'Avg Dwell':<12}")
            lines.append(f"  {'─'*16} {'─'*10} {'─'*14} {'─'*12}")

            for zone in config.ZONES:
                zone_data = behavior_df[behavior_df['zone_name'] == zone]
                visits = len(zone_data)
                total_dwell = zone_data['dwell_time_seconds'].sum() \
                    if 'dwell_time_seconds' in zone_data.columns else 0
                avg_dwell = zone_data['dwell_time_seconds'].mean() \
                    if visits > 0 and 'dwell_time_seconds' in zone_data.columns \
                    else 0

                lines.append(f"  {zone:<16} {visits:<10} "
                             f"{total_dwell:<14.1f} {avg_dwell:<12.1f}")

            # Most popular
            most_visited = behavior_df['zone_name'].value_counts()
            if not most_visited.empty:
                lines.append("")
                lines.append(f"  Most Visited Zone:    "
                             f"{most_visited.index[0]} "
                             f"({most_visited.values[0]} visits)")
        else:
            lines.append("  No behavior data available.")
        lines.append("")

        # --- Queue Statistics ---
        lines.append(f"  {'─' * 40}")
        lines.append("  QUEUE STATISTICS")
        lines.append(f"  {'─' * 40}")

        if not queue_df.empty and 'queue_length' in queue_df.columns:
            peak = queue_df['queue_length'].max()
            avg = queue_df['queue_length'].mean()
            alerts = queue_df['alert_triggered'].sum() \
                if 'alert_triggered' in queue_df.columns else 0
            total = len(queue_df)

            lines.append(f"  Peak Queue Length:     {peak}")
            lines.append(f"  Avg Queue Length:      {avg:.1f}")
            lines.append(f"  Total Snapshots:       {total}")
            lines.append(f"  Alert Triggers:        {int(alerts)}")
            lines.append(f"  Alert Percentage:      "
                         f"{alerts/total*100:.1f}%" if total > 0 else "0%")

            if 'crowd_level' in queue_df.columns:
                lines.append("")
                lines.append("  Crowd Level Distribution:")
                for level, count in queue_df['crowd_level'].value_counts().items():
                    pct = count / total * 100
                    lines.append(f"    {level:<12} {count:>4} "
                                 f"({pct:.1f}%)")
        else:
            lines.append("  No queue data available.")
        lines.append("")

        # --- Movement Statistics ---
        lines.append(f"  {'─' * 40}")
        lines.append("  MOVEMENT STATISTICS")
        lines.append(f"  {'─' * 40}")

        if not movement_df.empty:
            total_points = len(movement_df)
            unique_tracks = movement_df['track_id'].nunique() \
                if 'track_id' in movement_df.columns else 0

            lines.append(f"  Total Data Points:    {total_points}")
            lines.append(f"  Unique Tracks:        {unique_tracks}")

            if 'speed' in movement_df.columns:
                speeds = pd.to_numeric(
                    movement_df['speed'], errors='coerce'
                ).dropna()
                if len(speeds) > 0:
                    lines.append(f"  Avg Speed:            {speeds.mean():.1f} px/s")
                    lines.append(f"  Max Speed:            {speeds.max():.1f} px/s")
        else:
            lines.append("  No movement data available.")
        lines.append("")

        # Footer
        lines.append(sep)
        lines.append("  END OF REPORT")
        lines.append(sep)

        report_text = "\n".join(lines)

        # Save to file
        report_path = os.path.join(self.reports_dir, "analytics_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"[REPORT] Saved: {report_path}")

        # Print to console
        if print_to_console:
            print(report_text)

        return report_text


if __name__ == "__main__":
    generator = ReportGenerator()
    generator.generate()
