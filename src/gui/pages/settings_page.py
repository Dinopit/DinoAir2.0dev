"""Settings Page - Application settings interface with watchdog controls.

This module provides a comprehensive settings interface for DinoAir, including
complete watchdog configuration controls with real-time updates and validation,
and file search system settings.
"""

import os
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QSlider, QSpinBox, QCheckBox, QMessageBox, QFormLayout, QFrame,
    QTabWidget, QLineEdit, QListWidget, QListWidgetItem, QTextEdit,
    QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from src.utils.config_loader import ConfigLoader
# Import base watchdog type for compatibility
from src.utils.Watchdog import SystemWatchdog
from src.gui.components.directory_limiter_widget import DirectoryLimiterWidget
from src.database.file_search_db import FileSearchDB
from src.utils.logger import Logger
from src.utils.colors import DinoPitColors
from src.tools.registry import ToolRegistry
from src.tools.discovery import ToolDiscovery


class SettingsPage(QWidget):
    """Settings page with comprehensive watchdog configuration controls.
    
    Features:
    - Real-time watchdog status display
    - All watchdog configuration parameters
    - Input validation with tooltips
    - Apply/Save/Reset functionality
    - Start/Stop watchdog control
    - Critical settings confirmation
    """
    
    # Signals
    watchdog_control_requested = Signal(str)  # 'start', 'stop', 'restart'
    watchdog_config_changed = Signal(dict)    # Emit new config when saved
    
    def __init__(self):
        """Initialize settings page with watchdog and file search controls."""
        super().__init__()
        self.logger = Logger()
        self.config_loader = ConfigLoader()
        self.watchdog_ref: Optional[SystemWatchdog] = None
        self.original_values: Dict[str, Any] = {}
        self.file_search_db = FileSearchDB()
        self.tool_registry = ToolRegistry()
        self.tool_discovery = ToolDiscovery(self.tool_registry)
        self._init_ui()
        self._load_current_settings()
        self._setup_status_timer()
        
    def _init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("⚙️ Application Settings")
        title.setStyleSheet("color: #FFFFFF;")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Watchdog Settings Tab
        watchdog_tab = QWidget()
        watchdog_layout = QVBoxLayout(watchdog_tab)
        
        # Watchdog Status Group
        self._create_status_group(watchdog_layout)
        
        # Watchdog Configuration Group
        self._create_config_group(watchdog_layout)
        
        # Add stretch to push everything to the top
        watchdog_layout.addStretch()
        
        self.tab_widget.addTab(watchdog_tab, "🐕 Watchdog Settings")
        
        # File Search Settings Tab
        file_search_tab = QWidget()
        file_search_layout = QVBoxLayout(file_search_tab)
        
        # Create file search settings
        self._create_file_search_settings(file_search_layout)
        
        # Add stretch
        file_search_layout.addStretch()
        
        self.tab_widget.addTab(file_search_tab, "🔍 File Search Settings")
        
        # Tools Settings Tab
        tools_tab = QWidget()
        tools_layout = QVBoxLayout(tools_tab)
        
        # Create tools settings
        self._create_tools_settings(tools_layout)
        
        # Add stretch
        tools_layout.addStretch()
        
        self.tab_widget.addTab(tools_tab, "🔧 Tools")
        
        layout.addWidget(self.tab_widget)
        
        # Control Buttons (shared for all tabs)
        self._create_control_buttons(layout)
        
    def _create_status_group(self, parent_layout: QVBoxLayout) -> None:
        """Create watchdog status display group."""
        group = QGroupBox("🐕 Watchdog Status")
        layout = QVBoxLayout()
        
        # Status display
        self.status_label = QLabel("Status: Not Running")
        self.status_label.setStyleSheet(
            "QLabel { padding: 10px; background-color: #2B3A52; "
            "border-radius: 5px; }"
        )
        layout.addWidget(self.status_label)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("▶️ Start Watchdog")
        self.start_button.setStyleSheet("color: #FFFFFF;")
        self.start_button.clicked.connect(self._on_start_watchdog)
        self.start_button.setToolTip("Start the system watchdog monitoring")
        
        self.stop_button = QPushButton("⏹️ Stop Watchdog")
        self.stop_button.setStyleSheet("color: #FFFFFF;")
        self.stop_button.clicked.connect(self._on_stop_watchdog)
        self.stop_button.setEnabled(False)
        self.stop_button.setToolTip("Stop the system watchdog monitoring")
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def _create_config_group(self, parent_layout: QVBoxLayout) -> None:
        """Create watchdog configuration controls group."""
        group = QGroupBox("🔧 Watchdog Configuration")
        layout = QFormLayout()
        layout.setSpacing(15)
        
        # Enable/Disable Watchdog
        self.enable_checkbox = QCheckBox("Enable Watchdog Monitoring")
        self.enable_checkbox.setToolTip(
            "Enable or disable automatic system monitoring on startup"
        )
        self.enable_checkbox.stateChanged.connect(self._on_settings_changed)
        layout.addRow("Auto-Start:", self.enable_checkbox)
        
        # VRAM Threshold
        vram_container = QWidget()
        vram_layout = QHBoxLayout(vram_container)
        vram_layout.setContentsMargins(0, 0, 0, 0)
        
        self.vram_slider = QSlider(Qt.Orientation.Horizontal)
        self.vram_slider.setRange(0, 100)
        self.vram_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.vram_slider.setTickInterval(10)
        self.vram_slider.valueChanged.connect(self._on_vram_changed)
        self.vram_slider.setToolTip(
            "VRAM usage percentage that triggers warnings"
        )
        
        self.vram_label = QLabel("80%")
        self.vram_label.setMinimumWidth(40)
        self.vram_label.setStyleSheet(
            f"color: {DinoPitColors.PRIMARY_TEXT}; font-weight: bold;"
        )
        
        vram_layout.addWidget(self.vram_slider)
        vram_layout.addWidget(self.vram_label)
        layout.addRow("VRAM Threshold:", vram_container)
        
        # Max DinoAir Processes
        self.max_processes_spin = QSpinBox()
        self.max_processes_spin.setRange(1, 20)
        self.max_processes_spin.setSuffix(" processes")
        self.max_processes_spin.setToolTip(
            "Maximum allowed DinoAir processes before critical alert"
        )
        self.max_processes_spin.valueChanged.connect(self._on_settings_changed)
        layout.addRow("Max Processes:", self.max_processes_spin)
        
        # Check Interval
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(5, 300)
        self.interval_spin.setSuffix(" seconds")
        self.interval_spin.setToolTip("How often to check system metrics")
        self.interval_spin.valueChanged.connect(self._on_settings_changed)
        layout.addRow("Check Interval:", self.interval_spin)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addRow(separator)
        
        # Emergency Shutdown (Critical Setting)
        emergency_container = QWidget()
        emergency_layout = QHBoxLayout(emergency_container)
        emergency_layout.setContentsMargins(0, 0, 0, 0)
        
        self.emergency_checkbox = QCheckBox("Enable Emergency Shutdown")
        self.emergency_checkbox.setStyleSheet("QCheckBox { color: #ff6b6b; }")
        self.emergency_checkbox.setToolTip(
            "⚠️ DANGEROUS: Allows watchdog to terminate DinoAir "
            "if critical limits are exceeded"
        )
        self.emergency_checkbox.stateChanged.connect(
            self._on_emergency_changed
        )
        
        warning_label = QLabel("⚠️")
        warning_label.setStyleSheet("color: #FFFFFF;")
        warning_label.setToolTip(
            "This setting allows automatic process termination!"
        )
        
        emergency_layout.addWidget(self.emergency_checkbox)
        emergency_layout.addWidget(warning_label)
        emergency_layout.addStretch()
        
        layout.addRow("Critical Action:", emergency_container)
        
        # Warning text
        warning_text = QLabel(
            "⚠️ Emergency shutdown will terminate all DinoAir "
            "processes if limits are exceeded!"
        )
        warning_text.setWordWrap(True)
        warning_text.setStyleSheet(
            "QLabel { color: #ff6b6b; font-size: 11px; padding: 5px; }"
        )
        layout.addRow("", warning_text)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def _create_control_buttons(self, parent_layout: QVBoxLayout) -> None:
        """Create apply/save/reset control buttons."""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Apply button
        self.apply_button = QPushButton("✓ Apply")
        self.apply_button.setStyleSheet("color: #FFFFFF;")
        self.apply_button.clicked.connect(self._on_apply_settings)
        self.apply_button.setEnabled(False)
        self.apply_button.setToolTip("Apply settings without saving to file")
        
        # Save button
        self.save_button = QPushButton("💾 Save")
        self.save_button.setStyleSheet("color: #FFFFFF;")
        self.save_button.clicked.connect(self._on_save_settings)
        self.save_button.setEnabled(False)
        self.save_button.setToolTip("Save settings to configuration file")
        
        # Reset button
        self.reset_button = QPushButton("↺ Reset to Defaults")
        self.reset_button.setStyleSheet("color: #FFFFFF;")
        self.reset_button.clicked.connect(self._on_reset_defaults)
        self.reset_button.setToolTip(
            "Reset all watchdog settings to default values"
        )
        
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.save_button)
        button_layout.addStretch()
        button_layout.addWidget(self.reset_button)
        
        parent_layout.addLayout(button_layout)
        
    def _setup_status_timer(self) -> None:
        """Setup timer for status updates."""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status_display)
        self.status_timer.start(5000)  # Update every 5 seconds (was 1)
        
    def _load_current_settings(self) -> None:
        """Load current settings from config file and database."""
        # Load watchdog settings
        self.enable_checkbox.setChecked(
            self.config_loader.get("watchdog.enabled", True)
        )
        
        vram_threshold = int(
            self.config_loader.get("watchdog.vram_threshold_percent", 80)
        )
        self.vram_slider.setValue(vram_threshold)
        
        self.max_processes_spin.setValue(
            self.config_loader.get("watchdog.max_dinoair_processes", 5)
        )
        
        self.interval_spin.setValue(
            self.config_loader.get("watchdog.check_interval_seconds", 10)
        )
        
        self.emergency_checkbox.setChecked(
            self.config_loader.get(
                "watchdog.self_terminate_on_critical", False
            )
        )
        
        # Load file search settings from database
        try:
            config_result = self.file_search_db.get_search_settings(
                "file_search_config"
            )
            if (config_result.get("success") and
                    config_result.get("setting_value")):
                settings = config_result["setting_value"]
                
                # Apply loaded settings
                self.max_file_size_spin.setValue(
                    settings.get("max_file_size_mb", 50)
                )
                self.chunk_size_spin.setValue(
                    settings.get("chunk_size", 1000)
                )
                self.chunk_overlap_spin.setValue(
                    settings.get("chunk_overlap", 200)
                )
                self.auto_index_checkbox.setChecked(
                    settings.get("auto_index_enabled", True)
                )
                
                # File types
                if "include_types" in settings:
                    self.include_types_edit.setText(
                        ",".join(settings["include_types"])
                    )
                if "exclude_types" in settings:
                    self.exclude_types_edit.setText(
                        ",".join(settings["exclude_types"])
                    )
                
                # Directory settings
                if "directory_settings" in settings:
                    self.directory_limiter.set_settings(
                        settings["directory_settings"]
                    )
            else:
                # No saved settings, use defaults
                default_allowed = [os.path.expanduser("~/Documents")]
                self.directory_limiter.set_settings({
                    "allowed_directories": default_allowed,
                    "excluded_directories": []
                })
                
        except Exception as e:
            self.logger.error(f"Error loading file search settings: {str(e)}")
            # Use defaults on error
            default_allowed = [os.path.expanduser("~/Documents")]
            self.directory_limiter.set_settings({
                "allowed_directories": default_allowed,
                "excluded_directories": []
            })
        
        # Store original values for change detection
        self._store_original_values()
        
    def _apply_file_search_settings(self, save_to_db: bool = False) -> None:
        """Apply or save file search settings."""
        try:
            # Get current settings
            settings = {
                "max_file_size_mb": self.max_file_size_spin.value(),
                "chunk_size": self.chunk_size_spin.value(),
                "chunk_overlap": self.chunk_overlap_spin.value(),
                "auto_index_enabled": self.auto_index_checkbox.isChecked(),
                "include_types": [
                    t.strip()
                    for t in self.include_types_edit.text().split(',')
                    if t.strip()
                ],
                "exclude_types": [
                    t.strip()
                    for t in self.exclude_types_edit.text().split(',')
                    if t.strip()
                ],
                "directory_settings": self.directory_limiter.get_settings()
            }
            
            if save_to_db:
                # Save settings to database
                self.file_search_db.update_search_settings(
                    "file_search_config", settings
                )
                
                # Save directory settings separately for easier access
                self.file_search_db.update_search_settings(
                    "allowed_directories",
                    settings["directory_settings"]["allowed_directories"]
                )
                self.file_search_db.update_search_settings(
                    "excluded_directories",
                    settings["directory_settings"]["excluded_directories"]
                )
                
                self.logger.info("File search settings saved to database")
            else:
                self.logger.info("File search settings applied (not saved)")
                
        except Exception as e:
            self.logger.error(f"Error applying file search settings: {str(e)}")
            QMessageBox.critical(
                self,
                "Settings Error",
                f"Failed to apply file search settings:\n{str(e)}"
            )
    
    def _store_original_values(self) -> None:
        """Store current values for change detection."""
        self.original_values = {
            # Watchdog settings
            "enabled": self.enable_checkbox.isChecked(),
            "vram_threshold": self.vram_slider.value(),
            "max_processes": self.max_processes_spin.value(),
            "interval": self.interval_spin.value(),
            "emergency": self.emergency_checkbox.isChecked(),
            # File search settings
            "max_file_size": self.max_file_size_spin.value(),
            "chunk_size": self.chunk_size_spin.value(),
            "chunk_overlap": self.chunk_overlap_spin.value(),
            "auto_index": self.auto_index_checkbox.isChecked(),
            "include_types": self.include_types_edit.text(),
            "exclude_types": self.exclude_types_edit.text(),
            "directory_settings": self.directory_limiter.get_settings()
        }
        
    def _on_vram_changed(self, value: int) -> None:
        """Handle VRAM slider value change."""
        self.vram_label.setText(f"{value}%")
        self._on_settings_changed()
        
    def _on_emergency_changed(self, state: int) -> None:
        """Handle emergency shutdown checkbox change."""
        if state == Qt.CheckState.Checked.value:
            # Show warning dialog
            reply = QMessageBox.warning(
                self,
                "⚠️ Critical Setting",
                "Enabling emergency shutdown allows the watchdog to "
                "automatically terminate all DinoAir processes if "
                "critical resource limits are exceeded.\n\n"
                "This is a safety feature but can result in data loss "
                "if processes "
                "are forcefully terminated.\n\n"
                "Are you sure you want to enable this?",
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                self.emergency_checkbox.setChecked(False)
                return
                
        self._on_settings_changed()
        
    def _on_settings_changed(self) -> None:
        """Handle any settings change."""
        # Check if values differ from originals
        current_values = {
            # Watchdog settings
            "enabled": self.enable_checkbox.isChecked(),
            "vram_threshold": self.vram_slider.value(),
            "max_processes": self.max_processes_spin.value(),
            "interval": self.interval_spin.value(),
            "emergency": self.emergency_checkbox.isChecked(),
            # File search settings
            "max_file_size": self.max_file_size_spin.value(),
            "chunk_size": self.chunk_size_spin.value(),
            "chunk_overlap": self.chunk_overlap_spin.value(),
            "auto_index": self.auto_index_checkbox.isChecked(),
            "include_types": self.include_types_edit.text(),
            "exclude_types": self.exclude_types_edit.text(),
            "directory_settings": self.directory_limiter.get_settings()
        }
        
        has_changes = current_values != self.original_values
        self.apply_button.setEnabled(has_changes)
        self.save_button.setEnabled(has_changes)
        
    def _create_file_search_settings(self, parent_layout: QVBoxLayout) -> None:
        """Create file search settings controls."""
        # File Search Configuration Group
        config_group = QGroupBox("📄 File Search Configuration")
        config_layout = QFormLayout()
        config_layout.setSpacing(15)
        
        # Maximum file size
        self.max_file_size_spin = QSpinBox()
        self.max_file_size_spin.setRange(1, 500)
        self.max_file_size_spin.setSuffix(" MB")
        self.max_file_size_spin.setValue(50)
        self.max_file_size_spin.setToolTip(
            "Maximum file size to index (in megabytes)"
        )
        self.max_file_size_spin.valueChanged.connect(self._on_settings_changed)
        config_layout.addRow("Max File Size:", self.max_file_size_spin)
        
        # Chunk size
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(100, 5000)
        self.chunk_size_spin.setSingleStep(100)
        self.chunk_size_spin.setValue(1000)
        self.chunk_size_spin.setSuffix(" characters")
        self.chunk_size_spin.setToolTip(
            "Size of text chunks for indexing"
        )
        self.chunk_size_spin.valueChanged.connect(self._on_settings_changed)
        config_layout.addRow("Chunk Size:", self.chunk_size_spin)
        
        # Chunk overlap
        self.chunk_overlap_spin = QSpinBox()
        self.chunk_overlap_spin.setRange(0, 1000)
        self.chunk_overlap_spin.setSingleStep(50)
        self.chunk_overlap_spin.setValue(200)
        self.chunk_overlap_spin.setSuffix(" characters")
        self.chunk_overlap_spin.setToolTip(
            "Overlap between consecutive chunks"
        )
        self.chunk_overlap_spin.valueChanged.connect(self._on_settings_changed)
        config_layout.addRow("Chunk Overlap:", self.chunk_overlap_spin)
        
        # Auto-indexing
        self.auto_index_checkbox = QCheckBox("Enable Automatic Indexing")
        self.auto_index_checkbox.setToolTip(
            "Automatically index new and modified files"
        )
        self.auto_index_checkbox.setChecked(True)
        self.auto_index_checkbox.stateChanged.connect(
            self._on_settings_changed
        )
        config_layout.addRow("Auto-Indexing:", self.auto_index_checkbox)
        
        # File types to include
        self.include_types_edit = QLineEdit()
        self.include_types_edit.setStyleSheet(
            "color: #FFFFFF; background-color: #2B3A52; "
            "border: 1px solid #4A5A7A; padding: 5px;"
        )
        self.include_types_edit.setPlaceholderText(
            ".txt, .pdf, .docx, .md, .py, .js"
        )
        self.include_types_edit.setText(
            ".txt,.pdf,.docx,.md,.py,.js,.java,.cpp"
        )
        self.include_types_edit.setToolTip(
            "Comma-separated list of file extensions to include"
        )
        self.include_types_edit.textChanged.connect(self._on_settings_changed)
        config_layout.addRow("Include Types:", self.include_types_edit)
        
        # File types to exclude
        self.exclude_types_edit = QLineEdit()
        self.exclude_types_edit.setStyleSheet(
            "color: #FFFFFF; background-color: #2B3A52; "
            "border: 1px solid #4A5A7A; padding: 5px;"
        )
        self.exclude_types_edit.setPlaceholderText(".exe, .dll, .bin")
        self.exclude_types_edit.setText(".exe,.dll,.bin,.obj,.class,.pyc")
        self.exclude_types_edit.setToolTip(
            "Comma-separated list of file extensions to exclude"
        )
        self.exclude_types_edit.textChanged.connect(self._on_settings_changed)
        config_layout.addRow("Exclude Types:", self.exclude_types_edit)
        
        config_group.setLayout(config_layout)
        parent_layout.addWidget(config_group)
        
        # Directory Limiter Widget
        dir_group = QGroupBox("📁 Directory Access Controls")
        dir_layout = QVBoxLayout()
        
        self.directory_limiter = DirectoryLimiterWidget()
        self.directory_limiter.directories_changed.connect(
            self._on_directories_changed
        )
        dir_layout.addWidget(self.directory_limiter)
        
        dir_group.setLayout(dir_layout)
        parent_layout.addWidget(dir_group)
    
    def _on_directories_changed(self, settings: Dict[str, Any]) -> None:
        """Handle directory settings change."""
        self._on_settings_changed()
        self.logger.info(f"Directory settings changed: {settings}")
    
    def _on_apply_settings(self) -> None:
        """Apply settings to running watchdog without saving."""
        # Apply watchdog settings
        config = self._get_current_config()
        
        # Emit signal for MainWindow to update watchdog
        self.watchdog_config_changed.emit(config)
        
        # If watchdog is running, it needs restart for some settings
        is_monitoring = False
        if self.watchdog_ref:
            # Check monitoring state based on implementation
            if (hasattr(self.watchdog_ref, 'controller') and
                    self.watchdog_ref.controller):
                if (hasattr(self.watchdog_ref.controller, '_thread') and
                        self.watchdog_ref.controller._thread and
                        self.watchdog_ref.controller._thread.isRunning()):
                    is_monitoring = True
            elif hasattr(self.watchdog_ref, '_monitoring'):
                is_monitoring = self.watchdog_ref._monitoring
                
        if is_monitoring:
            reply = QMessageBox.question(
                self,
                "Restart Required",
                "Some settings require restarting the watchdog. Restart now?",
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.watchdog_control_requested.emit('restart')
        
        # Apply file search settings
        self._apply_file_search_settings(save_to_db=False)
                
        # Update original values
        self._store_original_values()
        self._on_settings_changed()
        
        QMessageBox.information(
            self, "Settings Applied",
            "Settings have been applied successfully."
        )
        
    def _on_save_settings(self) -> None:
        """Save settings to configuration file and database."""
        # Save watchdog settings
        config = self._get_current_config()
        
        # Save to config file
        for key, value in config.items():
            self.config_loader.set(f"watchdog.{key}", value)
            
        # Apply to running watchdog
        self.watchdog_config_changed.emit(config)
        
        # Save file search settings
        self._apply_file_search_settings(save_to_db=True)
        
        # Update original values
        self._store_original_values()
        self._on_settings_changed()
        
        QMessageBox.information(
            self, "Settings Saved",
            "Settings have been saved successfully."
        )
        
    def _on_reset_defaults(self) -> None:
        """Reset settings to default values."""
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "Are you sure you want to reset all settings "
            "to default values?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reset watchdog values
            self.enable_checkbox.setChecked(True)
            self.vram_slider.setValue(80)
            self.max_processes_spin.setValue(5)
            self.interval_spin.setValue(10)
            self.emergency_checkbox.setChecked(False)
            
            # Reset file search values
            self.max_file_size_spin.setValue(50)
            self.chunk_size_spin.setValue(1000)
            self.chunk_overlap_spin.setValue(200)
            self.auto_index_checkbox.setChecked(True)
            self.include_types_edit.setText(
                ".txt,.pdf,.docx,.md,.py,.js,.java,.cpp"
            )
            self.exclude_types_edit.setText(".exe,.dll,.bin,.obj,.class,.pyc")
            
            # Reset directory limiter to defaults
            self.directory_limiter.set_settings({
                "allowed_directories": [os.path.expanduser("~/Documents")],
                "excluded_directories": []  # Will auto-add defaults
            })
            
            self._on_settings_changed()
            
    def _get_current_config(self) -> Dict[str, Any]:
        """Get current configuration as dictionary."""
        return {
            "enabled": self.enable_checkbox.isChecked(),
            "vram_threshold_percent": float(self.vram_slider.value()),
            "max_dinoair_processes": self.max_processes_spin.value(),
            "check_interval_seconds": self.interval_spin.value(),
            "self_terminate_on_critical": self.emergency_checkbox.isChecked()
        }
        
    def _on_start_watchdog(self) -> None:
        """Handle start watchdog button."""
        self.watchdog_control_requested.emit('start')
        
    def _on_stop_watchdog(self) -> None:
        """Handle stop watchdog button."""
        reply = QMessageBox.question(
            self,
            "Stop Watchdog",
            "Are you sure you want to stop the system watchdog?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.watchdog_control_requested.emit('stop')
            
    def _update_status_display(self) -> None:
        """Update watchdog status display."""
        if self.watchdog_ref:
            # Check if monitoring based on implementation type
            is_monitoring = False
            
            # Try Qt-based implementation first
            if (hasattr(self.watchdog_ref, 'controller') and
                    self.watchdog_ref.controller):
                if (hasattr(self.watchdog_ref.controller, '_thread') and
                        self.watchdog_ref.controller._thread and
                        self.watchdog_ref.controller._thread.isRunning()):
                    is_monitoring = True
            # Fallback to legacy check
            elif hasattr(self.watchdog_ref, '_monitoring'):
                is_monitoring = self.watchdog_ref._monitoring
            
            if is_monitoring:
                self.status_label.setText("Status: 🟢 Running")
                self.status_label.setStyleSheet(
                    "QLabel { padding: 10px; background-color: #2d5a2d; "
                    "border-radius: 5px; color: #90ee90; }"
                )
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                
                # Get current metrics if available
                metrics = None
                if hasattr(self.watchdog_ref, '_last_metrics'):
                    metrics = self.watchdog_ref._last_metrics
                elif (hasattr(self.watchdog_ref, 'fallback') and
                        hasattr(self.watchdog_ref.fallback,
                                'last_good_metrics')):
                    metrics = self.watchdog_ref.fallback.last_good_metrics
                
                if metrics:
                    status_text = (
                        f"Status: 🟢 Running\n"
                        f"VRAM: {metrics.vram_percent:.1f}% | "
                        f"RAM: {metrics.ram_percent:.1f}% | "
                        f"CPU: {metrics.cpu_percent:.1f}% | "
                        f"Processes: {metrics.dinoair_processes}"
                    )
                    self.status_label.setText(status_text)
                    
                # Add implementation mode if available
                if hasattr(self.watchdog_ref, 'current_mode'):
                    current_text = self.status_label.text()
                    self.status_label.setText(
                        f"{current_text} "
                        f"({self.watchdog_ref.current_mode.value} mode)"
                    )
            else:
                self._set_stopped_status()
        else:
            self._set_stopped_status()
            
    def _set_stopped_status(self) -> None:
        """Set status display to stopped state."""
        self.status_label.setText("Status: 🔴 Not Running")
        self.status_label.setStyleSheet(
            "QLabel { padding: 10px; background-color: #5a2d2d; "
            "border-radius: 5px; color: #ff6b6b; }"
        )
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
    def set_watchdog_reference(
        self, watchdog: Optional[SystemWatchdog]
    ) -> None:
        """Set reference to the watchdog instance for status updates.
        
        Args:
            watchdog: The SystemWatchdog instance or None
        """
        self.watchdog_ref = watchdog
        self._update_status_display()
    
    def _create_tools_settings(self, parent_layout: QVBoxLayout) -> None:
        """Create tools discovery and management interface."""
        # Tool Discovery Status Group
        status_group = QGroupBox("🔧 Tool System Status")
        status_layout = QVBoxLayout()
        
        # Status info
        self.tools_status_label = QLabel("Initializing tool system...")
        self.tools_status_label.setStyleSheet(
            "QLabel { padding: 10px; background-color: #2B3A52; "
            "border-radius: 5px; }"
        )
        status_layout.addWidget(self.tools_status_label)
        
        # Statistics
        stats_layout = QHBoxLayout()
        self.total_tools_label = QLabel("Total Tools: 0")
        self.enabled_tools_label = QLabel("Enabled: 0")
        self.active_tools_label = QLabel("Active: 0")
        
        stats_layout.addWidget(self.total_tools_label)
        stats_layout.addWidget(self.enabled_tools_label)
        stats_layout.addWidget(self.active_tools_label)
        stats_layout.addStretch()
        
        status_layout.addLayout(stats_layout)
        status_group.setLayout(status_layout)
        parent_layout.addWidget(status_group)
        
        # Main tools interface
        main_layout = QHBoxLayout()
        
        # Left side - Tool list with search
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Search box
        search_layout = QHBoxLayout()
        self.tool_search_edit = QLineEdit()
        self.tool_search_edit.setPlaceholderText("🔍 Search tools...")
        self.tool_search_edit.setStyleSheet(
            "QLineEdit { padding: 5px; background-color: #2B3A52; "
            "border: 1px solid #4A5A7A; border-radius: 3px; }"
        )
        self.tool_search_edit.textChanged.connect(self._on_tool_search)
        
        self.refresh_tools_button = QPushButton("↻ Refresh")
        self.refresh_tools_button.clicked.connect(self._refresh_tools)
        self.refresh_tools_button.setToolTip("Scan for new tools")
        
        search_layout.addWidget(self.tool_search_edit)
        search_layout.addWidget(self.refresh_tools_button)
        left_layout.addLayout(search_layout)
        
        # Tool list
        self.tools_list = QListWidget()
        self.tools_list.setStyleSheet("""
            QListWidget {
                background-color: #1E2A3A;
                border: 1px solid #4A5A7A;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2B3A52;
            }
            QListWidget::item:selected {
                background-color: #3A4A6A;
            }
            QListWidget::item:hover {
                background-color: #2B3A52;
            }
        """)
        self.tools_list.currentItemChanged.connect(self._on_tool_selected)
        left_layout.addWidget(self.tools_list)
        
        # Right side - Tool details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tool info group
        self.tool_info_group = QGroupBox("Tool Information")
        self.tool_info_layout = QFormLayout()
        
        # Stacked widget for showing either placeholder or tool details
        self.tool_details_stack = QStackedWidget()
        
        # Placeholder when no tool selected
        placeholder_label = QLabel("Select a tool to view details")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("color: #7A8A9A;")
        self.tool_details_stack.addWidget(placeholder_label)
        
        # Tool details widget
        tool_details_widget = QWidget()
        tool_details_layout = QVBoxLayout(tool_details_widget)
        
        # Tool metadata
        metadata_form = QFormLayout()
        self.tool_name_label = QLabel()
        self.tool_version_label = QLabel()
        self.tool_category_label = QLabel()
        self.tool_author_label = QLabel()
        
        metadata_form.addRow("Name:", self.tool_name_label)
        metadata_form.addRow("Version:", self.tool_version_label)
        metadata_form.addRow("Category:", self.tool_category_label)
        metadata_form.addRow("Author:", self.tool_author_label)
        
        tool_details_layout.addLayout(metadata_form)
        
        # Description
        desc_label = QLabel("Description:")
        desc_label.setStyleSheet("font-weight: bold;")
        tool_details_layout.addWidget(desc_label)
        
        self.tool_description_text = QTextEdit()
        self.tool_description_text.setReadOnly(True)
        self.tool_description_text.setMaximumHeight(100)
        self.tool_description_text.setStyleSheet(
            "QTextEdit { background-color: #2B3A52; "
            "border: 1px solid #4A5A7A; "
            "border-radius: 3px; padding: 5px; }"
        )
        tool_details_layout.addWidget(self.tool_description_text)
        
        # Tool controls
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()
        
        # Enable/Disable checkbox
        self.tool_enabled_checkbox = QCheckBox("Enabled")
        self.tool_enabled_checkbox.setToolTip(
            "Enable or disable this tool"
        )
        self.tool_enabled_checkbox.stateChanged.connect(
            self._on_tool_enabled_changed
        )
        controls_layout.addWidget(self.tool_enabled_checkbox)
        
        # Status info
        self.tool_status_label = QLabel("Status: Not Loaded")
        self.tool_status_label.setStyleSheet(
            "padding: 5px; background-color: #2B3A52; border-radius: 3px;"
        )
        controls_layout.addWidget(self.tool_status_label)
        
        # Usage statistics
        self.tool_usage_label = QLabel("Usage: 0 times")
        controls_layout.addWidget(self.tool_usage_label)
        
        # Last used
        self.tool_last_used_label = QLabel("Last Used: Never")
        controls_layout.addWidget(self.tool_last_used_label)
        
        controls_group.setLayout(controls_layout)
        tool_details_layout.addWidget(controls_group)
        
        # Dependencies section (if any)
        self.dependencies_group = QGroupBox("Dependencies")
        self.dependencies_layout = QVBoxLayout()
        self.dependencies_label = QLabel("No dependencies")
        self.dependencies_label.setStyleSheet("color: #7A8A9A;")
        self.dependencies_layout.addWidget(self.dependencies_label)
        self.dependencies_group.setLayout(self.dependencies_layout)
        self.dependencies_group.setVisible(False)
        tool_details_layout.addWidget(self.dependencies_group)
        
        tool_details_layout.addStretch()
        self.tool_details_stack.addWidget(tool_details_widget)
        
        self.tool_info_layout.addRow(self.tool_details_stack)
        self.tool_info_group.setLayout(self.tool_info_layout)
        right_layout.addWidget(self.tool_info_group)
        
        # Add widgets to main layout
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 2)
        
        parent_layout.addLayout(main_layout)
        
        # Discovery paths group
        paths_group = QGroupBox("📁 Tool Discovery Paths")
        paths_layout = QVBoxLayout()
        
        paths_info = QLabel(
            "Tools are automatically discovered from the following locations:"
        )
        paths_info.setWordWrap(True)
        paths_layout.addWidget(paths_info)
        
        self.discovery_paths_list = QTextEdit()
        self.discovery_paths_list.setReadOnly(True)
        self.discovery_paths_list.setMaximumHeight(80)
        self.discovery_paths_list.setStyleSheet(
            "QTextEdit { background-color: #2B3A52; "
            "border: 1px solid #4A5A7A; "
            "border-radius: 3px; padding: 5px; font-family: monospace; }"
        )
        paths_layout.addWidget(self.discovery_paths_list)
        
        # Discovery buttons
        discovery_buttons_layout = QHBoxLayout()
        
        self.discover_button = QPushButton("🔍 Discover Tools")
        self.discover_button.clicked.connect(self._discover_tools)
        self.discover_button.setToolTip(
            "Scan all configured paths for new tools"
        )
        
        self.add_path_button = QPushButton("➕ Add Path")
        self.add_path_button.clicked.connect(self._add_discovery_path)
        self.add_path_button.setEnabled(False)  # Not implemented yet
        self.add_path_button.setToolTip("Add a new tool discovery path")
        
        discovery_buttons_layout.addWidget(self.discover_button)
        discovery_buttons_layout.addWidget(self.add_path_button)
        discovery_buttons_layout.addStretch()
        
        paths_layout.addLayout(discovery_buttons_layout)
        paths_group.setLayout(paths_layout)
        parent_layout.addWidget(paths_group)
        
        # Initialize tool list
        QTimer.singleShot(100, self._initialize_tools)
    
    def _initialize_tools(self) -> None:
        """Initialize the tools interface with current registry data."""
        try:
            # Get registry statistics
            stats = self.tool_registry.get_statistics()
            
            # Update status
            self.tools_status_label.setText(
                f"Tool system initialized • "
                f"Registry: {stats['total_tools']} tools registered"
            )
            
            # Update statistics
            self._update_tool_statistics()
            
            # Load tools into list
            self._refresh_tools()
            
            # Set discovery paths
            paths = [
                "src/tools/examples/",
                "src/tools/integration/",
                "src/tools/monitoring/",
                "~/.dinoair/tools/",
                "./tools/"
            ]
            self.discovery_paths_list.setPlainText("\n".join(paths))
            
        except Exception as e:
            self.logger.error(f"Error initializing tools: {str(e)}")
            self.tools_status_label.setText(f"Error: {str(e)}")
    
    def _refresh_tools(self) -> None:
        """Refresh the tool list from registry."""
        try:
            # Clear current list
            self.tools_list.clear()
            
            # Get all tools from registry
            tools = self.tool_registry.list_tools(enabled_only=False)
            
            # Sort by category and name
            tools.sort(key=lambda t: (t['category'], t['name']))
            
            # Add to list
            for tool in tools:
                # Create list item
                item = QListWidgetItem()
                
                # Set display text
                status_icon = "🟢" if tool['is_enabled'] else "🔴"
                category_emoji = self._get_category_emoji(tool['category'])
                item.setText(
                    f"{status_icon} {category_emoji} {tool['name']} "
                    f"(v{tool['version']})"
                )
                
                # Store tool data
                item.setData(Qt.ItemDataRole.UserRole, tool)
                
                # Add to list
                self.tools_list.addItem(item)
            
            # Update statistics
            self._update_tool_statistics()
            
        except Exception as e:
            self.logger.error(f"Error refreshing tools: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to refresh tools: {str(e)}"
            )
    
    def _get_category_emoji(self, category: str) -> str:
        """Get emoji for tool category."""
        category_emojis = {
            "data_processing": "📊",
            "ai_integration": "🤖",
            "file_operations": "📁",
            "monitoring": "📈",
            "testing": "🧪",
            "debugging": "🐛",
            "orchestration": "🎭",
            "utility": "🔧"
        }
        return category_emojis.get(category, "📦")
    
    def _on_tool_search(self, text: str) -> None:
        """Filter tools based on search text."""
        search_text = text.lower()
        
        for i in range(self.tools_list.count()):
            item = self.tools_list.item(i)
            tool_data = item.data(Qt.ItemDataRole.UserRole)
            
            # Search in name, description, category, and tags
            visible = (
                search_text in tool_data['name'].lower() or
                search_text in tool_data['description'].lower() or
                search_text in tool_data['category'].lower() or
                any(search_text in tag.lower()
                    for tag in tool_data.get('tags', []))
            )
            
            item.setHidden(not visible)
    
    def _on_tool_selected(
        self, current: QListWidgetItem, previous: QListWidgetItem
    ) -> None:
        """Handle tool selection."""
        if not current:
            self.tool_details_stack.setCurrentIndex(0)
            return
        
        # Get tool data
        tool_data = current.data(Qt.ItemDataRole.UserRole)
        if not tool_data:
            return
        
        # Show tool details
        self.tool_details_stack.setCurrentIndex(1)
        
        # Update tool information
        self.tool_name_label.setText(tool_data['name'])
        self.tool_version_label.setText(tool_data['version'])
        self.tool_category_label.setText(
            tool_data['category'].replace('_', ' ').title()
        )
        
        # Get metadata for author
        metadata = self.tool_registry.get_tool_metadata(tool_data['name'])
        if metadata and hasattr(metadata, 'author'):
            self.tool_author_label.setText(metadata.author)
        else:
            self.tool_author_label.setText("Unknown")
        
        # Description
        self.tool_description_text.setPlainText(tool_data['description'])
        
        # Enable/disable state
        self.tool_enabled_checkbox.setChecked(tool_data['is_enabled'])
        
        # Status
        if tool_data.get('is_instantiated'):
            status_text = f"Status: {tool_data.get('status', 'Unknown')}"
            if tool_data.get('is_ready'):
                self.tool_status_label.setStyleSheet(
                    "padding: 5px; background-color: #2d5a2d; "
                    "border-radius: 3px; color: #90ee90;"
                )
            else:
                self.tool_status_label.setStyleSheet(
                    "padding: 5px; background-color: #5a5a2d; "
                    "border-radius: 3px; color: #ffff90;"
                )
        else:
            status_text = "Status: Not Loaded"
            self.tool_status_label.setStyleSheet(
                "padding: 5px; background-color: #2B3A52; "
                "border-radius: 3px;"
            )
        self.tool_status_label.setText(status_text)
        
        # Usage statistics
        self.tool_usage_label.setText(f"Usage: {tool_data['use_count']} times")
        
        # Last used
        if tool_data['last_used']:
            self.tool_last_used_label.setText(
                f"Last Used: {tool_data['last_used']}"
            )
        else:
            self.tool_last_used_label.setText("Last Used: Never")
        
        # Dependencies (if available from metadata)
        if (metadata and hasattr(metadata, 'dependencies') and
                metadata.dependencies):
            self.dependencies_group.setVisible(True)
            # Clear old dependencies
            while self.dependencies_layout.count():
                child = self.dependencies_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Add dependencies
            for dep in metadata.dependencies:
                dep_label = QLabel(f"• {dep}")
                self.dependencies_layout.addWidget(dep_label)
        else:
            self.dependencies_group.setVisible(False)
    
    def _on_tool_enabled_changed(self, state: int) -> None:
        """Handle tool enable/disable toggle."""
        current_item = self.tools_list.currentItem()
        if not current_item:
            return
        
        tool_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not tool_data:
            return
        
        try:
            if state == Qt.CheckState.Checked.value:
                # Enable tool
                if self.tool_registry.enable_tool(tool_data['name']):
                    self.logger.info(f"Enabled tool: {tool_data['name']}")
                else:
                    raise Exception("Failed to enable tool")
            else:
                # Disable tool
                if self.tool_registry.disable_tool(tool_data['name']):
                    self.logger.info(f"Disabled tool: {tool_data['name']}")
                else:
                    raise Exception("Failed to disable tool")
            
            # Refresh the list to update status icon
            self._refresh_tools()
            
            # Re-select the same tool
            for i in range(self.tools_list.count()):
                item = self.tools_list.item(i)
                item_data = item.data(Qt.ItemDataRole.UserRole)
                if item_data['name'] == tool_data['name']:
                    self.tools_list.setCurrentItem(item)
                    break
                    
        except Exception as e:
            self.logger.error(f"Error toggling tool state: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to change tool state: {str(e)}"
            )
            # Revert checkbox state
            self.tool_enabled_checkbox.setChecked(not state)
    
    def _discover_tools(self) -> None:
        """Discover new tools from configured paths."""
        try:
            # Show progress
            self.discover_button.setEnabled(False)
            self.discover_button.setText("🔍 Discovering...")
            
            # Discover from common paths
            paths = [
                "src/tools/examples",
                "src/tools/integration",
                "src/tools/monitoring"
            ]
            
            results = self.tool_discovery.discover_and_register_all(
                paths=paths,
                discover_packages=True,
                auto_enable=False
            )
            
            # Show results
            total_discovered = results['total']['discovered']
            total_registered = results['total']['registered']
            total_failed = results['total']['failed']
            
            message = (
                f"Discovery complete!\n\n"
                f"Discovered: {total_discovered} tools\n"
                f"Registered: {total_registered} tools\n"
                f"Failed: {total_failed} tools"
            )
            
            if total_discovered > 0:
                QMessageBox.information(
                    self,
                    "Tool Discovery",
                    message
                )
                
                # Refresh tool list
                self._refresh_tools()
            else:
                QMessageBox.information(
                    self,
                    "Tool Discovery",
                    "No new tools were discovered."
                )
                
        except Exception as e:
            self.logger.error(f"Error discovering tools: {str(e)}")
            QMessageBox.critical(
                self,
                "Discovery Error",
                f"Failed to discover tools: {str(e)}"
            )
        finally:
            # Restore button
            self.discover_button.setEnabled(True)
            self.discover_button.setText("🔍 Discover Tools")
    
    def _add_discovery_path(self) -> None:
        """Add a new tool discovery path (placeholder)."""
        QMessageBox.information(
            self,
            "Coming Soon",
            "The ability to add custom tool discovery paths will be "
            "available in a future update."
        )
    
    def _update_tool_statistics(self) -> None:
        """Update tool statistics display."""
        try:
            stats = self.tool_registry.get_statistics()
            
            self.total_tools_label.setText(
                f"Total Tools: {stats['total_tools']}"
            )
            self.enabled_tools_label.setText(
                f"Enabled: {stats['enabled_tools']}"
            )
            self.active_tools_label.setText(
                f"Active: {stats['instantiated_tools']}"
            )
            
        except Exception as e:
            self.logger.error(f"Error updating tool statistics: {str(e)}")
