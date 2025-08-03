"""Debug script to monitor indexing process and catch unexpected shutdowns"""

import sys
import os
import threading
import traceback
import psutil
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Disable watchdog
os.environ['DINOAIR_DISABLE_WATCHDOG'] = '1'

# Setup crash logging
crash_log = Path("indexing_crash.log")
crash_log.write_text(f"=== Indexing Debug Log Started: {datetime.now()} ===\n")

def log_crash(msg):
    """Log to crash file"""
    with open(crash_log, 'a') as f:
        f.write(f"[{datetime.now()}] {msg}\n")
    print(f"[DEBUG] {msg}")

# Monitor system resources
def resource_monitor():
    """Monitor memory and CPU usage during indexing"""
    process = psutil.Process()
    while True:
        try:
            mem_info = process.memory_info()
            mem_mb = mem_info.rss / 1024 / 1024
            cpu_percent = process.cpu_percent(interval=1)
            
            status = f"Memory: {mem_mb:.1f}MB | CPU: {cpu_percent:.1f}% | Threads: {threading.active_count()}"
            log_crash(f"RESOURCES: {status}")
            
            # Check for high memory usage
            if mem_mb > 2000:  # 2GB
                log_crash(f"WARNING: High memory usage: {mem_mb:.1f}MB")
            
            time.sleep(5)  # Check every 5 seconds
        except Exception as e:
            log_crash(f"Resource monitor error: {e}")
            break

# Start resource monitoring in background
monitor_thread = threading.Thread(target=resource_monitor, daemon=True)
monitor_thread.start()

# Monkey patch thread creation to track all threads
original_thread_init = threading.Thread.__init__

def tracked_thread_init(self, *args, **kwargs):
    log_crash(f"NEW THREAD: {kwargs.get('target', 'Unknown')} | Name: {kwargs.get('name', 'Unnamed')}")
    original_thread_init(self, *args, **kwargs)

threading.Thread.__init__ = tracked_thread_init

# Track all exceptions
def exception_handler(exc_type, exc_value, exc_traceback):
    """Log all uncaught exceptions"""
    if exc_type != KeyboardInterrupt:
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        log_crash(f"UNCAUGHT EXCEPTION:\n{error_msg}")
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = exception_handler

# Import after setting up debugging
try:
    log_crash("Importing PySide6...")
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer, QObject, Signal
    
    log_crash("Importing application modules...")
    from src.gui.pages.file_search_page import FileSearchPage
    from src.rag.file_processor import FileProcessor
    from src.utils.logger import Logger
    
    # Patch FileProcessor to add logging
    if hasattr(FileProcessor, 'process_file'):
        original_process_file = FileProcessor.process_file
        
        def logged_process_file(self, file_path, *args, **kwargs):
            log_crash(f"INDEXING FILE: {file_path}")
            try:
                result = original_process_file(self, file_path, *args, **kwargs)
                log_crash(f"INDEXED OK: {file_path}")
                return result
            except Exception as e:
                log_crash(f"INDEXING ERROR: {file_path} - {e}")
                raise
        
        FileProcessor.process_file = logged_process_file
    
except Exception as e:
    log_crash(f"Import error: {e}")
    traceback.print_exc()
    sys.exit(1)

class IndexingMonitor(QObject):
    """Monitor indexing progress and detect hangs"""
    
    indexing_hung = Signal()
    
    def __init__(self):
        super().__init__()
        self.last_activity = time.time()
        self.indexing_active = False
        self.files_processed = 0
        
        # Check for hangs every 10 seconds
        self.hang_timer = QTimer()
        self.hang_timer.timeout.connect(self.check_for_hang)
        self.hang_timer.start(10000)
        
    def activity_detected(self, activity_type="general"):
        """Update last activity timestamp"""
        self.last_activity = time.time()
        log_crash(f"ACTIVITY: {activity_type}")
        
    def file_processed(self):
        """Track file processing"""
        self.files_processed += 1
        self.activity_detected(f"File processed (total: {self.files_processed})")
        
    def indexing_started(self):
        """Mark indexing as active"""
        self.indexing_active = True
        self.last_activity = time.time()
        log_crash("INDEXING STARTED")
        
    def indexing_stopped(self):
        """Mark indexing as inactive"""
        self.indexing_active = False
        log_crash(f"INDEXING STOPPED - Processed {self.files_processed} files")
        
    def check_for_hang(self):
        """Check if indexing has hung"""
        if self.indexing_active:
            idle_time = time.time() - self.last_activity
            if idle_time > 30:  # 30 seconds without activity
                log_crash(f"WARNING: Indexing appears hung (idle for {idle_time:.0f}s)")
                self.indexing_hung.emit()

def main():
    """Run the test with comprehensive monitoring"""
    log_crash("Starting monitored test...")
    
    app = QApplication(sys.argv)
    
    # Create activity monitor
    monitor = IndexingMonitor()
    
    # Create file search page
    log_crash("Creating FileSearchPage...")
    search_page = FileSearchPage()
    
    # Hook into indexing signals if available
    if hasattr(search_page, 'indexing_status'):
        status_widget = search_page.indexing_status
        
        # Connect to any available signals
        if hasattr(status_widget, 'indexing_started'):
            status_widget.indexing_started.connect(monitor.indexing_started)
        if hasattr(status_widget, 'indexing_stopped'):
            status_widget.indexing_stopped.connect(monitor.indexing_stopped)
        if hasattr(status_widget, 'file_processed'):
            status_widget.file_processed.connect(monitor.file_processed)
    
    # Monitor for hang
    monitor.indexing_hung.connect(lambda: log_crash("CRITICAL: Indexing hang detected!"))
    
    # Add periodic heartbeat
    heartbeat_timer = QTimer()
    heartbeat_count = 0
    
    def heartbeat():
        nonlocal heartbeat_count
        heartbeat_count += 1
        log_crash(f"HEARTBEAT #{heartbeat_count} - App still running")
    
    heartbeat_timer.timeout.connect(heartbeat)
    heartbeat_timer.start(15000)  # Every 15 seconds
    
    # Show the page
    search_page.show()
    log_crash("FileSearchPage shown, entering event loop...")
    
    # Track app exit
    app.aboutToQuit.connect(lambda: log_crash("APP ABOUT TO QUIT"))
    
    try:
        exit_code = app.exec()
        log_crash(f"App exited normally with code: {exit_code}")
    except Exception as e:
        log_crash(f"App crashed with exception: {e}")
        traceback.print_exc()
        raise
    finally:
        log_crash("=== Test completed ===")

if __name__ == "__main__":
    main()