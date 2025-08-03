"""
Diagnostic script to identify the RAG indexing synchronization issue
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

def diagnose_sync_issue():
    """Diagnose the directory settings synchronization issue"""
    logger = Logger()
    logger.info("\n" + "="*60)
    logger.info("RAG INDEXING SYNC ISSUE DIAGNOSIS")
    logger.info("="*60)
    
    user_name = "default_user"
    
    # 1. Check QSettings
    logger.info("\n1. CHECKING QSETTINGS (GUI Storage):")
    settings = QSettings("DinoAir", "FileSearch")
    allowed_dirs_qsettings = settings.value("allowed_directories", [], list)
    excluded_dirs_qsettings = settings.value("excluded_directories", [], list)
    
    logger.info(f"   QSettings Allowed Directories: {allowed_dirs_qsettings}")
    logger.info(f"   QSettings Excluded Directories: {excluded_dirs_qsettings}")
    
    # 2. Check FileSearchDB
    logger.info("\n2. CHECKING FILESEARCHDB (Database Storage):")
    db = FileSearchDB(user_name)
    
    # Get allowed directories from database
    allowed_result = db.get_search_settings("allowed_directories")
    if allowed_result.get("success"):
        allowed_dirs_db = allowed_result.get("setting_value", [])
    else:
        allowed_dirs_db = []
        logger.warning("   No allowed_directories found in database")
    
    # Get excluded directories from database
    excluded_result = db.get_search_settings("excluded_directories")
    if excluded_result.get("success"):
        excluded_dirs_db = excluded_result.get("setting_value", [])
    else:
        excluded_dirs_db = []
        logger.warning("   No excluded_directories found in database")
    
    logger.info(f"   Database Allowed Directories: {allowed_dirs_db}")
    logger.info(f"   Database Excluded Directories: {excluded_dirs_db}")
    
    # 3. Check DirectoryValidator
    logger.info("\n3. CHECKING DIRECTORY VALIDATOR:")
    validator = DirectoryValidator()
    
    # Load from database (as FileProcessor does)
    if allowed_dirs_db:
        validator.set_allowed_directories(allowed_dirs_db)
    if excluded_dirs_db:
        validator.set_excluded_directories(excluded_dirs_db)
    
    stats = validator.get_statistics()
    logger.info(f"   Validator Stats: {stats}")
    
    # 4. Test validation on a sample directory
    test_dir = r"C:\Users\DinoP\Documents"
    logger.info(f"\n4. TESTING VALIDATION ON: {test_dir}")
    
    validation_result = validator.validate_path(test_dir)
    logger.info(f"   Validation Result: {validation_result}")
    
    # 5. Compare QSettings vs Database
    logger.info("\n5. SYNCHRONIZATION ANALYSIS:")
    
    # Check if they match
    qsettings_set = set(allowed_dirs_qsettings)
    db_set = set(allowed_dirs_db)
    
    if qsettings_set == db_set:
        logger.info("   ✓ Allowed directories ARE synchronized")
    else:
        logger.error("   ✗ Allowed directories NOT synchronized!")
        logger.error(f"     In QSettings but not in DB: {qsettings_set - db_set}")
        logger.error(f"     In DB but not in QSettings: {db_set - qsettings_set}")
    
    # 6. Check FileProcessor's view
    logger.info("\n6. FILEPROCESSOR DIRECTORY LOADING:")
    processor = FileProcessor(user_name)
    
    # Access the processor's validator
    proc_validator = processor.directory_validator
    proc_stats = proc_validator.get_statistics()
    logger.info(f"   FileProcessor Validator Stats: {proc_stats}")
    
    # 7. Database statistics
    logger.info("\n7. DATABASE STATISTICS:")
    file_stats = db.get_indexed_files_stats()
    logger.info(f"   Total Files: {file_stats.get('total_files', 0)}")
    logger.info(f"   Total Chunks: {file_stats.get('total_chunks', 0)}")
    logger.info(f"   Total Embeddings: {file_stats.get('total_embeddings', 0)}")
    
    # 8. Recommendations
    logger.info("\n8. DIAGNOSIS SUMMARY:")
    logger.info("   PROBLEM IDENTIFIED: Directory settings are stored in two places:")
    logger.info("   - GUI saves to QSettings (file_search_page.py:1135-1160)")
    logger.info("   - FileProcessor loads from FileSearchDB (file_processor.py:90-100)")
    logger.info("   - This causes validation failures when indexing")
    
    logger.info("\n9. REQUIRED FIXES:")
    logger.info("   1. Modify _on_directory_settings_changed() to save to BOTH QSettings and FileSearchDB")
    logger.info("   2. Add auto-add functionality in _start_indexing() to add directory to allowed list")
    logger.info("   3. Improve error reporting to surface these validation failures")

if __name__ == "__main__":
    diagnose_sync_issue()