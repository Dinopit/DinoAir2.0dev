#!/usr/bin/env python3
"""
GUI Integration Example

This example shows how to build a complete GUI application
with the Pseudocode Translator using PySide6.
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QSplitter,
    QLabel, QProgressBar, QComboBox, QMenuBar,
    QMenu, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QAction, QKeySequence

from pseudocode_translator import PseudocodeTranslatorAPI
from pseudocode_translator.gui_worker import TranslationResult


class PseudocodeTranslatorWindow(QMainWindow):
    """Main window for the Pseudocode Translator GUI"""
    
    def __init__(self):
        super().__init__()
        self.translator = PseudocodeTranslatorAPI()
        self.current_file = None
        
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Pseudocode Translator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        toolbar_layout = QHBoxLayout()
        
        # Model selector
        self.model_combo = QComboBox()
        self.model_combo.addItems(["qwen", "gpt2", "codegen"])
        toolbar_layout.addWidget(QLabel("Model:"))
        toolbar_layout.addWidget(self.model_combo)
        
        # Translate button
        self.translate_btn = QPushButton("Translate (Ctrl+Enter)")
        self.translate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        toolbar_layout.addWidget(self.translate_btn)
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        toolbar_layout.addWidget(self.cancel_btn)
        
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
        # Create splitter for input/output
        splitter = QSplitter(Qt.Horizontal)
        
        # Input panel
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.addWidget(QLabel("Pseudocode Input:"))
        
        self.input_text = QTextEdit()
        self.input_text.setFont(QFont("Consolas", 10))
        self.input_text.setPlaceholderText(
            "Enter your pseudocode here...\n\n"
            "Example:\n"
            "create a function that calculates factorial"
        )
        input_layout.addWidget(self.input_text)
        
        # Output panel
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.addWidget(QLabel("Generated Python Code:"))
        
        self.output_text = QTextEdit()
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        
        splitter.addWidget(input_widget)
        splitter.addWidget(output_widget)
        splitter.setSizes([600, 600])
        
        layout.addWidget(splitter)
        
        # Status bar with progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.statusBar().addWidget(self.status_label)
        
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        translate_action = QAction("Translate", self)
        translate_action.setShortcut("Ctrl+Enter")
        translate_action.triggered.connect(self.translate)
        edit_menu.addAction(translate_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def connect_signals(self):
        """Connect signals to slots"""
        # Translation signals
        self.translator.translation_started.connect(
            self.on_translation_started
        )
        self.translator.translation_progress.connect(
            self.on_translation_progress
        )
        self.translator.translation_completed.connect(
            self.on_translation_completed
        )
        self.translator.translation_error.connect(
            self.on_translation_error
        )
        
        # UI signals
        self.translate_btn.clicked.connect(self.translate)
        self.cancel_btn.clicked.connect(self.cancel_translation)
        self.model_combo.currentTextChanged.connect(self.switch_model)
        
    def translate(self):
        """Start translation"""
        pseudocode = self.input_text.toPlainText().strip()
        if not pseudocode:
            QMessageBox.warning(
                self, "Warning", "Please enter some pseudocode"
            )
            return
        
        self.translator.translate_async(pseudocode)
        
    def cancel_translation(self):
        """Cancel ongoing translation"""
        self.translator.cancel_translation()
        
    def switch_model(self, model_name):
        """Switch to a different model"""
        self.translator.switch_model(model_name)
        self.status_label.setText(f"Switched to {model_name} model")
        
    def on_translation_started(self):
        """Handle translation start"""
        self.translate_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Translating...")
        self.output_text.clear()
        
    def on_translation_progress(self, progress):
        """Handle translation progress"""
        self.progress_bar.setValue(progress)
        
    def on_translation_completed(self, result: TranslationResult):
        """Handle translation completion"""
        self.translate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        if result.success:
            self.output_text.setPlainText(result.code)
            self.status_label.setText("Translation completed")
            
            # Show warnings if any
            if result.warnings:
                warning_text = "\n".join(
                    f"• {w}" for w in result.warnings
                )
                QMessageBox.information(
                    self, "Translation Warnings", warning_text
                )
        else:
            error_text = "\n".join(f"• {e}" for e in result.errors)
            self.output_text.setPlainText(
                f"# Translation failed:\n{error_text}"
            )
            self.status_label.setText("Translation failed")
            
    def on_translation_error(self, error):
        """Handle translation error"""
        self.translate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        QMessageBox.critical(self, "Error", str(error))
        self.status_label.setText("Error occurred")
        
    def new_file(self):
        """Create a new file"""
        if self.input_text.document().isModified():
            reply = QMessageBox.question(
                self, "Save Changes",
                "Do you want to save your changes?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                return
        
        self.input_text.clear()
        self.output_text.clear()
        self.current_file = None
        self.setWindowTitle("Pseudocode Translator")
        
    def open_file(self):
        """Open a file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Pseudocode File",
            "", "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    content = f.read()
                self.input_text.setPlainText(content)
                self.current_file = filename
                self.setWindowTitle(
                    f"Pseudocode Translator - {filename}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to open file: {e}"
                )
                
    def save_file(self):
        """Save the current file"""
        if not self.current_file:
            self.save_file_as()
            return
            
        try:
            with open(self.current_file, 'w') as f:
                f.write(self.input_text.toPlainText())
            self.status_label.setText(f"Saved to {self.current_file}")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to save file: {e}"
            )
            
    def save_file_as(self):
        """Save file with a new name"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Pseudocode File",
            "", "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            self.current_file = filename
            self.save_file()
            self.setWindowTitle(
                f"Pseudocode Translator - {filename}"
            )
            
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About Pseudocode Translator",
            "<h3>Pseudocode Translator</h3>"
            "<p>Transform your ideas into Python code!</p>"
            "<p>Write in plain English mixed with Python syntax, "
            "and let AI translate it into working code.</p>"
            "<p><b>Version:</b> 1.0.0</p>"
            "<p><b>License:</b> MIT</p>"
        )


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    window = PseudocodeTranslatorWindow()
    window.show()
    
    # Load example pseudocode
    example = """Create a TodoList class that:
- has a list of tasks (initially empty)
- has an add_task method that adds a task with description and priority
- has a remove_task method that removes a task by index
- has a get_high_priority_tasks method that returns tasks with priority > 3
- has a __str__ method that returns a formatted list of all tasks"""
    
    window.input_text.setPlainText(example)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()