"""
run.py
======
Convenience launcher for the Retail Intelligence System.
Automatically starts the Flask web dashboard server in the background,
then runs the OpenCV main application.
"""

import sys
import os
import threading
import time

# Ensure the current directory is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from main import main
from web_app import app

def run_server():
    # Hide flask startup warnings for a cleaner console
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Removed WERKZEUG_RUN_MAIN to prevent KeyError
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("[INFO] Starting Web Dashboard server in the background...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Give the server a moment to start before launching the camera
    time.sleep(1)

    try:
        main()
        
        # After main() finishes (user pressed 'q')
        print("\n" + "="*62)
        print("  ✅ WEB DASHBOARD READY")
        print("  Click the link below to view your final interactive analytics:")
        print("  http://localhost:5000")
        print("  (Press Ctrl+C in this terminal to completely exit)")
        print("="*62 + "\n")
        
        # Keep the main thread alive so the daemon server keeps running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[INFO] Application interrupted and closed by user.")
        sys.exit(0)
