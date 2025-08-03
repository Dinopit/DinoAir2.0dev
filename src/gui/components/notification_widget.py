"""
Notification Widget Component - Display system alerts and notifications
"""

from typing import List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve
)


class AlertLevel(Enum):
    """Alert severity levels for notifications.
    
    This matches the AlertLevel enum from Watchdog module.
    """
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Notification:
    """Data class for individual notifications"""
    level: AlertLevel
    message: str
    timestamp: datetime
    auto_dismiss: bool = True
    dismiss_delay: int = 5000  # milliseconds


class NotificationItem(QFrame):
    """Individual notification display widget"""
    
    dismissed = Signal()
    
    def __init__(self, notification: Notification, parent=None):
        super().__init__(parent)
        self.notification = notification
        self.setup_ui()
        
        # Auto-dismiss timer
        if notification.auto_dismiss and notification.level == AlertLevel.INFO:
            self.dismiss_timer = QTimer()
            self.dismiss_timer.timeout.connect(self.dismiss)
            self.dismiss_timer.start(notification.dismiss_delay)
        
    def setup_ui(self):
        """Setup the notification item UI"""
        # Frame styling based on severity
        self.setFrameStyle(QFrame.Shape.Box)
        self.setObjectName("NotificationItem")
        
        # Apply styling based on alert level
        style_map = {
            AlertLevel.INFO: {
                "bg": "#2C5F2D",      # Dark green
                "border": "#4CAF50",   # Light green
                "icon": "ℹ️"
            },
            AlertLevel.WARNING: {
                "bg": "#6B4226",      # Dark orange/brown
                "border": "#FF9800",   # Orange
                "icon": "⚠️"
            },
            AlertLevel.CRITICAL: {
                "bg": "#6B1F1F",      # Dark red
                "border": "#F44336",   # Red
                "icon": "🚨"
            }
        }
        
        style = style_map.get(
            self.notification.level,
            style_map[AlertLevel.INFO]
        )
        
        self.setStyleSheet(f"""
            QFrame#NotificationItem {{
                background-color: {style['bg']};
                border: 2px solid {style['border']};
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }}
            QLabel {{
                color: #FFFFFF;
                background-color: transparent;
            }}
            QPushButton {{
                background-color: {style['border']};
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #FFFFFF;
                color: {style['bg']};
            }}
        """)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Icon
        icon_label = QLabel(style['icon'])
        icon_label.setStyleSheet("font-size: 24px;")
        layout.addWidget(icon_label)
        
        # Content layout
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        
        # Level and timestamp
        header_layout = QHBoxLayout()
        level_label = QLabel(f"<b>{self.notification.level.value.upper()}</b>")
        level_label.setStyleSheet("font-size: 12px;")
        header_layout.addWidget(level_label)
        
        time_label = QLabel(self.notification.timestamp.strftime("%H:%M:%S"))
        time_label.setStyleSheet("font-size: 11px; color: #CCCCCC;")
        header_layout.addWidget(time_label)
        header_layout.addStretch()
        
        content_layout.addLayout(header_layout)
        
        # Message
        message_label = QLabel(self.notification.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 13px;")
        content_layout.addWidget(message_label)
        
        layout.addLayout(content_layout, 1)
        
        # Dismiss button
        dismiss_btn = QPushButton("✕")
        dismiss_btn.setFixedSize(24, 24)
        dismiss_btn.clicked.connect(self.dismiss)
        dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(dismiss_btn, alignment=Qt.AlignmentFlag.AlignTop)
        
        # Set size policy
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        
    def dismiss(self):
        """Dismiss this notification with fade animation"""
        # Stop auto-dismiss timer if active
        if hasattr(self, 'dismiss_timer'):
            self.dismiss_timer.stop()
            
        # Fade out animation
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.fade_animation.finished.connect(self.dismissed.emit)
        self.fade_animation.start()


class NotificationWidget(QWidget):
    """Main notification widget container"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notifications: List[NotificationItem] = []
        self.max_notifications = 5  # Maximum visible notifications
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the notification widget UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QLabel("System Notifications")
        header.setStyleSheet("""
            QLabel {
                background-color: #1E2A3A;
                color: #FFFFFF;
                padding: 8px;
                font-weight: bold;
                font-size: 14px;
                border-bottom: 2px solid #3498db;
            }
        """)
        layout.addWidget(header)
        
        # Scroll area for notifications
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #2B3A52;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2B3A52;
                width: 10px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #3498db;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        # Container for notification items
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(5, 5, 5, 5)
        self.container_layout.setSpacing(5)
        self.container_layout.addStretch()  # Push notifications to top
        
        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)
        
        # Clear all button
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: #FFFFFF;
                border: none;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2c3e50;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_all)
        layout.addWidget(self.clear_btn)
        
        # Hide clear button initially
        self.clear_btn.hide()
        
    def add_notification(self, level: AlertLevel, message: str):
        """Add a new notification to the widget"""
        # Create notification
        notification = Notification(
            level=level,
            message=message,
            timestamp=datetime.now(),
            auto_dismiss=(level == AlertLevel.INFO),
            dismiss_delay=5000 if level == AlertLevel.INFO else 0
        )
        
        # Create notification item
        item = NotificationItem(notification)
        item.dismissed.connect(lambda: self.remove_notification(item))
        
        # Insert at the top (after any stretch)
        insert_index = 0
        self.container_layout.insertWidget(insert_index, item)
        self.notifications.insert(0, item)
        
        # Remove oldest if exceeding max
        if len(self.notifications) > self.max_notifications:
            oldest = self.notifications.pop()
            oldest.dismiss()
        
        # Show clear button if we have notifications
        if self.notifications:
            self.clear_btn.show()
            
        # Scroll to top to show new notification
        self.scroll_area.verticalScrollBar().setValue(0)
        
    def remove_notification(self, item: NotificationItem):
        """Remove a notification item"""
        if item in self.notifications:
            self.notifications.remove(item)
            self.container_layout.removeWidget(item)
            item.deleteLater()
            
        # Hide clear button if no notifications
        if not self.notifications:
            self.clear_btn.hide()
            
    def clear_all(self):
        """Clear all notifications"""
        for item in self.notifications[:]:
            item.dismiss()