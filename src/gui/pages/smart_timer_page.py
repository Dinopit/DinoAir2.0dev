#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Smart Timer Page - Timer management interface with multiple timers
"""

import sqlite3
from datetime import datetime
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QLabel, QPushButton, QFrame,
    QListWidget, QMessageBox,
    QGroupBox, QSpinBox, QDoubleSpinBox, QLineEdit
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction

from ...utils.colors import DinoPitColors
from ...utils.logger import Logger
from ...utils.scaling import get_scaling_helper
from ...utils.smart_timer import SmartTimer, TimerManager


class SmartTimerPage(QWidget):
    """Smart Timer page widget with timer management functionality."""
    
    timer_updated = Signal(str, float)  # timer_name, elapsed_time
    
    def __init__(self):
        """Initialize the smart timer page."""
        super().__init__()
        self.logger = Logger()
        self.timer_manager = TimerManager()
        self._current_timer_name: Optional[str] = None
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_display)
        self._update_timer.setInterval(100)  # Update every 100ms
        self._scaling_helper = get_scaling_helper()
        
        # Database connection
        self._init_database()
        
        # Setup UI
        self.setup_ui()
        
        # Load saved timers
        self._load_saved_timers()
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
    def _init_database(self):
        """Initialize database connection for timer logs."""
        try:
            self.conn = sqlite3.connect('timers.db')
            self.conn.execute('''
            CREATE TABLE IF NOT EXISTS timer_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT,
                start_time DATETIME,
                end_time DATETIME,
                elapsed_seconds REAL
            );
            ''')
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            self.conn = None
            
    def setup_ui(self):
        """Setup the timer page UI."""
        layout = QVBoxLayout(self)
        
        # Use font metrics for consistent spacing
        font_metrics = self.fontMetrics()
        margin = font_metrics.height() // 2
        spacing = font_metrics.height() // 4
        
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(spacing)
        
        # Create toolbar
        toolbar_container = self._create_toolbar()
        layout.addWidget(toolbar_container)
        
        # Main content area
        main_content = QWidget()
        main_layout = QHBoxLayout(main_content)
        main_layout.setContentsMargins(0, margin, 0, 0)
        main_layout.setSpacing(margin)
        
        # Left panel - Timer list
        left_panel = self._create_timer_list_panel()
        main_layout.addWidget(left_panel)
        
        # Right panel - Timer details
        right_panel = self._create_timer_details_panel()
        main_layout.addWidget(right_panel, 1)  # Give more space to details
        
        layout.addWidget(main_content)
        
        # Bottom status panel
        self.status_label = QLabel("No timer selected")
        self.status_label.setStyleSheet(f"""
            background-color: {DinoPitColors.PANEL_BACKGROUND};
            color: {DinoPitColors.PRIMARY_TEXT};
            padding: {self._scaling_helper.scaled_size(10)}px;
            border-radius: {self._scaling_helper.scaled_size(4)}px;
            font-size: {self._scaling_helper.scaled_font_size(12)}px;
            font-weight: bold;
        """)
        layout.addWidget(self.status_label)
        
    def _create_toolbar(self) -> QWidget:
        """Create the toolbar with actions."""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self._update_toolbar_style()
        
        # New Timer action
        new_action = QAction("✚ New Timer", self)
        new_action.triggered.connect(self._create_new_timer)
        self.toolbar.addAction(new_action)
        
        # Start/Stop action
        self.start_stop_action = QAction("▶️ Start", self)
        self.start_stop_action.triggered.connect(self._toggle_timer)
        self.start_stop_action.setEnabled(False)
        self.toolbar.addAction(self.start_stop_action)
        
        # Reset action
        self.reset_action = QAction("🔄 Reset", self)
        self.reset_action.triggered.connect(self._reset_timer)
        self.reset_action.setEnabled(False)
        self.toolbar.addAction(self.reset_action)
        
        # Delete action
        self.delete_action = QAction("🗑️ Delete", self)
        self.delete_action.triggered.connect(self._delete_timer)
        self.delete_action.setEnabled(False)
        self.toolbar.addAction(self.delete_action)
        
        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().Policy.Expanding,
            spacer.sizePolicy().Policy.Preferred
        )
        self.toolbar.addWidget(spacer)
        
        # Timer count label
        self.count_label = QLabel("0 timers")
        self.count_label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT}; font-weight: bold;")
        self.toolbar.addWidget(self.count_label)
        
        container_layout.addWidget(self.toolbar)
        return container
        
    def _create_timer_list_panel(self) -> QWidget:
        """Create the timer list panel."""
        panel = QFrame()
        panel.setMaximumWidth(self._scaling_helper.scaled_size(300))
        panel.setMinimumWidth(self._scaling_helper.scaled_size(200))
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {DinoPitColors.SIDEBAR_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {self._scaling_helper.scaled_size(4)}px;
            }}
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10)
        )
        
        # Title
        title = QLabel("Timers")
        title.setStyleSheet(f"""
            color: {DinoPitColors.DINOPIT_ORANGE};
            font-size: {self._scaling_helper.scaled_font_size(16)}px;
            font-weight: bold;
            padding-bottom: {self._scaling_helper.scaled_size(10)}px;
        """)
        layout.addWidget(title)
        
        # Timer list
        self.timer_list = QListWidget()
        self.timer_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: none;
                border-radius: {self._scaling_helper.scaled_size(4)}px;
                padding: {self._scaling_helper.scaled_size(5)}px;
            }}
            QListWidget::item {{
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: {self._scaling_helper.scaled_size(8)}px;
                border-radius: {self._scaling_helper.scaled_size(4)}px;
                margin-bottom: {self._scaling_helper.scaled_size(2)}px;
            }}
            QListWidget::item:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QListWidget::item:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE};
            }}
        """)
        self.timer_list.currentTextChanged.connect(self._on_timer_selected)
        layout.addWidget(self.timer_list)
        
        return panel
        
    def _create_timer_details_panel(self) -> QWidget:
        """Create the timer details panel."""
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {self._scaling_helper.scaled_size(4)}px;
            }}
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            self._scaling_helper.scaled_size(20),
            self._scaling_helper.scaled_size(20),
            self._scaling_helper.scaled_size(20),
            self._scaling_helper.scaled_size(20)
        )
        
        # Timer display
        self.timer_display = QLabel("00:00:00")
        self.timer_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_timer_display_style()
        layout.addWidget(self.timer_display)
        
        # Current timer name
        self.timer_name_label = QLabel("No timer selected")
        self.timer_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_name_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: {self._scaling_helper.scaled_font_size(18)}px;
            font-weight: bold;
            margin: {self._scaling_helper.scaled_size(20)}px 0;
        """)
        layout.addWidget(self.timer_name_label)
        
        # Session logs
        logs_group = QGroupBox("Session Logs")
        logs_group.setStyleSheet(f"""
            QGroupBox {{
                color: {DinoPitColors.DINOPIT_ORANGE};
                font-weight: bold;
                font-size: {self._scaling_helper.scaled_font_size(14)}px;
                border: 2px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {self._scaling_helper.scaled_size(4)}px;
                margin-top: {self._scaling_helper.scaled_size(10)}px;
                padding-top: {self._scaling_helper.scaled_size(15)}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {self._scaling_helper.scaled_size(10)}px;
                padding: 0 {self._scaling_helper.scaled_size(5)}px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        logs_layout = QVBoxLayout(logs_group)
        
        self.logs_list = QListWidget()
        self.logs_list.setMaximumHeight(self._scaling_helper.scaled_size(150))
        self.logs_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: none;
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: {self._scaling_helper.scaled_font_size(12)}px;
            }}
        """)
        logs_layout.addWidget(self.logs_list)
        
        layout.addWidget(logs_group)
        
        # Quick actions section
        quick_actions_group = QGroupBox("Quick Actions")
        quick_actions_group.setStyleSheet(f"""
            QGroupBox {{
                color: {DinoPitColors.DINOPIT_ORANGE};
                font-weight: bold;
                font-size: {self._scaling_helper.scaled_font_size(14)}px;
                border: 2px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {self._scaling_helper.scaled_size(4)}px;
                margin-top: {self._scaling_helper.scaled_size(10)}px;
                padding-top: {self._scaling_helper.scaled_size(15)}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {self._scaling_helper.scaled_size(10)}px;
                padding: 0 {self._scaling_helper.scaled_size(5)}px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        quick_layout = QHBoxLayout(quick_actions_group)
        
        # Run repeats section
        repeats_label = QLabel("Repeats:")
        repeats_label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT};")
        quick_layout.addWidget(repeats_label)
        
        self.repeats_spin = QSpinBox()
        self.repeats_spin.setMinimum(1)
        self.repeats_spin.setMaximum(100)
        self.repeats_spin.setValue(5)
        self.repeats_spin.setStyleSheet(self._get_spinbox_style())
        quick_layout.addWidget(self.repeats_spin)
        
        duration_label = QLabel("Duration (s):")
        duration_label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT};")
        quick_layout.addWidget(duration_label)
        
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setMinimum(0.1)
        self.duration_spin.setMaximum(3600.0)
        self.duration_spin.setValue(1.0)
        self.duration_spin.setSingleStep(0.1)
        self.duration_spin.setStyleSheet(self._get_spinbox_style())
        quick_layout.addWidget(self.duration_spin)
        
        self.run_repeats_btn = QPushButton("Run Repeats")
        self.run_repeats_btn.setEnabled(False)
        self.run_repeats_btn.clicked.connect(self._run_repeats)
        self.run_repeats_btn.setStyleSheet(self._get_button_style())
        quick_layout.addWidget(self.run_repeats_btn)
        
        layout.addWidget(quick_actions_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        return panel
        
    def _get_spinbox_style(self) -> str:
        """Get spinbox style."""
        return f"""
            QSpinBox, QDoubleSpinBox {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {self._scaling_helper.scaled_size(4)}px;
                padding: {self._scaling_helper.scaled_size(5)}px;
                font-size: {self._scaling_helper.scaled_font_size(12)}px;
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                border: none;
                width: {self._scaling_helper.scaled_size(20)}px;
            }}
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
            }}
        """
        
    def _get_button_style(self) -> str:
        """Get button style."""
        return f"""
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: {self._scaling_helper.scaled_size(4)}px;
                padding: {self._scaling_helper.scaled_size(8)}px;
                padding-left: {self._scaling_helper.scaled_size(16)}px;
                padding-right: {self._scaling_helper.scaled_size(16)}px;
                font-weight: bold;
                font-size: {self._scaling_helper.scaled_font_size(12)}px;
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
        
    def _create_new_timer(self):
        """Create a new timer."""
        # Simple input dialog
        from PySide6.QtWidgets import QInputDialog
        
        timer_name, ok = QInputDialog.getText(
            self,
            "New Timer",
            "Enter timer name:",
            QLineEdit.EchoMode.Normal,
            ""
        )
        
        if ok and timer_name:
            # Check if timer already exists
            if timer_name in self.timer_manager.list_timers():
                QMessageBox.warning(
                    self,
                    "Timer Exists",
                    f"A timer named '{timer_name}' already exists."
                )
                return
                
            # Create timer
            self.timer_manager.create_timer(timer_name)
            
            # Add to list
            self.timer_list.addItem(timer_name)
            
            # Update count
            self._update_timer_count()
            
            # Select the new timer
            self.timer_list.setCurrentRow(self.timer_list.count() - 1)
            
            self.logger.info(f"Created new timer: {timer_name}")
            
    def _on_timer_selected(self, timer_name: str):
        """Handle timer selection."""
        if not timer_name:
            self._current_timer_name = None
            self.timer_name_label.setText("No timer selected")
            self.start_stop_action.setEnabled(False)
            self.reset_action.setEnabled(False)
            self.delete_action.setEnabled(False)
            self.run_repeats_btn.setEnabled(False)
            self._update_display()
            return
            
        self._current_timer_name = timer_name
        timer = self.timer_manager.get_timer(timer_name)
        
        if timer:
            # Update display
            self.timer_name_label.setText(timer_name)
            
            # Update button states
            self.start_stop_action.setEnabled(True)
            self.reset_action.setEnabled(True)
            self.delete_action.setEnabled(True)
            self.run_repeats_btn.setEnabled(not timer.running)
            
            # Update start/stop button text
            if timer.running:
                self.start_stop_action.setText("⏸️ Stop")
            else:
                self.start_stop_action.setText("▶️ Start")
                
            # Update logs display
            self._update_logs_display()
            
            # Update time display
            self._update_display()
            
    def _toggle_timer(self):
        """Start or stop the current timer."""
        if not self._current_timer_name:
            return
            
        timer = self.timer_manager.get_timer(self._current_timer_name)
        if not timer:
            return
            
        if timer.running:
            # Stop timer
            start_time = (datetime.fromtimestamp(timer.start_time)
                          if timer.start_time else datetime.now())
            timer.stop()
            self.start_stop_action.setText("▶️ Start")
            self._update_timer.stop()
            self.run_repeats_btn.setEnabled(True)
            
            # Log to database
            if self.conn:
                try:
                    elapsed = timer.get_elapsed_time()
                    end_time = datetime.now()
                    self._log_timer_to_db(
                        self._current_timer_name,
                        start_time,
                        end_time,
                        elapsed
                    )
                except Exception as e:
                    self.logger.error(f"Failed to log timer: {e}")
                    
            # Update status
            self.status_label.setText(
                f"Timer '{self._current_timer_name}' stopped"
            )
        else:
            # Start timer
            timer.start()
            self.start_stop_action.setText("⏸️ Stop")
            self._update_timer.start()
            self.run_repeats_btn.setEnabled(False)
            
            # Update status
            self.status_label.setText(
                f"Timer '{self._current_timer_name}' started"
            )
            
        # Update logs display
        self._update_logs_display()
        
    def _reset_timer(self):
        """Reset the current timer."""
        if not self._current_timer_name:
            return
            
        timer = self.timer_manager.get_timer(self._current_timer_name)
        if not timer:
            return
            
        # Confirm reset
        reply = QMessageBox.question(
            self,
            "Reset Timer",
            f"Are you sure you want to reset '{self._current_timer_name}'?\n"
            "This will clear all session logs.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            timer.reset()
            self._update_display()
            self._update_logs_display()
            self.start_stop_action.setText("▶️ Start")
            self._update_timer.stop()
            self.run_repeats_btn.setEnabled(True)
            
            # Update status
            self.status_label.setText(
                f"Timer '{self._current_timer_name}' reset"
            )
            
    def _delete_timer(self):
        """Delete the current timer."""
        if not self._current_timer_name:
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Timer",
            f"Are you sure you want to delete '{self._current_timer_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove from manager
            self.timer_manager.remove_timer(self._current_timer_name)
            
            # Remove from list
            items = self.timer_list.findItems(
                self._current_timer_name,
                Qt.MatchFlag.MatchExactly
            )
            for item in items:
                self.timer_list.takeItem(self.timer_list.row(item))
                
            # Clear selection
            self._current_timer_name = None
            self.timer_name_label.setText("No timer selected")
            self.timer_display.setText("00:00:00")
            self.logs_list.clear()
            
            # Update count
            self._update_timer_count()
            
            # Update status
            self.status_label.setText("Timer deleted")
            
    def _run_repeats(self):
        """Run the timer for specified repeats."""
        if not self._current_timer_name:
            return
            
        timer = self.timer_manager.get_timer(self._current_timer_name)
        if not timer or timer.running:
            return
            
        repeats = self.repeats_spin.value()
        duration = self.duration_spin.value()
        
        # Disable UI during repeats
        self.run_repeats_btn.setEnabled(False)
        self.start_stop_action.setEnabled(False)
        self.reset_action.setEnabled(False)
        self.delete_action.setEnabled(False)
        
        # Run repeats
        self.status_label.setText(
            f"Running {repeats} repeats of {duration}s each..."
        )
        
        # Use QTimer to avoid blocking the UI
        self._repeat_count = 0
        self._total_repeats = repeats
        self._repeat_duration = duration
        
        self._run_single_repeat()
        
    def _run_single_repeat(self):
        """Run a single repeat cycle."""
        if self._repeat_count >= self._total_repeats:
            # Finished all repeats
            self._finish_repeats()
            return
            
        timer = self.timer_manager.get_timer(self._current_timer_name)
        if not timer:
            self._finish_repeats()
            return
            
        # Start timer
        timer.start()
        self._update_timer.start()
        
        # Schedule stop after duration
        QTimer.singleShot(
            int(self._repeat_duration * 1000),
            self._complete_single_repeat
        )
        
    def _complete_single_repeat(self):
        """Complete a single repeat cycle."""
        timer = self.timer_manager.get_timer(self._current_timer_name)
        if timer and self._current_timer_name:
            # Log to database before stopping
            start_time = (datetime.fromtimestamp(timer.start_time)
                          if timer.start_time else datetime.now())
            timer.stop()
            
            if self.conn:
                try:
                    elapsed = self._repeat_duration
                    end_time = datetime.now()
                    self._log_timer_to_db(
                        self._current_timer_name,
                        start_time,
                        end_time,
                        elapsed
                    )
                except Exception as e:
                    self.logger.error(f"Failed to log repeat: {e}")
                    
        self._repeat_count += 1
        
        # Update status
        self.status_label.setText(
            f"Completed repeat {self._repeat_count}/{self._total_repeats}"
        )
        
        # Update displays
        self._update_display()
        self._update_logs_display()
        
        # Schedule next repeat with small delay
        QTimer.singleShot(100, self._run_single_repeat)
        
    def _finish_repeats(self):
        """Finish the repeat cycle."""
        # Re-enable UI
        self.run_repeats_btn.setEnabled(True)
        self.start_stop_action.setEnabled(True)
        self.reset_action.setEnabled(True)
        self.delete_action.setEnabled(True)
        
        # Update status
        self.status_label.setText(
            f"Completed {self._repeat_count} repeats"
        )
        
        # Stop update timer
        self._update_timer.stop()
        
    def _update_display(self):
        """Update the timer display."""
        if not self._current_timer_name:
            self.timer_display.setText("00:00:00")
            return
            
        timer = self.timer_manager.get_timer(self._current_timer_name)
        if not timer:
            self.timer_display.setText("00:00:00")
            return
            
        elapsed = timer.get_elapsed_time()
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        milliseconds = int((elapsed % 1) * 10)
        
        self.timer_display.setText(
            f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds}"
        )
        
        # Emit signal for external updates
        self.timer_updated.emit(self._current_timer_name, elapsed)
        
    def _update_logs_display(self):
        """Update the session logs display."""
        self.logs_list.clear()
        
        if not self._current_timer_name:
            return
            
        timer = self.timer_manager.get_timer(self._current_timer_name)
        if not timer:
            return
            
        logs = timer.get_logs()
        for i, log_time in enumerate(logs, 1):
            self.logs_list.addItem(f"Session {i}: {log_time:.2f}s")
            
        # Add total if there are logs
        if logs:
            total = sum(logs)
            self.logs_list.addItem(f"Total: {total:.2f}s")
            
    def _update_timer_count(self):
        """Update the timer count display."""
        count = len(self.timer_manager.list_timers())
        self.count_label.setText(f"{count} timer{'s' if count != 1 else ''}")
        
    def _log_timer_to_db(self, task_name: str, start_time: datetime, 
                         end_time: datetime, elapsed_seconds: float):
        """Log timer data to database."""
        if not self.conn:
            return
            
        try:
            self.conn.execute(
                """INSERT INTO timer_logs 
                (task_name, start_time, end_time, elapsed_seconds) 
                VALUES (?, ?, ?, ?)""",
                (task_name, start_time, end_time, elapsed_seconds)
            )
            self.conn.commit()
            self.logger.info(
                f"Logged timer: {task_name} - {elapsed_seconds:.2f}s"
            )
        except Exception as e:
            self.logger.error(f"Failed to log timer to database: {e}")
            
    def _load_saved_timers(self):
        """Load previously saved timers from configuration or database."""
        # For now, create a few default timers
        default_timers = ["Work", "Break", "Exercise", "Study"]
        for timer_name in default_timers:
            self.timer_manager.create_timer(timer_name)
            self.timer_list.addItem(timer_name)
            
        self._update_timer_count()
        
    def closeEvent(self, event):
        """Handle close event to clean up resources."""
        # Stop update timer
        self._update_timer.stop()
        
        # Close database connection
        if self.conn:
            self.conn.close()
            
        event.accept()
        
    def _update_toolbar_style(self):
        """Update toolbar style with current scaling."""
        s = self._scaling_helper
        self.toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: none;
                padding: {s.scaled_size(5)}px;
                spacing: {s.scaled_size(10)}px;
            }}
            QToolButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: {s.scaled_size(4)}px;
                padding: {s.scaled_size(8)}px {s.scaled_size(16)}px;
                font-weight: bold;
                font-size: {s.scaled_font_size(12)}px;
                margin-right: {s.scaled_size(5)}px;
            }}
            QToolButton:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
            }}
            QToolButton:pressed {{
                background-color: #E55A2B;
            }}
            QToolButton:disabled {{
                background-color: #666666;
                color: #999999;
            }}
        """)
        
    def _update_timer_display_style(self):
        """Update timer display style with current scaling."""
        self.timer_display.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: {self._scaling_helper.scaled_font_size(48)}px;
            font-weight: bold;
            font-family: 'Courier New', monospace;
            background-color: {DinoPitColors.MAIN_BACKGROUND};
            border: 2px solid {DinoPitColors.SOFT_ORANGE};
            border-radius: {self._scaling_helper.scaled_size(8)}px;
            padding: {self._scaling_helper.scaled_size(20)}px;
        """)
        
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes."""
        # Update toolbar style
        self._update_toolbar_style()
        
        # Update timer display style
        self._update_timer_display_style()
        
        # Update status label
        self.status_label.setStyleSheet(f"""
            background-color: {DinoPitColors.PANEL_BACKGROUND};
            color: {DinoPitColors.PRIMARY_TEXT};
            padding: {self._scaling_helper.scaled_size(10)}px;
            border-radius: {self._scaling_helper.scaled_size(4)}px;
            font-size: {self._scaling_helper.scaled_font_size(12)}px;
            font-weight: bold;
        """)