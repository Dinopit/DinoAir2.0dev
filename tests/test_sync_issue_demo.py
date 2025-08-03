"""
Demonstrate the sync issue between QSettings and Database
"""

import os
import sys
from pathlib import Path
from PySide6.QtCore import QSettings

# Disable Watchdog
os.environ['DINOAIR_DISABLE_WATCHDOG'] = '1'

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.utils.logger import Logger
from src.database.file_search_db import FileSearchDB
from src.rag.file_processor import FileProcessor
from src.rag.directory_validator import DirectoryValidator


def demonstrate_sync_issue():
    """Demonstrate the sync issue step by step"""
    logger = Logger()
    logger.info("\n" + "="*60)
    logger.info("DEMONSTRATING SYNC ISSUE")
    logger.info("="*60)
    
    user_name = "default_user"
    test_dir = r"C:\Users\DinoP\Documents\TestFolder"
    
    # Step 1: Simulate GUI saving to QSettings
    logger.info("\nSTEP 1: GUI saves directory to QSettings")
    settings = QSettings("DinoAir", "FileSearch")
    settings.setValue("allowed_directories", [test_dir])
    settings.sync()
    logger.info(f"   Saved to QSettings: {[test_dir]}")
    
    # Step 2: Show what FileProcessor sees
    logger.info("\nSTEP 2: FileProcessor loads from Database")
    db = FileSearchDB(user_name)
    allowed_result = db.get_search_settings("allowed_directories")
    
    if allowed_result.get("success"):
        db_dirs = allowed_result.get("setting_value", [])
    else:
        db_dirs = []
    
    logger.info(f"   Database has: {db_dirs}")
    
    # Step 3: Create FileProcessor and test validation
    logger.info("\nSTEP 3: FileProcessor validates the directory")
    processor = FileProcessor(user_name)
    
    # Get validator state
    validator_stats = processor.directory_validator.get_statistics()
    logger.info(f"   Validator allowed dirs: "
                f"{validator_stats['allowed_directories']}")
    
    # Test validation
    validation = processor.directory_validator.validate_path(test_dir)
    logger.info(f"   Validation result: {validation}")
    
    # Step 4: Show the mismatch
    logger.info("\nSTEP 4: THE MISMATCH")
    qsettings_dirs = settings.value("allowed_directories", [], list)
    logger.info(f"   QSettings has: {qsettings_dirs}")
    logger.info(f"   Database has: {db_dirs}")
    logger.info(f"   FileProcessor sees: "
                f"{validator_stats['allowed_directories']}")
    
    if qsettings_dirs and not db_dirs:
        logger.error("\n   ❌ SYNC ISSUE CONFIRMED!")
        logger.error("   GUI saved directories but FileProcessor can't see them")
        logger.error("   This causes 'Access denied' errors during indexing")
    
    # Step 5: Show the fix
    logger.info("\nSTEP 5: THE FIX (What should happen)")
    logger.info("   When GUI saves directory settings:")
    logger.info("   1. Save to QSettings (for GUI persistence)")
    logger.info("   2. ALSO save to Database using:")
    logger.info("      db.update_search_settings('allowed_directories', dirs)")
    logger.info("   3. Then FileProcessor will see the settings!")
    
    # Demonstrate the fix
    logger.info("\n   Applying the fix...")
    db.update_search_settings('allowed_directories', qsettings_dirs)
    
    # Re-create processor to reload settings
    processor2 = FileProcessor(user_name)
    validator_stats2 = processor2.directory_validator.get_statistics()
    validation2 = processor2.directory_validator.validate_path(test_dir)
    
    logger.info(f"   After fix - Validator sees: "
                f"{validator_stats2['allowed_directories']}")
    logger.info(f"   After fix - Validation result: {validation2}")


if __name__ == "__main__":
    demonstrate_sync_issue()