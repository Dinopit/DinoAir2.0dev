#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Chat Tab Widget
Chat interface with database integration for message persistence.
"""

from datetime import datetime
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QScrollArea, QLabel, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut

from ...models.chat_session import ChatSession
from ...database.chat_history_db import ChatHistoryDatabase
from ...utils.colors import DinoPitColors
from ...utils.scaling import get_scaling_helper
from .loading_components import (
    TypingIndicator, MessageSendIndicator
)


class ChatMessageWidget(QFrame):
    """A single chat message widget."""
    
    def __init__(self, message, is_user=True):
        """Initialize a chat message.
        
        Args:
            message (str): The message text
            is_user (bool): True if from user, False if from assistant
        """
        super().__init__()
        self._scaling_helper = get_scaling_helper()
        
        # Set frame style
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMaximumWidth(self._scaling_helper.scaled_size(600))
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(5),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(5)
        )
        
        # Create message bubble
        message_frame = QFrame()
        message_frame.setFrameShape(QFrame.Shape.StyledPanel)
        message_frame.setFrameShadow(QFrame.Shadow.Plain)
        message_frame.setLineWidth(1)
        
        # Style based on sender with DinoPit brand colors and blue theme
        if is_user:
            message_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {DinoPitColors.DINOPIT_ORANGE};
                    color: white;
                    border-radius: {self._scaling_helper.scaled_size(15)}px;
                    border: none;
                }}
            """)
            layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            message_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {DinoPitColors.PANEL_BACKGROUND};
                    color: {DinoPitColors.PRIMARY_TEXT};
                    border-radius: {self._scaling_helper.scaled_size(15)}px;
                    border: none;
                }}
            """)
            layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Create message layout
        message_layout = QVBoxLayout(message_frame)
        message_layout.setContentsMargins(
            self._scaling_helper.scaled_size(15),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(15),
            self._scaling_helper.scaled_size(10)
        )
        
        # Create message label with improved typography
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        # Use new font scale system for 16px base font size
        font_size = self._scaling_helper.get_font_for_role('body_primary')
        message_label.setStyleSheet(f"""
            border: none;
            background: transparent;
            font-size: {font_size}px;
            line-height: 1.5;
        """)
        # Prevent HTML injection
        message_label.setTextFormat(Qt.TextFormat.PlainText)
        
        message_layout.addWidget(message_label)
        layout.addWidget(message_frame)
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes"""
        self.setMaximumWidth(self._scaling_helper.scaled_size(600))


class EnhancedChatTabWidget(QWidget):
    """Enhanced chat tab with database integration."""
    
    # Signal emitted when a message is sent
    message_sent = Signal(str)
    # Signal emitted when session changes
    session_changed = Signal(str)  # session_id
    
    def __init__(self, chat_db: ChatHistoryDatabase):
        """Initialize the enhanced chat tab widget."""
        super().__init__()
        self.chat_db = chat_db
        self.current_session: Optional[ChatSession] = None
        self.current_model: Optional[str] = None
        self._scaling_helper = get_scaling_helper()
        
        # Loading and feedback components
        self._typing_indicator: Optional[TypingIndicator] = None
        self._message_send_indicator: Optional[MessageSendIndicator] = None
        
        # Create UI
        self._setup_ui()
        
        # Start a new session by default
        self.start_new_session()
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
    def _setup_ui(self):
        """Setup the UI components"""
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10)
        )
        self.main_layout.setSpacing(self._scaling_helper.scaled_size(10))
        
        # Create session info bar
        self.session_bar = self._create_session_bar()
        
        # Create chat area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._update_chat_scroll_style()
        
        # Create chat content widget
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10)
        )
        self.chat_layout.setSpacing(self._scaling_helper.scaled_size(10))
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Set chat content as the widget for scroll area
        self.chat_scroll.setWidget(self.chat_content)
        
        # Create input area
        self.input_frame = QFrame()
        self.input_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.input_frame.setFrameShadow(QFrame.Shadow.Plain)
        self.input_frame.setLineWidth(1)
        self._update_input_frame_style()
        self.input_frame.setFixedHeight(self._scaling_helper.scaled_size(60))
        
        # Create input layout
        input_layout = QHBoxLayout(self.input_frame)
        input_layout.setContentsMargins(
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(10)
        )
        input_layout.setSpacing(self._scaling_helper.scaled_size(10))
        
        # Create input field
        self.input_field = QLineEdit()
        self.input_field.setStyleSheet(
            "color: #FFFFFF; background-color: #2B3A52; "
            "border: 1px solid #4A5A7A; padding: 5px;"
        )
        self.input_field.setPlaceholderText("Type your message here...")
        self._update_input_field_style()
        
        # Create send button
        self.send_button = QPushButton("Send")
        self.send_button.setStyleSheet("color: #FFFFFF;")
        self.send_button.setFixedSize(
            self._scaling_helper.scaled_size(70),
            self._scaling_helper.scaled_size(36)
        )
        self._update_send_button_style()
        
        # Connect signals
        self.input_field.textChanged.connect(self.on_text_changed)
        self.input_field.returnPressed.connect(self.send_message)
        self.send_button.clicked.connect(self.send_message)
        
        # Add widgets to input layout
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        
        # Create message send indicator
        self._message_send_indicator = MessageSendIndicator()
        
        # Add widgets to main layout
        self.main_layout.addWidget(self.session_bar)
        # Give more space to chat area
        self.main_layout.addWidget(self.chat_scroll, 1)
        self.main_layout.addWidget(self._message_send_indicator)
        self.main_layout.addWidget(self.input_frame)
        
        # Initially disable send button
        self.send_button.setEnabled(False)
        
    def _create_session_bar(self) -> QWidget:
        """Create the session info bar"""
        bar = QWidget()
        bar.setStyleSheet(f"""
            background-color: {DinoPitColors.PANEL_BACKGROUND};
            border-radius: {self._scaling_helper.scaled_size(4)}px;
        """)
        bar.setFixedHeight(self._scaling_helper.scaled_size(40))
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(5),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(5)
        )
        
        # Session title label with improved typography
        self.session_title_label = QLabel("New Chat")
        title_font_size = self._scaling_helper.get_font_for_role(
            'heading_tertiary'
        )
        self.session_title_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-weight: bold;
            font-size: {title_font_size}px;
        """)
        
        # New chat button
        self.new_chat_button = QPushButton("+ New Chat")
        self.new_chat_button.setFixedSize(
            self._scaling_helper.scaled_size(90),
            self._scaling_helper.scaled_size(28)
        )
        button_font_size = self._scaling_helper.get_font_for_role(
            'body_secondary'
        )
        self.new_chat_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: {self._scaling_helper.scaled_size(14)}px;
                font-size: {button_font_size}px;
                font-weight: bold;
                transition: all 150ms ease-in-out;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background-color: #E55A2B;
                transform: translateY(0px);
            }}
        """)
        self.new_chat_button.clicked.connect(self._on_new_chat_clicked)
        
        layout.addWidget(self.session_title_label)
        layout.addStretch()
        layout.addWidget(self.new_chat_button)
        
        return bar
        
    def start_new_session(self, title: Optional[str] = None,
                          project_id: Optional[str] = None):
        """Start a new chat session"""
        # Save current session if it has messages
        if self.current_session and self.current_session.messages:
            # Update session title if it's still default
            if self.current_session.title.startswith("Chat "):
                # Use first message as title
                if self.current_session.messages:
                    first_msg = self.current_session.messages[0]
                    if first_msg.is_user:
                        preview = first_msg.message[:30]
                        if len(first_msg.message) > 30:
                            preview += "..."
                        self.current_session.title = preview
                        self.chat_db.update_session(
                            self.current_session.id,
                            {"title": preview}
                        )
        
        # Create new session
        self.current_session = ChatSession(
            title=title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            project_id=project_id
        )
        
        # Save to database
        result = self.chat_db.create_session(self.current_session)
        if not result.get("success"):
            QMessageBox.warning(
                self,
                "Session Error",
                "Failed to create new session: " +
                result.get('error', 'Unknown error')
            )
            return
            
        # Clear chat area
        self.clear_chat()
        
        # Update UI
        self.session_title_label.setText(self.current_session.title)
        
        # Add welcome message
        self.add_message(
            "Welcome to the chat! How can I help you today?",
            is_user=False,
            save_to_db=False  # Don't save system messages
        )
        
        # Emit signal
        self.session_changed.emit(self.current_session.id)
        
    def load_session(self, session_id: str):
        """Load an existing chat session"""
        # Load session from database
        session = self.chat_db.get_session(session_id)
        if not session:
            QMessageBox.warning(
                self,
                "Session Error",
                "Failed to load chat session"
            )
            return
            
        self.current_session = session
        
        # Clear and reload messages
        self.clear_chat()
        
        # Update UI
        self.session_title_label.setText(session.title)
        
        # Load all messages
        for msg in session.messages:
            self.add_message(
                msg.message,
                is_user=msg.is_user,
                save_to_db=False  # Already in database
            )
            
        # Emit signal
        self.session_changed.emit(session.id)
        
    def on_text_changed(self, text):
        """Handle text change in the input field.
        
        Args:
            text (str): The current text in the input field
        """
        # Enable/disable send button based on whether there's text
        self.send_button.setEnabled(bool(text.strip()))
        
    def send_message(self):
        """Send the message from the input field."""
        message = self.input_field.text().strip()
        
        if message and self.current_session:
            # Show sending indicator
            if self._message_send_indicator:
                self._message_send_indicator.set_sending()
            
            # Add user message to chat
            self.add_message(message, is_user=True)
            
            # Show typing indicator for AI response
            self.show_typing_indicator()
            
            # Emit the message_sent signal
            self.message_sent.emit(message)
            
            # Clear the input field
            self.input_field.clear()
            
            # Disable the send button
            self.send_button.setEnabled(False)
            
            # Show message sent confirmation
            if self._message_send_indicator:
                self._message_send_indicator.set_sent()
            
            # Scroll to bottom
            self.scroll_to_bottom()
            
    def add_message(self, message: str, is_user: bool = True,
                    save_to_db: bool = True):
        """Add a message to the chat.
        
        Args:
            message: The message text
            is_user: True if message is from user, False if from assistant
            save_to_db: Whether to save this message to database
        """
        # Hide typing indicator when adding AI message
        if not is_user:
            self.hide_typing_indicator()
            
        # Create message widget
        message_widget = ChatMessageWidget(message, is_user)
        self.chat_layout.addWidget(message_widget)
        
        # Save to database if requested
        if save_to_db and self.current_session:
            # Add to session
            msg = self.current_session.add_message(message, is_user)
            
            # Save to database
            result = self.chat_db.add_message(self.current_session.id, msg)
            if not result.get("success"):
                # Log error but don't interrupt user experience
                print(f"Failed to save message: {result.get('error')}")
                # Show error in send indicator
                if self._message_send_indicator:
                    self._message_send_indicator.set_error("Failed to save")
        
        # Scroll to bottom after adding message
        self.scroll_to_bottom()
        
    def scroll_to_bottom(self):
        """Scroll the chat area to the bottom."""
        # Use a timer to ensure the scroll happens after the widget is rendered
        from PySide6.QtCore import QTimer
        QTimer.singleShot(
            10,
            lambda: self.chat_scroll.verticalScrollBar().setValue(
                self.chat_scroll.verticalScrollBar().maximum()
            )
        )
        
    def clear_chat(self):
        """Clear all messages from the chat display."""
        while self.chat_layout.count():
            child = self.chat_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def _on_new_chat_clicked(self):
        """Handle new chat button click"""
        # Check if current session has unsaved messages
        if self.current_session and self.current_session.messages:
            reply = QMessageBox.question(
                self,
                "New Chat",
                "Start a new chat session?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
                
        self.start_new_session()
        
    def _update_chat_scroll_style(self):
        """Update chat scroll area style"""
        self.chat_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.PANEL_BACKGROUND};
                border-radius: {self._scaling_helper.scaled_size(8)}px;
            }}
        """)
        
    def _update_input_frame_style(self):
        """Update input frame style"""
        self.input_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {self._scaling_helper.scaled_size(8)}px;
            }}
        """)
        
    def _update_input_field_style(self):
        """Update input field style with improved typography"""
        input_font_size = self._scaling_helper.get_font_for_role(
            'body_primary'
        )
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {self._scaling_helper.scaled_size(20)}px;
                padding: {self._scaling_helper.scaled_size(8)}px;
                padding-left: {self._scaling_helper.scaled_size(15)}px;
                padding-right: {self._scaling_helper.scaled_size(15)}px;
                font-size: {input_font_size}px;
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 0.5);
            }}
            QLineEdit:focus {{
                border-color: {DinoPitColors.SOFT_ORANGE_HOVER};
            }}
        """)
        
    def _update_send_button_style(self):
        """Update send button style with improved typography"""
        send_button_font_size = self._scaling_helper.get_font_for_role(
            'body_primary'
        )
        self.send_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: {self._scaling_helper.scaled_size(18)}px;
                font-size: {send_button_font_size}px;
                font-weight: bold;
                min-height: {self._scaling_helper.scaled_size(36)}px;
                padding: {self._scaling_helper.scaled_size(8)}px
                         {self._scaling_helper.scaled_size(16)}px;
                transition: all 150ms ease-in-out;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
                transform: translateY(-1px);
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
            QPushButton:pressed {{
                background-color: #E55A2B;
                transform: translateY(0px);
                box-shadow: none;
            }}
            QPushButton:disabled {{
                background-color: #666666;
                color: #999999;
                transform: none;
                box-shadow: none;
            }}
        """)
        
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes"""
        # Update all styled components
        self._update_chat_scroll_style()
        self._update_input_frame_style()
        self._update_input_field_style()
        self._update_send_button_style()
        
        # Update fixed sizes
        self.input_frame.setFixedHeight(self._scaling_helper.scaled_size(60))
    
    def set_current_model(self, model_name: str):
        """Set the current model for chat interactions
        
        Args:
            model_name: Name of the selected model
        """
        self.current_model = model_name
        # Update UI to show current model if needed
        # Could add model indicator in chat interface
        
    def get_current_model(self) -> Optional[str]:
        """Get the currently selected model
        
        Returns:
            Current model name or None if not set
        """
        return self.current_model

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for enhanced user experience"""
        # Ctrl+N: New chat
        self.new_chat_shortcut = QShortcut(
            QKeySequence("Ctrl+N"), self
        )
        self.new_chat_shortcut.activated.connect(self._on_new_chat_clicked)
        
        # Ctrl+Enter: Send message (alternative to Enter)
        self.send_message_shortcut = QShortcut(
            QKeySequence("Ctrl+Return"), self
        )
        self.send_message_shortcut.activated.connect(self.send_message)
        
        # Escape: Clear input field
        self.clear_input_shortcut = QShortcut(
            QKeySequence("Escape"), self
        )
        self.clear_input_shortcut.activated.connect(self._clear_input)
        
        # Ctrl+L: Focus input field
        self.focus_input_shortcut = QShortcut(
            QKeySequence("Ctrl+L"), self
        )
        self.focus_input_shortcut.activated.connect(self._focus_input)

    def _clear_input(self):
        """Clear the input field"""
        self.input_field.clear()
        self.input_field.setFocus()

    def _focus_input(self):
        """Focus the input field"""
        self.input_field.setFocus()

    def show_typing_indicator(self):
        """Show the typing indicator for AI responses"""
        if self._typing_indicator is None:
            self._typing_indicator = TypingIndicator()
            
        # Add typing indicator to chat
        self.chat_layout.addWidget(self._typing_indicator)
        self._typing_indicator.start_animation()
        
        # Scroll to bottom to show typing indicator
        self.scroll_to_bottom()
        
    def hide_typing_indicator(self):
        """Hide the typing indicator"""
        if self._typing_indicator is not None:
            self._typing_indicator.stop_animation()
            self.chat_layout.removeWidget(self._typing_indicator)
            self._typing_indicator.setParent(None)
            self._typing_indicator = None