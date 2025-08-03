"""
Logger utility for DinoAir
Provides centralized logging functionality
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class Logger:
    """Centralized logging utility"""
    
    _instance: Optional['Logger'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'Logger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.setup_logging()
            Logger._initialized = True
    
    def setup_logging(self) -> None:
        """Setup logging configuration"""
        # Create logs directory
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"dinoair_{timestamp}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('DinoAir')
    
    def info(self, message: str) -> None:
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log error message"""
        self.logger.error(message)
    
    def debug(self, message: str) -> None:
        """Log debug message"""
        self.logger.debug(message)
    
    def critical(self, message: str) -> None:
        """Log critical message"""
        self.logger.critical(message)


# Convenience functions for direct import
def log_info(message: str) -> None:
    Logger().info(message)

def log_warning(message: str) -> None:
    Logger().warning(message)

def log_error(message: str) -> None:
    Logger().error(message)

def log_debug(message: str) -> None:
    Logger().debug(message)

def log_critical(message: str) -> None:
    Logger().critical(message)
