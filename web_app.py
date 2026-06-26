"""
web_app.py
==========
Flask backend for the Retail Intelligence Interactive Dashboard.
Provides APIs for data and a live MJPEG stream of the OpenCV frames.
"""

from flask import Flask, render_template, jsonify, send_file, Response
import os
import cv2
import time

import config
from database.db_manager import DatabaseManager
from shared_state import SharedState

app = Flask(__name__)

def get_db():
    return DatabaseManager(config.DB_PATH)

def get_latest_session_id(db):
    db.cursor.execute("SELECT session_id FROM sessions ORDER BY start_time DESC LIMIT 1")
    row = db.cursor.fetchone()
    return row[0] if row else None

# ==========================================
# Video Streaming Route
# ==========================================
def generate_frames():
    """Generator function that continuously yields JPEG frames."""
    while True:
        frame = SharedState.get_frame()
        if frame is None:
            # If no frame yet, yield a blank black frame or wait
            time.sleep(0.1)
            continue
        
        # Encode the frame in JPEG format
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            time.sleep(0.1)
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Limit to ~30 FPS
        time.sleep(1/30.0)

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# ==========================================
# API Routes
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/summary')
def api_summary():
    db = get_db()
    session_id = get_latest_session_id(db)
    if not session_id:
        db.close()
        return jsonify({"error": "No session found"}), 404
    
    summary = db.get_session_summary(session_id)
    
    # Active visitors
    db.cursor.execute("SELECT COUNT(*) FROM visitors WHERE session_id=? AND status='ACTIVE'", (session_id,))
    active_count = db.cursor.fetchone()[0]
    
    # Area/Crowd density estimate (just a mock calculation based on occupancy)
    # E.g., assume max comfortable occupancy is 20
    max_cap = 20
    density = round((active_count / max_cap) * 100) if active_count else 0
    
    if summary:
        summary['active_visitors'] = active_count
        summary['crowd_density'] = min(density, 100)
    
    db.close()
    return jsonify(summary)

@app.route('/api/zones')
def api_zones():
    db = get_db()
    session_id = get_latest_session_id(db)
    if not session_id:
        db.close()
        return jsonify([]), 404
    
    zone_stats = db.get_zone_summary(session_id)
    db.close()
    return jsonify(zone_stats)

@app.route('/api/queue')
def api_queue():
    db = get_db()
    session_id = get_latest_session_id(db)
    if not session_id:
        db.close()
        return jsonify([]), 404
    
    queue_data = db.get_queue(session_id)
    db.close()
    return jsonify(queue_data[-100:])

@app.route('/api/events')
def api_events():
    db = get_db()
    session_id = get_latest_session_id(db)
    if not session_id:
        db.close()
        return jsonify([]), 404
        
    # Fetch latest 15 events from behavior_log
    query = """
        SELECT timestamp, visitor_id, event_type, zone_name 
        FROM behavior_log 
        WHERE session_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 15
    """
    db.cursor.execute(query, (session_id,))
    rows = db.cursor.fetchall()
    
    events = []
    for row in rows:
        events.append({
            "timestamp": row[0],
            "visitor_id": row[1],
            "event_type": row[2],
            "zone_name": row[3] if row[3] else ""
        })
        
    db.close()
    return jsonify(events)

@app.route('/api/heatmap')
def api_heatmap():
    heatmap_path = os.path.join(config.REPORTS_DIR, "heatmap.png")
    
    if not os.path.exists(heatmap_path):
        import glob
        snaps = glob.glob(os.path.join(config.REPORTS_DIR, "heatmap_snap_*.png"))
        if snaps:
            heatmap_path = sorted(snaps)[-1]
        else:
            return jsonify({"error": "No heatmap found"}), 404
            
    return send_file(heatmap_path, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
