#!/usr/bin/env python3
"""
Check for black color references in GUI files
"""
import os
import re
from pathlib import Path

# Color patterns to search for
BLACK_PATTERNS = [
    r'#000000',       # Full hex black
    r'#000(?![0-9A-Fa-f])',  # Short hex black (not followed by more hex)
    r'\bblack\b',     # Word "black" as color
    r'rgb\s*\(\s*0\s*,\s*0\s*,\s*0\s*\)',      # RGB black
    r'rgba\s*\(\s*0\s*,\s*0\s*,\s*0\s*,',      # RGBA black
    r'color:\s*["\']?#(?:0{3}|0{6})["\']?',    # Color property with black
    r'BLACK',         # Uppercase BLACK constant
    r'Qt\.(?:GlobalColor\.)?black',             # Qt black color
    r'QColor\s*\(\s*0\s*,\s*0\s*,\s*0\s*\)',   # QColor black
    r'#1[0-2][0-2][0-2][0-2][0-2]',            # Very dark grays (almost black)
    r'#0[0-5][0-5][0-5][0-5][0-5]',            # Near black colors
]

# Additional patterns to check for potentially dark text
DARK_PATTERNS = [
    r'#333333',       # Dark gray
    r'#222222',       # Darker gray  
    r'#111111',       # Very dark gray
    r'#2B2B2B',       # Common dark theme background
    r'#1E1E1E',       # VS Code dark background
]


def check_file_for_black(filepath):
    """Check a file for black color references"""
    black_refs = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line_num, line in enumerate(lines, 1):
            # Skip comments and imports
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('//'):
                continue
                
            for pattern in BLACK_PATTERNS:
                matches = list(re.finditer(pattern, line, re.IGNORECASE))
                for match in matches:
                    # Skip if it's in a comment
                    comment_pos = line.find('#')
                    if comment_pos != -1 and match.start() > comment_pos:
                        continue
                        
                    # Skip certain contexts
                    context = line[max(0, match.start()-20):match.end()+20]
                    
                    # Skip if it's part of a background color or border
                    if any(skip in context.lower() for skip in [
                        'background', 'border', 'shadow', 'outline',
                        'frame', 'separator', 'divider'
                    ]):
                        continue
                    
                    # Look for text/color context
                    if any(text_indicator in context.lower() for text_indicator in [
                        'color:', 'text', 'label', 'font', 'foreground'
                    ]):
                        black_refs.append({
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': pattern,
                            'match': match.group()
                        })
                        
            # Check dark patterns too
            for pattern in DARK_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    context = line.lower()
                    if any(text_indicator in context for text_indicator in [
                        'color:', 'text', 'label', 'font', 'foreground'
                    ]):
                        black_refs.append({
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': pattern,
                            'match': pattern,
                            'dark': True
                        })
                        
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        
    return black_refs


def main():
    """Main function to check all GUI files"""
    print("Checking for Black/Dark Text Color References in GUI Files")
    print("=" * 80)
    
    # Define directories to check
    gui_dirs = [
        'src/gui/pages',
        'src/gui/components',
        'src/gui'
    ]
    
    total_refs = 0
    files_with_black = []
    
    for dir_path in gui_dirs:
        if not os.path.exists(dir_path):
            print(f"Directory not found: {dir_path}")
            continue
            
        print(f"\nChecking {dir_path}...")
        
        for file_path in Path(dir_path).glob('*.py'):
            # Skip __pycache__ and test files
            if '__pycache__' in str(file_path) or 'test_' in file_path.name:
                continue
                
            refs = check_file_for_black(file_path)
            if refs:
                files_with_black.append((file_path, refs))
                total_refs += len(refs)
                
    # Report findings
    print("\n" + "=" * 80)
    print(f"SUMMARY: Found {total_refs} black/dark text references in {len(files_with_black)} files")
    print("=" * 80)
    
    if files_with_black:
        print("\nDetailed Findings:\n")
        for file_path, refs in files_with_black:
            print(f"\n📄 {file_path}")
            print("-" * 60)
            for ref in refs:
                dark_indicator = " [DARK GRAY]" if ref.get('dark') else ""
                print(f"  Line {ref['line']}: {ref['match']}{dark_indicator}")
                print(f"    >> {ref['content']}")
    else:
        print("\n✅ No black text color references found!")
        
    # Check for specific color constants
    print("\n" + "=" * 80)
    print("CHECKING COLOR CONSTANTS:")
    print("=" * 80)
    
    # Check if there are any color constants that might be black
    colors_file = Path('src/utils/colors.py')
    if colors_file.exists():
        print(f"\nChecking {colors_file}...")
        with open(colors_file, 'r') as f:
            content = f.read()
            for line_num, line in enumerate(content.splitlines(), 1):
                if any(pattern in line for pattern in ['#000', 'black', '0, 0, 0']):
                    print(f"  Line {line_num}: {line.strip()}")


if __name__ == "__main__":
    main()