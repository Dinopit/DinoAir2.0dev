"""
File Indexing Status Widget - Display indexing progress and statistics
"""

import os
from typing import Dict, Any
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame, QGroupBox,
    QFileDialog
)
from PySide6.QtCore import Signal, Qt, QTimer

from ...utils.colors import DinoPitColors
from ...utils.logger import Logger
from ...utils.scaling import get_scaling_helper


class IndexingStatusWidget(QWidget):
    """Widget to display file indexing status and controls"""
    
    # Signals
    index_directory_requested = Signal(str)  # directory_path
    cancel_indexing_requested = Signal()
    
    def __init__(self):
        super().__init__()
        self.logger = Logger()
        self._is_indexing = False
        self._last_update_time = None
        self._scaling_helper = get_scaling_helper()
        
        self.setup_ui()
        
        # Timer for updating "last updated" display
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_time_display)
        self._update_timer.setInterval(60000)  # Update every minute
        self._update_timer.start()
    
    def setup_ui(self):
        """Setup the status widget UI"""
        main_layout = QVBoxLayout(self)
        
        # Main status frame
        status_frame = QFrame()
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        
        status_layout = QVBoxLayout(status_frame)
        
        # Header with title and controls
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📊 Indexing Status")
        title_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-weight: bold;
            font-size: 16px;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Index button
        self.index_button = QPushButton("📁 Index Directory")
        self.index_button.setStyleSheet(self._get_button_style())
        self.index_button.clicked.connect(self._on_index_clicked)
        header_layout.addWidget(self.index_button)
        
        # Cancel button (hidden by default)
        self.cancel_button = QPushButton("❌ Cancel")
        self.cancel_button.setStyleSheet(self._get_cancel_button_style())
        self.cancel_button.clicked.connect(self.cancel_indexing_requested.emit)
        self.cancel_button.hide()
        header_layout.addWidget(self.cancel_button)
        
        status_layout.addLayout(header_layout)
        
        # Progress section
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress label
        self.progress_label = QLabel("No indexing in progress")
        self.progress_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: 13px;
        """)
        progress_layout.addWidget(self.progress_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 5px;
                text-align: center;
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                border-radius: 4px;
            }}
        """)
        self.progress_bar.hide()
        progress_layout.addWidget(self.progress_bar)
        
        status_layout.addWidget(self.progress_widget)
        
        # Status message
        self.status_message = QLabel("")
        self.status_message.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: 12px;
            padding: 5px;
            border-radius: 3px;
        """)
        self.status_message.setWordWrap(True)
        self.status_message.hide()
        status_layout.addWidget(self.status_message)
        
        # Statistics section
        stats_group = QGroupBox("Index Statistics")
        stats_group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: {DinoPitColors.PRIMARY_TEXT};
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        
        stats_layout = QVBoxLayout(stats_group)
        
        # Stats grid
        stats_grid_layout = QHBoxLayout()
        
        # Total files
        self.files_stat = self._create_stat_widget(
            "📄 Total Files", "0"
        )
        stats_grid_layout.addWidget(self.files_stat)
        
        # Total chunks
        self.chunks_stat = self._create_stat_widget(
            "🧩 Total Chunks", "0"
        )
        stats_grid_layout.addWidget(self.chunks_stat)
        
        # Total size
        self.size_stat = self._create_stat_widget(
            "💾 Total Size", "0 B"
        )
        stats_grid_layout.addWidget(self.size_stat)
        
        # Last updated
        self.updated_stat = self._create_stat_widget(
            "🕐 Last Updated", "Never"
        )
        stats_grid_layout.addWidget(self.updated_stat)
        
        stats_layout.addLayout(stats_grid_layout)
        status_layout.addWidget(stats_group)
        
        main_layout.addWidget(status_frame)
    
    def _create_stat_widget(self, label: str, value: str) -> QWidget:
        """Create a statistics display widget"""
        widget = QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(2)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: 11px;
        """)
        label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_widget)
        
        value_widget = QLabel(value)
        value_widget.setObjectName("stat_value")  # For easy updating
        value_widget.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: 14px;
            font-weight: bold;
        """)
        value_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_widget)
        
        return widget
    
    def _get_button_style(self) -> str:
        """Get button stylesheet"""
        return f"""
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: 15px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
            }}
            QPushButton:pressed {{
                background-color: #E55A2B;
            }}
            QPushButton:disabled {{
                background-color: #666666;
                color: #999999;
            }}
        """
    
    def _get_cancel_button_style(self) -> str:
        """Get cancel button stylesheet"""
        return """
            QPushButton {{
                background-color: #DC3545;
                color: white;
                border: none;
                border-radius: 15px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #C82333;
            }}
            QPushButton:pressed {{
                background-color: #BD2130;
            }}
        """
    
    def _on_index_clicked(self):
        """Handle index button click"""
        # Get last directory from parent if available
        last_dir = ""
        parent = self.parent()
        if parent and hasattr(parent, '_last_selected_directory'):
            last_dir = getattr(parent, '_last_selected_directory', '')
        
        # Show directory picker
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Index",
            last_dir or os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly |
            QFileDialog.Option.DontResolveSymlinks
        )
        
        if directory:
            self.index_directory_requested.emit(directory)
    
    def set_indexing_active(self, active: bool):
        """Set whether indexing is currently active"""
        self._is_indexing = active
        
        if active:
            self.index_button.hide()
            self.cancel_button.show()
            self.progress_bar.show()
            self.progress_bar.setValue(0)
            self.progress_label.setText("Starting indexing...")
        else:
            self.index_button.show()
            self.cancel_button.hide()
            self.progress_bar.hide()
            self.progress_label.setText("No indexing in progress")
    
    def update_progress(self, message: str, current: int, total: int):
        """Update indexing progress"""
        self.progress_label.setText(message)
        
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
            self.progress_bar.setFormat(f"{current}/{total} ({progress}%)")
        else:
            self.progress_bar.setValue(0)
    
    def update_status(self, message: str, status_type: str = "info"):
        """Update status message"""
        self.status_message.setText(message)
        self.status_message.show()
        
        # Style based on status type
        if status_type == "success":
            bg_color = "#28A745"
        elif status_type == "error":
            bg_color = "#DC3545"
        elif status_type == "warning":
            bg_color = DinoPitColors.DINOPIT_ORANGE
        else:  # info
            bg_color = DinoPitColors.DINOPIT_ORANGE
        
        self.status_message.setStyleSheet(f"""
            color: white;
            font-size: 12px;
            padding: 5px;
            background-color: {bg_color};
            border-radius: 3px;
        """)
        
        # Auto-hide after 5 seconds for non-error messages
        if status_type != "error":
            QTimer.singleShot(5000, self.status_message.hide)
    
    def update_stats(self, stats: Dict[str, Any]):
        """Update statistics display"""
        # Update file count
        if 'total_files' in stats:
            value_label = self.files_stat.findChild(QLabel, "stat_value")
            if value_label:
                value_label.setText(str(stats['total_files']))
        
        # Update chunk count
        if 'total_chunks' in stats:
            value_label = self.chunks_stat.findChild(QLabel, "stat_value")
            if value_label:
                value_label.setText(str(stats['total_chunks']))
        
        # Update size
        if 'total_size' in stats:
            value_label = self.size_stat.findChild(QLabel, "stat_value")
            if value_label:
                value_label.setText(
                    self._format_file_size(stats['total_size'])
                )
        
        # Update last updated time
        if 'last_indexed' in stats and stats['last_indexed']:
            self._last_update_time = datetime.fromisoformat(
                stats['last_indexed']
            )
            self._update_time_display()
        elif stats.get('total_files', 0) > 0:
            # If we have files but no timestamp, use now
            self._last_update_time = datetime.now()
            self._update_time_display()
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size for display"""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def _update_time_display(self):
        """Update the last updated time display"""
        if not self._last_update_time:
            return
        
        value_label = self.updated_stat.findChild(QLabel, "stat_value")
        if not value_label:
            return
        
        # Calculate time difference
        now = datetime.now()
        diff = now - self._last_update_time
        
        # Format based on time difference
        if diff.total_seconds() < 60:
            text = "Just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            text = f"{minutes} min{'s' if minutes != 1 else ''} ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            text = f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.days < 7:
            text = f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        else:
            text = self._last_update_time.strftime("%Y-%m-%d")
        
        value_label.setText(text)