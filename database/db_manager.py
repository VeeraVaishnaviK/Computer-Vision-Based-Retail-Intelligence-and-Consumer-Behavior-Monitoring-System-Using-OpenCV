"""
db_manager.py
=============
SQLite database manager for the Retail Intelligence System.

Replaces CSV logging with structured database storage. Provides:
    - Table creation with proper schema and foreign keys
    - Insert operations for all data types
    - Query operations for dashboard and reporting
    - Session management (each run = one session)
    - Backwards-compatible with CSV logger interface

Tables:
    sessions   — One row per application run
    visitors   — One row per detected person
    movement   — Position tracking data points
    behavior   — Zone visit events with dwell times
    queue      — Queue status snapshots

Usage:
    db = DatabaseManager()
    db.create_session()
    db.insert_visitor(track_id=0, entry_time="2026-...")
    db.insert_movement(visitor_id=1, x=320, y=240, ...)
    visitors_df = db.get_visitors_dataframe()
    db.close()
"""

import sqlite3
import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class DatabaseManager:
    """
    SQLite database manager with full CRUD operations.

    Attributes:
        db_path:     Path to the SQLite database file.
        conn:        sqlite3.Connection object.
        cursor:      sqlite3.Cursor object.
        session_id:  UUID for the current session.
    """

    def __init__(self, db_path=None):
        """
        Initialize the database manager and create tables.

        Args:
            db_path: Path to the SQLite file. Default from config.
        """
        self.db_path = db_path or config.DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")   # Better concurrency
        self.conn.execute("PRAGMA foreign_keys=ON")     # Enforce FK constraints
        self.cursor = self.conn.cursor()

        self.session_id = None
        self._create_tables()
        print(f"[DATABASE] Connected: {self.db_path}")

    def _create_tables(self):
        """Create all tables if they don't exist."""
        self.cursor.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                total_entries INTEGER DEFAULT 0,
                total_exits INTEGER DEFAULT 0,
                peak_occupancy INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS visitors (
                visitor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                track_id INTEGER NOT NULL,
                entry_time TEXT NOT NULL,
                exit_time TEXT,
                duration_seconds REAL,
                status TEXT DEFAULT 'ACTIVE',
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS movement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_id INTEGER NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                normalized_x REAL,
                normalized_y REAL,
                timestamp TEXT NOT NULL,
                speed REAL DEFAULT 0.0,
                FOREIGN KEY (visitor_id) REFERENCES visitors(visitor_id)
            );

            CREATE TABLE IF NOT EXISTS behavior (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_id INTEGER NOT NULL,
                zone_name TEXT NOT NULL,
                enter_time TEXT NOT NULL,
                exit_time TEXT,
                dwell_time_seconds REAL DEFAULT 0.0,
                visit_number INTEGER DEFAULT 1,
                FOREIGN KEY (visitor_id) REFERENCES visitors(visitor_id)
            );

            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT NOT NULL,
                queue_length INTEGER NOT NULL,
                estimated_wait_seconds REAL DEFAULT 0.0,
                crowd_level TEXT DEFAULT 'LOW',
                alert_triggered INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE INDEX IF NOT EXISTS idx_visitors_session
                ON visitors(session_id);
            CREATE INDEX IF NOT EXISTS idx_movement_visitor
                ON movement(visitor_id);
            CREATE INDEX IF NOT EXISTS idx_behavior_visitor
                ON behavior(visitor_id);
            CREATE INDEX IF NOT EXISTS idx_queue_session
                ON queue(session_id);
        """)
        self.conn.commit()

    # =================================================================
    # SESSION MANAGEMENT
    # =================================================================

    def create_session(self):
        """
        Create a new session for this application run.

        Returns:
            String — the new session UUID.
        """
        self.session_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        self.cursor.execute(
            "INSERT INTO sessions (session_id, start_time) VALUES (?, ?)",
            (self.session_id, now)
        )
        self.conn.commit()
        print(f"[DATABASE] Session created: {self.session_id}")
        return self.session_id

    def close_session(self, total_entries=0, total_exits=0, peak_occupancy=0):
        """
        Close the current session with final statistics.

        Args:
            total_entries:  Final entry count.
            total_exits:    Final exit count.
            peak_occupancy: Maximum occupancy observed.
        """
        if self.session_id:
            now = datetime.now().isoformat()
            self.cursor.execute("""
                UPDATE sessions
                SET end_time=?, total_entries=?, total_exits=?, peak_occupancy=?
                WHERE session_id=?
            """, (now, total_entries, total_exits, peak_occupancy,
                  self.session_id))
            self.conn.commit()
            print(f"[DATABASE] Session closed: {self.session_id}")

    # =================================================================
    # INSERT OPERATIONS
    # =================================================================

    def insert_visitor(self, track_id, entry_time, exit_time=None,
                       duration=None, status="ACTIVE"):
        """
        Insert or update a visitor record.

        Args:
            track_id:   Tracker-assigned ID.
            entry_time: ISO timestamp string.
            exit_time:  ISO timestamp string or None.
            duration:   Duration in seconds or None.
            status:     "ACTIVE" or "EXITED".

        Returns:
            Integer — the visitor_id (primary key).
        """
        self.cursor.execute("""
            INSERT INTO visitors
                (session_id, track_id, entry_time, exit_time,
                 duration_seconds, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (self.session_id, track_id, entry_time, exit_time,
              duration, status))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_visitor_exit(self, track_id, exit_time, duration):
        """
        Update a visitor's exit information.

        Args:
            track_id:  Tracker-assigned ID.
            exit_time: ISO timestamp string.
            duration:  Duration in seconds.
        """
        self.cursor.execute("""
            UPDATE visitors
            SET exit_time=?, duration_seconds=?, status='EXITED'
            WHERE session_id=? AND track_id=? AND status='ACTIVE'
        """, (exit_time, duration, self.session_id, track_id))
        self.conn.commit()

    def insert_movement(self, track_id, x, y, norm_x=None, norm_y=None,
                        speed=0.0):
        """
        Insert a movement data point.

        Args:
            track_id:   Tracker-assigned ID.
            x, y:       Pixel coordinates.
            norm_x, norm_y: Normalized coordinates (0-1).
            speed:      Speed in pixels/second.
        """
        self.cursor.execute("SELECT visitor_id FROM visitors WHERE session_id=? AND track_id=?", (self.session_id, track_id))
        row = self.cursor.fetchone()
        if not row:
            return
            
        now = datetime.now().isoformat()
        self.cursor.execute("""
            INSERT INTO movement
                (visitor_id, x, y, normalized_x, normalized_y,
                 timestamp, speed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (row[0], x, y, norm_x, norm_y, now, speed))
        # Commit in batches for performance (handled by caller or periodic)

    def insert_behavior(self, track_id, zone_name, enter_time,
                        exit_time=None, dwell_time=0.0, visit_number=1):
        """
        Insert a zone visit record.

        Args:
            track_id:     Tracker-assigned ID.
            zone_name:    Zone name string.
            enter_time:   ISO timestamp.
            exit_time:    ISO timestamp or None.
            dwell_time:   Seconds spent in zone.
            visit_number: Visit sequence number.
        """
        self.cursor.execute("SELECT visitor_id FROM visitors WHERE session_id=? AND track_id=?", (self.session_id, track_id))
        row = self.cursor.fetchone()
        if not row:
            return
            
        self.cursor.execute("""
            INSERT INTO behavior
                (visitor_id, zone_name, enter_time, exit_time,
                 dwell_time_seconds, visit_number)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (row[0], zone_name, enter_time, exit_time,
              dwell_time, visit_number))
        self.conn.commit()

    def insert_queue(self, queue_length, estimated_wait, crowd_level,
                     alert_triggered):
        """
        Insert a queue status snapshot.

        Args:
            queue_length:     People in queue.
            estimated_wait:   Estimated wait in seconds.
            crowd_level:      LOW/MEDIUM/HIGH/CRITICAL.
            alert_triggered:  Boolean.
        """
        now = datetime.now().isoformat()
        self.cursor.execute("""
            INSERT INTO queue
                (session_id, timestamp, queue_length,
                 estimated_wait_seconds, crowd_level, alert_triggered)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (self.session_id, now, queue_length, estimated_wait,
              crowd_level, int(alert_triggered)))
        # Batch commit for performance

    def commit(self):
        """Manually commit pending transactions (for batch inserts)."""
        self.conn.commit()

    # =================================================================
    # QUERY OPERATIONS — For Dashboard & Reporting
    # =================================================================

    def get_visitors(self, session_id=None):
        """Get all visitors, optionally filtered by session."""
        sid = session_id or self.session_id
        if sid:
            self.cursor.execute(
                "SELECT * FROM visitors WHERE session_id=? ORDER BY entry_time",
                (sid,))
        else:
            self.cursor.execute("SELECT * FROM visitors ORDER BY entry_time")
        columns = [d[0] for d in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def get_movement(self, visitor_id=None):
        """Get movement data, optionally filtered by visitor."""
        if visitor_id:
            self.cursor.execute(
                "SELECT * FROM movement WHERE visitor_id=? ORDER BY timestamp",
                (visitor_id,))
        else:
            self.cursor.execute("SELECT * FROM movement ORDER BY timestamp")
        columns = [d[0] for d in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def get_behavior(self, visitor_id=None):
        """Get behavior data, optionally filtered by visitor."""
        if visitor_id:
            self.cursor.execute(
                "SELECT * FROM behavior WHERE visitor_id=? ORDER BY enter_time",
                (visitor_id,))
        else:
            self.cursor.execute("SELECT * FROM behavior ORDER BY enter_time")
        columns = [d[0] for d in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def get_queue(self, session_id=None):
        """Get queue snapshots, optionally filtered by session."""
        sid = session_id or self.session_id
        if sid:
            self.cursor.execute(
                "SELECT * FROM queue WHERE session_id=? ORDER BY timestamp",
                (sid,))
        else:
            self.cursor.execute("SELECT * FROM queue ORDER BY timestamp")
        columns = [d[0] for d in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def get_session_summary(self, session_id=None):
        """Get summary statistics for a session."""
        sid = session_id or self.session_id
        self.cursor.execute("SELECT * FROM sessions WHERE session_id=?", (sid,))
        row = self.cursor.fetchone()
        if row:
            columns = [d[0] for d in self.cursor.description]
            return dict(zip(columns, row))
        return None

    def get_zone_summary(self, session_id=None):
        """
        Get aggregated zone statistics.

        Returns:
            List of dicts with zone_name, total_visits, total_dwell,
            avg_dwell for each zone.
        """
        sid = session_id or self.session_id
        query = """
            SELECT
                b.zone_name,
                COUNT(*) as total_visits,
                SUM(b.dwell_time_seconds) as total_dwell,
                AVG(b.dwell_time_seconds) as avg_dwell
            FROM behavior b
            JOIN visitors v ON b.visitor_id = v.visitor_id
            WHERE v.session_id = ?
            GROUP BY b.zone_name
            ORDER BY total_visits DESC
        """
        self.cursor.execute(query, (sid,))
        columns = [d[0] for d in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def get_all_sessions(self):
        """Get all sessions, most recent first."""
        self.cursor.execute(
            "SELECT * FROM sessions ORDER BY start_time DESC")
        columns = [d[0] for d in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    # =================================================================
    # Pandas DataFrame exports (for dashboard compatibility)
    # =================================================================

    def get_visitors_dataframe(self):
        """Export visitors table as Pandas DataFrame."""
        import pandas as pd
        return pd.read_sql_query("SELECT * FROM visitors", self.conn)

    def get_movement_dataframe(self):
        """Export movement table as Pandas DataFrame."""
        import pandas as pd
        return pd.read_sql_query("SELECT * FROM movement", self.conn)

    def get_behavior_dataframe(self):
        """Export behavior table as Pandas DataFrame."""
        import pandas as pd
        return pd.read_sql_query("SELECT * FROM behavior", self.conn)

    def get_queue_dataframe(self):
        """Export queue table as Pandas DataFrame."""
        import pandas as pd
        return pd.read_sql_query("SELECT * FROM queue", self.conn)

    # =================================================================
    # UTILITIES
    # =================================================================

    def get_table_counts(self):
        """Get row counts for all tables."""
        counts = {}
        for table in ["sessions", "visitors", "movement", "behavior", "queue"]:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = self.cursor.fetchone()[0]
        return counts

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            print(f"[DATABASE] Connection closed: {self.db_path}")

    def __del__(self):
        """Ensure connection is closed on garbage collection."""
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
