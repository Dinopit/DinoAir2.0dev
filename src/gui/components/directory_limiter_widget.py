"""Directory Limiter Widget for File Search Settings.

This module provides a widget for managing allowed and excluded directories
for the RAG file search system, with security validations and import/export.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QFileDialog, QMessageBox, QGroupBox, QListWidgetItem,
    QMenu, QToolButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QAction

from src.utils.logger import Logger


class DirectoryLimiterWidget(QWidget):
    """Widget for managing directory access controls for file search.
    
    Features:
    - Allowed directories list with add/remove
    - Excluded directories list with add/remove
    - Directory browser for selection
    - Path validation and security checks
    - Import/export settings functionality
    - Default system directory exclusions
    """
    
    # Signals
    directories_changed = Signal(dict)  # Emitted when directories are modified
    
    # Default excluded system directories for Windows
    DEFAULT_EXCLUDED_DIRS = [
        "C:\\Windows",
        "C:\\Windows\\System32",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\ProgramData",
        "C:\\$Recycle.Bin",
        "C:\\System Volume Information",
        "C:\\Recovery",
        "C:\\hiberfil.sys",
        "C:\\pagefile.sys",
        "C:\\swapfile.sys"
    ]
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the directory limiter widget."""
        super().__init__(parent)
        self.logger = Logger()
        self._allowed_dirs: List[str] = []
        self._excluded_dirs: List[str] = self.DEFAULT_EXCLUDED_DIRS.copy()
        self._init_ui()
        self._update_directory_display()
        
    def _init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title and description
        title = QLabel("📁 Directory Access Controls")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        description = QLabel(
            "Configure which directories the file search system can access. "
            "This helps protect sensitive system files and improves performance."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #888; margin-bottom: 10px;")
        layout.addWidget(description)
        
        # Allowed directories section
        allowed_group = QGroupBox("✅ Allowed Directories")
        allowed_layout = QVBoxLayout()
        
        # Allowed directories list
        self.allowed_list = QListWidget()
        self.allowed_list.setToolTip(
            "Directories that will be included in file search indexing"
        )
        self.allowed_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.allowed_list.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self.allowed_list, pos)
        )
        allowed_layout.addWidget(self.allowed_list)
        
        # Allowed directories controls
        allowed_controls = QHBoxLayout()
        self.add_allowed_btn = QPushButton("➕ Add Directory")
        self.add_allowed_btn.setStyleSheet("color: #FFFFFF;")
        self.add_allowed_btn.clicked.connect(self._add_allowed_directory)
        self.add_allowed_btn.setToolTip("Browse and add a directory to allow")
        
        self.remove_allowed_btn = QPushButton("➖ Remove")
        self.remove_allowed_btn.setStyleSheet("color: #FFFFFF;")
        self.remove_allowed_btn.clicked.connect(self._remove_allowed_directory)
        self.remove_allowed_btn.setEnabled(False)
        self.remove_allowed_btn.setToolTip("Remove selected allowed directory")
        
        allowed_controls.addWidget(self.add_allowed_btn)
        allowed_controls.addWidget(self.remove_allowed_btn)
        allowed_controls.addStretch()
        allowed_layout.addLayout(allowed_controls)
        
        allowed_group.setLayout(allowed_layout)
        layout.addWidget(allowed_group)
        
        # Excluded directories section
        excluded_group = QGroupBox("🚫 Excluded Directories")
        excluded_layout = QVBoxLayout()
        
        # Excluded directories list
        self.excluded_list = QListWidget()
        self.excluded_list.setToolTip(
            "Directories that will be excluded from file search indexing"
        )
        self.excluded_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.excluded_list.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self.excluded_list, pos)
        )
        excluded_layout.addWidget(self.excluded_list)
        
        # Excluded directories controls
        excluded_controls = QHBoxLayout()
        self.add_excluded_btn = QPushButton("➕ Add Directory")
        self.add_excluded_btn.setStyleSheet("color: #FFFFFF;")
        self.add_excluded_btn.clicked.connect(self._add_excluded_directory)
        self.add_excluded_btn.setToolTip("Browse and add a directory to exclude")
        
        self.remove_excluded_btn = QPushButton("➖ Remove")
        self.remove_excluded_btn.setStyleSheet("color: #FFFFFF;")
        self.remove_excluded_btn.clicked.connect(self._remove_excluded_directory)
        self.remove_excluded_btn.setEnabled(False)
        self.remove_excluded_btn.setToolTip("Remove selected excluded directory")
        
        self.reset_excluded_btn = QPushButton("↺ Reset to Defaults")
        self.reset_excluded_btn.setStyleSheet("color: #FFFFFF;")
        self.reset_excluded_btn.clicked.connect(self._reset_excluded_to_defaults)
        self.reset_excluded_btn.setToolTip(
            "Reset excluded directories to system defaults"
        )
        
        excluded_controls.addWidget(self.add_excluded_btn)
        excluded_controls.addWidget(self.remove_excluded_btn)
        excluded_controls.addWidget(self.reset_excluded_btn)
        excluded_controls.addStretch()
        excluded_layout.addLayout(excluded_controls)
        
        excluded_group.setLayout(excluded_layout)
        layout.addWidget(excluded_group)
        
        # Import/Export controls
        import_export_layout = QHBoxLayout()
        import_export_layout.addStretch()
        
        self.import_btn = QPushButton("📥 Import Settings")
        self.import_btn.setStyleSheet("color: #FFFFFF;")
        self.import_btn.clicked.connect(self._import_settings)
        self.import_btn.setToolTip("Import directory settings from JSON file")
        
        self.export_btn = QPushButton("📤 Export Settings")
        self.export_btn.setStyleSheet("color: #FFFFFF;")
        self.export_btn.clicked.connect(self._export_settings)
        self.export_btn.setToolTip("Export directory settings to JSON file")
        
        import_export_layout.addWidget(self.import_btn)
        import_export_layout.addWidget(self.export_btn)
        layout.addLayout(import_export_layout)
        
        # Connect selection change signals
        self.allowed_list.itemSelectionChanged.connect(
            self._on_allowed_selection_changed
        )
        self.excluded_list.itemSelectionChanged.connect(
            self._on_excluded_selection_changed
        )
        
    def _add_allowed_directory(self) -> None:
        """Add a new allowed directory via file dialog."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Allow",
            os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            # Validate and add directory
            validation_result = self._validate_directory(directory)
            if validation_result['valid']:
                # Check if already in list
                if directory in self._allowed_dirs:
                    QMessageBox.information(
                        self,
                        "Directory Already Added",
                        f"'{directory}' is already in the allowed list."
                    )
                    return
                
                # Check if it's excluded
                if directory in self._excluded_dirs:
                    reply = QMessageBox.question(
                        self,
                        "Directory is Excluded",
                        f"'{directory}' is currently in the excluded list. "
                        "Do you want to remove it from excluded and add to allowed?",
                        QMessageBox.StandardButton.Yes |
                        QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self._excluded_dirs.remove(directory)
                    else:
                        return
                
                self._allowed_dirs.append(directory)
                self._update_directory_display()
                self._emit_changes()
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Directory",
                    f"Cannot add directory:\n{validation_result['message']}"
                )
    
    def _add_excluded_directory(self) -> None:
        """Add a new excluded directory via file dialog."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Exclude",
            os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            # Validate directory
            validation_result = self._validate_directory(directory)
            if validation_result['valid']:
                # Check if already in list
                if directory in self._excluded_dirs:
                    QMessageBox.information(
                        self,
                        "Directory Already Added",
                        f"'{directory}' is already in the excluded list."
                    )
                    return
                
                # Check if it's allowed
                if directory in self._allowed_dirs:
                    reply = QMessageBox.question(
                        self,
                        "Directory is Allowed",
                        f"'{directory}' is currently in the allowed list. "
                        "Do you want to remove it from allowed and add to excluded?",
                        QMessageBox.StandardButton.Yes |
                        QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self._allowed_dirs.remove(directory)
                    else:
                        return
                
                self._excluded_dirs.append(directory)
                self._update_directory_display()
                self._emit_changes()
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Directory",
                    f"Cannot add directory:\n{validation_result['message']}"
                )
    
    def _remove_allowed_directory(self) -> None:
        """Remove selected allowed directory."""
        current_item = self.allowed_list.currentItem()
        if current_item:
            directory = current_item.text()
            self._allowed_dirs.remove(directory)
            self._update_directory_display()
            self._emit_changes()
    
    def _remove_excluded_directory(self) -> None:
        """Remove selected excluded directory."""
        current_item = self.excluded_list.currentItem()
        if current_item:
            directory = current_item.text()
            
            # Check if it's a default system directory
            if directory in self.DEFAULT_EXCLUDED_DIRS:
                reply = QMessageBox.warning(
                    self,
                    "System Directory",
                    f"'{directory}' is a system directory that should "
                    "typically remain excluded for security reasons.\n\n"
                    "Are you sure you want to remove it from the excluded list?",
                    QMessageBox.StandardButton.Yes |
                    QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            self._excluded_dirs.remove(directory)
            self._update_directory_display()
            self._emit_changes()
    
    def _reset_excluded_to_defaults(self) -> None:
        """Reset excluded directories to system defaults."""
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "This will reset the excluded directories to system defaults. "
            "Any custom exclusions will be lost.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._excluded_dirs = self.DEFAULT_EXCLUDED_DIRS.copy()
            self._update_directory_display()
            self._emit_changes()
    
    def _validate_directory(self, directory: str) -> Dict[str, Any]:
        """Validate a directory path for security.
        
        Args:
            directory: Directory path to validate
            
        Returns:
            Dict with 'valid' bool and 'message' str
        """
        try:
            # Convert to absolute path
            abs_path = os.path.abspath(directory)
            
            # Check for path traversal attempts
            if ".." in abs_path or abs_path != os.path.normpath(abs_path):
                return {
                    "valid": False,
                    "message": "Path traversal detected. Please use absolute paths."
                }
            
            # Check if path exists
            if not os.path.exists(abs_path):
                return {
                    "valid": False,
                    "message": f"Directory does not exist: {abs_path}"
                }
            
            # Check if it's a directory
            if not os.path.isdir(abs_path):
                return {
                    "valid": False,
                    "message": f"Path is not a directory: {abs_path}"
                }
            
            # Additional security checks for critical system paths
            critical_paths = [
                "C:\\Windows\\System32\\config",
                "C:\\Windows\\System32\\drivers",
                "C:\\Users\\All Users",
                "C:\\ProgramData\\Microsoft\\Windows"
            ]
            
            for critical in critical_paths:
                if abs_path.lower().startswith(critical.lower()):
                    return {
                        "valid": False,
                        "message": f"Access to critical system path is restricted: {critical}"
                    }
            
            return {"valid": True, "message": "Directory is valid"}
            
        except Exception as e:
            return {
                "valid": False,
                "message": f"Error validating directory: {str(e)}"
            }
    
    def _update_directory_display(self) -> None:
        """Update the display of directories in both lists."""
        # Update allowed list
        self.allowed_list.clear()
        for directory in sorted(self._allowed_dirs):
            item = QListWidgetItem(directory)
            item.setToolTip(directory)
            self.allowed_list.addItem(item)
        
        # Update excluded list
        self.excluded_list.clear()
        for directory in sorted(self._excluded_dirs):
            item = QListWidgetItem(directory)
            item.setToolTip(directory)
            # Mark system directories
            if directory in self.DEFAULT_EXCLUDED_DIRS:
                item.setData(Qt.ItemDataRole.UserRole, "system")
                item.setText(f"{directory} (System)")
            self.excluded_list.addItem(item)
    
    def _on_allowed_selection_changed(self) -> None:
        """Handle selection change in allowed list."""
        has_selection = bool(self.allowed_list.selectedItems())
        self.remove_allowed_btn.setEnabled(has_selection)
    
    def _on_excluded_selection_changed(self) -> None:
        """Handle selection change in excluded list."""
        has_selection = bool(self.excluded_list.selectedItems())
        self.remove_excluded_btn.setEnabled(has_selection)
    
    def _show_context_menu(self, list_widget: QListWidget, pos) -> None:
        """Show context menu for list items."""
        item = list_widget.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        # Copy path action
        copy_action = QAction("📋 Copy Path", self)
        copy_action.triggered.connect(
            lambda: self._copy_to_clipboard(item.text().replace(" (System)", ""))
        )
        menu.addAction(copy_action)
        
        # Open in explorer action
        open_action = QAction("📂 Open in Explorer", self)
        open_action.triggered.connect(
            lambda: self._open_in_explorer(item.text().replace(" (System)", ""))
        )
        menu.addAction(open_action)
        
        menu.exec(list_widget.mapToGlobal(pos))
    
    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard."""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
    
    def _open_in_explorer(self, directory: str) -> None:
        """Open directory in file explorer."""
        import subprocess
        try:
            subprocess.Popen(f'explorer "{directory}"')
        except Exception as e:
            self.logger.error(f"Failed to open explorer: {str(e)}")
    
    def _import_settings(self) -> None:
        """Import directory settings from JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Directory Settings",
            os.path.expanduser("~"),
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validate structure
                if not isinstance(data, dict):
                    raise ValueError("Invalid settings format")
                
                # Import allowed directories
                if 'allowed_directories' in data:
                    allowed = data['allowed_directories']
                    if isinstance(allowed, list):
                        # Validate each directory
                        valid_allowed = []
                        for directory in allowed:
                            if self._validate_directory(directory)['valid']:
                                valid_allowed.append(directory)
                        self._allowed_dirs = valid_allowed
                
                # Import excluded directories
                if 'excluded_directories' in data:
                    excluded = data['excluded_directories']
                    if isinstance(excluded, list):
                        # Validate each directory
                        valid_excluded = []
                        for directory in excluded:
                            if self._validate_directory(directory)['valid']:
                                valid_excluded.append(directory)
                        # Merge with defaults
                        self._excluded_dirs = list(set(
                            valid_excluded + self.DEFAULT_EXCLUDED_DIRS
                        ))
                
                self._update_directory_display()
                self._emit_changes()
                
                QMessageBox.information(
                    self,
                    "Import Successful",
                    "Directory settings imported successfully."
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Import Failed",
                    f"Failed to import settings:\n{str(e)}"
                )
    
    def _export_settings(self) -> None:
        """Export directory settings to JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Directory Settings",
            os.path.join(os.path.expanduser("~"), "file_search_directories.json"),
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                settings = {
                    "allowed_directories": self._allowed_dirs,
                    "excluded_directories": self._excluded_dirs,
                    "export_date": os.path.basename(file_path),
                    "version": "1.0"
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Directory settings exported to:\n{file_path}"
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export settings:\n{str(e)}"
                )
    
    def _emit_changes(self) -> None:
        """Emit signal with current directory settings."""
        settings = {
            "allowed_directories": self._allowed_dirs.copy(),
            "excluded_directories": self._excluded_dirs.copy()
        }
        self.directories_changed.emit(settings)
        self.logger.info(f"Directory settings changed: {settings}")
    
    def get_settings(self) -> Dict[str, List[str]]:
        """Get current directory settings.
        
        Returns:
            Dict with 'allowed_directories' and 'excluded_directories' lists
        """
        return {
            "allowed_directories": self._allowed_dirs.copy(),
            "excluded_directories": self._excluded_dirs.copy()
        }
    
    def set_settings(self, settings: Dict[str, List[str]]) -> None:
        """Set directory settings.
        
        Args:
            settings: Dict with 'allowed_directories' and 'excluded_directories'
        """
        if 'allowed_directories' in settings:
            self._allowed_dirs = settings['allowed_directories'].copy()
        
        if 'excluded_directories' in settings:
            # Merge with defaults to ensure system directories are excluded
            self._excluded_dirs = list(set(
                settings['excluded_directories'] + self.DEFAULT_EXCLUDED_DIRS
            ))
        
        self._update_directory_display()