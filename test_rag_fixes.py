"""
Test script to verify the RAG indexing fixes
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


def test_fixes():
    """Test that the fixes are working"""
    logger = Logger()
    logger.info("\n" + "="*60)
    logger.info("TESTING RAG INDEXING FIXES")
    logger.info("="*60)
    
    user_name = "default_user"
    test_dir = r"C:\Users\DinoP\Documents"
    
    # Step 1: Simulate GUI setting directories
    logger.info("\nSTEP 1: Simulating GUI directory settings")
    settings = QSettings("DinoAir", "FileSearch")
    settings.setValue("allowed_directories", [test_dir])
    settings.sync()
    
    # Step 2: Also save to database (as the fix does)
    logger.info("\nSTEP 2: Syncing to database (fix applied)")
    db = FileSearchDB(user_name)
    result = db.update_search_settings("allowed_directories", [test_dir])
    logger.info(f"   Database update result: {result}")
    
    # Step 3: Create new FileProcessor and verify it sees the settings
    logger.info("\nSTEP 3: Creating FileProcessor to verify sync")
    processor = FileProcessor(user_name)
    
    # Check validator stats
    stats = processor.directory_validator.get_statistics()
    logger.info(f"   FileProcessor sees allowed dirs: {stats['allowed_directories']}")
    logger.info(f"   Has restrictions: {stats['has_restrictions']}")
    
    # Step 4: Test validation
    logger.info("\nSTEP 4: Testing directory validation")
    validation = processor.directory_validator.validate_path(test_dir)
    logger.info(f"   Validation result: {validation}")
    
    # Step 5: Test processing a single file
    logger.info("\nSTEP 5: Testing file processing")
    
    # Find a test file
    test_files = []
    for file in os.listdir(test_dir):
        if file.endswith('.txt'):
            test_files.append(os.path.join(test_dir, file))
            if len(test_files) >= 1:
                break
    
    if test_files:
        test_file = test_files[0]
        logger.info(f"   Processing test file: {test_file}")
        
        result = processor.process_file(test_file, force_reprocess=True)
        
        if result['success']:
            logger.info(f"   ✓ SUCCESS: File processed successfully")
            logger.info(f"   Chunks created: {len(result.get('chunks', []))}")
        else:
            logger.error(f"   ✗ FAILED: {result.get('error')}")
    else:
        logger.warning("   No .txt files found for testing")
    
    # Step 6: Verify sync is working
    logger.info("\nSTEP 6: VERIFICATION")
    
    # Check both storages have the same data
    qsettings_dirs = settings.value("allowed_directories", [], list)
    db_result = db.get_search_settings("allowed_directories")
    db_dirs = db_result.get("setting_value", []) if db_result.get("success") else []
    
    logger.info(f"   QSettings has: {qsettings_dirs}")
    logger.info(f"   Database has: {db_dirs}")
    
    if set(qsettings_dirs) == set(db_dirs):
        logger.info("   ✓ Directory settings are SYNCHRONIZED!")
    else:
        logger.error("   ✗ Directory settings NOT synchronized")
    
    # Final summary
    logger.info("\n" + "="*60)
    logger.info("FIX VERIFICATION COMPLETE")
    logger.info("="*60)
    
    if validation['valid'] and set(qsettings_dirs) == set(db_dirs):
        logger.info("✓ All fixes are working correctly!")
        logger.info("✓ Directory sync is operational")
        logger.info("✓ File processing should now work in the GUI")
    else:
        logger.error("✗ Some issues remain - check the logs above")


if __name__ == "__main__":
    test_fixes()