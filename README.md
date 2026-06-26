# Computer Vision-Based Retail Intelligence and Consumer Behavior Monitoring System

This project is a comprehensive Computer Vision system designed to analyze consumer behavior in a retail environment using a standard webcam. It processes video feeds in real-time to detect customers, track their movements, analyze zone interactions, manage queues, and generate actionable analytics.

## Features

*   **Real-time Person Detection & Tracking:** Uses YOLOv4-tiny (with HOG fallback) for fast and accurate detection, coupled with a Centroid Tracker for maintaining persistent identities across frames.
*   **Occupancy & Counting:** Accurately counts entries and exits across defined lines to monitor total store occupancy.
*   **Movement Analytics:** Calculates total distance traveled, instantaneous speed, and generates smooth movement trails for each customer.
*   **Zone & Behavior Analysis:** Defines virtual retail zones (e.g., Electronics, Grocery, Fashion, Billing) and measures dwell times, visit frequencies, and favorite zones per customer.
*   **Queue Management:** Monitors the billing area, estimates wait times based on queue length, classifies crowd density, and triggers visual alerts for overcrowding.
*   **Spatial Heatmaps:** Generates Gaussian-weighted heatmaps highlighting high-traffic areas, accessible live or generated offline from historical data.
*   **Dual Data Storage:** Logs all events simultaneously to human-readable CSV files and a structured SQLite database for robust session management and complex querying.
*   **Analytics Dashboard:** Automatically generates a suite of Matplotlib charts and a formatted text report detailing session statistics, visitor trends, and zone popularity upon closing the application.

## Requirements

*   Python 3.8+
*   OpenCV (`opencv-python`)
*   NumPy
*   Pandas
*   Matplotlib
*   SciPy

## Installation

1.  **Clone the repository.**
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Download Model Weights:**
    Run the provided script to fetch the YOLOv4-tiny weights and config files:
    ```bash
    python download_models.py
    ```

## Usage

You can run the system using the main launcher:

```bash
python run.py
```

### Command Line Arguments

*   `--video <path>`: Run the analysis on a pre-recorded video file instead of the webcam.
*   `--hog`: Force the system to use the HOG+SVM detector instead of YOLOv4-tiny (useful for testing on systems without YOLO weights).
*   `--camera <index>`: Specify the camera index (default is 0).
*   `--no-display`: Run in headless mode without showing the GUI.

Example:
```bash
python run.py --video sample_retail_footage.mp4
```

### Interactive Controls

While the display window is active, you can use the following keyboard controls:

*   `q` : Quit the application. This will safely close the database session, flush logs, and auto-generate the analytics dashboard and report.
*   `r` : Reset all counters (entries, exits, occupancy).
*   `s` : Save a screenshot of the current frame to the `data/reports/` directory.
*   `h` : Toggle between YOLOv4-tiny and HOG detection backends.
*   `m` : Save a snapshot of the current accumulated heatmap to `data/reports/`.
*   `SPACE` : Pause or resume the video feed.

## Project Structure

*   `main.py` / `run.py`: Application entry points.
*   `config.py`: Centralized configuration constants (zones, thresholds, paths).
*   `core/`: Core computer vision modules (`detector.py`, `tracker.py`, `counter.py`, `movement_analyzer.py`, `zone_manager.py`).
*   `analytics/`: Advanced analysis modules (`behavior_analyzer.py`, `queue_manager.py`, `heatmap_generator.py`).
*   `database/`: Data persistence handling (`csv_logger.py`, `db_manager.py`).
*   `dashboard/`: Report and chart generation tools (`dashboard.py`, `report_generator.py`).
*   `utils/`: Helper functions for math, drawing, and video handling.
*   `data/`: Generated artifacts (logs, SQLite DB, reports, models).

## Generating Analytics Offline

You can regenerate the charts and reports from historical CSV data without running the main camera loop:

```bash
python -m dashboard.dashboard
python -m dashboard.report_generator
```

To generate a heatmap offline from `movement_log.csv`:

```bash
python -m analytics.heatmap_generator
```
