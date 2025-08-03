"""Debug script to identify unexpected GUI shutdown after ~45 seconds"""

import sys
import os
import atexit
import signal
import logging
from datetime import datetime
from pathlib import Path

# Create debug log
log_path = Path("shutdown_debug.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SHUTDOWN_DEBUG")

# Track shutdown source
shutdown_source = "UNKNOWN"

def log_exit(code=None):
    """Log when exit is called"""
    global shutdown_source
    import traceback
    shutdown_source = "EXIT_CALLED"
    logger.critical(f"EXIT CALLED with code: {code}")
    logger.critical("Stack trace:")
    for line in traceback.format_stack():
        logger.critical(line.strip())

def log_atexit():
    """Log at exit"""
    logger.critical(f"ATEXIT: Application shutting down. Source: {shutdown_source}")
    logger.critical(f"Exit time: {datetime.now()}")

def signal_handler(signum, frame):
    """Log signal reception"""
    global shutdown_source
    shutdown_source = f"SIGNAL_{signum}"
    logger.critical(f"SIGNAL {signum} received")
    
# Register handlers
atexit.register(log_atexit)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Monkey patch exit functions to track source
original_exit = sys.exit
original_os_exit = os._exit

def tracked_sys_exit(*args, **kwargs):
    log_exit(args[0] if args else None)
    original_exit(*args, **kwargs)

def tracked_os_exit(*args, **kwargs):
    log_exit(args[0] if args else None)
    original_os_exit(*args, **kwargs)

sys.exit = tracked_sys_exit
os._exit = tracked_os_exit

# Import after patching
logger.info("=" * 60)
logger.info("STARTING DEBUG SESSION")
logger.info(f"Script: {sys.argv[0]}")
logger.info(f"Arguments: {sys.argv[1:]}")
logger.info("=" * 60)

try:
    # Check which script is being run
    script_name = Path(sys.argv[0]).name
    logger.info(f"Running script: {script_name}")
    
    # Patch Watchdog if it exists
    try:
        from src.utils.Watchdog import ResourceWatchdog
        original_emergency = ResourceWatchdog._perform_emergency_shutdown
        
        def logged_emergency_shutdown(self):
            global shutdown_source
            shutdown_source = "WATCHDOG_EMERGENCY"
            logger.critical("WATCHDOG EMERGENCY SHUTDOWN TRIGGERED!")
            logger.critical(f"Self terminate enabled: {self.self_terminate_on_critical}")
            original_emergency(self)
            
        ResourceWatchdog._perform_emergency_shutdown = logged_emergency_shutdown
        logger.info("Watchdog emergency shutdown patched for logging")
    except Exception as e:
        logger.info(f"Could not patch Watchdog: {e}")
    
    # Patch QTimer if using Qt
    try:
        from PySide6.QtCore import QTimer, QCoreApplication
        original_quit = QCoreApplication.quit
        
        def logged_quit(*args, **kwargs):
            global shutdown_source
            shutdown_source = "QT_APP_QUIT"
            logger.critical("QT APPLICATION QUIT CALLED")
            import traceback
            for line in traceback.format_stack():
                logger.critical(line.strip())
            original_quit(*args, **kwargs)
            
        QCoreApplication.quit = logged_quit
        logger.info("Qt application quit patched for logging")
        
        # Log all QTimer.singleShot calls
        original_singleshot = QTimer.singleShot
        
        def logged_singleshot(msec, *args, **kwargs):
            if len(args) > 0:
                callback = str(args[0])
                if 'quit' in callback.lower() or 'close' in callback.lower():
                    logger.warning(f"QTimer.singleShot({msec}ms) scheduled for: {callback}")
            return original_singleshot(msec, *args, **kwargs)
            
        QTimer.singleShot = logged_singleshot
        logger.info("QTimer.singleShot patched for logging")
    except Exception as e:
        logger.info(f"Could not patch Qt: {e}")
    
    # Now run the actual script
    if script_name == "test_directory_selection.py":
        logger.warning("Running TEST script - may have auto-close timers!")
        import test_directory_selection
    elif script_name == "main.py":
        logger.info("Running main application")
        import main
    else:
        logger.warning(f"Unknown script: {script_name}")
        
except Exception as e:
    shutdown_source = f"EXCEPTION: {type(e).__name__}"
    logger.exception("Exception during execution")
    raise