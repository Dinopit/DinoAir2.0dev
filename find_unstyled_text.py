#!/usr/bin/env python3
"""
Find widgets that might be using default (black) text color
"""
import os
import re
from pathlib import Path

# Widget patterns that typically display text
TEXT_WIDGETS = [
    r'QLabel\s*\(',
    r'QPushButton\s*\(',
    r'QLineEdit\s*\(',
    r'QTextEdit\s*\(',
    r'QPlainTextEdit\s*\(',
    r'QComboBox\s*\(',
    r'QListWidget\s*\(',
    r'QTableWidget\s*\(',
    r'QTreeWidget\s*\(',
    r'QCheckBox\s*\(',
    r'QRadioButton\s*\(',
    r'QGroupBox\s*\(',
    r'QSpinBox\s*\(',
    r'QDoubleSpinBox\s*\(',
    r'QDateEdit\s*\(',
    r'QTimeEdit\s*\(',
    r'QDateTimeEdit\s*\(',
    r'\.setText\s*\(',
    r'\.setPlaceholderText\s*\(',
    r'\.addItem\s*\(',
    r'\.setTitle\s*\(',
]

def check_widget_styling(filepath):
    """Check if widgets have explicit color styling"""
    unstyled_widgets = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
            
        # Track widget declarations
        for line_num, line in enumerate(lines, 1):
            for pattern in TEXT_WIDGETS:
                if re.search(pattern, line):
                    # Found a widget, now check if it has styling
                    widget_name = extract_widget_name(line)
                    if widget_name:
                        # Look for styling in the next 20 lines
                        has_style = False
                        for i in range(line_num, min(line_num + 20, len(lines))):
                            check_line = lines[i-1]
                            if widget_name in check_line and any(style in check_line for style in [
                                'setStyleSheet', 'color:', 'setForeground', 'setPalette'
                            ]):
                                has_style = True
                                break
                        
                        if not has_style:
                            unstyled_widgets.append({
                                'line': line_num,
                                'content': line.strip(),
                                'widget': widget_name,
                                'type': pattern
                            })
                            
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        
    return unstyled_widgets

def extract_widget_name(line):
    """Try to extract widget variable name from line"""
    # Match patterns like: self.widget = QLabel() or widget = QLabel()
    match = re.search(r'(\w+)\s*=\s*Q\w+\s*\(', line)
    if match:
        return match.group(1)
    
    # Match patterns like: QLabel("text")
    match = re.search(r'(Q\w+)\s*\(', line)
    if match:
        return None  # Anonymous widget
        
    return None

def find_style_definitions(filepath):
    """Find any global style definitions that might set black text"""
    style_issues = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line_num, line in enumerate(lines, 1):
            # Look for stylesheet definitions without explicit color
            if 'setStyleSheet' in line and 'color:' not in line:
                # Check if this stylesheet might need color
                if any(widget in line for widget in ['QLabel', 'QPushButton', 'QLineEdit']):
                    style_issues.append({
                        'line': line_num,
                        'content': line.strip(),
                        'issue': 'Stylesheet without explicit color'
                    })
                    
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        
    return style_issues

def main():
    """Main function to find potentially unstyled text widgets"""
    print("Finding Widgets That Might Use Default (Black) Text Color")
    print("=" * 80)
    
    gui_dirs = [
        'src/gui/pages',
        'src/gui/components',
        'src/gui'
    ]
    
    total_unstyled = 0
    files_with_issues = []
    
    for dir_path in gui_dirs:
        if not os.path.exists(dir_path):
            continue
            
        print(f"\nChecking {dir_path}...")
        
        for file_path in Path(dir_path).glob('*.py'):
            if '__pycache__' in str(file_path):
                continue
                
            unstyled = check_widget_styling(file_path)
            style_issues = find_style_definitions(file_path)
            
            if unstyled or style_issues:
                files_with_issues.append((file_path, unstyled, style_issues))
                total_unstyled += len(unstyled)
                
    # Report findings
    print("\n" + "=" * 80)
    print(f"SUMMARY: Found {total_unstyled} potentially unstyled text widgets")
    print("=" * 80)
    
    if files_with_issues:
        print("\nWidgets that may need explicit white text color:\n")
        for file_path, unstyled, style_issues in files_with_issues:
            if unstyled:
                print(f"\n📄 {file_path}")
                print("-" * 60)
                for widget in unstyled[:10]:  # Limit output
                    print(f"  Line {widget['line']}: {widget['type']}")
                    print(f"    >> {widget['content']}")
                if len(unstyled) > 10:
                    print(f"  ... and {len(unstyled) - 10} more")
                    
    # Check specific files that commonly have text
    print("\n" + "=" * 80)
    print("CHECKING KEY FILES FOR TEXT COLOR ISSUES:")
    print("=" * 80)
    
    key_files = [
        'src/gui/main_window.py',
        'src/gui/components/sidebar.py',
        'src/gui/components/topbar.py',
        'src/gui/components/statusbar.py',
    ]
    
    for file_path in key_files:
        if os.path.exists(file_path):
            print(f"\n📄 {file_path}")
            with open(file_path, 'r') as f:
                content = f.read()
                # Look for any QLabel or text-setting without color
                labels_without_color = []
                for i, line in enumerate(content.splitlines(), 1):
                    if ('QLabel' in line or 'setText' in line) and i < len(content.splitlines()):
                        # Check next few lines for color setting
                        next_lines = content.splitlines()[i:i+5]
                        if not any('color' in l for l in next_lines):
                            labels_without_color.append((i, line.strip()))
                
                if labels_without_color:
                    print(f"  Found {len(labels_without_color)} labels potentially without color")
                    for line_num, line in labels_without_color[:5]:
                        print(f"    Line {line_num}: {line}")

if __name__ == "__main__":
    main()