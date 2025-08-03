#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ChatInputWidget class for the PySide6 application.
This widget displays the chat input area at the bottom of the application.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor


class SendButton(QPushButton):
    """Custom send button with icon."""
    
    def __init__(self):
        """Initialize the send button."""
        super().__init__()
        
        # Set button properties
        self.setFixedSize(40, 40)
        self.setText("→")  # Using arrow character as icon
        
        # Set button style with DinoPit brand colors
        self.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 16px;
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


class ChatInputWidget(QWidget):
    """Widget for the chat input area at the bottom of the application."""
    
    # Signal emitted when a message is sent
    message_sent = Signal(str)
    
    def __init__(self):
        """Initialize the chat input widget."""
        super().__init__()
        
        # Set widget properties
        self.setFixedHeight(80)
        
        # Create main frame
        self.main_frame = QFrame()
        self.main_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.main_frame.setFrameShadow(QFrame.Shadow.Plain)
        self.main_frame.setLineWidth(1)
        self.main_frame.setStyleSheet(
            "QFrame { border-top: 1px solid #CC8B66; "
            "background-color: #2B3A52; }"
        )
        
        # Create main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.main_frame)
        
        # Create frame layout
        self.layout = QHBoxLayout(self.main_frame)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(10)
        
        # Create input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Press Enter to send chat")
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: 1px solid #CC8B66;
                border-radius: 20px;
                padding: 10px 15px;
                font-size: 14px;
                background-color: #34435A;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                border-color: #E6A085;
            }
        """)
        
        # Create send button
        self.send_button = SendButton()
        self.send_button.setEnabled(False)  # Initially disabled
        
        # Connect signals
        self.input_field.textChanged.connect(self.on_text_changed)
        self.input_field.returnPressed.connect(self.send_message)
        self.send_button.clicked.connect(self.send_message)
        
        # Add widgets to layout
        self.layout.addWidget(self.input_field)
        self.layout.addWidget(self.send_button)
    
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
            # Emit the message_sent signal
            self.message_sent.emit(message)
            
            # Clear the input field
            self.input_field.clear()
            
            # Disable the send button
            self.send_button.setEnabled(False)
    
    def set_input_text(self, text):
        """Set the text in the input field.
        
        Args:
            text (str): The text to set
        """
        self.input_field.setText(text)
    
    def get_input_text(self):
        """Get the current text in the input field.
        
        Returns:
            str: The current text in the input field
        """
        return self.input_field.text()
    
    def clear_input(self):
        """Clear the input field."""
        self.input_field.clear()
    
    def set_placeholder_text(self, text):
        """Set the placeholder text for the input field.
        
        Args:
            text (str): The placeholder text
        """
        self.input_field.setPlaceholderText(text)