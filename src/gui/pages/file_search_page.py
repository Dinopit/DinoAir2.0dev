"""
File Search Page - RAG-powered local file search interface
"""

import os
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMessageBox, QLabel, QPushButton, QFrame,
    QCheckBox, QGroupBox, QComboBox, QLineEdit
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QSettings
from PySide6.QtGui import QKeySequence, QShortcut

from ...rag.vector_search import VectorSearchEngine, SearchResult
from ...rag.file_processor import FileProcessor
from ...rag.directory_validator import DirectoryValidator
from ...database.file_search_db import FileSearchDB
from ...utils.colors import DinoPitColors
from ...utils.logger import Logger
from ...utils.scaling import get_scaling_helper
from ...utils.window_state import window_state_manager
from ..components.enhanced_file_search_results import EnhancedFileSearchResultsWidget
from ..components.file_indexing_status import IndexingStatusWidget
from ..components.directory_limiter_widget import DirectoryLimiterWidget


class IndexingWorker(QThread):
    """Worker thread for file indexing operations"""
    progress_update = Signal(str, int, int)  # message, current, total
    indexing_complete = Signal(dict)  # results
    indexing_error = Signal(str)  # error message
    
    def __init__(self, file_processor: FileProcessor, 
                 directory_path: str,
                 file_types: List[str],
                 recursive: bool = True):
        super().__init__()
        self.file_processor = file_processor
        self.directory_path = directory_path
        self.file_types = file_types
        self.recursive = recursive
        self._is_cancelled = False
    
    def run(self):
        """Run the indexing process"""
        try:
            result = self.file_processor.process_directory(
                self.directory_path,
                recursive=self.recursive,
                file_extensions=self.file_types,
                force_reprocess=False,
                progress_callback=self._progress_callback
            )
            
            if not self._is_cancelled:
                self.indexing_complete.emit(result)
                
        except Exception as e:
            if not self._is_cancelled:
                self.indexing_error.emit(str(e))
    
    def _progress_callback(self, message: str, current: int, total: int):
        """Handle progress updates"""
        if not self._is_cancelled:
            self.progress_update.emit(message, current, total)
    
    def cancel(self):
        """Cancel the indexing operation"""
        self._is_cancelled = True


class FileSearchPage(QWidget):
    """File Search page with RAG-powered search and indexing"""
    
    # Signals
    file_selected = Signal(str)  # file_path
    
    def __init__(self):
        """Initialize the file search page"""
        super().__init__()
        self.logger = Logger()
        self._current_user = "default_user"  # Can be updated from settings
        
        # Initialize settings
        self.settings = QSettings("DinoAir", "FileSearch")
        
        # Initialize RAG components
        self.search_engine = VectorSearchEngine(self._current_user)
        self.file_processor = FileProcessor(
            user_name=self._current_user,
            chunk_size=1000,
            chunk_overlap=200,
            generate_embeddings=True
        )
        self.file_search_db = FileSearchDB(self._current_user)
        
        # Initialize directory validator
        self.directory_validator = DirectoryValidator()
        self._load_directory_settings()
        
        # State variables
        self._search_results: List[SearchResult] = []
        self._indexing_worker: Optional[IndexingWorker] = None
        self._active_file_types: List[str] = []
        self._search_mode = "hybrid"  # vector, keyword, or hybrid
        self._indexed_directories: List[str] = []
        self._last_selected_directory = ""
        
        # UI components
        self._scaling_helper = get_scaling_helper()
        
        self.setup_ui()
        self._load_initial_state()
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
        # Setup refresh timer for status updates
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._update_indexing_status)
        self._status_timer.setInterval(5000)  # Update every 5 seconds
        self._status_timer.start()
    
    def setup_ui(self):
        """Setup the file search page UI"""
        layout = QVBoxLayout(self)
        
        # Use font metrics for consistent spacing
        font_metrics = self.fontMetrics()
        margin = font_metrics.height() // 2
        
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(0)
        
        # Create toolbar with search
        toolbar_container = self._create_toolbar_with_search()
        layout.addWidget(toolbar_container)
        
        # Create main content area
        self.content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.content_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                height: 2px;
            }}
        """)
        
        # Search controls section
        controls_section = self._create_search_controls()
        self.content_splitter.addWidget(controls_section)
        
        # Results section
        results_section = self._create_results_section()
        self.content_splitter.addWidget(results_section)
        
        # Status section
        status_section = self._create_status_section()
        self.content_splitter.addWidget(status_section)
        
        # Set initial splitter proportions
        self._update_splitter_sizes()
        
        # Connect splitter moved signal
        self.content_splitter.splitterMoved.connect(self._save_splitter_state)
        
        # Restore splitter state if available
        self._restore_splitter_state()
        
        layout.addWidget(self.content_splitter)
    
    def _create_toolbar_with_search(self) -> QWidget:
        """Create the toolbar with search functionality"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        font_metrics = self.fontMetrics()
        spacing = font_metrics.height() // 4
        container_layout.setSpacing(spacing)
        
        # Header
        header = QLabel("🔍 File Search")
        header.setStyleSheet(f"""
            background-color: {DinoPitColors.DINOPIT_ORANGE};
            color: white;
            padding: 10px;
            font-weight: bold;
            font-size: 18px;
            border-radius: 5px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(header)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        
        # Search mode selector
        self.search_mode_combo = QComboBox()
        self.search_mode_combo.addItems(["Hybrid", "Semantic", "Keyword"])
        self.search_mode_combo.setCurrentText("Hybrid")
        self.search_mode_combo.currentTextChanged.connect(
            self._on_search_mode_changed
        )
        self.search_mode_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 8px 12px;
                border: 2px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
                min-width: 100px;
            }}
            QComboBox:hover {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 5px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {DinoPitColors.PRIMARY_TEXT};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {DinoPitColors.SIDEBAR_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                selection-background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
        """)
        search_layout.addWidget(self.search_mode_combo)
        
        # Search input with history
        self.search_input = QComboBox()
        self.search_input.setEditable(True)
        self.search_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.search_input.lineEdit().setPlaceholderText("Search your files...")
        self.search_input.setMaxCount(10)  # Keep last 10 searches
        self.search_input.setStyleSheet(f"""
            QComboBox {{
                padding: 10px 15px;
                border: 2px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 20px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: 14px;
                min-width: 300px;
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 0.5);
            }}
            QLineEdit:focus {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        self.search_input.lineEdit().textChanged.connect(self._on_search_text_changed)
        self.search_input.activated.connect(lambda: self._perform_search())
        self.search_input.lineEdit().returnPressed.connect(self._perform_search)
        search_layout.addWidget(self.search_input, 1)
        
        # Search button
        self.search_button = QPushButton("🔍 Search")
        self.search_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: 20px;
                padding: 10px 25px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #00A8E8;
            }}
            QPushButton:pressed {{
                background-color: #0096D6;
            }}
        """)
        self.search_button.clicked.connect(self._perform_search)
        search_layout.addWidget(self.search_button)
        
        # Clear button
        self.clear_button = QPushButton("✖ Clear")
        self.clear_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                color: white;
                border: none;
                border-radius: 20px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #B87A56;
            }}
            QPushButton:disabled {{
                background-color: #666666;
                color: #999999;
            }}
        """)
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self._clear_search)
        search_layout.addWidget(self.clear_button)
        
        # Settings button
        self.settings_button = QPushButton("⚙️ Settings")
        self.settings_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
                border: 2px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 20px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                color: white;
            }}
        """)
        self.settings_button.clicked.connect(self._show_settings)
        search_layout.addWidget(self.settings_button)
        
        container_layout.addLayout(search_layout)
        
        # Setup debounce timer for search
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._perform_search)
        
        # Setup shortcuts
        self._setup_shortcuts()
        
        return container
    
    def _create_search_controls(self) -> QWidget:
        """Create search controls section"""
        controls_widget = QFrame()
        controls_widget.setStyleSheet(f"""
            QFrame {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        
        layout = QHBoxLayout(controls_widget)
        
        # File type filters
        filters_group = QGroupBox("File Type Filters")
        filters_group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: {DinoPitColors.PRIMARY_TEXT};
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        
        filters_layout = QHBoxLayout(filters_group)
        
        # Common file types
        file_types = [
            ("📄 Documents", [".pdf", ".docx", ".doc", ".txt"]),
            ("💻 Code", [".py", ".js", ".java", ".cpp", ".c", ".cs"]),
            ("📝 Text", [".txt", ".md", ".json", ".csv"]),
            ("🌐 Web", [".html", ".css", ".js", ".jsx", ".tsx"]),
            ("📊 Data", [".csv", ".json", ".xml", ".yaml"])
        ]
        
        self.file_type_checkboxes = {}
        for label, extensions in file_types:
            checkbox = QCheckBox(label)
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: {DinoPitColors.PRIMARY_TEXT};
                    spacing: 5px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 2px solid {DinoPitColors.SOFT_ORANGE};
                    border-radius: 3px;
                    background-color: {DinoPitColors.MAIN_BACKGROUND};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {DinoPitColors.DINOPIT_ORANGE};
                    border-color: {DinoPitColors.DINOPIT_ORANGE};
                }}
            """)
            checkbox.toggled.connect(self._on_filter_toggled)
            self.file_type_checkboxes[label] = (checkbox, extensions)
            filters_layout.addWidget(checkbox)
        
        # Check all by default
        for checkbox, _ in self.file_type_checkboxes.values():
            checkbox.setChecked(True)
        
        filters_layout.addStretch()
        layout.addWidget(filters_group)
        
        # Quick stats
        stats_group = QGroupBox("Quick Stats")
        stats_group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: {DinoPitColors.PRIMARY_TEXT};
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        
        stats_layout = QHBoxLayout(stats_group)
        
        self.stats_label = QLabel("Loading stats...")
        self.stats_label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT}; font-weight: bold;")
        stats_layout.addWidget(self.stats_label)
        
        layout.addWidget(stats_group)
        
        return controls_widget
    
    def _create_results_section(self) -> QWidget:
        """Create results display section"""
        results_widget = QWidget()
        layout = QVBoxLayout(results_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Results header
        header_layout = QHBoxLayout()
        
        self.results_count_label = QLabel("No results")
        self.results_count_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-weight: bold;
            font-size: 16px;
        """)
        header_layout.addWidget(self.results_count_label)
        
        header_layout.addStretch()
        
        # Sort options
        sort_label = QLabel("Sort by:")
        sort_label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT}; font-weight: bold;")
        header_layout.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(
            ["Relevance", "File Name", "Modified Date", "File Type"]
        )
        self.sort_combo.currentTextChanged.connect(self._on_sort_changed)
        self.sort_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 5px 10px;
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {DinoPitColors.PRIMARY_TEXT};
                margin-right: 5px;
            }}
        """)
        header_layout.addWidget(self.sort_combo)
        
        layout.addLayout(header_layout)
        
        # Results display widget
        self.results_widget = EnhancedFileSearchResultsWidget()
        self.results_widget.file_selected.connect(self._on_file_selected)
        self.results_widget.file_open_requested.connect(self._open_file)
        self.results_widget.copy_path_requested.connect(self._copy_file_path)
        self.results_widget.create_note_requested.connect(
            self._create_note_from_result
        )
        self.results_widget.save_as_artifact_requested.connect(
            self._save_as_artifact
        )
        layout.addWidget(self.results_widget)
        
        return results_widget
    
    def _create_status_section(self) -> QWidget:
        """Create indexing status section"""
        status_widget = QWidget()
        layout = QVBoxLayout(status_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Indexing status widget
        self.indexing_status = IndexingStatusWidget()
        self.indexing_status.index_directory_requested.connect(
            self._start_indexing
        )
        self.indexing_status.cancel_indexing_requested.connect(
            self._cancel_indexing
        )
        layout.addWidget(self.indexing_status)
        
        return status_widget
    
    def _on_search_text_changed(self, text: str):
        """Handle search text changes with debouncing"""
        # Stop any existing timer
        self._search_timer.stop()
        
        # Enable/disable clear button
        self.clear_button.setEnabled(bool(text))
        
        # Start debounce timer (300ms)
        if text:
            self._search_timer.start(300)
        else:
            self._clear_search()
    
    def _on_search_mode_changed(self, mode: str):
        """Handle search mode change"""
        self._search_mode = mode.lower()
        
        # Re-run search if we have a query
        if self.search_input.currentText():
            self._perform_search()
    
    def _on_filter_toggled(self):
        """Handle file type filter toggle"""
        # Update active file types
        self._active_file_types = []
        for label, (checkbox, extensions) in self.file_type_checkboxes.items():
            if checkbox.isChecked():
                self._active_file_types.extend(extensions)
        
        # Re-run search if we have results
        if self._search_results:
            self._apply_filters()
    
    def _on_sort_changed(self, sort_by: str):
        """Handle sort option change"""
        if self._search_results:
            self._sort_results(sort_by)
    
    def _perform_search(self):
        """Perform the actual search"""
        query = self.search_input.currentText().strip()
        if not query:
            return
        
        # Add to search history if not already there
        if query and self.search_input.findText(query) == -1:
            self.search_input.insertItem(0, query)
            # Remove oldest if we exceed max count
            while self.search_input.count() > self.search_input.maxCount():
                self.search_input.removeItem(self.search_input.count() - 1)
        
        try:
            # Disable search button during search
            self.search_button.setEnabled(False)
            self.search_button.setText("🔄 Searching...")
            
            # Perform search based on mode
            if self._search_mode in ("semantic", "vector"):
                results = self.search_engine.search(
                    query,
                    top_k=50,
                    file_types=self._active_file_types,
                    distance_metric='cosine'
                )
            elif self._search_mode == "keyword":
                results = self.search_engine.keyword_search(
                    query,
                    top_k=50,
                    file_types=self._active_file_types
                )
            else:  # hybrid
                results = self.search_engine.hybrid_search(
                    query,
                    top_k=50,
                    file_types=self._active_file_types,
                    rerank=True
                )
            
            self._search_results = results
            self._display_results(results)
            
            # Update results count
            count = len(results)
            if count == 0:
                self.results_count_label.setText(
                    f"No results found for '{query}'"
                )
            else:
                self.results_count_label.setText(
                    f"{count} result{'s' if count != 1 else ''} found"
                )
            
        except Exception as e:
            self.logger.error(f"Search error: {str(e)}")
            QMessageBox.critical(
                self,
                "Search Error",
                f"Failed to perform search: {str(e)}"
            )
        
        finally:
            # Re-enable search button
            self.search_button.setEnabled(True)
            self.search_button.setText("🔍 Search")
    
    def _clear_search(self):
        """Clear search and results"""
        self.search_input.clear()
        self.clear_button.setEnabled(False)
        self._search_results = []
        self.results_widget.clear_results()
        self.results_count_label.setText("No results")
    
    def _display_results(self, results: List[SearchResult]):
        """Display search results"""
        self.results_widget.display_results(results, self.search_input.currentText())
    
    def _apply_filters(self):
        """Apply file type filters to current results"""
        if not self._search_results:
            return
        
        # Filter results based on active file types
        filtered_results = [
            result for result in self._search_results
            if any(result.file_path.lower().endswith(ext) 
                   for ext in self._active_file_types)
        ]
        
        self._display_results(filtered_results)
        
        # Update count
        count = len(filtered_results)
        self.results_count_label.setText(
            f"{count} result{'s' if count != 1 else ''} "
            f"(filtered from {len(self._search_results)})"
        )
    
    def _sort_results(self, sort_by: str):
        """Sort current results"""
        if not self._search_results:
            return
        
        sorted_results = self._search_results.copy()
        
        if sort_by == "Relevance":
            sorted_results.sort(key=lambda x: x.score, reverse=True)
        elif sort_by == "File Name":
            sorted_results.sort(
                key=lambda x: os.path.basename(x.file_path).lower()
            )
        elif sort_by == "Modified Date":
            # Would need to get file stats for this
            pass
        elif sort_by == "File Type":
            sorted_results.sort(
                key=lambda x: os.path.splitext(x.file_path)[1].lower()
            )
        
        self._display_results(sorted_results)
    
    def _on_file_selected(self, file_path: str):
        """Handle file selection from results"""
        self.file_selected.emit(file_path)
    
    def _open_file(self, file_path: str):
        """Open file in default application"""
        try:
            import os
            os.startfile(file_path)  # Windows
        except Exception as e:
            self.logger.error(f"Failed to open file: {str(e)}")
            QMessageBox.warning(
                self,
                "Open File",
                f"Failed to open file: {str(e)}"
            )
    
    def _copy_file_path(self, file_path: str):
        """Copy file path to clipboard"""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(file_path)
        
        # Show brief notification (could use a toast widget)
        self.indexing_status.update_status("Path copied to clipboard!", "info")
    
    def _show_settings(self):
        """Show settings dialog"""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox
        
        # Create settings dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("File Search Settings")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(500)
        
        layout = QVBoxLayout(dialog)
        
        # Add directory limiter widget
        directory_widget = DirectoryLimiterWidget()
        
        # Load current settings
        allowed_dirs = self.settings.value("allowed_directories", [], list)
        excluded_dirs = self.settings.value("excluded_directories", [], list)
        # Ensure lists for settings
        allowed_list = (
            allowed_dirs if isinstance(allowed_dirs, list) else []
        )
        excluded_list = (
            excluded_dirs if isinstance(excluded_dirs, list) else []
        )
        directory_widget.set_settings({
            "allowed_directories": allowed_list,
            "excluded_directories": excluded_list
        })
        
        # Connect changes
        directory_widget.directories_changed.connect(
            self._on_directory_settings_changed
        )
        
        layout.addWidget(directory_widget)
        
        # Add dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Settings already saved via signal
            self.indexing_status.update_status(
                "Directory settings updated", "success"
            )
    
    def _start_indexing(self, directory: str):
        """Start indexing a directory with validation"""
        if self._indexing_worker and self._indexing_worker.isRunning():
            QMessageBox.warning(
                self,
                "Indexing Active",
                "An indexing operation is already in progress."
            )
            return
        
        # First check if directory exists
        if not os.path.exists(directory):
            QMessageBox.critical(
                self,
                "Directory Not Found",
                f"The directory does not exist:\n{directory}"
            )
            return
        
        # AUTO-ADD FIX: Check if directory needs to be added to allowed list
        current_allowed = self.settings.value("allowed_directories", [], list)
        if not isinstance(current_allowed, list):
            current_allowed = []
        
        # Check if directory is in allowed list or if no restrictions exist
        validator_stats = self.directory_validator.get_statistics()
        has_restrictions = validator_stats.get('has_restrictions', False)
        
        if has_restrictions and directory not in current_allowed:
            # Ask user if they want to auto-add it
            reply = QMessageBox.question(
                self,
                "Add Directory to Allowed List?",
                f"The directory '{directory}' is not in your allowed directories list.\n\n"
                "Would you like to add it to the allowed list and proceed with indexing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Add to allowed directories
                self.logger.info(f"Auto-adding directory to allowed list: {directory}")
                current_allowed.append(directory)
                
                # Save to both QSettings and database
                self.settings.setValue("allowed_directories", current_allowed)
                self.settings.sync()
                
                # Save to database
                result = self.file_search_db.update_search_settings(
                    "allowed_directories", current_allowed
                )
                if result['success']:
                    self.logger.info("Auto-added directory to database")
                    # Update validators
                    self.directory_validator.set_allowed_directories(current_allowed)
                    self.file_processor.update_settings(
                        allowed_directories=current_allowed
                    )
                else:
                    self.logger.error(f"Failed to auto-add to database: {result.get('error')}")
                    QMessageBox.warning(
                        self,
                        "Warning",
                        "Directory was added but database sync failed. "
                        "You may need to restart the application."
                    )
            else:
                return
        
        # Validate directory with updated settings
        validation_result = self.directory_validator.validate_path(directory)
        if not validation_result['valid']:
            # Show detailed error with more context
            error_message = f"Cannot index directory:\n{validation_result['message']}\n\n"
            
            # Add helpful context based on the error
            if "not in allowed directories" in validation_result['message']:
                error_message += "Please add this directory to your allowed list in Settings."
            elif "excluded directory" in validation_result['message']:
                error_message += "This directory is in your excluded list. Remove it from Settings to index."
            
            QMessageBox.critical(
                self,
                "Directory Access Denied",
                error_message
            )
            
            # Log the validation failure for debugging
            self.logger.warning(f"Directory validation failed: {validation_result}")
            return
        
        # Use resolved path
        directory = validation_result['resolved_path']
        
        # Save as last selected directory
        self._last_selected_directory = directory
        self.settings.setValue("last_selected_directory", directory)
        
        # Check if directory is already indexed
        if directory in self._indexed_directories:
            reply = QMessageBox.question(
                self,
                "Directory Already Indexed",
                f"The directory '{directory}' has already been indexed.\n\n"
                "Do you want to re-index it?",
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Create and start worker thread
        self._indexing_worker = IndexingWorker(
            self.file_processor,
            directory,
            self._active_file_types,
            recursive=True
        )
        
        # Connect signals
        self._indexing_worker.progress_update.connect(
            self._on_indexing_progress
        )
        self._indexing_worker.indexing_complete.connect(
            lambda result: self._on_indexing_complete(result, directory)
        )
        self._indexing_worker.indexing_error.connect(self._on_indexing_error)
        
        # Start indexing
        self._indexing_worker.start()
        
        # Update UI
        self.indexing_status.set_indexing_active(True)
        self.indexing_status.update_status(
            f"Starting to index: {directory}", "info"
        )
    
    def _cancel_indexing(self):
        """Cancel ongoing indexing operation"""
        if self._indexing_worker and self._indexing_worker.isRunning():
            self._indexing_worker.cancel()
            self._indexing_worker.wait()
            self.indexing_status.update_status("Indexing cancelled", "warning")
            self.indexing_status.set_indexing_active(False)
    
    def _on_indexing_progress(self, message: str, current: int, total: int):
        """Handle indexing progress updates"""
        self.indexing_status.update_progress(message, current, total)
    
    def _on_indexing_complete(self, result: Dict[str, Any], directory: str):
        """Handle indexing completion"""
        self.indexing_status.set_indexing_active(False)
        
        if result['success']:
            stats = result.get('stats', {})
            message = (
                f"Indexing complete! Processed: {stats.get('processed', 0)}, "
                f"Failed: {stats.get('failed', 0)}, "
                f"Skipped: {stats.get('skipped', 0)}"
            )
            self.indexing_status.update_status(message, "success")
            
            # Add to indexed directories if not already there
            if directory not in self._indexed_directories:
                self._indexed_directories.append(directory)
                self._save_indexed_directories()
            
            # Show notification if any files failed
            if stats.get('failed', 0) > 0:
                failed_files = result.get('failed_files', [])
                if failed_files:
                    details = "\n".join(failed_files[:5])  # Show first 5
                    if len(failed_files) > 5:
                        details += f"\n... and {len(failed_files) - 5} more"
                    
                    QMessageBox.warning(
                        self,
                        "Some Files Failed",
                        f"{stats['failed']} file(s) failed to index:"
                        f"\n\n{details}"
                    )
        else:
            self.indexing_status.update_status(
                f"Indexing failed: {result.get('error', 'Unknown error')}",
                "error"
            )
            QMessageBox.critical(
                self,
                "Indexing Failed",
                f"Failed to index directory:\n"
                f"{result.get('error', 'Unknown error')}"
            )
        
        # Update stats
        self._update_indexing_status()
    
    def _on_indexing_error(self, error: str):
        """Handle indexing error"""
        self.indexing_status.set_indexing_active(False)
        self.indexing_status.update_status(f"Indexing error: {error}", "error")
    
    def _update_indexing_status(self):
        """Update indexing statistics"""
        try:
            stats = self.file_processor.get_processing_stats()
            
            # Update quick stats label
            self.stats_label.setText(
                f"Files: {stats.get('total_files', 0)} | "
                f"Chunks: {stats.get('total_chunks', 0)} | "
                f"Size: {self._format_file_size(stats.get('total_size', 0))}"
            )
            
            # Update indexing status widget
            self.indexing_status.update_stats(stats)
            
        except Exception as e:
            self.logger.error(f"Failed to update stats: {str(e)}")
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size for display"""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def _load_initial_state(self):
        """Load initial state and statistics"""
        self._update_active_file_types()
        self._update_indexing_status()
    
    def _update_active_file_types(self):
        """Update the list of active file types from checkboxes"""
        self._active_file_types = []
        for label, (checkbox, extensions) in self.file_type_checkboxes.items():
            if checkbox.isChecked():
                self._active_file_types.extend(extensions)
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Ctrl+F to focus search
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.search_input.setFocus)
        
        # Escape to clear search
        escape_shortcut = QShortcut(QKeySequence("Escape"), self.search_input)
        escape_shortcut.activated.connect(self._clear_search)
    
    def _update_splitter_sizes(self):
        """Set splitter proportions based on window height"""
        total_height = self.height()
        self.content_splitter.setSizes([
            int(total_height * 0.15),  # 15% for controls
            int(total_height * 0.65),  # 65% for results
            int(total_height * 0.20)   # 20% for status
        ])
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        if hasattr(self, 'content_splitter'):
            if not hasattr(self, '_state_restored'):
                self._update_splitter_sizes()
    
    def _save_splitter_state(self):
        """Save the splitter state"""
        window_state_manager.save_splitter_from_widget(
            "file_search_content", self.content_splitter
        )
    
    def _restore_splitter_state(self):
        """Restore the splitter state"""
        window_state_manager.restore_splitter_to_widget(
            "file_search_content", self.content_splitter
        )
        self._state_restored = True
    
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes"""
        # Update any scaled elements if needed
        pass
    
    def _create_note_from_result(self, result_data: Dict[str, Any]):
        """Create a note from search result"""
        try:
            # Import here to avoid circular imports
            from ...models.note import Note
            from ...database.notes_db import NotesDatabase
            
            # Create note content with search context
            query = result_data.get('search_query', 'N/A')
            content = f"**Search Query:** {query}\n\n"
            content += f"**File:** {result_data['file_path']}\n"
            chunk_num = result_data.get('chunk_index', 0) + 1
            content += f"**Chunk:** {chunk_num}\n\n"
            content += "---\n\n"
            content += result_data['content']
            
            # Create the note
            note = Note(
                title=result_data['title'],
                content=content,
                tags=['file-search', 'imported']
            )
            
            # Save to database
            notes_db = NotesDatabase(self._current_user)
            result = notes_db.create_note(note)
            
            if result['success']:
                QMessageBox.information(
                    self,
                    "Note Created",
                    f"Note '{result_data['title']}' created successfully!"
                )
                # TODO: Switch to Notes tab and select the new note
            else:
                raise Exception(result.get('error', 'Unknown error'))
                
        except Exception as e:
            self.logger.error(f"Failed to create note: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create note: {str(e)}"
            )
    
    def _save_as_artifact(self, artifact_data: Dict[str, Any]):
        """Save search result as artifact"""
        try:
            # Import here to avoid circular imports
            from ...models.artifact import Artifact
            from ...database.artifacts_db import ArtifactsDatabase
            
            # Create artifact content with search context
            query = artifact_data.get('search_query', 'N/A')
            content = f"**Search Query:** {query}\n"
            content += f"**Score:** {artifact_data.get('score', 0):.2%}\n\n"
            content += f"**File:** {artifact_data['file_path']}\n"
            chunk_num = artifact_data.get('chunk_index', 0) + 1
            content += f"**Chunk:** {chunk_num}\n\n"
            content += "---\n\n"
            content += artifact_data['content']
            
            # Create the artifact
            artifact = Artifact(
                name=artifact_data['title'],
                description="Search result from File Search",
                content_type='text',
                content=content,
                tags=['file-search', 'imported'],
                metadata={
                    'file_path': artifact_data['file_path'],
                    'search_query': artifact_data.get('search_query'),
                    'chunk_index': artifact_data.get('chunk_index'),
                    'score': artifact_data.get('score')
                }
            )
            
            # Save to database
            artifacts_db = ArtifactsDatabase(self._current_user)
            result = artifacts_db.create_artifact(artifact)
            
            if result['success']:
                QMessageBox.information(
                    self,
                    "Artifact Created",
                    f"Artifact '{artifact_data['title']}' saved successfully!"
                )
                # TODO: Switch to Artifacts tab and select the new artifact
            else:
                raise Exception(result.get('error', 'Failed to save artifact'))
                
        except Exception as e:
            self.logger.error(f"Failed to save artifact: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save artifact: {str(e)}"
            )
    
    def _load_directory_settings(self):
        """Load directory settings from preferences and sync with database"""
        try:
            # Load allowed directories from QSettings
            allowed_dirs = self.settings.value("allowed_directories", [], list)
            excluded_dirs = self.settings.value(
                "excluded_directories", [], list
            )
            
            # Ensure we have lists
            if not isinstance(allowed_dirs, list):
                allowed_dirs = []
            if not isinstance(excluded_dirs, list):
                excluded_dirs = []
            
            # INITIALIZATION SYNC: Ensure database has the same settings
            if allowed_dirs or excluded_dirs:
                self.logger.info("Syncing directory settings to database on startup...")
                
                # Sync allowed directories to database
                if allowed_dirs:
                    result = self.file_search_db.update_search_settings(
                        "allowed_directories", allowed_dirs
                    )
                    if result['success']:
                        self.logger.info(
                            f"Synced {len(allowed_dirs)} allowed dirs to DB"
                        )
                    else:
                        self.logger.warning(
                            f"Failed to sync allowed dirs: {result.get('error')}"
                        )
                
                # Sync excluded directories to database
                if excluded_dirs:
                    result = self.file_search_db.update_search_settings(
                        "excluded_directories", excluded_dirs
                    )
                    if result['success']:
                        self.logger.info(
                            f"Synced {len(excluded_dirs)} excluded dirs to DB"
                        )
                    else:
                        self.logger.warning(
                            f"Failed to sync excluded dirs: {result.get('error')}"
                        )
            
            # Update directory validator
            if allowed_dirs:
                self.directory_validator.set_allowed_directories(allowed_dirs)
            if excluded_dirs:
                self.directory_validator.set_excluded_directories(
                    excluded_dirs
                )
            
            # Also ensure file processor has the same settings
            self.file_processor.update_settings(
                allowed_directories=allowed_dirs,
                excluded_directories=excluded_dirs
            )
            
            # Load indexed directories
            indexed_dirs = self.settings.value(
                "indexed_directories", [], list
            )
            self._indexed_directories = (
                indexed_dirs if isinstance(indexed_dirs, list) else []
            )
            
            # Load last selected directory
            last_dir = self.settings.value(
                "last_selected_directory", "", str
            )
            self._last_selected_directory = (
                last_dir if isinstance(last_dir, str) else ""
            )
            
            self.logger.info(
                f"Loaded directory settings: {len(allowed_dirs)} allowed, "
                f"{len(excluded_dirs)} excluded, "
                f"{len(self._indexed_directories)} indexed"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load directory settings: {str(e)}")
    
    def _save_indexed_directories(self):
        """Save the list of indexed directories"""
        try:
            self.settings.setValue(
                "indexed_directories", self._indexed_directories
            )
            self.settings.sync()
        except Exception as e:
            self.logger.error(f"Failed to save indexed directories: {str(e)}")
    
    def _on_directory_settings_changed(self, settings: Dict[str, List[str]]):
        """Handle directory settings changes from the settings dialog"""
        try:
            # Save settings to QSettings (for GUI persistence)
            self.settings.setValue(
                "allowed_directories",
                settings.get("allowed_directories", [])
            )
            self.settings.setValue(
                "excluded_directories",
                settings.get("excluded_directories", [])
            )
            self.settings.sync()
            
            # CRITICAL FIX: Also save to database so FileProcessor can see them
            self.logger.info("Syncing directory settings to database...")
            
            # Update allowed directories in database
            allowed_dirs = settings.get("allowed_directories", [])
            result = self.file_search_db.update_search_settings(
                "allowed_directories", allowed_dirs
            )
            if result['success']:
                self.logger.info(f"Saved {len(allowed_dirs)} allowed directories to database")
            else:
                self.logger.error(f"Failed to save allowed directories: {result.get('error')}")
            
            # Update excluded directories in database
            excluded_dirs = settings.get("excluded_directories", [])
            result = self.file_search_db.update_search_settings(
                "excluded_directories", excluded_dirs
            )
            if result['success']:
                self.logger.info(f"Saved {len(excluded_dirs)} excluded directories to database")
            else:
                self.logger.error(f"Failed to save excluded directories: {result.get('error')}")
            
            # Update validator
            self.directory_validator.set_allowed_directories(allowed_dirs)
            self.directory_validator.set_excluded_directories(excluded_dirs)
            
            # Also update the file processor's validator to reflect changes immediately
            self.file_processor.update_settings(
                allowed_directories=allowed_dirs,
                excluded_directories=excluded_dirs
            )
            
            self.logger.info("Directory settings updated and synchronized to database")
            
        except Exception as e:
            self.logger.error(f"Failed to update directory settings: {str(e)}")
            QMessageBox.critical(
                self,
                "Settings Error",
                f"Failed to save directory settings: {str(e)}"
            )
