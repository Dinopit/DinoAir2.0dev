"""Calendar Page - Calendar interface"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class CalendarPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Calendar Page - Coming Soon"))
