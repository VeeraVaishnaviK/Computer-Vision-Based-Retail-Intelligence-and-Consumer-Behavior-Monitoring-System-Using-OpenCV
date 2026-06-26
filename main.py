"""
main.py — Retail Intelligence System (Fully Integrated)
========================================================
Single entry point for the Computer Vision-Based Retail Intelligence
and Consumer Behavior Monitoring System.

Integrates all modules:
    ✅ P1: Person detection (YOLOv4-tiny / HOG fallback)
    ✅ P2: Multi-object tracking with movement analysis
    ✅ P3: Virtual zone management + behavior analysis
    ✅ P4: Queue detection + crowd management + alerts
    ✅ P5: Analytics dashboard (Matplotlib charts + text report)
    ✅ P6: Spatial heatmap generation (Gaussian + JET colormap)
    ✅ P7: SQLite database storage (parallel with CSV)

Controls:
    q     — Quit the application
    r     — Reset all counters
    s     — Save current frame as screenshot
    h     — Toggle HOG/YOLO detector
    m     — Save current heatmap snapshot
    SPACE — Pause/Resume

Usage:
    python main.py                    # Use webcam
    python main.py --video path.mp4   # Use video file
    python main.py --hog              # Use HOG instead of YOLO
"""

import cv2
import time
import argparse
import os
import sys
from datetime import datetime

# Import project modules
import config
from core.detector import PersonDetector
from core.tracker import CentroidTracker
from core.counter import PeopleCounter
from core.movement_analyzer import MovementAnalyzer
from core.zone_manager import ZoneManager
from analytics.behavior_analyzer import BehaviorAnalyzer
from analytics.queue_manager import QueueManager
from analytics.heatmap_generator import HeatmapGenerator
from database.csv_logger import CSVLogger
from database.db_manager import DatabaseManager
from dashboard.dashboard import RetailDashboard
from dashboard.report_generator import ReportGenerator
from utils.video_utils import get_video_capture, preprocess_frame, release_capture
from utils.drawing_utils import (
    draw_bounding_box,
    draw_centroid,
    draw_entry_exit_lines,
    draw_zones,
    draw_info_panel,
    draw_trail,
    draw_fps,
    draw_movement_label,
    draw_zone_people_count,
    draw_zone_label,
    draw_alert,
)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Retail Intelligence System — Phase 4: Full Pipeline with Queue Management"
    )
    parser.add_argument(
        "--video", type=str, default=None,
        help="Path to a video file. If not provided, uses webcam."
    )
    parser.add_argument(
        "--hog", action="store_true",
        help="Use HOG+SVM detector instead of YOLOv4-tiny."
    )
    parser.add_argument(
        "--camera", type=int, default=config.CAMERA_INDEX,
        help=f"Camera index (default: {config.CAMERA_INDEX})."
    )
    parser.add_argument(
        "--no-display", action="store_true",
        help="Run without GUI display (headless mode for testing)."
    )
    return parser.parse_args()


def print_banner():
    """Print the application startup banner."""
    print()
    print("=" * 62)
    print("  RETAIL INTELLIGENCE SYSTEM")
    print("  Computer Vision-Based Consumer Behavior Monitoring")
    print("  Fully Integrated System (Phases 1-7)")
    print("=" * 62)
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Frame size: {config.FRAME_WIDTH}x{config.FRAME_HEIGHT}")
    print("=" * 62)
    print()
    print("  Controls:")
    print("    q     — Quit (generates dashboard + heatmap + report)")
    print("    r     — Reset counters")
    print("    s     — Save screenshot")
    print("    h     — Toggle HOG/YOLO detector")
    print("    m     — Save heatmap snapshot")
    print("    SPACE — Pause/Resume")
    print()


def main():
    """Main application loop."""
    args = parse_arguments()
    print_banner()

    # =========================================================
    # STEP 1: Initialize all modules
    # =========================================================
    print("[INIT] Initializing modules...")

    video_source = args.video if args.video else args.camera

    # Detector
    backend = "hog" if args.hog else config.DETECTION_BACKEND
    detector = PersonDetector(backend=backend)
    print(f"[INIT] Detector: {detector.get_backend_info()['backend']}")

    # Tracker
    tracker = CentroidTracker(
        max_disappeared=config.MAX_DISAPPEARED,
        max_distance=config.MAX_DISTANCE,
    )

    # Counter
    counter = PeopleCounter(
        entry_line_y=config.ENTRY_LINE_Y,
        exit_line_y=config.EXIT_LINE_Y,
    )

    # CSV Logger
    csv_logger = CSVLogger(config.LOGS_DIR)

    # SQLite Database (Phase 7)
    db = DatabaseManager()
    db.create_session()

    # Movement Analyzer (Phase 2)
    movement_analyzer = MovementAnalyzer(
        csv_logger=csv_logger,
        frame_width=config.FRAME_WIDTH,
        frame_height=config.FRAME_HEIGHT,
        log_interval=0.5,
    )

    # Zone Manager (Phase 3)
    zone_manager = ZoneManager()

    # Behavior Analyzer (Phase 3)
    behavior_analyzer = BehaviorAnalyzer(csv_logger=csv_logger)

    # Queue Manager (Phase 4)
    queue_manager = QueueManager(csv_logger=csv_logger, log_interval=2.0)

    # Heatmap Generator (Phase 6)
    heatmap_generator = HeatmapGenerator(
        width=config.FRAME_WIDTH,
        height=config.FRAME_HEIGHT,
        radius=25,
    )

    # Video source
    cap = get_video_capture(video_source, config.FRAME_WIDTH, config.FRAME_HEIGHT)

    print()
    print("[READY] All modules initialized. Starting main loop...")
    print("-" * 62)

    # =========================================================
    # STEP 2: Main processing loop
    # =========================================================
    frame_count = 0
    fps = 0.0
    prev_time = time.time()
    paused = False
    running = True
    logged_entries = set()
    logged_exits = set()

    while running:
        # Handle pause
        if paused:
            key = cv2.waitKey(100) & 0xFF
            if key == ord(' '):
                paused = False
                print("[INFO] Resumed")
            elif key == ord('q'):
                break
            continue

        # Read frame
        ret, frame = cap.read()
        if not ret:
            if args.video:
                print("[INFO] Video ended. Restarting...")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            else:
                print("[ERROR] Cannot read from webcam. Exiting.")
                break

        # Preprocess
        frame = preprocess_frame(frame, config.FRAME_WIDTH, config.FRAME_HEIGHT)
        frame_count += 1

        # FPS calculation
        current_time = time.time()
        elapsed = current_time - prev_time
        if elapsed > 0:
            fps = 1.0 / elapsed
        prev_time = current_time

        # =====================================================
        # PIPELINE: Detect → Track → Move → Zone → Behave → Queue → Count
        # =====================================================

        # 3. Detect
        detections = detector.detect(frame)

        # 4. Track
        tracked_objects = tracker.update(detections)
        bboxes = tracker.get_bboxes()

        # 5. Movement analysis
        movement_analyzer.update(tracked_objects)

        # 5b. Accumulate heatmap points (Phase 6)
        for person_id, centroid in tracked_objects.items():
            heatmap_generator.add_point(centroid[0], centroid[1])

        # 6. Zone mapping
        person_zones = zone_manager.get_person_zones(tracked_objects)
        zone_counts = zone_manager.get_zone_counts()

        # 7. Behavior analysis
        behavior_events = behavior_analyzer.update(person_zones, tracked_objects)
        for evt in behavior_events["entries"]:
            print(f"[BEHAVIOR] ID:{evt['person_id']} ENTERED {evt['zone']}")
        for evt in behavior_events["exits"]:
            print(f"[BEHAVIOR] ID:{evt['person_id']} LEFT {evt['zone']}")

        # 8. Queue management (Phase 4)
        queue_status = queue_manager.update(person_zones, zone_counts)

        # 9. Entry/Exit counting
        new_entries, new_exits = counter.update(tracked_objects)
        entries, exits, occupancy = counter.get_counts()

        # 10. Log visitor events
        for entry_id in new_entries:
            if entry_id not in logged_entries:
                entry_time = counter.get_entry_time(entry_id)
                ts = entry_time.isoformat() if entry_time else \
                    datetime.now().isoformat()
                csv_logger.log_visitor(
                    track_id=entry_id,
                    entry_time=ts,
                    status="ACTIVE",
                )
                db.insert_visitor(
                    track_id=entry_id, entry_time=ts, status="ACTIVE"
                )
                logged_entries.add(entry_id)

        for exit_event in counter.get_exit_log():
            eid = exit_event["track_id"]
            if eid not in logged_exits:
                et = counter.get_entry_time(eid)
                csv_logger.log_visitor(
                    track_id=eid,
                    entry_time=et.isoformat() if et else "",
                    exit_time=exit_event["timestamp"],
                    duration=exit_event.get("duration"),
                    status="EXITED",
                )
                db.update_visitor_exit(
                    track_id=eid,
                    exit_time=exit_event["timestamp"],
                    duration=exit_event.get("duration", 0),
                )
                logged_exits.add(eid)

        # =====================================================
        # STEP 11: Draw visual overlays
        # =====================================================
        if not args.no_display:
            # Draw zones
            frame = draw_zones(frame, config.ZONES, config.ZONE_COLORS)

            # Draw zone people counts
            frame = draw_zone_people_count(
                frame, config.ZONES, zone_counts, config.ZONE_COLORS
            )

            # Draw entry/exit lines
            frame = draw_entry_exit_lines(
                frame, config.ENTRY_LINE_Y, config.EXIT_LINE_Y,
                config.FRAME_WIDTH,
            )

            # Draw per-person overlays
            person_display_info = movement_analyzer.get_active_person_display_info(
                tracked_objects
            )
            for pinfo in person_display_info:
                oid = pinfo["id"]
                centroid = pinfo["centroid"]

                # Bounding box
                if oid in bboxes:
                    frame = draw_bounding_box(frame, bboxes[oid], oid)

                # Centroid
                frame = draw_centroid(frame, centroid, oid)

                # Movement trail
                trail_pts = movement_analyzer.get_trail_points(oid, 50)
                if trail_pts:
                    frame = draw_trail(frame, trail_pts)

                # Movement label
                frame = draw_movement_label(
                    frame, centroid, oid,
                    pinfo["distance"], pinfo["speed"]
                )

                # Zone label
                zone_label = behavior_analyzer.get_active_zone_label(oid)
                frame = draw_zone_label(frame, centroid, zone_label)

            # Draw alert banner if overcrowding (Phase 4)
            if queue_status["alert_active"]:
                frame = draw_alert(frame, queue_status["alert_message"])

            # FPS
            frame = draw_fps(frame, fps)

            # Build info panel metrics
            movement_summary = movement_analyzer.get_summary_metrics()
            behavior_metrics = behavior_analyzer.get_dashboard_metrics()

            metrics = {
                "Visitors": entries,
                "Entries / Exits": f"{entries} / {exits}",
                "Occupancy": occupancy,
                "Active Tracks": tracker.get_active_count(),
                "--- Queue ---": "",
                "Queue Length": queue_status["queue_length"],
                "Wait Estimate": queue_status["wait_formatted"],
                "Crowd Level": queue_status["crowd_level"],
                "Peak Queue": queue_status["peak_length"],
                "--- Zones ---": "",
                "Most Visited": f"{behavior_metrics['most_visited_zone']} "
                                f"({behavior_metrics['most_visited_count']})",
                "Most Time": f"{behavior_metrics['most_time_zone']} "
                             f"({behavior_metrics['most_time_seconds']}s)",
                "--- Movement ---": "",
                "Avg Distance": f"{movement_summary['avg_distance_px']} px",
            }

            # Info panel
            display_frame = draw_info_panel(frame, metrics)
            cv2.imshow("Retail Intelligence System", display_frame)

        # =====================================================
        # STEP 12: Handle keyboard input
        # =====================================================
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            print("\n[INFO] Quit signal received.")
            running = False
        elif key == ord('r'):
            counter.reset()
            logged_entries.clear()
            logged_exits.clear()
            print("[INFO] Counters reset.")
        elif key == ord('s'):
            screenshot_path = os.path.join(
                config.REPORTS_DIR,
                f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            cv2.imwrite(screenshot_path, frame)
            print(f"[INFO] Screenshot saved: {screenshot_path}")
        elif key == ord('h'):
            new_backend = "hog" if detector.backend == "yolo" else "yolo"
            detector = PersonDetector(backend=new_backend)
            print(f"[INFO] Switched to: {detector.backend}")
        elif key == ord('m'):
            snap_path = os.path.join(
                config.REPORTS_DIR,
                f"heatmap_snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            heatmap_generator.save(filepath=snap_path)
            print(f"[INFO] Heatmap snapshot saved: {snap_path}")
        elif key == ord(' '):
            paused = True
            print("[INFO] Paused. Press SPACE to resume.")

    # =========================================================
    # STEP 13: Cleanup and session summary
    # =========================================================
    movement_summary = movement_analyzer.get_summary_metrics()
    behavior_metrics = behavior_analyzer.get_dashboard_metrics()
    queue_stats = queue_manager.get_statistics()
    all_person_stats = movement_analyzer.get_all_stats()

    print()
    print("=" * 62)
    print("  SESSION SUMMARY")
    print("=" * 62)
    print(f"  Frames Processed:   {frame_count}")
    print(f"  Entries / Exits:    {entries} / {exits}")
    print(f"  Final Occupancy:    {occupancy}")
    print(f"  Tracks Created:     {tracker.total_registered}")
    print()
    print("  --- Queue Statistics ---")
    print(f"  Peak Queue Length:  {queue_stats['peak_queue_length']}")
    print(f"  Avg Queue Length:   {queue_stats['avg_queue_length']}")
    print(f"  Total Alerts:       {queue_stats['total_alerts']}")
    print(f"  Alert Time:         {queue_stats['alert_percentage']}%")
    print()
    print("  --- Zone Analysis ---")
    print(f"  Most Visited Zone:  {behavior_metrics['most_visited_zone']} "
          f"({behavior_metrics['most_visited_count']} visits)")
    print(f"  Most Time Zone:     {behavior_metrics['most_time_zone']} "
          f"({behavior_metrics['most_time_seconds']}s)")
    print()
    print("  Zone Visit Counts:")
    for zone, count in behavior_metrics["zone_visits"].items():
        dwell = behavior_metrics["zone_dwell"].get(zone, 0)
        print(f"    {zone:<15} {count} visits   {dwell:.1f}s dwell")
    print()
    print("  --- Movement ---")
    print(f"  Avg Distance:       {movement_summary['avg_distance_px']} px")
    print(f"  Max Distance:       {movement_summary['max_distance_px']} px")
    print()

    if all_person_stats:
        print("  --- Per-Person Breakdown ---")
        print(f"  {'ID':<5} {'Dist(px)':<11} {'Spd':<9} "
              f"{'Time(s)':<10} {'Fav Zone':<16} {'Queue Wait':<12}")
        print(f"  {'-'*5} {'-'*11} {'-'*9} {'-'*10} {'-'*16} {'-'*12}")
        for ps in all_person_stats:
            fav_zone, fav_time = behavior_analyzer.get_person_favorite_zone(
                ps["person_id"]
            )
            q_wait = queue_manager.get_person_wait_time(ps["person_id"])
            print(f"  {ps['person_id']:<5} "
                  f"{ps['total_distance_px']:<11} "
                  f"{ps['current_speed_px_s']:<9} "
                  f"{ps['duration_seconds']:<10} "
                  f"{fav_zone} ({fav_time}s){'':>2} "
                  f"{q_wait:.1f}s")
        print()

    print(f"  CSV Logs: {config.LOGS_DIR}")
    print(f"    - visitor_log.csv")
    print(f"    - movement_log.csv")
    print(f"    - behavior_log.csv")
    print(f"    - queue_log.csv")
    print("=" * 62)
    print()

    release_capture(cap)

    # =========================================================
    # STEP 14: Generate heatmap (Phase 6)
    # =========================================================
    print("[INFO] Generating heatmap...")
    try:
        heatmap_generator.save()
    except Exception as e:
        print(f"[WARNING] Heatmap generation failed: {e}")

    # =========================================================
    # STEP 15: Generate dashboard charts and report (Phase 5)
    # =========================================================
    print("[INFO] Generating analytics dashboard...")
    try:
        dashboard = RetailDashboard()
        dashboard.generate_all()
    except Exception as e:
        print(f"[WARNING] Dashboard generation failed: {e}")

    print("[INFO] Generating analytics report...")
    try:
        report = ReportGenerator()
        report.generate(print_to_console=True)
    except Exception as e:
        print(f"[WARNING] Report generation failed: {e}")

    # =========================================================
    # STEP 16: Close database session (Phase 7)
    # =========================================================
    try:
        db.close_session(
            total_entries=entries,
            total_exits=exits,
            peak_occupancy=max(occupancy, entries - exits),
        )
        table_counts = db.get_table_counts()
        print(f"[DATABASE] Table counts: {table_counts}")
        db.close()
    except Exception as e:
        print(f"[WARNING] Database close failed: {e}")

    print("[INFO] Application closed.")


if __name__ == "__main__":
    main()
