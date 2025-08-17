#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Chat History Widget
Chat history with database integration, filtering, and search capabilities.
"""

from datetime import datetime
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QLineEdit, QComboBox,
    QDateEdit, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QDate, Slot
from PySide6.QtGui import QAction

from src.database.chat_history_db import ChatHistoryDatabase
from src.models.chat_session import ChatSession
from src.utils.colors import DinoPitColors
from src.utils.scaling import get_scaling_helper


class ChatHistoryItem(QFrame):
    """Enhanced chat history item with more information"""
    
    clicked = Signal(str)  # Emit session ID when clicked
    delete_requested = Signal(str)  # Emit session ID for deletion
    
    def __init__(self, session: ChatSession):
        """Initialize the chat history item.
        
        Args:
            session: ChatSession object
        """
        super().__init__()
        self.session = session
        self._scaling_helper = get_scaling_helper()
        
        # Set frame style
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setLineWidth(1)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Set initial style
        self._update_style(hover=False)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10)
        )
        layout.setSpacing(self._scaling_helper.scaled_size(5))
        
        # Create title label
        self.title_label = QLabel(session.title or "Untitled Chat")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(f"""
            color: {DinoPitColors.DINOPIT_ORANGE};
            font-size: {self._scaling_helper.scaled_font_size(14)}px;
            font-weight: bold;
        """)
        
        # Create preview label
        preview_text = session.get_preview(60)
        self.preview_label = QLabel(preview_text)
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: {self._scaling_helper.scaled_font_size(12)}px;
        """)
        
        # Create info layout
        info_layout = QHBoxLayout()
        info_layout.setSpacing(self._scaling_helper.scaled_size(10))
        
        # Time label
        time_diff = datetime.now() - session.updated_at
        if time_diff.days > 0:
            days = time_diff.days
            time_str = f"{days} day{'s' if days > 1 else ''} ago"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            time_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            minutes = max(1, time_diff.seconds // 60)
            time_str = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            
        self.time_label = QLabel(time_str)
        self.time_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: {self._scaling_helper.scaled_font_size(10)}px;
        """)
        
        # Message count
        message_count = len(session.messages)
        self.count_label = QLabel(f"{message_count} messages")
        self.count_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: {self._scaling_helper.scaled_font_size(10)}px;
        """)
        
        # Status indicator
        if session.status == "active":
            status_color = "#4CAF50"  # Green
        elif session.status == "archived":
            status_color = "#FFC107"  # Amber
        else:
            status_color = "#9E9E9E"  # Gray
            
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet(f"""
            color: {status_color};
            font-size: {self._scaling_helper.scaled_font_size(12)}px;
        """)
        
        info_layout.addWidget(self.time_label)
        info_layout.addWidget(self.count_label)
        info_layout.addStretch()
        info_layout.addWidget(self.status_indicator)
        
        # Add widgets to layout
        layout.addWidget(self.title_label)
        layout.addWidget(self.preview_label)
        layout.addLayout(info_layout)
        
        # Connect zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
    def _update_style(self, hover: bool = False):
        """Update the widget style"""
        if hover:
            bg_color = DinoPitColors.SOFT_ORANGE
        else:
            bg_color = DinoPitColors.PANEL_BACKGROUND
            
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {self._scaling_helper.scaled_size(8)}px;
            }}
        """)
        
    def enterEvent(self, event):
        """Handle mouse enter"""
        self._update_style(hover=True)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Handle mouse leave"""
        self._update_style(hover=False)
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.session.id)
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.pos())
        super().mousePressEvent(event)
        
    def _show_context_menu(self, pos):
        """Show context menu"""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
            }}
            QMenu::item {{
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: {self._scaling_helper.scaled_size(8)}px;
                padding-left: {self._scaling_helper.scaled_size(20)}px;
                padding-right: {self._scaling_helper.scaled_size(20)}px;
            }}
            QMenu::item:selected {{
                background-color: {DinoPitColors.SOFT_ORANGE};
            }}
        """)
        
        # Add actions
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(
            lambda: self.delete_requested.emit(self.session.id)
        )
        menu.addAction(delete_action)
        
        is_active = self.session.status == "active"
        action_text = "Archive" if is_active else "Unarchive"
        archive_action = QAction(action_text, self)
        archive_action.triggered.connect(self._toggle_archive)
        menu.addAction(archive_action)
        
        menu.exec(self.mapToGlobal(pos))
        
    def _toggle_archive(self):
        """Toggle archive status"""
        # This will be handled by the parent widget
        pass
        
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes"""
        # Update all scaled values
        self._update_style(hover=False)


class EnhancedChatHistoryWidget(QWidget):
    """Enhanced chat history with database integration and filtering"""
    
    session_selected = Signal(str)  # Emit session ID when selected
    
    def __init__(self, chat_db: ChatHistoryDatabase):
        """Initialize the enhanced chat history widget"""
        super().__init__()
        self.chat_db = chat_db
        self._scaling_helper = get_scaling_helper()
        self._current_sessions: List[ChatSession] = []
        
        # Set fixed width
        self.setFixedWidth(self._scaling_helper.scaled_size(350))
        
        # Setup UI
        self._setup_ui()
        
        # Load initial sessions
        self._load_recent_sessions()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._load_recent_sessions)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
    def _setup_ui(self):
        """Setup the UI components"""
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create header with DinoPit brand colors
        self.header = QWidget()
        self._update_header_style()
        self.header.setFixedHeight(self._scaling_helper.scaled_size(50))
        
        # Create header layout
        header_layout = QVBoxLayout(self.header)
        header_layout.setContentsMargins(
            self._scaling_helper.scaled_size(15),
            0,
            self._scaling_helper.scaled_size(15),
            0
        )
        
        # Create header label
        header_label = QLabel("Recent Chats")
        header_label.setStyleSheet(f"""
            font-weight: bold;
            color: white;
            font-size: {self._scaling_helper.scaled_font_size(14)}px;
        """)
        
        # Add header label to header layout
        header_layout.addWidget(header_label)
        
        # Create filter section
        filter_container = self._create_filter_section()
        
        # Create scroll area for chat history items
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {DinoPitColors.PANEL_BACKGROUND};
                width: {self._scaling_helper.scaled_size(10)}px;
                border-radius: {self._scaling_helper.scaled_size(5)}px;
            }}
            QScrollBar::handle:vertical {{
                background: {DinoPitColors.SOFT_ORANGE};
                border-radius: {self._scaling_helper.scaled_size(5)}px;
                min-height: {self._scaling_helper.scaled_size(30)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        
        # Create container widget for chat history items
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10)
        )
        self.scroll_layout.setSpacing(self._scaling_helper.scaled_size(10))
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Set scroll content as the widget for scroll area
        self.scroll_area.setWidget(self.scroll_content)
        
        # Add components to main layout
        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(filter_container)
        self.main_layout.addWidget(self.scroll_area, 1)
        
    def _create_filter_section(self) -> QWidget:
        """Create the filter controls section"""
        container = QWidget()
        container.setStyleSheet(f"""
            background-color: {DinoPitColors.PANEL_BACKGROUND};
            border-bottom: 1px solid {DinoPitColors.SOFT_ORANGE};
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10)
        )
        layout.setSpacing(self._scaling_helper.scaled_size(8))
        
        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search chats...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {self._scaling_helper.scaled_size(4)}px;
                padding: {self._scaling_helper.scaled_size(8)}px;
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: {self._scaling_helper.scaled_font_size(12)}px;
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 0.5);
            }}
            QLineEdit:focus {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        self.search_input.textChanged.connect(self._apply_filters)
        
        # Filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(self._scaling_helper.scaled_size(5))
        
        # Date filter
        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setDate(QDate.currentDate())
        self.date_filter.setDisplayFormat("MMM dd, yyyy")
        self.date_filter.setStyleSheet(self._get_filter_style())
        self.date_filter.dateChanged.connect(self._apply_filters)
        
        # Clear date button
        self.clear_date_btn = QPushButton("×")
        self.clear_date_btn.setFixedSize(
            self._scaling_helper.scaled_size(24),
            self._scaling_helper.scaled_size(24)
        )
        self.clear_date_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                color: white;
                border: none;
                border-radius: {self._scaling_helper.scaled_size(12)}px;
                font-weight: bold;
                font-size: {self._scaling_helper.scaled_font_size(16)}px;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        self.clear_date_btn.clicked.connect(self._clear_date_filter)
        
        # Status filter
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Active", "Archived"])
        self.status_filter.setStyleSheet(self._get_filter_style())
        self.status_filter.currentTextChanged.connect(self._apply_filters)
        
        filter_row.addWidget(QLabel("Date:"))
        filter_row.addWidget(self.date_filter)
        filter_row.addWidget(self.clear_date_btn)
        filter_row.addWidget(QLabel("Status:"))
        filter_row.addWidget(self.status_filter)
        filter_row.addStretch()
        
        layout.addWidget(self.search_input)
        layout.addLayout(filter_row)
        
        return container
        
    def _get_filter_style(self) -> str:
        """Get common style for filter widgets"""
        return f"""
            QDateEdit, QComboBox {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {self._scaling_helper.scaled_size(4)}px;
                padding: {self._scaling_helper.scaled_size(4)}px;
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: {self._scaling_helper.scaled_font_size(11)}px;
            }}
            QDateEdit:focus, QComboBox:focus {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QDateEdit::drop-down, QComboBox::drop-down {{
                border: none;
                width: {self._scaling_helper.scaled_size(20)}px;
            }}
            QDateEdit::down-arrow, QComboBox::down-arrow {{
                image: none;
                border-style: solid;
                border-color: transparent;
                border-top-color: {DinoPitColors.PRIMARY_TEXT};
                border-width: {self._scaling_helper.scaled_size(6)}px
                             {self._scaling_helper.scaled_size(4)}px 0;
                width: 0;
                height: 0;
            }}
        """
        
    def _clear_date_filter(self):
        """Clear the date filter"""
        self.date_filter.setDate(QDate.currentDate().addDays(1))  # Tomorrow
        self._apply_filters()
        
    @Slot()
    def _apply_filters(self):
        """Apply current filters and reload sessions"""
        self._load_recent_sessions()
        
    def _load_recent_sessions(self):
        """Load recent sessions from database with current filters"""
        # Get filter values
        search_query = None
        if hasattr(self, 'search_input'):
            search_query = self.search_input.text().strip()
        
        # Date filter - only apply if not tomorrow (our "no filter" indicator)
        filter_date = None
        if hasattr(self, 'date_filter'):
            selected_date = self.date_filter.date()
            if selected_date <= QDate.currentDate():
                filter_date = datetime(
                    selected_date.year(),
                    selected_date.month(),
                    selected_date.day()
                )
        
        # Status filter
        filter_status = None
        if hasattr(self, 'status_filter'):
            status_text = self.status_filter.currentText()
            if status_text != "All":
                filter_status = status_text.lower()
        
        # Load sessions from database
        self._current_sessions = self.chat_db.get_recent_sessions(
            limit=50,
            filter_date=filter_date,
            filter_status=filter_status,
            search_query=search_query
        )
        
        # Clear existing items
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # Add new items
        if self._current_sessions:
            for session in self._current_sessions:
                item = ChatHistoryItem(session)
                item.clicked.connect(self._on_session_clicked)
                item.delete_requested.connect(self._delete_session)
                self.scroll_layout.addWidget(item)
        else:
            # Show empty state
            empty_label = QLabel("No chats found")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"""
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: {self._scaling_helper.scaled_font_size(14)}px;
                padding: {self._scaling_helper.scaled_size(50)}px;
            """)
            self.scroll_layout.addWidget(empty_label)
            
    def _on_session_clicked(self, session_id: str):
        """Handle session click"""
        self.session_selected.emit(session_id)
        
    def _delete_session(self, session_id: str):
        """Delete a session"""
        reply = QMessageBox.question(
            self,
            "Delete Chat",
            "Are you sure you want to delete this chat?\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = self.chat_db.delete_session(session_id)
            if result.get("success"):
                self._load_recent_sessions()
            else:
                QMessageBox.warning(
                    self,
                    "Delete Failed",
                    "Failed to delete chat: " +
                    result.get('error', 'Unknown error')
                )
                
    def refresh(self):
        """Manually refresh the session list"""
        self._load_recent_sessions()
        
    def _update_header_style(self):
        """Update header style with current scaling"""
        self.header.setStyleSheet(f"""
            background-color: {DinoPitColors.DINOPIT_ORANGE};
            border-bottom: {self._scaling_helper.scaled_size(2)}px solid
                          {DinoPitColors.DINOPIT_FIRE};
        """)
        
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes"""
        # Update fixed width
        self.setFixedWidth(self._scaling_helper.scaled_size(350))
        
        # Update header
        self._update_header_style()
        self.header.setFixedHeight(self._scaling_helper.scaled_size(50))
        
        # Refresh filters
        if hasattr(self, 'search_input'):
            self.search_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {DinoPitColors.MAIN_BACKGROUND};
                    border: 1px solid {DinoPitColors.SOFT_ORANGE};
                    border-radius: {self._scaling_helper.scaled_size(4)}px;
                    padding: {self._scaling_helper.scaled_size(8)}px;
                    color: {DinoPitColors.PRIMARY_TEXT};
                    font-size: {self._scaling_helper.scaled_font_size(12)}px;
                }}
                QLineEdit::placeholder {{
                    color: rgba(255, 255, 255, 0.5);
                }}
                QLineEdit:focus {{
                    border-color: {DinoPitColors.DINOPIT_ORANGE};
                }}
            """)
            
        # Reload sessions to update item styles
        self._load_recent_sessions()