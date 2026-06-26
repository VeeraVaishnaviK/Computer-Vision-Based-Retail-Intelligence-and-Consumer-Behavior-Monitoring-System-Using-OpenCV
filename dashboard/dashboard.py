"""
dashboard.py
============
Matplotlib-based analytics dashboard for the Retail Intelligence System.

Reads all CSV log files and generates visual analytics:
    1. visitor_trends.png   — Visitor count over time, entry/exit timeline
    2. zone_analysis.png    — Zone popularity, dwell time comparison
    3. queue_statistics.png — Queue length over time, crowd level distribution
    4. heatmap.png          — Spatial heatmap of movement (generated in Phase 6)
    5. dashboard_summary.png — Combined 4-panel overview dashboard

All charts are saved to data/reports/ and can be regenerated at any time
by running: python -m dashboard.dashboard

Usage:
    from dashboard.dashboard import RetailDashboard
    dash = RetailDashboard()
    dash.generate_all()
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend (no GUI window needed)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class RetailDashboard:
    """
    Generates analytics charts from CSV log data.

    Attributes:
        logs_dir:    Path to CSV log files.
        reports_dir: Path to save generated charts.
        visitor_df:  DataFrame from visitor_log.csv.
        movement_df: DataFrame from movement_log.csv.
        behavior_df: DataFrame from behavior_log.csv.
        queue_df:    DataFrame from queue_log.csv.
    """

    # Professional color palette
    COLORS = {
        "primary":    "#2196F3",   # Blue
        "secondary":  "#FF9800",   # Orange
        "success":    "#4CAF50",   # Green
        "danger":     "#F44336",   # Red
        "purple":     "#9C27B0",   # Purple
        "teal":       "#009688",   # Teal
        "background": "#1a1a2e",   # Dark navy
        "panel":      "#16213e",   # Slightly lighter navy
        "text":       "#e0e0e0",   # Light gray text
        "grid":       "#333355",   # Subtle grid
    }

    ZONE_COLORS = {
        "Electronics": "#FF9800",
        "Grocery":     "#4CAF50",
        "Fashion":     "#E91E63",
        "Billing":     "#00BCD4",
    }

    def __init__(self, logs_dir=None, reports_dir=None):
        """
        Initialize the dashboard.

        Args:
            logs_dir:    Path to CSV logs. Default from config.
            reports_dir: Path to save charts. Default from config.
        """
        self.logs_dir = logs_dir or config.LOGS_DIR
        self.reports_dir = reports_dir or config.REPORTS_DIR
        os.makedirs(self.reports_dir, exist_ok=True)

        # DataFrames (loaded on demand)
        self.visitor_df = None
        self.movement_df = None
        self.behavior_df = None
        self.queue_df = None

        # Set global matplotlib style
        plt.rcParams.update({
            'figure.facecolor': self.COLORS['background'],
            'axes.facecolor': self.COLORS['panel'],
            'axes.edgecolor': self.COLORS['grid'],
            'axes.labelcolor': self.COLORS['text'],
            'text.color': self.COLORS['text'],
            'xtick.color': self.COLORS['text'],
            'ytick.color': self.COLORS['text'],
            'grid.color': self.COLORS['grid'],
            'grid.alpha': 0.3,
            'font.size': 10,
            'axes.titlesize': 13,
            'axes.titleweight': 'bold',
        })

    def _load_csv(self, filename, date_columns=None):
        """
        Safely load a CSV file into a DataFrame.

        Args:
            filename:     CSV filename (not full path).
            date_columns: List of column names to parse as datetime.

        Returns:
            DataFrame, or empty DataFrame if file doesn't exist/is empty.
        """
        filepath = os.path.join(self.logs_dir, filename)
        if not os.path.exists(filepath):
            print(f"[DASHBOARD] Warning: {filename} not found")
            return pd.DataFrame()

        try:
            df = pd.read_csv(filepath)
            if df.empty:
                print(f"[DASHBOARD] Warning: {filename} is empty")
                return df

            # Parse date columns
            if date_columns:
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')

            return df
        except Exception as e:
            print(f"[DASHBOARD] Error reading {filename}: {e}")
            return pd.DataFrame()

    def load_all_data(self):
        """Load all CSV log files into DataFrames."""
        print("[DASHBOARD] Loading CSV data...")

        self.visitor_df = self._load_csv(
            "visitor_log.csv",
            date_columns=["entry_time", "exit_time"]
        )
        self.movement_df = self._load_csv(
            "movement_log.csv",
            date_columns=["timestamp"]
        )
        self.behavior_df = self._load_csv(
            "behavior_log.csv",
            date_columns=["enter_time", "exit_time"]
        )
        self.queue_df = self._load_csv(
            "queue_log.csv",
            date_columns=["timestamp"]
        )

        print(f"[DASHBOARD] Loaded: "
              f"visitors={len(self.visitor_df)}, "
              f"movement={len(self.movement_df)}, "
              f"behavior={len(self.behavior_df)}, "
              f"queue={len(self.queue_df)}")

    def generate_visitor_trends(self):
        """
        Generate visitor trends chart.

        Chart includes:
            - Cumulative visitor count over time
            - Entry/Exit event markers
            - Occupancy over time (if data available)

        Saves: visitor_trends.png
        """
        fig, axes = plt.subplots(2, 1, figsize=(12, 8),
                                 gridspec_kw={'height_ratios': [2, 1]})
        fig.suptitle("Visitor Trends Analysis", fontsize=16, fontweight='bold',
                     color='white', y=0.98)

        # --- Top chart: Cumulative entries over time ---
        ax1 = axes[0]
        if not self.visitor_df.empty and 'entry_time' in self.visitor_df.columns:
            df = self.visitor_df.dropna(subset=['entry_time']).copy()
            if not df.empty:
                df = df.sort_values('entry_time')
                df['cumulative'] = range(1, len(df) + 1)

                ax1.plot(df['entry_time'], df['cumulative'],
                         color=self.COLORS['primary'], linewidth=2,
                         marker='o', markersize=4, label='Cumulative Visitors')
                ax1.fill_between(df['entry_time'], df['cumulative'],
                                 alpha=0.15, color=self.COLORS['primary'])

                # Mark entries and exits
                entries = df[df['status'] == 'ACTIVE']
                exits = df[df['status'] == 'EXITED']

                if not entries.empty:
                    ax1.scatter(entries['entry_time'],
                                entries['cumulative'],
                                color=self.COLORS['success'], s=50,
                                zorder=5, label='Entry', marker='^')
                if not exits.empty:
                    ax1.scatter(exits['entry_time'],
                                exits['cumulative'],
                                color=self.COLORS['danger'], s=50,
                                zorder=5, label='Exit', marker='v')

        ax1.set_ylabel("Cumulative Visitors")
        ax1.set_title("Visitor Arrivals Over Time")
        ax1.legend(loc='upper left', framealpha=0.8,
                   facecolor=self.COLORS['panel'])
        ax1.grid(True, alpha=0.3)

        # --- Bottom chart: Visitor status distribution ---
        ax2 = axes[1]
        if not self.visitor_df.empty and 'status' in self.visitor_df.columns:
            status_counts = self.visitor_df['status'].value_counts()
            colors = [self.COLORS['success'] if s == 'ACTIVE'
                      else self.COLORS['danger']
                      for s in status_counts.index]
            bars = ax2.bar(status_counts.index, status_counts.values,
                           color=colors, edgecolor='white', linewidth=0.5)

            # Add value labels on bars
            for bar, val in zip(bars, status_counts.values):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                         str(val), ha='center', fontweight='bold', fontsize=12)

            # Add total visitors annotation
            total = len(self.visitor_df)
            ax2.text(0.98, 0.95, f"Total: {total}",
                     transform=ax2.transAxes, ha='right', va='top',
                     fontsize=14, fontweight='bold',
                     bbox=dict(boxstyle='round,pad=0.3',
                               facecolor=self.COLORS['primary'], alpha=0.8))
        else:
            ax2.text(0.5, 0.5, "No visitor data available",
                     ha='center', va='center', fontsize=14,
                     transform=ax2.transAxes)

        ax2.set_ylabel("Count")
        ax2.set_title("Visitor Status Distribution")
        ax2.grid(True, alpha=0.3, axis='y')

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        save_path = os.path.join(self.reports_dir, "visitor_trends.png")
        fig.savefig(save_path, dpi=150, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"[DASHBOARD] Saved: {save_path}")

    def generate_zone_analysis(self):
        """
        Generate zone analysis chart.

        Chart includes:
            - Total visits per zone (bar chart)
            - Total dwell time per zone (bar chart)
            - Dwell time distribution (box plot)
            - Zone popularity pie chart

        Saves: zone_analysis.png
        """
        fig = plt.figure(figsize=(14, 10))
        fig.suptitle("Zone Analysis", fontsize=16, fontweight='bold',
                     color='white', y=0.98)
        gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

        zone_names = list(config.ZONES.keys())
        colors = [self.ZONE_COLORS.get(z, '#888888') for z in zone_names]

        if not self.behavior_df.empty:
            # --- Top-left: Visits per zone ---
            ax1 = fig.add_subplot(gs[0, 0])
            visit_counts = self.behavior_df['zone_name'].value_counts()
            visit_vals = [visit_counts.get(z, 0) for z in zone_names]

            bars = ax1.bar(zone_names, visit_vals, color=colors,
                           edgecolor='white', linewidth=0.5)
            for bar, val in zip(bars, visit_vals):
                if val > 0:
                    ax1.text(bar.get_x() + bar.get_width()/2,
                             bar.get_height() + 0.1,
                             str(val), ha='center', fontweight='bold')
            ax1.set_title("Total Visits Per Zone")
            ax1.set_ylabel("Visit Count")
            ax1.grid(True, alpha=0.3, axis='y')

            # --- Top-right: Total dwell time per zone ---
            ax2 = fig.add_subplot(gs[0, 1])
            dwell_sums = self.behavior_df.groupby('zone_name')[
                'dwell_time_seconds'].sum()
            dwell_vals = [round(dwell_sums.get(z, 0), 1) for z in zone_names]

            bars = ax2.bar(zone_names, dwell_vals, color=colors,
                           edgecolor='white', linewidth=0.5)
            for bar, val in zip(bars, dwell_vals):
                if val > 0:
                    ax2.text(bar.get_x() + bar.get_width()/2,
                             bar.get_height() + 0.2,
                             f"{val}s", ha='center', fontweight='bold')
            ax2.set_title("Total Dwell Time Per Zone")
            ax2.set_ylabel("Seconds")
            ax2.grid(True, alpha=0.3, axis='y')

            # --- Bottom-left: Dwell time distribution ---
            ax3 = fig.add_subplot(gs[1, 0])
            zone_dwell_data = []
            zone_labels = []
            for z in zone_names:
                zdata = self.behavior_df[
                    self.behavior_df['zone_name'] == z
                ]['dwell_time_seconds'].values
                if len(zdata) > 0:
                    zone_dwell_data.append(zdata)
                    zone_labels.append(z)

            if zone_dwell_data:
                bp = ax3.boxplot(zone_dwell_data, labels=zone_labels,
                                 patch_artist=True, widths=0.6)
                for patch, color in zip(bp['boxes'],
                                        [self.ZONE_COLORS.get(z, '#888')
                                         for z in zone_labels]):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)
                for element in ['whiskers', 'caps', 'medians']:
                    for item in bp[element]:
                        item.set_color(self.COLORS['text'])
            ax3.set_title("Dwell Time Distribution")
            ax3.set_ylabel("Seconds")
            ax3.grid(True, alpha=0.3, axis='y')

            # --- Bottom-right: Zone popularity pie ---
            ax4 = fig.add_subplot(gs[1, 1])
            if sum(visit_vals) > 0:
                non_zero = [(z, v, c) for z, v, c
                            in zip(zone_names, visit_vals, colors) if v > 0]
                if non_zero:
                    labels, vals, cols = zip(*non_zero)
                    wedges, texts, autotexts = ax4.pie(
                        vals, labels=labels, colors=cols,
                        autopct='%1.1f%%', startangle=90,
                        textprops={'color': 'white', 'fontsize': 10},
                        wedgeprops={'edgecolor': 'white', 'linewidth': 1}
                    )
                    for t in autotexts:
                        t.set_fontweight('bold')
            ax4.set_title("Zone Popularity Share")

        else:
            ax = fig.add_subplot(gs[:, :])
            ax.text(0.5, 0.5, "No behavior data available.\n"
                    "Run the system and visit some zones first.",
                    ha='center', va='center', fontsize=14,
                    transform=ax.transAxes)

        save_path = os.path.join(self.reports_dir, "zone_analysis.png")
        fig.savefig(save_path, dpi=150, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"[DASHBOARD] Saved: {save_path}")

    def generate_queue_statistics(self):
        """
        Generate queue statistics chart.

        Chart includes:
            - Queue length over time (line chart)
            - Crowd level distribution (pie chart)
            - Alert timeline (scatter)
            - Summary statistics (text box)

        Saves: queue_statistics.png
        """
        fig = plt.figure(figsize=(14, 10))
        fig.suptitle("Queue & Crowd Statistics", fontsize=16,
                     fontweight='bold', color='white', y=0.98)
        gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

        if not self.queue_df.empty:
            # --- Top-left: Queue length over time ---
            ax1 = fig.add_subplot(gs[0, :])
            if 'timestamp' in self.queue_df.columns:
                df = self.queue_df.sort_values('timestamp')

                ax1.plot(df['timestamp'], df['queue_length'],
                         color=self.COLORS['primary'], linewidth=1.5,
                         label='Queue Length')
                ax1.fill_between(df['timestamp'], df['queue_length'],
                                 alpha=0.15, color=self.COLORS['primary'])

                # Highlight alerts
                alerts = df[df['alert_triggered'] == 1]
                if not alerts.empty:
                    ax1.scatter(alerts['timestamp'],
                                alerts['queue_length'],
                                color=self.COLORS['danger'], s=40,
                                zorder=5, label='Alert Triggered',
                                marker='x', linewidths=2)

                ax1.axhline(y=config.CROWD_THRESHOLDS.get("HIGH", 6),
                            color=self.COLORS['danger'], linestyle='--',
                            alpha=0.5, label='HIGH Threshold')
                ax1.axhline(y=config.CROWD_THRESHOLDS.get("MEDIUM", 4),
                            color=self.COLORS['secondary'], linestyle='--',
                            alpha=0.5, label='MEDIUM Threshold')

            ax1.set_title("Queue Length Over Time")
            ax1.set_ylabel("People in Queue")
            ax1.legend(loc='upper left', framealpha=0.8,
                       facecolor=self.COLORS['panel'])
            ax1.grid(True, alpha=0.3)

            # --- Bottom-left: Crowd level distribution ---
            ax2 = fig.add_subplot(gs[1, 0])
            if 'crowd_level' in self.queue_df.columns:
                level_counts = self.queue_df['crowd_level'].value_counts()
                level_colors = {
                    'LOW': self.COLORS['success'],
                    'MEDIUM': self.COLORS['secondary'],
                    'HIGH': self.COLORS['danger'],
                    'CRITICAL': '#8B0000',
                }
                labels = level_counts.index.tolist()
                vals = level_counts.values.tolist()
                cols = [level_colors.get(l, '#888') for l in labels]

                if vals:
                    wedges, texts, autotexts = ax2.pie(
                        vals, labels=labels, colors=cols,
                        autopct='%1.1f%%', startangle=90,
                        textprops={'color': 'white'},
                        wedgeprops={'edgecolor': 'white', 'linewidth': 1}
                    )
                    for t in autotexts:
                        t.set_fontweight('bold')
            ax2.set_title("Crowd Level Distribution")

            # --- Bottom-right: Summary statistics ---
            ax3 = fig.add_subplot(gs[1, 1])
            ax3.axis('off')

            if 'queue_length' in self.queue_df.columns:
                peak = self.queue_df['queue_length'].max()
                avg = self.queue_df['queue_length'].mean()
                total_alerts = self.queue_df['alert_triggered'].sum()
                total_snapshots = len(self.queue_df)
                alert_pct = (total_alerts / total_snapshots * 100
                             if total_snapshots > 0 else 0)

                stats_text = (
                    f"Queue Statistics Summary\n"
                    f"{'─' * 30}\n\n"
                    f"Peak Queue Length:    {peak}\n\n"
                    f"Average Queue Length: {avg:.1f}\n\n"
                    f"Total Snapshots:     {total_snapshots}\n\n"
                    f"Alert Triggers:      {int(total_alerts)}\n\n"
                    f"Alert Time:          {alert_pct:.1f}%\n\n"
                    f"Avg Wait Estimate:   "
                    f"{self.queue_df['estimated_wait_seconds'].mean():.0f}s"
                )
                ax3.text(0.1, 0.95, stats_text,
                         transform=ax3.transAxes,
                         fontsize=12, fontfamily='monospace',
                         verticalalignment='top',
                         bbox=dict(boxstyle='round,pad=0.5',
                                   facecolor=self.COLORS['panel'],
                                   edgecolor=self.COLORS['grid']))
        else:
            ax = fig.add_subplot(gs[:, :])
            ax.text(0.5, 0.5, "No queue data available.\n"
                    "Run the system with people in the Billing zone.",
                    ha='center', va='center', fontsize=14,
                    transform=ax.transAxes)

        save_path = os.path.join(self.reports_dir, "queue_statistics.png")
        fig.savefig(save_path, dpi=150, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"[DASHBOARD] Saved: {save_path}")

    def generate_summary_dashboard(self):
        """
        Generate a combined 4-panel summary dashboard.

        Combines key metrics from all modules into one image:
            - Top-left:     Visitor summary stats
            - Top-right:    Zone visits bar chart
            - Bottom-left:  Queue length timeline
            - Bottom-right: Movement heatmap placeholder / stats

        Saves: dashboard_summary.png
        """
        fig = plt.figure(figsize=(16, 10))
        fig.suptitle("RETAIL INTELLIGENCE — Dashboard Summary",
                     fontsize=18, fontweight='bold', color='white', y=0.98)
        gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

        # --- Panel 1: Visitor Summary ---
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.axis('off')

        total_visitors = len(self.visitor_df) if not self.visitor_df.empty else 0
        active = len(self.visitor_df[self.visitor_df['status'] == 'ACTIVE']) \
            if not self.visitor_df.empty and 'status' in self.visitor_df.columns \
            else 0
        exited = len(self.visitor_df[self.visitor_df['status'] == 'EXITED']) \
            if not self.visitor_df.empty and 'status' in self.visitor_df.columns \
            else 0

        avg_duration = 0.0
        if not self.visitor_df.empty and 'duration_seconds' in self.visitor_df.columns:
            durations = pd.to_numeric(
                self.visitor_df['duration_seconds'], errors='coerce'
            ).dropna()
            if len(durations) > 0:
                avg_duration = durations.mean()

        summary_text = (
            f"👥  VISITOR SUMMARY\n"
            f"{'─' * 28}\n\n"
            f"Total Visitors:     {total_visitors}\n\n"
            f"Currently Active:   {active}\n\n"
            f"Exited:             {exited}\n\n"
            f"Avg Stay Duration:  {avg_duration:.1f}s\n\n"
            f"Occupancy:          {active}"
        )
        ax1.text(0.1, 0.95, summary_text, transform=ax1.transAxes,
                 fontsize=13, fontfamily='monospace', va='top',
                 bbox=dict(boxstyle='round,pad=0.5',
                           facecolor=self.COLORS['panel'],
                           edgecolor=self.COLORS['primary'],
                           linewidth=2))
        ax1.set_title("Visitor Overview", pad=15)

        # --- Panel 2: Zone Visits ---
        ax2 = fig.add_subplot(gs[0, 1])
        zone_names = list(config.ZONES.keys())
        colors = [self.ZONE_COLORS.get(z, '#888') for z in zone_names]

        if not self.behavior_df.empty:
            visit_counts = self.behavior_df['zone_name'].value_counts()
            vals = [visit_counts.get(z, 0) for z in zone_names]
            bars = ax2.barh(zone_names, vals, color=colors,
                            edgecolor='white', linewidth=0.5, height=0.6)
            for bar, val in zip(bars, vals):
                if val > 0:
                    ax2.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                             str(val), va='center', fontweight='bold', fontsize=12)
        else:
            ax2.text(0.5, 0.5, "No zone data", ha='center', va='center',
                     transform=ax2.transAxes, fontsize=12)
        ax2.set_title("Zone Visit Counts")
        ax2.set_xlabel("Visits")
        ax2.grid(True, alpha=0.3, axis='x')

        # --- Panel 3: Queue Timeline ---
        ax3 = fig.add_subplot(gs[1, 0])
        if not self.queue_df.empty and 'timestamp' in self.queue_df.columns:
            df = self.queue_df.sort_values('timestamp')
            ax3.plot(df['timestamp'], df['queue_length'],
                     color=self.COLORS['primary'], linewidth=1.5)
            ax3.fill_between(df['timestamp'], df['queue_length'],
                             alpha=0.15, color=self.COLORS['primary'])
            ax3.axhline(y=config.CROWD_THRESHOLDS.get("HIGH", 6),
                        color=self.COLORS['danger'], linestyle='--', alpha=0.5)
        else:
            ax3.text(0.5, 0.5, "No queue data", ha='center', va='center',
                     transform=ax3.transAxes, fontsize=12)
        ax3.set_title("Queue Length Timeline")
        ax3.set_ylabel("People")
        ax3.grid(True, alpha=0.3)

        # --- Panel 4: Movement Summary ---
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.axis('off')

        total_points = len(self.movement_df) if not self.movement_df.empty else 0
        avg_speed = 0.0
        if not self.movement_df.empty and 'speed' in self.movement_df.columns:
            speeds = pd.to_numeric(
                self.movement_df['speed'], errors='coerce'
            ).dropna()
            if len(speeds) > 0:
                avg_speed = speeds.mean()

        unique_tracks = 0
        if not self.movement_df.empty and 'track_id' in self.movement_df.columns:
            unique_tracks = self.movement_df['track_id'].nunique()

        queue_peak = 0
        queue_alerts = 0
        if not self.queue_df.empty:
            if 'queue_length' in self.queue_df.columns:
                queue_peak = int(self.queue_df['queue_length'].max())
            if 'alert_triggered' in self.queue_df.columns:
                queue_alerts = int(self.queue_df['alert_triggered'].sum())

        mvmt_text = (
            f"📊  ANALYTICS SUMMARY\n"
            f"{'─' * 28}\n\n"
            f"Movement Points:    {total_points}\n\n"
            f"Unique Tracks:      {unique_tracks}\n\n"
            f"Avg Speed:          {avg_speed:.1f} px/s\n\n"
            f"Peak Queue:         {queue_peak}\n\n"
            f"Queue Alerts:       {queue_alerts}"
        )
        ax4.text(0.1, 0.95, mvmt_text, transform=ax4.transAxes,
                 fontsize=13, fontfamily='monospace', va='top',
                 bbox=dict(boxstyle='round,pad=0.5',
                           facecolor=self.COLORS['panel'],
                           edgecolor=self.COLORS['teal'],
                           linewidth=2))
        ax4.set_title("Analytics Overview", pad=15)

        save_path = os.path.join(self.reports_dir, "dashboard_summary.png")
        fig.savefig(save_path, dpi=150, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"[DASHBOARD] Saved: {save_path}")

    def generate_all(self):
        """
        Generate all dashboard charts.

        Loads data from CSVs and generates:
            1. visitor_trends.png
            2. zone_analysis.png
            3. queue_statistics.png
            4. dashboard_summary.png
        """
        print()
        print("=" * 50)
        print("  GENERATING DASHBOARD")
        print("=" * 50)

        self.load_all_data()

        self.generate_visitor_trends()
        self.generate_zone_analysis()
        self.generate_queue_statistics()
        self.generate_summary_dashboard()

        print()
        print(f"  All charts saved to: {self.reports_dir}")
        print("=" * 50)
        print()

    def get_summary_stats(self):
        """
        Get summary statistics as a dictionary (for programmatic use).

        Returns:
            Dict with total_visitors, avg_duration, zone_visits, etc.
        """
        if self.visitor_df is None:
            self.load_all_data()

        stats = {
            "total_visitors": len(self.visitor_df)
            if not self.visitor_df.empty else 0,
            "total_movement_points": len(self.movement_df)
            if not self.movement_df.empty else 0,
            "total_behavior_events": len(self.behavior_df)
            if not self.behavior_df.empty else 0,
            "total_queue_snapshots": len(self.queue_df)
            if not self.queue_df.empty else 0,
        }
        return stats


# =====================================================
# Standalone execution: python -m dashboard.dashboard
# =====================================================
if __name__ == "__main__":
    dashboard = RetailDashboard()
    dashboard.generate_all()
