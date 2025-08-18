
# DinoAir2.0dev - ResilientDB.py
# This file provides a resilient database wrapper for SQLite, ensuring safe initialization and recovery.

import sqlite3
import os
import shutil
import time
from pathlib import Path
from datetime import datetime
try:
    from src.models.note import Note, NoteList
except ImportError:
    from models.note import Note, NoteList


class ResilientDB:
    """A wrapper that makes SQLite initialization and recovery safer and more user-friendly."""

    def __init__(self, db_path: Path, schema_initializer, user_feedback=None):
        self.db_path = db_path
        self.schema_initializer = schema_initializer
        self.user_feedback = user_feedback or print

    def log(self, message):
        self.user_feedback(f"{message}")

    def connect(self):
        """Attempts to connect to the DB with recovery logic."""
        try:
            return self._attempt_connection()
        except sqlite3.OperationalError as e:
            if "unable to open database file" in str(e) or "no such file or directory" in str(e):
                self.log("Creating database folder - this is normal for first-time setup.")
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                return self._attempt_connection()
            elif "database is locked" in str(e):
                self.log("Database is busy. Waiting a moment and trying again...")
                time.sleep(2)
                return self._attempt_connection()
            else:
                raise
        except sqlite3.DatabaseError as e:
            if "file is not a database" in str(e) or "database disk image is malformed" in str(e):
                self.log("Found a damaged database file. Creating a backup and starting fresh...")
                self._backup_corrupted_db()
                return self._attempt_connection()
            else:
                raise
        except PermissionError:
            self.log("Permission denied accessing database folder. Please check folder permissions or run as administrator.")
            raise RuntimeError("Cannot access database due to permission restrictions.")
        except Exception as e:
            self.log(f"Unexpected database issue: {str(e)}")
            raise RuntimeError("Database setup failed due to an unexpected error.") from e

    def _attempt_connection(self):
        conn = sqlite3.connect(self.db_path)
        # Test the connection
        conn.execute("SELECT 1")
        self.schema_initializer(conn)
        return conn

    def _backup_corrupted_db(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.db_path.with_name(f"{self.db_path.stem}_corrupted_{timestamp}.db")
        try:
            shutil.move(self.db_path, backup_path)
            self.log(f"Backup saved to: {backup_path}")
        except Exception:
            # If we can't move it, just delete it
            self.db_path.unlink(missing_ok=True)
            self.log("Removed damaged database file.")

    def connect_with_retry(self, retries=3, delay=1):
        for attempt in range(retries):
            try:
                return self.connect()
            except Exception as e:
                if attempt < retries - 1:
                    self.log(f"Setup attempt {attempt+1} failed. Trying again in {delay * (attempt + 1)} seconds...")
                    time.sleep(delay * (attempt + 1))
                else:
                    self.log("Database setup failed after multiple attempts. Please contact support.")
                    raise RuntimeError("Database initialization failed after all retry attempts.") from e