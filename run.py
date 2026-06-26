"""
run.py
======
Convenience launcher for the Retail Intelligence System.
Simply run: python run.py
"""

import sys
import os

# Ensure the current directory is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from main import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Application interrupted by user.")
        sys.exit(0)
