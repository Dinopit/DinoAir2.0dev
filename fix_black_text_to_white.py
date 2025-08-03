#!/usr/bin/env python3
"""
Fix all black/dark text to white in GUI files
"""
import os
import re
from pathlib import Path

# Files and their specific fixes
FIXES = {
    'src/gui/components/topbar.py': [
        {
            'search': 'color: #333;',
            'replace': 'color: #FFFFFF;',
            'description': 'Title label dark gray to white'
        }
    ],
    'src/gui/components/sidebar.py': [
        {
            'search': '''            }}
            QPushButton {{
                text-align: left;''',
            'replace': '''            }}
            QPushButton {{
                color: #FFFFFF;
                text-align: left;''',
            'description': 'Add white text color to buttons'
        }
    ],
    'src/gui/components/statusbar.py': [
        {
            'search': '''    def setup_ui(self):
        """Setup the status bar UI"""
        # Database status
        self.db_status = QLabel("Database: Ready")''',
            'replace': '''    def setup_ui(self):
        """Setup the status bar UI"""
        # Database status
        self.db_status = QLabel("Database: Ready")
        self.db_status.setStyleSheet("color: #FFFFFF;")''',
            'description': 'Add white color to database status label'
        }
    ],
    'src/gui/main_window.py': [
        {
            'search': '''        # Create zoom indicator label
        self.zoom_label = QLabel()
        self._update_zoom_label()''',
            'replace': '''        # Create zoom indicator label
        self.zoom_label = QLabel()
        self.zoom_label.setStyleSheet("color: #FFFFFF;")
        self._update_zoom_label()''',
            'description': 'Add white color to zoom label'
        }
    ]
}

# Generic patterns to add white text color
GENERIC_FIXES = [
    # For QLabel without setStyleSheet
    {
        'pattern': r'(\w+)\s*=\s*QLabel\([^)]*\)\s*$',
        'condition': lambda content, match: f"{match.group(1)}.setStyleSheet" not in content[match.end():match.end()+200],
        'fix': lambda match: f'{match.group(0)}\n{" " * (len(match.group(0)) - len(match.group(0).lstrip()))}{match.group(1)}.setStyleSheet("color: #FFFFFF;")'
    },
    # For QPushButton without color in stylesheet
    {
        'pattern': r'(\w+)\s*=\s*QPushButton\([^)]*\)\s*$',
        'condition': lambda content, match: not has_color_style(content, match.group(1), match.end()),
        'fix': lambda match: f'{match.group(0)}\n{" " * (len(match.group(0)) - len(match.group(0).lstrip()))}{match.group(1)}.setStyleSheet("color: #FFFFFF;")'
    },
    # For QLineEdit without color
    {
        'pattern': r'(\w+)\s*=\s*QLineEdit\([^)]*\)\s*$',
        'condition': lambda content, match: not has_color_style(content, match.group(1), match.end()),
        'fix': lambda match: f'{match.group(0)}\n{" " * (len(match.group(0)) - len(match.group(0).lstrip()))}{match.group(1)}.setStyleSheet("color: #FFFFFF; background-color: #2B3A52; border: 1px solid #4A5A7A; padding: 5px;")'
    },
    # Add color to existing stylesheets without color
    {
        'pattern': r'\.setStyleSheet\s*\(\s*["\']([^"\']*)["\']',
        'condition': lambda content, match: 'color:' not in match.group(1) and any(widget in match.group(1) for widget in ['QLabel', 'QPushButton', 'QLineEdit', 'QTextEdit', 'QComboBox']),
        'fix': lambda match: f'.setStyleSheet("{match.group(1)}{"" if match.group(1).strip().endswith(";") else ";"} color: #FFFFFF;"'
    }
]

def has_color_style(content, widget_name, start_pos):
    """Check if widget has color styling in next 200 chars"""
    check_content = content[start_pos:start_pos+500]
    return (f"{widget_name}.setStyleSheet" in check_content and 
            "color:" in check_content)

def apply_fixes(filepath, fixes):
    """Apply specific fixes to a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for fix in fixes:
            if 'search' in fix:
                content = content.replace(fix['search'], fix['replace'])
                
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    return False

def apply_generic_fixes(filepath):
    """Apply generic pattern-based fixes"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for fix in GENERIC_FIXES:
            pattern = fix['pattern']
            matches = list(re.finditer(pattern, content, re.MULTILINE))
            
            # Process matches in reverse to avoid offset issues
            for match in reversed(matches):
                if fix['condition'](content, match):
                    replacement = fix['fix'](match)
                    content = content[:match.start()] + replacement + content[match.end():]
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    return False

def main():
    """Main function to fix all black text"""
    print("Fixing Black/Dark Text to White in GUI Files")
    print("=" * 80)
    
    # Apply specific fixes
    print("\nApplying specific fixes...")
    for filepath, fixes in FIXES.items():
        if os.path.exists(filepath):
            if apply_fixes(filepath, fixes):
                print(f"✅ Fixed {filepath}")
            else:
                print(f"❌ No changes needed in {filepath}")
        else:
            print(f"⚠️  File not found: {filepath}")
    
    # Apply generic fixes to all GUI files
    print("\nApplying generic fixes to all GUI files...")
    gui_dirs = ['src/gui/pages', 'src/gui/components', 'src/gui']
    
    files_fixed = 0
    for dir_path in gui_dirs:
        if not os.path.exists(dir_path):
            continue
            
        for file_path in Path(dir_path).glob('*.py'):
            if '__pycache__' in str(file_path):
                continue
                
            if apply_generic_fixes(file_path):
                files_fixed += 1
                print(f"✅ Fixed {file_path}")
    
    print(f"\n{'=' * 80}")
    print(f"Total files fixed: {files_fixed}")
    print("=" * 80)
    
    # Add global stylesheet recommendation
    print("\nRECOMMENDATION: Add a global stylesheet to ensure consistency")
    print("Add this to your main application initialization:")
    print("""
app.setStyleSheet('''
    QLabel { color: #FFFFFF; }
    QPushButton { color: #FFFFFF; }
    QLineEdit { color: #FFFFFF; }
    QTextEdit { color: #FFFFFF; }
    QPlainTextEdit { color: #FFFFFF; }
    QComboBox { color: #FFFFFF; }
    QListWidget { color: #FFFFFF; }
    QTreeWidget { color: #FFFFFF; }
    QTableWidget { color: #FFFFFF; }
    QCheckBox { color: #FFFFFF; }
    QRadioButton { color: #FFFFFF; }
    QGroupBox { color: #FFFFFF; }
    QSpinBox { color: #FFFFFF; }
    QDateEdit { color: #FFFFFF; }
    QTimeEdit { color: #FFFFFF; }
''')
    """)

if __name__ == "__main__":
    main()