"""
Appointments Page - Calendar interface with event management
"""

from typing import Optional, Dict
from datetime import datetime, date, time, timedelta
import uuid
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QMessageBox, QLabel, QPushButton, QFrame,
    QMenu, QCalendarWidget, QListWidget, QListWidgetItem,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QTimeEdit,
    QCheckBox, QComboBox, QSpinBox, QDateEdit, QDialogButtonBox,
    QGroupBox
)
from PySide6.QtCore import Qt, QDate, QTime, Signal, QTimer
from PySide6.QtGui import (
    QAction, QKeySequence, QShortcut, QTextCharFormat, QColor
)

from ...database.appointments_db import AppointmentsDatabase
from ...models.calendar_event import CalendarEvent, EventType, EventStatus
from ...utils.colors import DinoPitColors
from ...utils.logger import Logger
from ...utils.scaling import get_scaling_helper
from ...utils.window_state import window_state_manager
from ..components.tag_input_widget import TagInputWidget
from ..components.project_combo_box import ProjectComboBox


class EventListItem(QListWidgetItem):
    """Custom list item for events"""
    def __init__(self, event: CalendarEvent):
        super().__init__()
        self.event = event
        self._update_display()
        
    def _update_display(self):
        """Update the display text for the event"""
        time_str = ""
        if self.event.all_day:
            time_str = "All day"
        elif self.event.start_time:
            time_str = self.event.start_time.strftime("%I:%M %p")
            if self.event.end_time:
                time_str += f" - {self.event.end_time.strftime('%I:%M %p')}"
        
        # Add status indicator
        status_icon = {
            EventStatus.SCHEDULED.value: "📅",
            EventStatus.IN_PROGRESS.value: "⏳",
            EventStatus.COMPLETED.value: "✅",
            EventStatus.CANCELLED.value: "❌",
            EventStatus.RESCHEDULED.value: "🔄"
        }.get(self.event.status, "📅")
        
        display_text = f"{status_icon} {time_str} - {self.event.title}"
        if self.event.location:
            display_text += f" 📍 {self.event.location}"
            
        self.setText(display_text)


class EventDialog(QDialog):
    """Dialog for creating/editing events"""
    
    def __init__(self, parent=None, event: Optional[CalendarEvent] = None,
                 selected_date: Optional[date] = None):
        super().__init__(parent)
        self.logger = Logger()
        self._event = event  # Renamed to avoid conflict with QWidget.event()
        self.selected_date = selected_date or date.today()
        self._scaling_helper = get_scaling_helper()
        self.setup_ui()
        
        if event:
            self.load_event(event)
            
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("New Event" if not self._event else "Edit Event")
        self.setModal(True)
        
        # Set minimum size with scaling
        self.setMinimumWidth(self._scaling_helper.scaled_size(500))
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(self._scaling_helper.scaled_size(10))
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(self._scaling_helper.scaled_size(8))
        
        # Title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter event title...")
        form_layout.addRow("Title:", self.title_input)
        
        # Event type
        self.type_combo = QComboBox()
        for event_type in EventType:
            self.type_combo.addItem(
                event_type.value.capitalize(), event_type.value
            )
        form_layout.addRow("Type:", self.type_combo)
        
        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(
            QDate(self.selected_date.year, self.selected_date.month,
                  self.selected_date.day)
        )
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        
        # Style the calendar popup
        calendar_popup = self.date_edit.calendarWidget()
        if calendar_popup:
            calendar_popup.setStyleSheet(f"""
                QCalendarWidget {{
                    background-color: {DinoPitColors.PANEL_BACKGROUND};
                    color: {DinoPitColors.PRIMARY_TEXT};
                }}
                
                /* Navigation bar */
                QCalendarWidget QWidget#qt_calendar_navigationbar {{
                    background-color: {DinoPitColors.PANEL_BACKGROUND};
                }}
                
                /* Month/Year labels and navigation buttons */
                QCalendarWidget QToolButton {{
                    color: {DinoPitColors.PRIMARY_TEXT};
                    background-color: {DinoPitColors.PANEL_BACKGROUND};
                    font-weight: bold;
                    padding: 5px;
                }}
                
                QCalendarWidget QToolButton:hover {{
                    background-color: {DinoPitColors.SOFT_ORANGE};
                    border-radius: 3px;
                }}
                
                /* Calendar grid */
                QCalendarWidget QTableView {{
                    background-color: {DinoPitColors.MAIN_BACKGROUND};
                    selection-background-color: {DinoPitColors.DINOPIT_ORANGE};
                    selection-color: white;
                    gridline-color: {DinoPitColors.SOFT_ORANGE};
                }}
                
                /* Days */
                QCalendarWidget QAbstractItemView::item {{
                    color: {DinoPitColors.PRIMARY_TEXT};
                    padding: 3px;
                }}
                
                QCalendarWidget QAbstractItemView::item:selected {{
                    background-color: {DinoPitColors.DINOPIT_ORANGE};
                    color: white;
                }}
                
                /* Ensure all date text is visible */
                QCalendarWidget QWidget {{
                    color: {DinoPitColors.PRIMARY_TEXT};
                }}
            """)
        
        form_layout.addRow("Date:", self.date_edit)
        
        # Time group
        time_group = QGroupBox("Time")
        time_layout = QVBoxLayout(time_group)
        
        # All day checkbox
        self.all_day_check = QCheckBox("All day event")
        self.all_day_check.toggled.connect(self._on_all_day_toggled)
        time_layout.addWidget(self.all_day_check)
        
        # Time inputs
        time_input_layout = QHBoxLayout()
        
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat("hh:mm AP")
        self.start_time_edit.setTime(QTime(9, 0))  # Default 9 AM
        time_input_layout.addWidget(QLabel("Start:"))
        time_input_layout.addWidget(self.start_time_edit)
        
        time_input_layout.addWidget(QLabel("End:"))
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat("hh:mm AP")
        self.end_time_edit.setTime(QTime(10, 0))  # Default 10 AM
        time_input_layout.addWidget(self.end_time_edit)
        
        time_layout.addLayout(time_input_layout)
        form_layout.addRow(time_group)
        
        # Location
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Enter location (optional)")
        form_layout.addRow("Location:", self.location_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText(
            "Enter description (optional)"
        )
        self.description_input.setMaximumHeight(
            self._scaling_helper.scaled_size(100)
        )
        form_layout.addRow("Description:", self.description_input)
        
        # Participants
        self.participants_input = QLineEdit()
        self.participants_input.setPlaceholderText(
            "Enter participants, separated by commas"
        )
        form_layout.addRow("Participants:", self.participants_input)
        
        # Tags
        self.tags_input = TagInputWidget()
        form_layout.addRow("Tags:", self.tags_input)
        
        # Status
        self.status_combo = QComboBox()
        for status in EventStatus:
            self.status_combo.addItem(status.value.capitalize(), status.value)
        form_layout.addRow("Status:", self.status_combo)
        
        # Reminder
        reminder_layout = QHBoxLayout()
        self.reminder_check = QCheckBox("Remind me")
        self.reminder_check.toggled.connect(self._on_reminder_toggled)
        reminder_layout.addWidget(self.reminder_check)
        
        self.reminder_spin = QSpinBox()
        self.reminder_spin.setMinimum(5)
        self.reminder_spin.setMaximum(1440)  # 24 hours
        self.reminder_spin.setSingleStep(5)
        self.reminder_spin.setValue(15)
        self.reminder_spin.setSuffix(" minutes before")
        self.reminder_spin.setEnabled(False)
        reminder_layout.addWidget(self.reminder_spin)
        reminder_layout.addStretch()
        
        form_layout.addRow("Reminder:", reminder_layout)
        
        # Color picker (simplified - just a combo box)
        self.color_combo = QComboBox()
        colors = [
            ("Default", None),
            ("Red", "#FF6B6B"),
            ("Orange", "#FF9F40"),
            ("Yellow", "#FFD93D"),
            ("Green", "#6BCF7F"),
            ("Blue", "#4ECDC4"),
            ("Purple", "#A78BFA"),
            ("Pink", "#F472B6")
        ]
        for color_name, color_value in colors:
            self.color_combo.addItem(color_name, color_value)
        form_layout.addRow("Color:", self.color_combo)
        
        # Project selector
        self.project_combo = ProjectComboBox(self, include_no_project=True)
        form_layout.addRow("Project:", self.project_combo)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Additional notes (optional)")
        self.notes_input.setMaximumHeight(
            self._scaling_helper.scaled_size(80)
        )
        form_layout.addRow("Notes:", self.notes_input)
        
        layout.addLayout(form_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        # Style buttons
        buttons.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
            }}
            QPushButton:pressed {{
                background-color: #E55A2B;
            }}
        """)
        
        layout.addWidget(buttons)
        
        # Set dialog style
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
            QLabel {{
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QLineEdit, QTextEdit, QTimeEdit, QDateEdit, QSpinBox {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 5px;
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: 14px;
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 0.5);
            }}
            QLineEdit:focus, QTextEdit:focus, QTimeEdit:focus,
            QDateEdit:focus, QSpinBox:focus {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            
            /* Calendar popup specific styling */
            QDateEdit::drop-down {{
                border: none;
                width: 20px;
            }}
            QDateEdit::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid {DinoPitColors.PRIMARY_TEXT};
            }}
            
            /* Time/Date display text */
            QDateEdit, QTimeEdit {{
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QComboBox {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 5px;
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: 14px;
            }}
            QComboBox:hover {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {DinoPitColors.PRIMARY_TEXT};
                margin-right: 5px;
            }}
            QCheckBox {{
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 3px;
                background-color: {DinoPitColors.MAIN_BACKGROUND};
            }}
            QCheckBox::indicator:checked {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QGroupBox {{
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        
    def _on_all_day_toggled(self, checked: bool):
        """Handle all day checkbox toggle"""
        self.start_time_edit.setEnabled(not checked)
        self.end_time_edit.setEnabled(not checked)
        
    def _on_reminder_toggled(self, checked: bool):
        """Handle reminder checkbox toggle"""
        self.reminder_spin.setEnabled(checked)
        
    def load_event(self, event: CalendarEvent):
        """Load event data into the form"""
        self.title_input.setText(event.title)
        
        # Set event type
        type_index = self.type_combo.findData(event.event_type)
        if type_index >= 0:
            self.type_combo.setCurrentIndex(type_index)
            
        # Set date
        if event.event_date:
            self.date_edit.setDate(
                QDate(event.event_date.year, event.event_date.month,
                      event.event_date.day)
            )
            
        # Set time
        self.all_day_check.setChecked(event.all_day)
        if event.start_time:
            self.start_time_edit.setTime(
                QTime(event.start_time.hour, event.start_time.minute,
                      event.start_time.second)
            )
        if event.end_time:
            self.end_time_edit.setTime(
                QTime(event.end_time.hour, event.end_time.minute,
                      event.end_time.second)
            )
            
        # Set other fields
        self.location_input.setText(event.location or "")
        self.description_input.setPlainText(event.description or "")
        
        if event.participants:
            self.participants_input.setText(", ".join(event.participants))
            
        if event.tags:
            self.tags_input.set_tags(event.tags)
            
        # Set status
        status_index = self.status_combo.findData(event.status)
        if status_index >= 0:
            self.status_combo.setCurrentIndex(status_index)
            
        # Set reminder
        if event.reminder_minutes_before:
            self.reminder_check.setChecked(True)
            self.reminder_spin.setValue(event.reminder_minutes_before)
            
        # Set color
        if event.color:
            color_index = self.color_combo.findData(event.color)
            if color_index >= 0:
                self.color_combo.setCurrentIndex(color_index)
                
        # Set notes
        self.notes_input.setPlainText(event.notes or "")
        
        # Set project
        if hasattr(event, 'project_id'):
            self.project_combo.set_project_id(event.project_id)
        else:
            self.project_combo.set_project_id(None)
        
    def get_event_data(self) -> CalendarEvent:
        """Get event data from the form"""
        # Parse participants
        participants_text = self.participants_input.text().strip()
        participants = []
        if participants_text:
            participants = [p.strip() for p in participants_text.split(',')]
            
        # Create or update event
        if self._event:
            event = self._event
        else:
            event = CalendarEvent()
            
        event.title = self.title_input.text().strip()
        event.event_type = self.type_combo.currentData()
        qdate = self.date_edit.date()
        event.event_date = date(qdate.year(), qdate.month(), qdate.day())
        event.all_day = self.all_day_check.isChecked()
        
        if not event.all_day:
            start_qtime = self.start_time_edit.time()
            event.start_time = time(start_qtime.hour(), start_qtime.minute())
            end_qtime = self.end_time_edit.time()
            event.end_time = time(end_qtime.hour(), end_qtime.minute())
        else:
            event.start_time = None
            event.end_time = None
            
        event.location = self.location_input.text().strip() or None
        event.description = (
            self.description_input.toPlainText().strip() or None
        )
        event.participants = participants
        event.tags = self.tags_input.get_tags()
        event.status = self.status_combo.currentData()
        
        if self.reminder_check.isChecked():
            event.reminder_minutes_before = self.reminder_spin.value()
        else:
            event.reminder_minutes_before = None
            
        event.color = self.color_combo.currentData()
        event.notes = self.notes_input.toPlainText().strip() or None
        event.project_id = self.project_combo.get_selected_project_id()
        
        # Update timestamp
        event.updated_at = datetime.now()
        
        return event


class AppointmentsPage(QWidget):
    """Appointments page with calendar and event management"""
    
    # Signals
    event_selected = Signal(CalendarEvent)
    
    def __init__(self):
        """Initialize the appointments page"""
        super().__init__()
        self.logger = Logger()
        # Initialize database
        from ...database.initialize_db import DatabaseManager
        db_manager = DatabaseManager()
        self.appointments_db = AppointmentsDatabase(db_manager)
        self._current_event: Optional[CalendarEvent] = None
        self._selected_date = date.today()
        self._event_dates: Dict[date, int] = {}  # Date to event count mapping
        self._current_project_filter: Optional[str] = None
        self._scaling_helper = get_scaling_helper()
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_calendar)
        self._refresh_timer.setInterval(60000)  # Refresh every minute
        self._refresh_timer.start()
        
        self.setup_ui()
        self._load_events()
        self._update_event_list()
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
    def setup_ui(self):
        """Setup the appointments page UI"""
        layout = QVBoxLayout(self)
        
        # Use font metrics for consistent spacing
        font_metrics = self.fontMetrics()
        margin = font_metrics.height() // 2
        
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(0)
        
        # Create toolbar
        toolbar_container = self._create_toolbar()
        layout.addWidget(toolbar_container)
        
        # Create splitter for calendar and events
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                width: 2px;
            }}
        """)
        
        # Calendar pane
        calendar_pane = self._create_calendar_pane()
        self.content_splitter.addWidget(calendar_pane)
        
        # Events pane
        events_pane = self._create_events_pane()
        self.content_splitter.addWidget(events_pane)
        
        # Set initial splitter proportions
        self._update_splitter_sizes()
        
        # Connect splitter moved signal
        self.content_splitter.splitterMoved.connect(self._save_splitter_state)
        
        # Restore splitter state if available
        self._restore_splitter_state()
        
        layout.addWidget(self.content_splitter)
        
    def _create_toolbar(self) -> QWidget:
        """Create the toolbar with actions"""
        # Container widget
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Use font metrics for spacing
        font_metrics = self.fontMetrics()
        spacing = font_metrics.height() // 4
        container_layout.setSpacing(spacing)
        
        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self._update_toolbar_style()
        
        # New Event action
        new_action = QAction("✚ New Event", self)
        new_action.triggered.connect(self._create_new_event)
        self.toolbar.addAction(new_action)
        
        # Edit action
        self.edit_action = QAction("✏️ Edit", self)
        self.edit_action.triggered.connect(self._edit_event)
        self.edit_action.setEnabled(False)
        self.toolbar.addAction(self.edit_action)
        
        # Delete action
        self.delete_action = QAction("🗑️ Delete", self)
        self.delete_action.triggered.connect(self._delete_event)
        self.delete_action.setEnabled(False)
        self.toolbar.addAction(self.delete_action)
        
        # Add spacer
        self.spacer1 = QWidget()
        self.spacer1.setFixedWidth(self._scaling_helper.scaled_size(20))
        self.toolbar.addWidget(self.spacer1)
        
        # Today button
        today_action = QAction("📅 Today", self)
        today_action.triggered.connect(self._go_to_today)
        self.toolbar.addAction(today_action)
        
        # Another spacer
        self.spacer2 = QWidget()
        self.spacer2.setFixedWidth(self._scaling_helper.scaled_size(20))
        self.toolbar.addWidget(self.spacer2)
        
        # Project selector
        self.project_label = QLabel("Project:")
        self.project_label.setStyleSheet(
            f"color: {DinoPitColors.PRIMARY_TEXT}; font-weight: bold;"
        )
        self.toolbar.addWidget(self.project_label)
        
        self.project_combo = ProjectComboBox(self, include_no_project=True)
        self.project_combo.project_changed.connect(
            self._on_project_filter_changed
        )
        self.toolbar.addWidget(self.project_combo)
        
        # Another spacer
        self.spacer3 = QWidget()
        self.spacer3.setFixedWidth(self._scaling_helper.scaled_size(20))
        self.toolbar.addWidget(self.spacer3)
        
        # View mode toggle
        self.view_action = QAction("📋 List View", self)
        self.view_action.setCheckable(True)
        self.view_action.triggered.connect(self._toggle_view_mode)
        self.toolbar.addAction(self.view_action)
        
        # Stretch spacer
        stretch_spacer = QWidget()
        stretch_spacer.setSizePolicy(
            stretch_spacer.sizePolicy().horizontalPolicy(),
            stretch_spacer.sizePolicy().verticalPolicy()
        )
        self.toolbar.addWidget(stretch_spacer)
        
        # Event count label
        self.count_label = QLabel("0 events")
        self.count_label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT}; font-weight: bold;")
        self.toolbar.addWidget(self.count_label)
        
        container_layout.addWidget(self.toolbar)
        
        # Setup shortcuts
        self._setup_shortcuts()
        
        return container
        
    def _create_calendar_pane(self) -> QWidget:
        """Create the calendar pane"""
        pane = QWidget()
        layout = QVBoxLayout(pane)
        
        # Calendar header
        header = QLabel("Calendar")
        header.setStyleSheet(f"""
            background-color: {DinoPitColors.DINOPIT_ORANGE};
            color: white;
            padding: 10px;
            font-weight: bold;
            font-size: 16px;
            border-radius: 5px 5px 0 0;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Calendar widget
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self._on_date_selected)
        self.calendar.activated.connect(self._on_date_activated)
        
        # Style the calendar
        self._style_calendar()
        
        layout.addWidget(self.calendar)
        
        # Legend
        legend_frame = QFrame()
        legend_frame.setStyleSheet(f"""
            background-color: {DinoPitColors.PANEL_BACKGROUND};
            border: 1px solid {DinoPitColors.SOFT_ORANGE};
            border-radius: 5px;
            padding: 10px;
        """)
        
        legend_layout = QVBoxLayout(legend_frame)
        legend_label = QLabel("Legend:")
        legend_label.setStyleSheet(
            f"color: {DinoPitColors.PRIMARY_TEXT}; font-weight: bold;"
        )
        legend_layout.addWidget(legend_label)
        
        legend_items = [
            ("📅 Scheduled", EventStatus.SCHEDULED.value),
            ("⏳ In Progress", EventStatus.IN_PROGRESS.value),
            ("✅ Completed", EventStatus.COMPLETED.value),
            ("❌ Cancelled", EventStatus.CANCELLED.value)
        ]
        
        for icon_text, _ in legend_items:
            item_label = QLabel(icon_text)
            item_label.setStyleSheet(
                f"color: {DinoPitColors.PRIMARY_TEXT}; padding-left: 10px;"
            )
            legend_layout.addWidget(item_label)
            
        layout.addWidget(legend_frame)
        layout.addStretch()
        
        return pane
        
    def _create_events_pane(self) -> QWidget:
        """Create the events pane"""
        pane = QWidget()
        layout = QVBoxLayout(pane)
        
        # Events header with date
        if isinstance(self._selected_date, date):
            date_str = self._selected_date.strftime('%B %d, %Y')
        else:
            date_str = "Unknown Date"
        self.events_header = QLabel(f"Events for {date_str}")
        self.events_header.setStyleSheet(f"""
            background-color: {DinoPitColors.DINOPIT_ORANGE};
            color: white;
            padding: 10px;
            font-weight: bold;
            font-size: 16px;
            border-radius: 5px 5px 0 0;
        """)
        self.events_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.events_header)
        
        # Event list
        self.event_list = QListWidget()
        self.event_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 0 0 5px 5px;
            }}
            QListWidget::item {{
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: 10px;
                border-bottom: 1px solid {DinoPitColors.SOFT_ORANGE};
            }}
            QListWidget::item:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        
        # Connect signals
        self.event_list.itemSelectionChanged.connect(self._on_event_selected)
        self.event_list.itemDoubleClicked.connect(
            self._on_event_double_clicked
        )
        self.event_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.event_list.customContextMenuRequested.connect(
            self._show_context_menu
        )
        
        layout.addWidget(self.event_list)
        
        # Quick add section
        quick_add_frame = QFrame()
        quick_add_frame.setStyleSheet(f"""
            background-color: {DinoPitColors.PANEL_BACKGROUND};
            border: 1px solid {DinoPitColors.SOFT_ORANGE};
            border-radius: 5px;
            padding: 10px;
        """)
        
        quick_add_layout = QHBoxLayout(quick_add_frame)
        
        self.quick_add_input = QLineEdit()
        self.quick_add_input.setPlaceholderText(
            "Quick add event (e.g., 'Meeting at 2pm')"
        )
        self.quick_add_input.setStyleSheet(f"""
            background-color: {DinoPitColors.MAIN_BACKGROUND};
            border: 1px solid {DinoPitColors.SOFT_ORANGE};
            border-radius: 20px;
            padding: 8px 15px;
            color: {DinoPitColors.PRIMARY_TEXT};
        """)
        self.quick_add_input.returnPressed.connect(self._quick_add_event)
        
        quick_add_btn = QPushButton("Add")
        quick_add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: 15px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
            }}
        """)
        quick_add_btn.clicked.connect(self._quick_add_event)
        
        quick_add_layout.addWidget(self.quick_add_input)
        quick_add_layout.addWidget(quick_add_btn)
        
        layout.addWidget(quick_add_frame)
        
        return pane
        
    def _style_calendar(self):
        """Apply custom styling to the calendar widget"""
        self.calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            
            /* Navigation bar */
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
            
            /* Month/Year labels and navigation buttons */
            QCalendarWidget QToolButton {{
                color: {DinoPitColors.PRIMARY_TEXT};
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                font-weight: bold;
                font-size: 14px;
                padding: 5px;
            }}
            
            QCalendarWidget QToolButton:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                border-radius: 3px;
            }}
            
            /* Calendar grid */
            QCalendarWidget QTableView {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                selection-background-color: {DinoPitColors.DINOPIT_ORANGE};
                selection-color: white;
                gridline-color: {DinoPitColors.SOFT_ORANGE};
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            
            /* Header (weekdays) */
            QCalendarWidget QHeaderView::section {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
                font-weight: bold;
                padding: 5px;
            }}
            
            /* Days - all states */
            QCalendarWidget QAbstractItemView::item {{
                padding: 5px;
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            
            QCalendarWidget QAbstractItemView::item:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
            }}
            
            QCalendarWidget QAbstractItemView::item:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            
            /* Today's date */
            QCalendarWidget QAbstractItemView::item:focus {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                color: {DinoPitColors.PRIMARY_TEXT};
                font-weight: bold;
            }}
            
            /* Inactive/disabled days from other months */
            QCalendarWidget QAbstractItemView:disabled {{
                color: #666666;
            }}
            
            /* Ensure all text in calendar cells is visible */
            QCalendarWidget QWidget {{
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            
            /* Calendar date cells specifically */
            QCalendarWidget QTableView::item {{
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            
            /* Make sure date text is white even for inactive dates */
            QCalendarWidget QAbstractItemView {{
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
        """)
        
    def _load_events(self):
        """Load all events and update calendar markers"""
        try:
            # Apply project filter if active
            if self._current_project_filter:
                all_events = self.appointments_db.get_events_by_project(
                    self._current_project_filter
                )
            else:
                # Get all events by using a wide date range
                all_events = self.appointments_db.get_events_for_date_range(
                    date(1900, 1, 1), date(2100, 12, 31)
                )
            
            # Clear and rebuild event dates mapping
            self._event_dates.clear()
            
            for event in all_events:
                if event.event_date:
                    # Count events per date
                    if event.event_date in self._event_dates:
                        self._event_dates[event.event_date] += 1
                    else:
                        self._event_dates[event.event_date] = 1
                        
            # Update calendar to show event indicators
            self._update_calendar_markers()
            
            # Update total count
            self._update_event_count(len(all_events))
            
        except Exception as e:
            self.logger.error(f"Failed to load events: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load events: {str(e)}"
            )
            
    def _update_calendar_markers(self):
        """Update calendar to show which dates have events"""
        # Clear all date formats
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())
        
        # Create format for dates with events
        event_format = QTextCharFormat()
        event_format.setBackground(QColor(DinoPitColors.SOFT_ORANGE))
        event_format.setForeground(QColor(DinoPitColors.PRIMARY_TEXT))
        
        # Apply format to dates with events
        for event_date, count in self._event_dates.items():
            qdate = QDate(event_date.year, event_date.month, event_date.day)
            
            # Adjust format based on event count
            if count > 3:
                event_format.setBackground(QColor(DinoPitColors.DINOPIT_FIRE))
            elif count > 1:
                event_format.setBackground(
                    QColor(DinoPitColors.DINOPIT_ORANGE)
                )
            else:
                event_format.setBackground(QColor(DinoPitColors.SOFT_ORANGE))
                
            self.calendar.setDateTextFormat(qdate, event_format)
            
    def _update_event_list(self):
        """Update the event list for the selected date"""
        self.event_list.clear()
        
        try:
            # Get events for selected date
            # Ensure selected_date is a date object
            if isinstance(self._selected_date, date):
                if self._current_project_filter:
                    # Get all events for project and filter by date
                    all_project_events = self.appointments_db.get_events_by_project(
                        self._current_project_filter
                    )
                    events = [e for e in all_project_events
                             if e.event_date == self._selected_date]
                else:
                    events = self.appointments_db.get_events_for_date(
                        self._selected_date
                    )
            else:
                events = []
            
            # Sort events by time
            events.sort(key=lambda e: (
                e.start_time if e.start_time else time(0, 0),
                e.title
            ))
            
            # Add events to list
            for event in events:
                item = EventListItem(event)
                self.event_list.addItem(item)
                
            # Update header
            event_count = len(events)
            if isinstance(self._selected_date, date):
                date_str = self._selected_date.strftime('%B %d, %Y')
            else:
                date_str = "Unknown Date"
            
            if event_count == 0:
                self.events_header.setText(f"No events for {date_str}")
            elif event_count == 1:
                self.events_header.setText(f"1 event for {date_str}")
            else:
                self.events_header.setText(
                    f"{event_count} events for {date_str}"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to update event list: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update event list: {str(e)}"
            )
            
    def _on_date_selected(self, qdate: QDate):
        """Handle date selection in calendar"""
        self._selected_date = qdate.toPython()
        self._update_event_list()
        
    def _on_date_activated(self, qdate: QDate):
        """Handle date double-click in calendar"""
        self._selected_date = qdate.toPython()
        self._create_new_event()
        
    def _on_event_selected(self):
        """Handle event selection in list"""
        selected_items = self.event_list.selectedItems()
        
        if selected_items:
            item = selected_items[0]
            if isinstance(item, EventListItem):
                self._current_event = item.event
            else:
                self._current_event = None
            self.edit_action.setEnabled(True)
            self.delete_action.setEnabled(True)
            self.event_selected.emit(self._current_event)
        else:
            self._current_event = None
            self.edit_action.setEnabled(False)
            self.delete_action.setEnabled(False)
            
    def _on_event_double_clicked(self, item: EventListItem):
        """Handle event double-click"""
        self._current_event = item.event
        self._edit_event()
        
    def _create_new_event(self):
        """Create a new event"""
        if isinstance(self._selected_date, date):
            dialog = EventDialog(self, selected_date=self._selected_date)
        else:
            dialog = EventDialog(self, selected_date=date.today())
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                event = dialog.get_event_data()
                
                # Validate
                if not event.title:
                    QMessageBox.warning(
                        self,
                        "Invalid Event",
                        "Please enter a title for the event."
                    )
                    return
                    
                # Validate time
                if not event.all_day and event.start_time and event.end_time:
                    if event.end_time <= event.start_time:
                        QMessageBox.warning(
                            self,
                            "Invalid Time",
                            "End time must be after start time."
                        )
                        return
                        
                # Create event
                result = self.appointments_db.create_event(event)
                
                if result["success"]:
                    self.logger.info(f"Created new event: {event.id}")
                    
                    # Refresh displays
                    self._load_events()
                    self._update_event_list()
                    
                    # Select the new event
                    for i in range(self.event_list.count()):
                        item = self.event_list.item(i)
                        if (isinstance(item, EventListItem) and
                                item.event.id == event.id):
                            self.event_list.setCurrentItem(item)
                            break
                else:
                    raise Exception(result.get("error", "Unknown error"))
                    
            except Exception as e:
                self.logger.error(f"Failed to create event: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create event: {str(e)}"
                )
                
    def _edit_event(self):
        """Edit the selected event"""
        if not self._current_event:
            return
            
        dialog = EventDialog(self, event=self._current_event)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                updated_event = dialog.get_event_data()
                
                # Validate
                if not updated_event.title:
                    QMessageBox.warning(
                        self,
                        "Invalid Event",
                        "Please enter a title for the event."
                    )
                    return
                    
                # Validate time
                if (not updated_event.all_day and
                        updated_event.start_time and updated_event.end_time):
                    if updated_event.end_time <= updated_event.start_time:
                        QMessageBox.warning(
                            self,
                            "Invalid Time",
                            "End time must be after start time."
                        )
                        return
                        
                # Update event
                result = self.appointments_db.update_event(
                    updated_event.id,
                    updated_event.to_dict()
                )
                
                if isinstance(result, dict) and result.get("success", False):
                    self.logger.info(f"Updated event: {updated_event.id}")
                    
                    # Refresh displays
                    self._load_events()
                    self._update_event_list()
                    
                    # Restore selection
                    for i in range(self.event_list.count()):
                        item = self.event_list.item(i)
                        if (isinstance(item, EventListItem) and
                                item.event.id == updated_event.id):
                            self.event_list.setCurrentItem(item)
                            break
                else:
                    error_msg = "Unknown error"
                    if isinstance(result, dict):
                        error_msg = result.get("error", "Unknown error")
                    raise Exception(error_msg)
                    
            except Exception as e:
                self.logger.error(f"Failed to update event: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to update event: {str(e)}"
                )
                
    def _delete_event(self):
        """Delete the selected event"""
        if not self._current_event:
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Event",
            f"Are you sure you want to delete '{self._current_event.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                result = self.appointments_db.delete_event(
                    self._current_event.id
                )
                
                if isinstance(result, bool) and result:
                    self.logger.info(
                        f"Deleted event: {self._current_event.id}"
                    )
                    
                    # Clear selection
                    self._current_event = None
                    self.edit_action.setEnabled(False)
                    self.delete_action.setEnabled(False)
                    
                    # Refresh displays
                    self._load_events()
                    self._update_event_list()
                else:
                    raise Exception("Failed to delete event")
                    
            except Exception as e:
                self.logger.error(f"Failed to delete event: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete event: {str(e)}"
                )
                
    def _quick_add_event(self):
        """Quick add event from input"""
        text = self.quick_add_input.text().strip()
        if not text:
            return
            
        try:
            # Parse the text for basic info
            # This is a simple implementation - could be enhanced with NLP
            event = CalendarEvent()
            event.title = text
            if isinstance(self._selected_date, date):
                event.event_date = self._selected_date
            else:
                event.event_date = date.today()
            event.event_type = EventType.APPOINTMENT.value
            
            # Simple time parsing
            text_lower = text.lower()
            
            # Check for all day
            if "all day" in text_lower:
                event.all_day = True
            else:
                # Look for time patterns
                import re
                
                # Match patterns like "2pm", "2:30pm", "14:00"
                time_pattern = r'(\d{1,2}):?(\d{0,2})\s*(am|pm)?'
                matches = re.findall(time_pattern, text_lower)
                
                if matches:
                    for match in matches:
                        hour = int(match[0])
                        minute = int(match[1]) if match[1] else 0
                        period = match[2]
                        
                        if period == 'pm' and hour < 12:
                            hour += 12
                        elif period == 'am' and hour == 12:
                            hour = 0
                            
                        if 0 <= hour < 24 and 0 <= minute < 60:
                            if not event.start_time:
                                event.start_time = time(hour, minute)
                            else:
                                event.end_time = time(hour, minute)
                                
                    # If only start time, set end time to 1 hour later
                    if event.start_time and not event.end_time:
                        start_hour = event.start_time.hour
                        start_minute = event.start_time.minute
                        
                        end_hour = start_hour + 1
                        if end_hour >= 24:
                            end_hour = 23
                            start_minute = 59
                            
                        event.end_time = time(end_hour, start_minute)
                        
            # Create the event
            result = self.appointments_db.create_event(event)
            
            if isinstance(result, dict) and result.get("success", False):
                self.logger.info(f"Quick added event: {event.id}")
                
                # Clear input
                self.quick_add_input.clear()
                
                # Refresh displays
                self._load_events()
                self._update_event_list()
            else:
                raise Exception(result.get("error", "Unknown error"))
                
        except Exception as e:
            self.logger.error(f"Failed to quick add event: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to add event: {str(e)}"
            )
            
    def _go_to_today(self):
        """Navigate calendar to today's date"""
        today = date.today()
        self.calendar.setSelectedDate(
            QDate(today.year, today.month, today.day)
        )
        self._selected_date = today
        self._update_event_list()
        
    def _toggle_view_mode(self, checked: bool):
        """Toggle between calendar and list view modes"""
        # This is a placeholder for future enhancement
        # Could switch to a full list view of all events
        try:
            self.logger.warning(f"List View toggle clicked - checked state: {checked}")
            self.logger.warning("_toggle_view_mode is not implemented yet - this is a placeholder")
            
            # For now, just uncheck the button to prevent it from staying in checked state
            if checked:
                self.view_action.setChecked(False)
                QMessageBox.information(
                    self,
                    "Feature Not Implemented",
                    "List view mode is not implemented yet. This feature will be available in a future update."
                )
        except Exception as e:
            self.logger.error(f"Error in _toggle_view_mode: {str(e)}")
            self.logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        
    def _show_context_menu(self, position):
        """Show context menu for event operations"""
        item = self.event_list.itemAt(position)
        if not item:
            return
            
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 5px;
            }}
            QMenu::item {{
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: 8px 20px;
                border-radius: 4px;
            }}
            QMenu::item:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                color: white;
            }}
        """)
        
        # Edit action
        edit_action = QAction("✏️ Edit", self)
        edit_action.triggered.connect(self._edit_event)
        menu.addAction(edit_action)
        
        # Duplicate action
        duplicate_action = QAction("📋 Duplicate", self)
        if isinstance(item, EventListItem):
            duplicate_action.triggered.connect(
                lambda: self._duplicate_event(item.event)
            )
        menu.addAction(duplicate_action)
        
        menu.addSeparator()
        
        # Status actions
        if (isinstance(item, EventListItem) and
                item.event.status != EventStatus.COMPLETED.value):
            complete_action = QAction("✅ Mark Complete", self)
            complete_action.triggered.connect(
                lambda: self._update_event_status(
                    item.event, EventStatus.COMPLETED.value
                )
            )
            menu.addAction(complete_action)
            
        if (isinstance(item, EventListItem) and
                item.event.status != EventStatus.CANCELLED.value):
            cancel_action = QAction("❌ Cancel", self)
            cancel_action.triggered.connect(
                lambda: self._update_event_status(
                    item.event, EventStatus.CANCELLED.value
                )
            )
            menu.addAction(cancel_action)
            
        menu.addSeparator()
        
        # Delete action
        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(self._delete_event)
        menu.addAction(delete_action)
        
        menu.exec(self.event_list.mapToGlobal(position))
        
    def _duplicate_event(self, event: CalendarEvent):
        """Duplicate an event"""
        try:
            # Create a copy
            new_event = CalendarEvent.from_dict(event.to_dict())
            new_event.id = str(uuid.uuid4())  # New ID
            new_event.title = f"{event.title} (Copy)"
            new_event.created_at = datetime.now()
            new_event.updated_at = datetime.now()
            new_event.status = EventStatus.SCHEDULED.value
            
            # Open edit dialog
            dialog = EventDialog(self, event=new_event)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                event_data = dialog.get_event_data()
                result = self.appointments_db.create_event(event_data)
                
                if result.get("success", False):
                    self.logger.info(f"Duplicated event: {event_data.id}")
                    self._load_events()
                    self._update_event_list()
                else:
                    raise Exception(result.get("error", "Unknown error"))
                    
        except Exception as e:
            self.logger.error(f"Failed to duplicate event: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to duplicate event: {str(e)}"
            )
            
    def _update_event_status(self, event: CalendarEvent, new_status: str):
        """Update event status"""
        try:
            updates = {"status": new_status}
            
            if new_status == EventStatus.COMPLETED.value:
                updates["completed_at"] = datetime.now().isoformat()
                
            result = self.appointments_db.update_event(event.id, updates)
            
            if isinstance(result, bool) and result:
                self.logger.info(
                    f"Updated event status: {event.id} -> {new_status}"
                )
                self._load_events()
                self._update_event_list()
            else:
                raise Exception("Failed to update event status")
                
        except Exception as e:
            self.logger.error(f"Failed to update event status: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update event status: {str(e)}"
            )
            
    def _update_event_count(self, total_count: int):
        """Update the event count display"""
        plural = 's' if total_count != 1 else ''
        self.count_label.setText(f"{total_count} event{plural}")
        
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Ctrl+N for new event
        new_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_shortcut.activated.connect(self._create_new_event)
        
        # Delete key for delete
        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self._delete_event)
        
        # Ctrl+T for today
        today_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        today_shortcut.activated.connect(self._go_to_today)
        
    def _refresh_calendar(self):
        """Refresh calendar display (called periodically)"""
        # Update "today" highlighting
        self.calendar.setSelectedDate(self.calendar.selectedDate())
        
        # Check for upcoming reminders
        self._check_reminders()
        
    def _check_reminders(self):
        """Check for events that need reminders"""
        try:
            # Get upcoming events
            # Get upcoming events for next 24 hours
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            upcoming = self.appointments_db.get_events_for_date_range(
                today,
                tomorrow
            )
            
            for event in upcoming:
                if event.reminder_minutes_before and not event.reminder_sent:
                    event_datetime = event.get_datetime()
                    if event_datetime:
                        reminder_time = event_datetime - timedelta(
                            minutes=event.reminder_minutes_before
                        )
                        
                        if datetime.now() >= reminder_time:
                            # Show reminder (placeholder)
                            self.logger.info(
                                f"Reminder: {event.title} at "
                                f"{event_datetime.strftime('%I:%M %p')}"
                            )
                            
                            # Mark reminder as sent
                            self.appointments_db.update_event(
                                event.id,
                                {"reminder_sent": True}
                            )
                            
        except Exception as e:
            self.logger.error(f"Failed to check reminders: {str(e)}")
            
    def _update_splitter_sizes(self):
        """Set splitter proportions based on window width"""
        total_width = self.width()
        self.content_splitter.setSizes([
            int(total_width * 0.4),  # 40% for calendar
            int(total_width * 0.6)   # 60% for events
        ])
        
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        if hasattr(self, 'content_splitter'):
            # Don't update sizes if we have restored state
            if not hasattr(self, '_state_restored'):
                self._update_splitter_sizes()
                
    def _save_splitter_state(self):
        """Save the splitter state"""
        window_state_manager.save_splitter_from_widget(
            "appointments_content", self.content_splitter
        )
        
    def _restore_splitter_state(self):
        """Restore the splitter state"""
        window_state_manager.restore_splitter_to_widget(
            "appointments_content", self.content_splitter
        )
        self._state_restored = True
        
    def _update_toolbar_style(self):
        """Update toolbar style with current scaling"""
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
                border-radius: 4px;
                padding: {s.scaled_size(8)}px {s.scaled_size(16)}px;
                font-weight: bold;
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
            QToolButton:checked {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        
    def _update_spacer_widths(self):
        """Update spacer widths with current scaling"""
        spacer_width = self._scaling_helper.scaled_size(20)
        if hasattr(self, 'spacer1'):
            self.spacer1.setFixedWidth(spacer_width)
        if hasattr(self, 'spacer2'):
            self.spacer2.setFixedWidth(spacer_width)
            
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes"""
        # Update toolbar style
        self._update_toolbar_style()
        
        # Update spacer widths
        
    def _on_project_filter_changed(self, project_id: Optional[str]):
        """Handle project filter change from combo box"""
        self._current_project_filter = project_id
        
        # Clear any existing event selection
        self._current_event = None
        self.edit_action.setEnabled(False)
        self.delete_action.setEnabled(False)
        
        # Reload events with new filter
        self._load_events()
        self._update_event_list()
        self._update_spacer_widths()