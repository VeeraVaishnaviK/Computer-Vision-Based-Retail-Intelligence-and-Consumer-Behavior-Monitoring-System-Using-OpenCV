"""
web_app.py
==========
Flask backend for the Retail Intelligence Interactive Dashboard.
Provides API endpoints to serve data from the SQLite database.
"""

from flask import Flask, render_template, jsonify, send_file
import os
import sqlite3

import config
from database.db_manager import DatabaseManager

app = Flask(__name__)

def get_db():
    """Create a thread-local database connection."""
    return DatabaseManager(config.DB_PATH)

def get_latest_session_id(db):
    db.cursor.execute("SELECT session_id FROM sessions ORDER BY start_time DESC LIMIT 1")
    row = db.cursor.fetchone()
    return row[0] if row else None

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
    
    # Count currently active
    db.cursor.execute(
        "SELECT COUNT(*) FROM visitors WHERE session_id=? AND status='ACTIVE'", 
        (session_id,)
    )
    active_count = db.cursor.fetchone()[0]
    
    if summary:
        summary['active_visitors'] = active_count
    
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
    
    # Only return the last 100 points for chart rendering
    queue_data = queue_data[-100:]
    return jsonify(queue_data)

@app.route('/api/heatmap')
def api_heatmap():
    heatmap_path = os.path.join(config.REPORTS_DIR, "heatmap.png")
    
    # Fallback to the latest snapshot if main heatmap isn't generated yet
    if not os.path.exists(heatmap_path):
        import glob
        snaps = glob.glob(os.path.join(config.REPORTS_DIR, "heatmap_snap_*.png"))
        if snaps:
            heatmap_path = sorted(snaps)[-1]
        else:
            return jsonify({"error": "No heatmap found"}), 404
            
    return send_file(heatmap_path, mimetype='image/png')

if __name__ == '__main__':
    print("=" * 60)
    print("  Starting Retail Intelligence Web Dashboard")
    print("  Access at: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
