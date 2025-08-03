#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ChatHistoryWidget class for the PySide6 application.
This widget displays the chat history in the left sidebar.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, 
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette


class ChatHistoryItem(QFrame):
    """A single chat history item widget."""
    
    def __init__(self, message, time_ago):
        """Initialize the chat history item.
        
        Args:
            message (str): The chat message text
            time_ago (str): Time information (e.g., "2 hours ago")
        """
        super().__init__()
        
        # Set frame style
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setLineWidth(1)
        
        # Set background color - DinoPit brand colors with desaturated blue
        palette = self.palette()
        # Desaturated blue-gray background
        palette.setColor(QPalette.ColorRole.Window, QColor(52, 67, 89))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Create message label with DinoPit brand colors
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        # Orange text for better visibility
        self.message_label.setStyleSheet(
            "color: #FF6B35; font-size: 12px; font-weight: 500;"
        )
        
        # Create time label with cyan color
        self.time_label = QLabel(time_ago)
        self.time_label.setStyleSheet("color: #FFFFFF; font-size: 10px;")
        
        # Add labels to layout
        layout.addWidget(self.message_label)
        layout.addWidget(self.time_label)


class ChatHistoryWidget(QWidget):
    """Widget displaying the chat history in the left sidebar."""
    
    def __init__(self):
        """Initialize the chat history widget."""
        super().__init__()
        
        # Set fixed width
        self.setFixedWidth(300)
        
        # Create main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Create header with DinoPit brand colors
        self.header = QWidget()
        self.header.setStyleSheet(
            "background-color: #FF6B35; border-bottom: 2px solid #FF4500;"
        )
        self.header.setFixedHeight(50)
        
        # Create header layout
        header_layout = QVBoxLayout(self.header)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        # Create header label with improved styling
        header_label = QLabel("Latest")
        header_label.setStyleSheet(
            "font-weight: bold; color: white; font-size: 14px;"
        )
        
        # Add header label to header layout
        header_layout.addWidget(header_label)
        
        # Create scroll area for chat history items
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Create container widget for chat history items
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(15, 15, 15, 15)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Set scroll content as the widget for scroll area
        self.scroll_area.setWidget(self.scroll_content)
        
        # Add header and scroll area to main layout
        self.layout.addWidget(self.header)
        self.layout.addWidget(self.scroll_area)
        
        # Add some example chat history items
        self.add_chat_item("Previous chat message 1...", "2 hours ago")
        self.add_chat_item("Previous chat message 2...", "5 hours ago")
        self.add_chat_item("Previous chat message 3...", "1 day ago")
    
    def add_chat_item(self, message, time_ago):
        """Add a chat history item to the widget.
        
        Args:
            message (str): The chat message text
            time_ago (str): Time information (e.g., "2 hours ago")
        """
        item = ChatHistoryItem(message, time_ago)
        self.scroll_layout.addWidget(item)