"""
Pseudocode Page - Pseudocode translator interface
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QComboBox, QLabel, QSplitter, QProgressBar, QGroupBox, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QTextCursor

# Import the translator API
try:
    from pseudocode_translator.integration.api import SimpleTranslator
    from pseudocode_translator.models.base_model import OutputLanguage
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    SimpleTranslator = None
    OutputLanguage = None


class TranslationThread(QThread):
    """Thread for running translation without blocking UI"""
    progress = Signal(int, str)  # percentage, message
    result = Signal(str, str)  # code, language
    error = Signal(str)  # error message
    
    def __init__(self, translator, pseudocode, output_language):
        super().__init__()
        self.translator = translator
        self.pseudocode = pseudocode
        self.output_language = output_language
        
    def run(self):
        """Run the translation"""
        try:
            # Create progress callback
            def on_progress(percentage, message):
                self.progress.emit(percentage, message)
            
            # Perform translation
            result = self.translator.translate(
                self.pseudocode,
                output_language=self.output_language,
                progress_callback=on_progress
            )
            
            # Emit result
            self.result.emit(result, self.output_language)
            
        except Exception as e:
            self.error.emit(str(e))


class PseudocodePage(QWidget):
    """Pseudocode translator page widget"""
    
    def __init__(self):
        super().__init__()
        self.translator = None
        self.translation_thread = None
        
        # Initialize translator if available
        if TRANSLATOR_AVAILABLE and SimpleTranslator:
            try:
                self.translator = SimpleTranslator()
            except Exception as e:
                print(f"Failed to initialize translator: {e}")
                
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the pseudocode page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Pseudocode Translator")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        # Language selector
        toolbar_layout.addWidget(QLabel("Output Language:"))
        self.language_combo = QComboBox()
        
        if TRANSLATOR_AVAILABLE and OutputLanguage:
            # Add all available languages
            for lang in OutputLanguage:
                self.language_combo.addItem(lang.value, lang)
            # Set Python as default
            self.language_combo.setCurrentText("python")
        else:
            # Fallback if translator not available
            self.language_combo.addItems(
                ["python", "javascript", "java", "cpp"]
            )
            
        toolbar_layout.addWidget(self.language_combo)
        
        # Translate button
        self.translate_btn = QPushButton("Translate")
        self.translate_btn.clicked.connect(self._translate)
        toolbar_layout.addWidget(self.translate_btn)
        
        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_all)
        toolbar_layout.addWidget(clear_btn)
        
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Create splitter for input/output
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Input pane
        input_group = QGroupBox("Pseudocode Input")
        input_layout = QVBoxLayout(input_group)
        
        self.input_editor = QTextEdit()
        self.input_editor.setPlaceholderText(
            "Enter your pseudocode here...\n\n"
            "Example:\n"
            "function fibonacci(n)\n"
            "    if n <= 1 then return n\n"
            "    return fibonacci(n-1) + fibonacci(n-2)\n"
            "end function"
        )
        input_layout.addWidget(self.input_editor)
        
        splitter.addWidget(input_group)
        
        # Output pane
        output_group = QGroupBox("Generated Code")
        output_layout = QVBoxLayout(output_group)
        
        # Output toolbar
        output_toolbar = QHBoxLayout()
        
        self.output_language_label = QLabel("Language: -")
        output_toolbar.addWidget(self.output_language_label)
        
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self._copy_output)
        output_toolbar.addWidget(copy_btn)
        
        output_toolbar.addStretch()
        output_layout.addLayout(output_toolbar)
        
        self.output_editor = QTextEdit()
        self.output_editor.setReadOnly(True)
        self.output_editor.setPlaceholderText(
            "Translation will appear here..."
        )
        
        # Set monospace font for code
        code_font = QFont("Consolas, Monaco, 'Courier New', monospace")
        code_font.setPointSize(10)
        self.output_editor.setFont(code_font)
        
        output_layout.addWidget(self.output_editor)
        
        splitter.addWidget(output_group)
        
        # Set splitter proportions
        splitter.setSizes([500, 500])
        
        layout.addWidget(splitter)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Load sample if translator not available
        if not TRANSLATOR_AVAILABLE:
            self._show_unavailable_message()
            
    def _translate(self):
        """Perform translation"""
        if not self.translator:
            self._show_error(
                "Translator not available. Please check installation."
            )
            return
            
        pseudocode = self.input_editor.toPlainText().strip()
        if not pseudocode:
            self._show_error("Please enter some pseudocode to translate.")
            return
            
        # Get selected language
        if TRANSLATOR_AVAILABLE and OutputLanguage:
            output_language = self.language_combo.currentData()
        else:
            output_language = self.language_combo.currentText()
            
        # Disable UI during translation
        self.translate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Translating...")
        
        # Create and start translation thread
        self.translation_thread = TranslationThread(
            self.translator, pseudocode, output_language
        )
        self.translation_thread.progress.connect(self._update_progress)
        self.translation_thread.result.connect(self._show_result)
        self.translation_thread.error.connect(self._show_error)
        self.translation_thread.finished.connect(self._translation_finished)
        self.translation_thread.start()
        
    def _update_progress(self, percentage, message):
        """Update progress bar and status"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
        
    def _show_result(self, code, language):
        """Show translation result"""
        self.output_editor.setPlainText(code)
        self.output_language_label.setText(f"Language: {language}")
        self.status_label.setText("Translation completed successfully!")
        
        # Highlight output
        cursor = self.output_editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.output_editor.setTextCursor(cursor)
        
    def _show_error(self, error_message):
        """Show error message"""
        self.status_label.setText(f"Error: {error_message}")
        self.output_editor.setPlainText(f"Error occurred:\n\n{error_message}")
        
    def _translation_finished(self):
        """Handle translation thread completion"""
        self.translate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.translation_thread = None
        
    def _clear_all(self):
        """Clear input and output"""
        self.input_editor.clear()
        self.output_editor.clear()
        self.output_language_label.setText("Language: -")
        self.status_label.setText("Ready")
        
    def _copy_output(self):
        """Copy output to clipboard"""
        output_text = self.output_editor.toPlainText()
        if output_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(output_text)
            self.status_label.setText("Code copied to clipboard!")
            
    def _show_unavailable_message(self):
        """Show message when translator is not available"""
        self.input_editor.setPlainText(
            "# Pseudocode Translator Demo\n\n"
            "The pseudocode translator module is not available.\n"
            "Please ensure it is properly installed.\n\n"
            "Features when available:\n"
            "- Translate natural language pseudocode to real code\n"
            "- Support for 14+ programming languages\n"
            "- Modern Python syntax support\n"
            "- Real-time translation with progress tracking\n"
            "- Multiple AI model support"
        )
        self.translate_btn.setEnabled(False)
        self.status_label.setText("Translator module not available")