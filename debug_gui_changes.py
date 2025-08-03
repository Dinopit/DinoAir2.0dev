#!/usr/bin/env python3
"""
Diagnostic script to check why GUI changes aren't being reflected
"""

import os
import sys
import importlib
import hashlib
from datetime import datetime
from pathlib import Path

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check_file_modifications():
    """Check if our modified files have recent timestamps"""
    print_section("File Modification Times")
    
    files_to_check = [
        "src/gui/pages/notes_page.py",
        "src/gui/pages/artifacts_page.py",
        "src/gui/pages/appointments_page.py",
        "src/gui/pages/file_search_page.py",
        "src/gui/pages/smart_timer_page.py",
        "src/gui/pages/settings_page.py",
        "src/gui/pages/tasks_page.py",
        "src/gui/components/enhanced_chat_tab.py",
        "src/gui/components/enhanced_chat_history.py",
        "src/gui/components/note_editor.py",
        "src/gui/components/notes_search.py",
        "src/gui/components/tag_input_widget.py",
        "src/gui/components/artifact_panel.py",
    ]
    
    current_time = datetime.now()
    for file_path in files_to_check:
        if os.path.exists(file_path):
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            time_diff = current_time - mtime
            minutes_ago = time_diff.total_seconds() / 60
            print(f"{file_path}: Modified {minutes_ago:.1f} minutes ago")
        else:
            print(f"{file_path}: FILE NOT FOUND")

def check_python_cache():
    """Check for Python bytecode cache files"""
    print_section("Python Cache Files")
    
    pycache_dirs = []
    for root, dirs, files in os.walk("src"):
        if "__pycache__" in dirs:
            pycache_dirs.append(os.path.join(root, "__pycache__"))
    
    print(f"Found {len(pycache_dirs)} __pycache__ directories")
    
    # Check if .pyc files are newer than .py files
    issues_found = 0
    for cache_dir in pycache_dirs[:5]:  # Check first 5 for brevity
        py_dir = os.path.dirname(cache_dir)
        print(f"\nChecking {py_dir}:")
        
        for pyc_file in os.listdir(cache_dir):
            if pyc_file.endswith('.pyc'):
                py_name = pyc_file.split('.')[0] + '.py'
                py_path = os.path.join(py_dir, py_name)
                pyc_path = os.path.join(cache_dir, pyc_file)
                
                if os.path.exists(py_path):
                    py_mtime = os.path.getmtime(py_path)
                    pyc_mtime = os.path.getmtime(pyc_path)
                    
                    if pyc_mtime > py_mtime:
                        print(f"  ✓ {py_name}: Cache is newer (expected)")
                    else:
                        print(f"  ⚠ {py_name}: Source is newer than cache!")
                        issues_found += 1
    
    if issues_found > 0:
        print(f"\n⚠ Found {issues_found} files where cache might be stale")

def check_imports():
    """Check if modules can be imported and show their file paths"""
    print_section("Module Import Paths")
    
    modules_to_check = [
        "src.gui.pages.notes_page",
        "src.gui.pages.artifacts_page",
        "src.gui.components.enhanced_chat_tab",
        "src.utils.colors",
    ]
    
    for module_name in modules_to_check:
        try:
            # Try to import the module
            module = importlib.import_module(module_name)
            file_path = getattr(module, '__file__', 'No file path')
            print(f"{module_name}:")
            print(f"  File: {file_path}")
            
            # Check if it has our expected changes
            if module_name == "src.utils.colors":
                if hasattr(module, 'DinoPitColors'):
                    colors = module.DinoPitColors
                    print(f"  PRIMARY_TEXT: {getattr(colors, 'PRIMARY_TEXT', 'NOT FOUND')}")
                    print(f"  ACCENT_TEXT: {getattr(colors, 'ACCENT_TEXT', 'NOT FOUND')}")
        except ImportError as e:
            print(f"{module_name}: IMPORT ERROR - {e}")

def check_working_directory():
    """Check current working directory and Python path"""
    print_section("Working Directory & Python Path")
    
    print(f"Current Working Directory: {os.getcwd()}")
    print(f"Script Location: {os.path.abspath(__file__)}")
    print(f"\nPython Path (first 5 entries):")
    for i, path in enumerate(sys.path[:5]):
        print(f"  {i}: {path}")

def check_file_content():
    """Check if specific changes are present in files"""
    print_section("Checking for Specific Changes")
    
    # Check if our placeholder styling is present
    test_cases = [
        {
            'file': 'src/gui/pages/file_search_page.py',
            'search': 'rgba(255, 255, 255, 0.5)',
            'description': 'Placeholder text styling'
        },
        {
            'file': 'src/gui/pages/tasks_page.py',
            'search': 'QLineEdit::placeholder',
            'description': 'QLineEdit placeholder selector'
        },
        {
            'file': 'src/gui/components/enhanced_chat_tab.py',
            'search': 'QLineEdit::placeholder',
            'description': 'Chat tab placeholder styling'
        }
    ]
    
    for test in test_cases:
        if os.path.exists(test['file']):
            with open(test['file'], 'r', encoding='utf-8') as f:
                content = f.read()
                if test['search'] in content:
                    print(f"✓ {test['file']}: {test['description']} FOUND")
                else:
                    print(f"✗ {test['file']}: {test['description']} NOT FOUND")
        else:
            print(f"✗ {test['file']}: FILE NOT FOUND")

def suggest_solutions():
    """Suggest solutions based on findings"""
    print_section("Suggested Solutions")
    
    print("1. **Restart the Application**")
    print("   The most common issue - changes require app restart:")
    print("   - Close DinoAir 2.0 completely")
    print("   - Make sure no Python processes are running")
    print("   - Start the application again")
    
    print("\n2. **Clear Python Cache**")
    print("   Remove cached bytecode files:")
    print("   - Run: python -B main.py (to ignore bytecode)")
    print("   - Or delete all __pycache__ directories")
    
    print("\n3. **Check Virtual Environment**")
    print("   Ensure you're running in the correct environment:")
    print("   - Verify the Python interpreter path")
    print("   - Check if the venv is activated")
    
    print("\n4. **Force Module Reload (if using interactive mode)**")
    print("   If testing in Python console:")
    print("   - importlib.reload(module_name)")
    print("   - Or restart the Python interpreter")

if __name__ == "__main__":
    print("DinoAir 2.0 GUI Change Diagnostic")
    print("=" * 60)
    
    check_working_directory()
    check_file_modifications()
    check_file_content()
    check_python_cache()
    check_imports()
    suggest_solutions()
    
    print("\n" + "=" * 60)
    print("Diagnostic Complete")