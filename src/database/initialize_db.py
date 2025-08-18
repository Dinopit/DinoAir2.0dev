### Database Initialization Script
### should run/initialize the database and tables when GUI application (pyside6) runs

import sqlite3
import os
import shutil
import time
import threading
from pathlib import Path
from datetime import datetime
try:
    from src.models.note import Note, NoteList
except ImportError:
    from models.note import Note, NoteList
from .resilient_db import ResilientDB

class DatabaseManager:
    """Manages multiple SQLite databases for the DinoAir application"""
    
    def __init__(self, user_name=None, user_feedback=None):
        self.user_name = user_name or "default_user"
        self.user_feedback = user_feedback or print
        self.base_dir = Path(__file__).parent.parent  # Root of DinoAir2.0dev
        self.user_db_dir = self.base_dir / "user_data" / self.user_name / "databases"
        
        # Track active connections for cleanup
        self._active_connections = []
        self._connection_lock = threading.Lock()
        
        # Database file paths
        self.notes_db_path = self.user_db_dir / "notes.db"
        self.memory_db_path = self.user_db_dir / "memory.db"
        self.user_tools_db_path = self.user_db_dir / "user_tools.db"
        self.chat_history_db_path = self.user_db_dir / "chat_history.db"
        self.appointments_db_path = self.user_db_dir / "appointments.db"
        self.artifacts_db_path = self.user_db_dir / "artifacts.db"
        self.file_search_db_path = self.user_db_dir / "file_search.db"
        self.projects_db_path = self.user_db_dir / "projects.db"
        
        # Ensure directory structure exists
        self._create_directory_structure()
    
    def _create_directory_structure(self):
        """Create the user-specific directory structure"""
        try:
            self.user_db_dir.mkdir(parents=True, exist_ok=True)
            
            # Also create other user-specific folders
            (self.user_db_dir.parent / "exports").mkdir(exist_ok=True)
            (self.user_db_dir.parent / "backups").mkdir(exist_ok=True)
            (self.user_db_dir.parent / "temp").mkdir(exist_ok=True)
            
            # Create artifact storage directories
            artifacts_dir = self.user_db_dir.parent / "artifacts"
            artifacts_dir.mkdir(exist_ok=True)
            
            # Create year/month subdirectories for current date
            now = datetime.now()
            year_dir = artifacts_dir / str(now.year)
            month_dir = year_dir / f"{now.month:02d}"
            month_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            self.user_feedback("Cannot create user folders. Please check permissions or run as administrator.")
            raise
        except OSError as e:
            self.user_feedback(f"OS error creating folders: {str(e)}. Check disk space and permissions.")
            raise
        except Exception as e:
            self.user_feedback(f"Unexpected error creating folders: {str(e)}")
            raise
    
    def initialize_all_databases(self):
        """Initialize all databases for the user with resilient error handling"""
        self.user_feedback(f"Setting up databases for {self.user_name}...")
        
        try:
            # Initialize each database with resilient handling
            notes_db = ResilientDB(self.notes_db_path, self._setup_notes_schema, self.user_feedback)
            notes_conn = notes_db.connect_with_retry()
            notes_conn.close()
            
            memory_db = ResilientDB(self.memory_db_path, self._setup_memory_schema, self.user_feedback)
            memory_conn = memory_db.connect_with_retry()
            memory_conn.close()
            
            tools_db = ResilientDB(self.user_tools_db_path, self._setup_user_tools_schema, self.user_feedback)
            tools_conn = tools_db.connect_with_retry()
            tools_conn.close()
            
            chat_db = ResilientDB(self.chat_history_db_path, self._setup_chat_history_schema, self.user_feedback)
            chat_conn = chat_db.connect_with_retry()
            chat_conn.close()
            
            appointments_db = ResilientDB(self.appointments_db_path, self._setup_appointments_schema, self.user_feedback)
            appointments_conn = appointments_db.connect_with_retry()
            appointments_conn.close()
            
            artifacts_db = ResilientDB(self.artifacts_db_path, self._setup_artifacts_schema, self.user_feedback)
            artifacts_conn = artifacts_db.connect_with_retry()
            artifacts_conn.close()
            
            file_search_db = ResilientDB(self.file_search_db_path, self._setup_file_search_schema, self.user_feedback)
            file_search_conn = file_search_db.connect_with_retry()
            file_search_conn.close()
            
            projects_db = ResilientDB(self.projects_db_path, self._setup_projects_schema, self.user_feedback)
            projects_conn = projects_db.connect_with_retry()
            projects_conn.close()
            
            self.user_feedback(f"[OK] All databases ready for {self.user_name}")
            
        except sqlite3.Error as e:
            self.user_feedback(f"[ERROR] Database error: {str(e)}. Please check database file permissions.")
            raise
        except PermissionError as e:
            self.user_feedback("[ERROR] Permission denied. Please run as administrator or check file permissions.")
            raise
        except Exception as e:
            self.user_feedback("[ERROR] Database setup failed. Please try restarting the application or contact support.")
            raise
    
    def _setup_notes_schema(self, conn):
        """Initialize the notes database schema"""
        cursor = conn.cursor()
        
        # Check if project_id column exists (for migration)
        cursor.execute("PRAGMA table_info(note_list)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'project_id' not in columns and 'note_list' in [table[0] for table in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            # Table exists but doesn't have project_id - add it
            cursor.execute('ALTER TABLE note_list ADD COLUMN project_id TEXT')
            self.user_feedback("[OK] Added project_id to existing notes table")
        
        # Create note_list table (will only create if doesn't exist)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS note_list (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                tags TEXT,
                project_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_title ON note_list(title)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_tags ON note_list(tags)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_created ON note_list(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_project ON note_list(project_id)')
        
        conn.commit()
    
    def _setup_memory_schema(self, conn):
        """Initialize the memory database schema"""
        cursor = conn.cursor()
        
        # Session data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_data (
                key TEXT PRIMARY KEY,
                value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME
            )
        ''')
        
        # Recently accessed notes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recent_notes (
                note_id TEXT,
                accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (note_id)
            )
        ''')
        
        # Watchdog metrics table for system monitoring history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchdog_metrics (
                id TEXT PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                vram_used_mb REAL,
                vram_total_mb REAL,
                vram_percent REAL,
                cpu_percent REAL,
                ram_used_mb REAL,
                ram_percent REAL,
                process_count INTEGER,
                dinoair_processes INTEGER,
                uptime_seconds INTEGER
            )
        ''')
        
        # Create indexes for efficient queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
            ON watchdog_metrics(timestamp DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_vram
            ON watchdog_metrics(vram_percent)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_processes
            ON watchdog_metrics(dinoair_processes)
        ''')
        
        conn.commit()
    
    def _setup_user_tools_schema(self, conn):
        """Initialize the user tools database schema"""
        cursor = conn.cursor()
        
        # User preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Application logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
    
    def _setup_chat_history_schema(self, conn):
        """Initialize the chat history database schema"""
        cursor = conn.cursor()
        
        # Main chat sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                project_id TEXT,
                task_id TEXT,
                tags TEXT,
                summary TEXT,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Individual chat messages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                message TEXT NOT NULL,
                is_user BOOLEAN DEFAULT 1,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
            )
        ''')
        
        # Cron-style scheduled entries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_schedules (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                cron_expression TEXT NOT NULL,
                next_run DATETIME,
                last_run DATETIME,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_created ON chat_sessions(created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_project ON chat_sessions(project_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_task ON chat_sessions(task_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_status ON chat_sessions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_schedules_session ON chat_schedules(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON chat_schedules(next_run)')
        
        conn.commit()
    
    def _setup_appointments_schema(self, conn):
        """Initialize the appointments database schema"""
        cursor = conn.cursor()
        
        # Main calendar events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar_events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                event_type TEXT DEFAULT 'appointment',
                status TEXT DEFAULT 'scheduled',
                event_date DATE,
                start_time TIME,
                end_time TIME,
                all_day BOOLEAN DEFAULT 0,
                location TEXT,
                participants TEXT,
                project_id TEXT,
                chat_session_id TEXT,
                recurrence_pattern TEXT DEFAULT 'none',
                recurrence_rule TEXT,
                reminder_minutes_before INTEGER,
                reminder_sent BOOLEAN DEFAULT 0,
                tags TEXT,
                notes TEXT,
                color TEXT,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )
        ''')
        
        # Event reminders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_reminders (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                reminder_time DATETIME NOT NULL,
                sent BOOLEAN DEFAULT 0,
                sent_at DATETIME,
                FOREIGN KEY (event_id) REFERENCES calendar_events (id)
            )
        ''')
        
        # Event attachments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_attachments (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT,
                file_type TEXT,
                file_size INTEGER,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES calendar_events (id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_date ON calendar_events(event_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_status ON calendar_events(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_project ON calendar_events(project_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_chat_session ON calendar_events(chat_session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_created ON calendar_events(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminders_event ON event_reminders(event_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminders_time ON event_reminders(reminder_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attachments_event ON event_attachments(event_id)')
        
        conn.commit()
    
    def _setup_artifacts_schema(self, conn):
        """Initialize the artifacts database schema"""
        cursor = conn.cursor()
        
        # Main artifacts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                content_type TEXT DEFAULT 'text',
                status TEXT DEFAULT 'active',
                content TEXT,
                content_path TEXT,
                size_bytes INTEGER DEFAULT 0,
                mime_type TEXT,
                checksum TEXT,
                collection_id TEXT,
                parent_id TEXT,
                version INTEGER DEFAULT 1,
                is_latest BOOLEAN DEFAULT 1,
                encrypted_fields TEXT,
                encryption_key_id TEXT,
                project_id TEXT,
                chat_session_id TEXT,
                note_id TEXT,
                tags TEXT,
                metadata TEXT,
                properties TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                accessed_at DATETIME,
                FOREIGN KEY (collection_id) REFERENCES artifact_collections (id),
                FOREIGN KEY (parent_id) REFERENCES artifacts (id)
            )
        ''')
        
        # Artifact versions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS artifact_versions (
                id TEXT PRIMARY KEY,
                artifact_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                artifact_data TEXT NOT NULL,
                change_summary TEXT,
                changed_by TEXT,
                changed_fields TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artifact_id) REFERENCES artifacts (id),
                UNIQUE(artifact_id, version_number)
            )
        ''')
        
        # Artifact collections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS artifact_collections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                parent_id TEXT,
                project_id TEXT,
                is_encrypted BOOLEAN DEFAULT 0,
                is_public BOOLEAN DEFAULT 0,
                tags TEXT,
                properties TEXT,
                artifact_count INTEGER DEFAULT 0,
                total_size_bytes INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES artifact_collections (id)
            )
        ''')
        
        # Artifact permissions table (future use)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS artifact_permissions (
                id TEXT PRIMARY KEY,
                artifact_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                can_read BOOLEAN DEFAULT 1,
                can_write BOOLEAN DEFAULT 0,
                can_delete BOOLEAN DEFAULT 0,
                can_share BOOLEAN DEFAULT 0,
                granted_by TEXT,
                granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                FOREIGN KEY (artifact_id) REFERENCES artifacts (id),
                UNIQUE(artifact_id, user_id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_artifacts_name ON artifacts(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(content_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_artifacts_status ON artifacts(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_artifacts_collection ON artifacts(collection_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_artifacts_created ON artifacts(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_artifacts_tags ON artifacts(tags)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_versions_artifact ON artifact_versions(artifact_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_versions_number ON artifact_versions(version_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_collections_name ON artifact_collections(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_collections_parent ON artifact_collections(parent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_permissions_artifact ON artifact_permissions(artifact_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_permissions_user ON artifact_permissions(user_id)')
        
        conn.commit()
    
    def _setup_file_search_schema(self, conn):
        """Initialize the file search database schema for RAG functionality"""
        cursor = conn.cursor()
        
        # Table for tracking indexed files
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indexed_files (
                id TEXT PRIMARY KEY,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                size INTEGER NOT NULL,
                modified_date DATETIME NOT NULL,
                indexed_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                file_type TEXT,
                status TEXT DEFAULT 'active',
                metadata TEXT
            )
        ''')
        
        # Table for storing text chunks
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_chunks (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                start_pos INTEGER NOT NULL,
                end_pos INTEGER NOT NULL,
                metadata TEXT,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES indexed_files (id)
                    ON DELETE CASCADE,
                UNIQUE(file_id, chunk_index)
            )
        ''')
        
        # Table for storing vector embeddings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_embeddings (
                id TEXT PRIMARY KEY,
                chunk_id TEXT UNIQUE NOT NULL,
                embedding_vector TEXT NOT NULL,  -- JSON array
                model_name TEXT NOT NULL,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chunk_id) REFERENCES file_chunks (id)
                    ON DELETE CASCADE
            )
        ''')
        
        # Table for search settings (directory limiters, etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_settings (
                id TEXT PRIMARY KEY,
                setting_name TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                modified_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('''CREATE INDEX IF NOT EXISTS
            idx_indexed_files_path ON indexed_files(file_path)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS
            idx_indexed_files_status ON indexed_files(status)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS
            idx_indexed_files_type ON indexed_files(file_type)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS
            idx_file_chunks_file_id ON file_chunks(file_id)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS
            idx_file_chunks_content ON file_chunks(content)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS
            idx_file_embeddings_chunk_id
            ON file_embeddings(chunk_id)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS
            idx_search_settings_name
            ON search_settings(setting_name)''')
        
        conn.commit()
    
    def _setup_projects_schema(self, conn):
        """Initialize the projects database schema"""
        cursor = conn.cursor()
        
        # Main projects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'archived')),
                color TEXT,
                icon TEXT,
                parent_project_id TEXT,
                tags TEXT,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                archived_at DATETIME,
                FOREIGN KEY (parent_project_id) REFERENCES projects (id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_parent ON projects(parent_project_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_tags ON projects(tags)')
        
        conn.commit()
    
    def _track_connection(self, conn):
        """Track a database connection for cleanup"""
        with self._connection_lock:
            self._active_connections.append(conn)
    
    def _cleanup_connections(self):
        """Close all tracked database connections"""
        with self._connection_lock:
            for conn in self._active_connections[:]:
                try:
                    if conn:
                        conn.close()
                        self.user_feedback(f"[OK] Database connection closed")
                except Exception as e:
                    self.user_feedback(f"[WARNING] Error closing connection: {e}")
            self._active_connections.clear()
    
    def get_notes_connection(self):
        """Get connection to notes database with resilient handling"""
        notes_db = ResilientDB(self.notes_db_path, self._setup_notes_schema, self.user_feedback)
        conn = notes_db.connect_with_retry()
        self._track_connection(conn)
        return conn
    
    def get_memory_connection(self):
        """Get connection to memory database with resilient handling"""
        memory_db = ResilientDB(self.memory_db_path, self._setup_memory_schema, self.user_feedback)
        conn = memory_db.connect_with_retry()
        self._track_connection(conn)
        return conn
    
    def get_user_tools_connection(self):
        """Get connection to user tools database with resilient handling"""
        tools_db = ResilientDB(self.user_tools_db_path, self._setup_user_tools_schema, self.user_feedback)
        conn = tools_db.connect_with_retry()
        self._track_connection(conn)
        return conn
    
    def get_chat_history_connection(self):
        """Get connection to chat history database with resilient handling"""
        chat_db = ResilientDB(self.chat_history_db_path, self._setup_chat_history_schema, self.user_feedback)
        conn = chat_db.connect_with_retry()
        self._track_connection(conn)
        return conn
    
    def get_appointments_connection(self):
        """Get connection to appointments database with resilient handling"""
        appointments_db = ResilientDB(self.appointments_db_path, self._setup_appointments_schema, self.user_feedback)
        conn = appointments_db.connect_with_retry()
        self._track_connection(conn)
        return conn
    
    def get_artifacts_connection(self):
        """Get connection to artifacts database with resilient handling"""
        artifacts_db = ResilientDB(self.artifacts_db_path, self._setup_artifacts_schema, self.user_feedback)
        conn = artifacts_db.connect_with_retry()
        self._track_connection(conn)
        return conn
    
    def get_file_search_connection(self):
        """Get connection to file search database with resilient handling"""
        file_search_db = ResilientDB(self.file_search_db_path, self._setup_file_search_schema, self.user_feedback)
        conn = file_search_db.connect_with_retry()
        self._track_connection(conn)
        return conn
    
    def get_projects_connection(self):
        """Get connection to projects database with resilient handling"""
        projects_db = ResilientDB(self.projects_db_path, self._setup_projects_schema, self.user_feedback)
        conn = projects_db.connect_with_retry()
        self._track_connection(conn)
        return conn
    
    def get_watchdog_metrics_manager(self):
        """Get WatchdogMetricsManager instance with memory database connection"""
        from ..models.watchdog_metrics import WatchdogMetricsManager
        conn = self.get_memory_connection()
        return WatchdogMetricsManager(conn)
    
    def backup_databases(self):
        """Create backups of all databases"""
        self.user_feedback("Creating database backups...")
        backup_dir = self.user_db_dir.parent / "backups"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            backup_dir.mkdir(exist_ok=True)
            
            for db_path in [self.notes_db_path, self.memory_db_path, self.user_tools_db_path, self.chat_history_db_path, self.appointments_db_path, self.artifacts_db_path, self.file_search_db_path, self.projects_db_path]:
                if db_path.exists():
                    backup_name = f"{db_path.stem}_{timestamp}.db"
                    backup_path = backup_dir / backup_name
                    shutil.copy2(db_path, backup_path)
            
            self.user_feedback(f"[OK] Backups saved to: {backup_dir}")
            
        except OSError as e:
            self.user_feedback(f"[ERROR] Backup failed - file system error: {str(e)}")
            raise
        except sqlite3.Error as e:
            self.user_feedback(f"[ERROR] Backup failed - database error: {str(e)}")
            raise
        except Exception as e:
            self.user_feedback(f"[ERROR] Backup failed - unexpected error: {str(e)}")
            raise
    
    def clean_memory_database(self, watchdog_retention_days=7):
        """Clean expired entries from memory database and close all connections"""
        try:
            # First cleanup all tracked connections
            self._cleanup_connections()
            
            # Then clean memory database
            with self.get_memory_connection() as conn:
                cursor = conn.cursor()
                
                # Remove expired session data
                cursor.execute('DELETE FROM session_data WHERE expires_at < CURRENT_TIMESTAMP')
                
                # Keep only last 100 recent notes
                cursor.execute('''
                    DELETE FROM recent_notes
                    WHERE note_id NOT IN (
                        SELECT note_id FROM recent_notes
                        ORDER BY accessed_at DESC
                        LIMIT 100
                    )
                ''')
                
                # Clean old watchdog metrics based on retention policy
                cursor.execute('''
                    DELETE FROM watchdog_metrics
                    WHERE timestamp < datetime('now', '-{} days')
                '''.format(watchdog_retention_days))
                
                deleted_metrics = cursor.rowcount
                
                conn.commit()
                
                # Vacuum to reclaim space
                cursor.execute("VACUUM")
                
                self.user_feedback(
                    f"[OK] Memory database cleaned (removed {deleted_metrics} old metrics)"
                )
                
        except sqlite3.Error as e:
            self.user_feedback(f"Warning: Database error during cleanup: {str(e)}")
        except Exception as e:
            self.user_feedback(f"Warning: Could not clean memory database: {str(e)}")


# For easy initialization when GUI starts
def initialize_user_databases(user_name=None, user_feedback=None):
    """Convenience function to initialize databases for a user"""
    db_manager = DatabaseManager(user_name, user_feedback)
    db_manager.initialize_all_databases()
    return db_manager


# Example usage in your GUI application:
if __name__ == "__main__":
    # Test with console feedback
    def console_feedback(message):
        print(f"[DinoAir] {message}")
    
    # Initialize for default user
    try:
        db_manager = initialize_user_databases("john_doe", console_feedback)
        console_feedback("Database setup completed successfully!")
    except sqlite3.Error as e:
        console_feedback(f"Database setup failed: {e}")
    except PermissionError as e:
        console_feedback(f"Permission error during setup: {e}")
    except Exception as e:
        console_feedback(f"Setup failed: {e}")