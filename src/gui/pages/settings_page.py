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
    QTabWidget, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from src.utils.config_loader import ConfigLoader
from src.utils.Watchdog import SystemWatchdog
from src.gui.components.directory_limiter_widget import DirectoryLimiterWidget
from src.database.file_search_db import FileSearchDB
from src.utils.logger import Logger
from src.utils.colors import DinoPitColors


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
        self.status_timer.start(1000)  # Update every second
        
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
        self.include_types_edit.setStyleSheet("color: #FFFFFF; background-color: #2B3A52; border: 1px solid #4A5A7A; padding: 5px;")
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
        self.exclude_types_edit.setStyleSheet("color: #FFFFFF; background-color: #2B3A52; border: 1px solid #4A5A7A; padding: 5px;")
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
        if self.watchdog_ref and self.watchdog_ref._monitoring:
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
            if self.watchdog_ref._monitoring:
                self.status_label.setText("Status: 🟢 Running")
                self.status_label.setStyleSheet(
                    "QLabel { padding: 10px; background-color: #2d5a2d; "
                    "border-radius: 5px; color: #90ee90; }"
                )
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                
                # Get current metrics if available
                if self.watchdog_ref._last_metrics:
                    metrics = self.watchdog_ref._last_metrics
                    status_text = (
                        f"Status: 🟢 Running\n"
                        f"VRAM: {metrics.vram_percent:.1f}% | "
                        f"RAM: {metrics.ram_percent:.1f}% | "
                        f"CPU: {metrics.cpu_percent:.1f}% | "
                        f"Processes: {metrics.dinoair_processes}"
                    )
                    self.status_label.setText(status_text)
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
