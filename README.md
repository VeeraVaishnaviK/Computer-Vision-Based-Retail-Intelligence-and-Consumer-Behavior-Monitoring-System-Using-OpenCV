<div align="center">
  <img src="https://img.icons8.com/color/96/000000/artificial-intelligence.png" alt="AI Icon"/>
  
  # Computer Vision-Based Retail Intelligence and Consumer Behavior Monitoring System
  
  <p>An enterprise-grade, real-time computer vision analytics platform designed to transform physical retail spaces into measurable data environments using <strong>YOLOv8</strong>, <strong>DeepSORT</strong>, and a dynamic <strong>Web Dashboard</strong>.</p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python Version"/>
    <img src="https://img.shields.io/badge/OpenCV-4.x-green.svg" alt="OpenCV Version"/>
    <img src="https://img.shields.io/badge/YOLOv8-Ultralytics-orange.svg" alt="YOLOv8"/>
    <img src="https://img.shields.io/badge/Flask-Backend-lightgrey.svg" alt="Flask"/>
  </p>
</div>

---

## 📖 Overview

Physical retail stores lack the granular analytics inherent to e-commerce (e.g., bounce rate, time spent on page, click-through rates). This system solves this by analyzing live security camera feeds to extract highly actionable business intelligence in real-time. 

Using state-of-the-art deep learning, the system tracks customer journeys, measures zone engagement (e.g., Electronics vs. Grocery), monitors checkout queues, and visualizes crowd density—all accessible through a beautifully designed, responsive Business Intelligence (BI) web dashboard.

> **Live Deployment:** *(Link to be added post-deployment)*

---

## ✨ Key Features

* **🎥 Live Video Streaming:** Real-time MJPEG camera stream embedded directly in the dashboard, augmented with tracking bounding boxes and virtual store zones.
* **🧍‍♂️ Person Detection & Tracking:** Highly accurate, frame-by-frame person identification utilizing **YOLOv8** and **DeepSORT**.
* **📊 Interactive BI Dashboard:** A light-themed, professional dashboard built with **Bootstrap 5** and **Chart.js** displaying real-time KPI metrics.
* **📍 Zone Analytics & Heatmaps:** Automatically maps customer movement to logical store zones, computing dwell times and generating live spatial heatmaps.
* **🛒 Queue Management:** Detects when the checkout queue exceeds comfortable capacities and issues real-time alerts.
* **🗄️ Robust Data Persistence:** All footfall and behavior events are logged securely into an **SQLite** database for historical queries.
* **📄 Instant PDF Reports:** One-click generation of beautifully formatted PDF analytics reports for management review.

---

## 🏗️ System Architecture

The application is built on a multi-threaded architecture to decouple the heavy computer vision processing from the web API layer, ensuring maximum FPS and a responsive UI.

1. **Vision Thread (`main.py`):** Captures video frames, runs YOLOv8 inference, updates DeepSORT tracks, computes analytics (zone intersections, movement), and logs events to SQLite. Passes the final annotated frame to the shared state.
2. **Web Thread (`web_app.py`):** A Flask web server that serves the dashboard, provides REST API endpoints (`/api/summary`, `/api/events`, etc.) by querying the SQLite database, and streams the MJPEG video feed.
3. **Shared State (`shared_state.py`):** Thread-safe locking mechanism allowing the Vision Thread to safely hand off video frames to the Web Thread.

---

## 📂 File Structure

```text
├── analytics/                 # Business logic for retail metrics
│   ├── behavior_analyzer.py   # Computes zone dwell time & visits
│   ├── heatmap_generator.py   # Generates spatial movement heatmaps
│   └── queue_manager.py       # Monitors checkout line volumes
├── core/                      # Core Computer Vision pipeline
│   ├── detector.py            # YOLOv8 object detection wrapper
│   ├── tracker.py             # DeepSORT tracking implementation
│   ├── entry_exit_counter.py  # Line-crossing algorithms for footfall
│   └── zone_manager.py        # Polygon intersection logic for virtual zones
├── database/                  # Storage Layer
│   └── db_manager.py          # SQLite database schema and ORM methods
├── models/                    # AI Weights (Auto-downloaded)
│   ├── yolov8n.pt             # YOLOv8 nano model
│   └── deep_sort_weights/     # DeepSORT feature extraction weights
├── static/                    # Frontend Web Assets
│   ├── css/style.css          # Custom Bootstrap overrides
│   └── js/main.js             # Client-side AJAX polling & Chart.js logic
├── templates/                 # Frontend Views
│   └── index.html             # Main dashboard UI
├── main.py                    # The core OpenCV processing loop
├── web_app.py                 # The Flask Backend API
├── run.py                     # Thread launcher (Starts both CV & Web Server)
├── shared_state.py            # Thread-safe cross-process variable sharing
└── config.py                  # Global configurations (Zones, Polygons, Thresholds)
```

---

## 🛠️ Technologies Used

### Deep Learning & Computer Vision
* **Ultralytics YOLOv8:** For high-speed, accurate person bounding-box detection.
* **DeepSORT:** For assigning persistent unique IDs to tracked persons across frames using visual feature extraction.
* **OpenCV:** For video stream decoding, frame manipulation, and overlay drawing.

### Backend & Data
* **Python 3.10+:** Core programming language.
* **Flask:** Lightweight WSGI web application framework.
* **SQLite:** Embedded relational database for zero-config data persistence.
* **Shapely:** For complex geometric calculations (e.g., Point-in-Polygon zone intersections).

### Frontend Dashboard
* **HTML5 / CSS3 / JavaScript (ES6)**
* **Bootstrap 5:** Responsive CSS framework.
* **Chart.js:** HTML5 Canvas-based chart rendering.
* **html2pdf.js:** Client-side PDF report generation.

---

## 🚀 Getting Started

### 1. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/VeeraVaishnaviK/Computer-Vision-Based-Retail-Intelligence-and-Consumer-Behavior-Monitoring-System-Using-OpenCV.git
cd Computer-Vision-Based-Retail-Intelligence-and-Consumer-Behavior-Monitoring-System-Using-OpenCV

pip install -r requirements.txt
```

### 2. Download AI Models
Run the setup script to download the YOLOv8 and DeepSORT weights into the `models/` directory:
```bash
python download_models.py
```

### 3. Run the System
Launch the multi-threaded application (this will start both the OpenCV camera window and the background web server):
```bash
python run.py
```

### 4. View the Dashboard
Once the system is running, open your web browser and navigate to:
```text
http://localhost:5000
```

---

## 💡 Configuration
You can customize the store layout by editing `config.py`. Update the polygon coordinates in `ZONES` to match your specific camera angle and store layout (e.g., defining where the 'Electronics' or 'Billing' areas are located). You can also adjust the `ENTRY_LINE` coordinates for footfall counting.

---

<div align="center">
  <i>Developed for Advanced Retail Analytics & Computer Vision Demonstrations</i>
</div>
