#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ChatTabWidget class for the PySide6 application.
This widget displays a proper chat interface in the main tab area.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, 
    QPushButton, QScrollArea, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor, QFont


class ChatMessage(QFrame):
    """A single chat message widget."""
    
    def __init__(self, message, is_user=True):
        """Initialize a chat message.
        
        Args:
            message (str): The message text
            is_user (bool): True if message is from user, False if from assistant
        """
        super().__init__()
        
        # Set frame style
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMaximumWidth(600)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Create message bubble
        message_frame = QFrame()
        message_frame.setFrameShape(QFrame.Shape.StyledPanel)
        message_frame.setFrameShadow(QFrame.Shadow.Plain)
        message_frame.setLineWidth(1)
        
        # Style based on sender with DinoPit brand colors and blue theme
        if is_user:
            message_frame.setStyleSheet("""
                QFrame {
                    background-color: #FF6B35;
                    color: white;
                    border-radius: 15px;
                    border: none;
                }
            """)
            layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            message_frame.setStyleSheet("""
                QFrame {
                    background-color: #34435A;
                    color: #FFFFFF;
                    border-radius: 15px;
                    border: none;
                }
            """)
            layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Create message layout
        message_layout = QVBoxLayout(message_frame)
        message_layout.setContentsMargins(15, 10, 15, 10)
        
        # Create message label
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("border: none; background: transparent;")
        
        message_layout.addWidget(message_label)
        layout.addWidget(message_frame)


class ChatTabWidget(QWidget):
    """Widget for the chat tab interface."""
    
    # Signal emitted when a message is sent
    message_sent = Signal(str)
    
    def __init__(self):
        """Initialize the chat tab widget."""
        super().__init__()
        
        # Create main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)
        
        # Create chat area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chat_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #2B3A52;
                border: 1px solid #34435A;
                border-radius: 8px;
            }
        """)
        
        # Create chat content widget
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(10)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Set chat content as the widget for scroll area
        self.chat_scroll.setWidget(self.chat_content)
        
        # Create input area
        self.input_frame = QFrame()
        self.input_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.input_frame.setFrameShadow(QFrame.Shadow.Plain)
        self.input_frame.setLineWidth(1)
        self.input_frame.setStyleSheet("""
            QFrame {
                background-color: #34435A;
                border: 1px solid #CC8B66;
                border-radius: 8px;
            }
        """)
        self.input_frame.setFixedHeight(60)
        
        # Create input layout
        input_layout = QHBoxLayout(self.input_frame)
        input_layout.setContentsMargins(10, 10, 10, 10)
        input_layout.setSpacing(10)
        
        # Create input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: 1px solid #CC8B66;
                border-radius: 20px;
                padding: 8px 15px;
                font-size: 14px;
                background-color: #2B3A52;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                border-color: #E6A085;
            }
        """)
        
        # Create send button
        self.send_button = QPushButton("Send")
        self.send_button.setFixedSize(70, 36)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF4500;
            }
            QPushButton:pressed {
                background-color: #E55A2B;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
        """)
        
        # Connect signals
        self.input_field.textChanged.connect(self.on_text_changed)
        self.input_field.returnPressed.connect(self.send_message)
        self.send_button.clicked.connect(self.send_message)
        
        # Add widgets to input layout
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        
        # Add widgets to main layout
        self.layout.addWidget(self.chat_scroll, 1)  # Give more space to chat area
        self.layout.addWidget(self.input_frame)
        
        # Add welcome message
        self.add_message("Welcome to the chat! How can I help you today?", is_user=False)
        
        # Initially disable send button
        self.send_button.setEnabled(False)
    
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
        
        if message:
            # Add user message to chat
            self.add_message(message, is_user=True)
            
            # Emit the message_sent signal
            self.message_sent.emit(message)
            
            # Clear the input field
            self.input_field.clear()
            
            # Disable the send button
            self.send_button.setEnabled(False)
            
            # Scroll to bottom
            self.scroll_to_bottom()
    
    def add_message(self, message, is_user=True):
        """Add a message to the chat.
        
        Args:
            message (str): The message text
            is_user (bool): True if message is from user, False if from assistant
        """
        message_widget = ChatMessage(message, is_user)
        self.chat_layout.addWidget(message_widget)
        
        # Scroll to bottom after adding message
        self.scroll_to_bottom()
    
    def scroll_to_bottom(self):
        """Scroll the chat area to the bottom."""
        # Use a timer to ensure the scroll happens after the widget is rendered
        from PySide6.QtCore import QTimer
        QTimer.singleShot(10, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))
    
    def clear_chat(self):
        """Clear all messages from the chat."""
        while self.chat_layout.count():
            child = self.chat_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
