"""
Loading Components - Reusable loading indicators and visual feedback widgets
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, 
    QProgressBar, QFrame
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, 
    QRect, QSize, Signal
)
from PySide6.QtGui import QPainter, QPen, QColor

from src.utils.colors import DinoPitColors
from src.utils.scaling import get_scaling_helper


class LoadingSpinner(QWidget):
    """Animated loading spinner widget"""
    
    def __init__(self, size: int = 20, parent=None):
        super().__init__(parent)
        self._scaling_helper = get_scaling_helper()
        self._size = self._scaling_helper.scaled_size(size)
        self._angle = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._rotate)
        self.setFixedSize(self._size, self._size)
        
    def start(self):
        """Start the spinning animation"""
        self._timer.start(50)  # 50ms = smooth 20fps animation
        
    def stop(self):
        """Stop the spinning animation"""
        self._timer.stop()
        self._angle = 0
        self.update()
        
    def _rotate(self):
        """Rotate the spinner"""
        self._angle = (self._angle + 15) % 360
        self.update()
        
    def paintEvent(self, event):
        """Paint the spinner"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set up the pen
        pen = QPen(QColor(DinoPitColors.DINOPIT_ORANGE))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        # Draw the spinner arc
        rect = QRect(2, 2, self._size - 4, self._size - 4)
        painter.drawArc(rect, self._angle * 16, 120 * 16)


class TypingIndicator(QWidget):
    """Animated typing indicator with dots"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scaling_helper = get_scaling_helper()
        self._setup_ui()
        self._animation_timer = QTimer()
        self._animation_timer.timeout.connect(self._animate_dots)
        self._dot_count = 0
        
    def _setup_ui(self):
        """Setup the typing indicator UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            self._scaling_helper.scaled_size(15),
            self._scaling_helper.scaled_size(10),
            self._scaling_helper.scaled_size(15),
            self._scaling_helper.scaled_size(10)
        )
        
        # Create frame with chat bubble styling
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border-radius: {self._scaling_helper.scaled_size(15)}px;
                border: none;
            }}
        """)
        self.setMaximumWidth(self._scaling_helper.scaled_size(150))
        
        # Typing text
        font_size = self._scaling_helper.get_font_for_role('body_secondary')
        self.typing_label = QLabel("AI is typing")
        self.typing_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: {font_size}px;
            font-style: italic;
            background: transparent;
            border: none;
        """)
        
        # Dots label for animation
        self.dots_label = QLabel("")
        self.dots_label.setStyleSheet(f"""
            color: {DinoPitColors.DINOPIT_ORANGE};
            font-size: {font_size}px;
            background: transparent;
            border: none;
        """)
        
        layout.addWidget(self.typing_label)
        layout.addWidget(self.dots_label)
        layout.addStretch()
        
    def start_animation(self):
        """Start the typing animation"""
        self._animation_timer.start(500)  # Change dots every 500ms
        
    def stop_animation(self):
        """Stop the typing animation"""
        self._animation_timer.stop()
        self.dots_label.setText("")
        
    def _animate_dots(self):
        """Animate the typing dots"""
        self._dot_count = (self._dot_count + 1) % 4
        dots = "." * self._dot_count
        self.dots_label.setText(dots)


class ProgressIndicator(QWidget):
    """Progress indicator with text for long operations"""
    
    def __init__(self, text: str = "Loading...", parent=None):
        super().__init__(parent)
        self._scaling_helper = get_scaling_helper()
        self._text = text
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the progress indicator UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(self._scaling_helper.scaled_size(10))
        layout.setContentsMargins(
            self._scaling_helper.scaled_size(20),
            self._scaling_helper.scaled_size(15),
            self._scaling_helper.scaled_size(20),
            self._scaling_helper.scaled_size(15)
        )
        
        # Spinner and text in horizontal layout
        content_layout = QHBoxLayout()
        content_layout.setSpacing(self._scaling_helper.scaled_size(10))
        
        # Add spinner
        self.spinner = LoadingSpinner(16)
        content_layout.addWidget(self.spinner)
        
        # Add text
        font_size = self._scaling_helper.get_font_for_role('body_primary')
        self.text_label = QLabel(self._text)
        self.text_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: {font_size}px;
            background: transparent;
        """)
        content_layout.addWidget(self.text_label)
        content_layout.addStretch()
        
        layout.addLayout(content_layout)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setFixedHeight(
            self._scaling_helper.scaled_size(6)
        )
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {self._scaling_helper.scaled_size(3)}px;
            }}
            QProgressBar::chunk {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                border-radius: {self._scaling_helper.scaled_size(2)}px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        
    def start(self):
        """Start the loading animation"""
        self.spinner.start()
        self.show()
        
    def stop(self):
        """Stop the loading animation"""
        self.spinner.stop()
        self.hide()
        
    def set_text(self, text: str):
        """Update the loading text"""
        self._text = text
        self.text_label.setText(text)
        
    def set_progress(self, value: int, maximum: int = 100):
        """Set specific progress value (0-100)"""
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)


class MessageSendIndicator(QWidget):
    """Visual feedback for message sending states"""
    
    # Signals
    retry_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scaling_helper = get_scaling_helper()
        self._state = "idle"  # idle, sending, sent, error
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the send indicator UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            self._scaling_helper.scaled_size(5),
            self._scaling_helper.scaled_size(5),
            self._scaling_helper.scaled_size(5),
            self._scaling_helper.scaled_size(5)
        )
        
        # Status icon/spinner
        self.status_widget = QLabel()
        self.status_widget.setFixedSize(
            self._scaling_helper.scaled_size(16),
            self._scaling_helper.scaled_size(16)
        )
        layout.addWidget(self.status_widget)
        
        # Status text
        font_size = self._scaling_helper.get_font_for_role('caption')
        self.status_text = QLabel("")
        self.status_text.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: {font_size}px;
            background: transparent;
        """)
        layout.addWidget(self.status_text)
        layout.addStretch()
        
        self.hide()  # Hidden by default
        
    def set_sending(self):
        """Show sending state"""
        self._state = "sending"
        self.status_widget.setText("⏳")
        self.status_text.setText("Sending...")
        self.show()
        
    def set_sent(self):
        """Show sent state"""
        self._state = "sent"
        self.status_widget.setText("✓")
        self.status_text.setText("Sent")
        self.show()
        # Auto-hide after 2 seconds
        QTimer.singleShot(2000, self.hide)
        
    def set_error(self, error_msg: str = "Failed to send"):
        """Show error state"""
        self._state = "error"
        self.status_widget.setText("❌")
        self.status_text.setText(error_msg)
        self.show()
        
    def reset(self):
        """Reset to idle state"""
        self._state = "idle"
        self.hide()