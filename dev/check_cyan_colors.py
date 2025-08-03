#!/usr/bin/env python3
"""
Check for remaining cyan color references in GUI files
"""
import os
import re
from pathlib import Path

# Color patterns to search for
CYAN_PATTERNS = [
    r'ACCENT_TEXT',
    r'STUDIOS_CYAN',
    r'#00BFFF',  # Direct cyan hex color
    r'#00CED1',  # Dark turquoise
    r'#00FFFF',  # Aqua/Cyan
]

def check_file_for_cyan(filepath):
    """Check a file for cyan color references"""
    cyan_refs = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line_num, line in enumerate(lines, 1):
            for pattern in CYAN_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    cyan_refs.append({
                        'line': line_num,
                        'content': line.strip(),
                        'pattern': pattern
                    })
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        
    return cyan_refs

def main():
    """Main function to check all GUI files"""
    print("Checking for Cyan Color References in GUI Files")
    print("=" * 80)
    
    # Define directories to check
    gui_dirs = [
        'src/gui/pages',
        'src/gui/components'
    ]
    
    total_refs = 0
    files_with_cyan = []
    
    for dir_path in gui_dirs:
        if not os.path.exists(dir_path):
            print(f"Directory not found: {dir_path}")
            continue
            
        print(f"\nChecking {dir_path}...")
        
        for file_path in Path(dir_path).glob('*.py'):
            refs = check_file_for_cyan(file_path)
            if refs:
                files_with_cyan.append((file_path, refs))
                total_refs += len(refs)
                
    # Report findings
    print("\n" + "=" * 80)
    print(f"SUMMARY: Found {total_refs} cyan color references in {len(files_with_cyan)} files")
    print("=" * 80)
    
    if files_with_cyan:
        print("\nDetailed Findings:\n")
        for file_path, refs in files_with_cyan:
            print(f"\n📄 {file_path}")
            print("-" * 60)
            for ref in refs:
                print(f"  Line {ref['line']}: {ref['pattern']}")
                print(f"    >> {ref['content']}")
    else:
        print("\n✅ No cyan color references found!")
        
    # Additional check for specific problem areas
    print("\n" + "=" * 80)
    print("SPECIFIC PROBLEM AREAS TO FIX:")
    print("=" * 80)
    
    specific_issues = [
        ("src/gui/pages/artifacts_page.py", 416, "Dropdown arrow color"),
        ("src/gui/pages/artifacts_page.py", 774, "View Project button"),
        ("src/gui/pages/artifacts_page.py", 953, "Content header"),
    ]
    
    for file, line, desc in specific_issues:
        if os.path.exists(file):
            print(f"\n⚠️  {desc} at {file}:{line}")

if __name__ == "__main__":
    main()