"""
File Search Results Widget - Display search results with rich formatting
"""

import os
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QHBoxLayout, QMenu
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFontMetrics

from ...rag.vector_search import SearchResult
from ...utils.colors import DinoPitColors
from ...utils.logger import Logger
from ...utils.scaling import get_scaling_helper


class SearchResultItem(QFrame):
    """Individual search result item widget"""
    
    # Signals
    clicked = Signal(str)  # file_path
    open_requested = Signal(str)  # file_path
    copy_path_requested = Signal(str)  # file_path
    create_note_requested = Signal(dict)  # result data
    save_as_artifact_requested = Signal(dict)  # result data
    
    def __init__(self, result: SearchResult, search_query: str,
                 ref_info: Optional[dict] = None):
        super().__init__()
        self.result = result
        self.search_query = search_query
        self.file_path = result.file_path
        self.ref_info = ref_info or {}
        self._scaling_helper = get_scaling_helper()
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the result item UI"""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            SearchResultItem {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 5px;
                padding: 10px;
                margin-bottom: 5px;
            }}
            SearchResultItem:hover {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        layout = QVBoxLayout(self)
        
        # File info header
        header_layout = QHBoxLayout()
        
        # File icon and name
        file_name = os.path.basename(self.file_path)
        file_ext = os.path.splitext(file_name)[1].lower()
        
        # Simple file type emoji mapping
        file_icon = self._get_file_icon(file_ext)
        
        file_label = QLabel(f"{file_icon} {file_name}")
        file_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-weight: bold;
            font-size: 14px;
        """)
        header_layout.addWidget(file_label)
        
        # Relevance score
        score_label = QLabel(f"Score: {self.result.score:.2%}")
        score_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: 12px;
            padding: 2px 8px;
            background-color: {DinoPitColors.MAIN_BACKGROUND};
            border-radius: 10px;
        """)
        header_layout.addWidget(score_label)
        
        header_layout.addStretch()
        
        # Match type badge
        match_type = self.result.match_type.capitalize()
        match_badge = QLabel(match_type)
        match_badge.setStyleSheet(f"""
            color: white;
            font-size: 11px;
            padding: 2px 6px;
            background-color: {self._get_match_type_color()};
            border-radius: 3px;
        """)
        header_layout.addWidget(match_badge)
        
        # Add reference badge if file is referenced
        if self.ref_info:
            ref_count = len(self.ref_info.get('in_notes', [])) + \
                       len(self.ref_info.get('in_artifacts', []))
            if ref_count > 0:
                ref_badge = QLabel(f"📌 {ref_count}")
                ref_badge.setToolTip("Referenced in notes/artifacts")
                ref_badge.setStyleSheet(f"""
                    color: white;
                    font-size: 11px;
                    padding: 2px 6px;
                    background-color: {DinoPitColors.DINOPIT_ORANGE};
                    border-radius: 3px;
                """)
                header_layout.addWidget(ref_badge)
        
        layout.addLayout(header_layout)
        
        # File path
        path_label = QLabel(self.file_path)
        path_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: 12px;
        """)
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        
        # Reference info if available
        if self.ref_info:
            ref_text_parts = []
            if self.ref_info.get('in_notes'):
                ref_text_parts.append(
                    f"📝 In {len(self.ref_info['in_notes'])} notes"
                )
            if self.ref_info.get('in_artifacts'):
                ref_text_parts.append(
                    f"💎 In {len(self.ref_info['in_artifacts'])} artifacts"
                )
            
            if ref_text_parts:
                ref_label = QLabel(" • ".join(ref_text_parts))
                ref_label.setStyleSheet(f"""
                    color: {DinoPitColors.PRIMARY_TEXT};
                    font-size: 11px;
                    font-style: italic;
                """)
                layout.addWidget(ref_label)
        
        # Content snippet with highlighting
        if self.result.content:
            snippet_label = QLabel(self._format_snippet())
            snippet_label.setStyleSheet(f"""
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: 13px;
                padding: 8px;
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border-radius: 4px;
                margin-top: 5px;
            """)
            snippet_label.setWordWrap(True)
            snippet_label.setTextFormat(Qt.TextFormat.RichText)
            
            # Limit height
            font_metrics = QFontMetrics(snippet_label.font())
            max_lines = 4
            snippet_label.setMaximumHeight(
                font_metrics.lineSpacing() * max_lines + 16  # padding
            )
            
            layout.addWidget(snippet_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        open_button = QPushButton("📂 Open")
        open_button.setStyleSheet(self._get_button_style())
        open_button.clicked.connect(
            lambda: self.open_requested.emit(self.file_path)
        )
        button_layout.addWidget(open_button)
        
        copy_button = QPushButton("📋 Copy Path")
        copy_button.setStyleSheet(self._get_button_style())
        copy_button.clicked.connect(
            lambda: self.copy_path_requested.emit(self.file_path)
        )
        button_layout.addWidget(copy_button)
        
        button_layout.addStretch()
        
        # Chunk info
        chunk_info = QLabel(f"Chunk {self.result.chunk_index + 1}")
        chunk_info.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: 11px;
        """)
        button_layout.addWidget(chunk_info)
        
        layout.addLayout(button_layout)
        
    def _get_file_icon(self, extension: str) -> str:
        """Get emoji icon for file type"""
        icon_map = {
            '.pdf': '📑',
            '.docx': '📄',
            '.doc': '📄',
            '.txt': '📝',
            '.md': '📝',
            '.py': '🐍',
            '.js': '🟨',
            '.java': '☕',
            '.cpp': '⚙️',
            '.c': '⚙️',
            '.cs': '🔷',
            '.html': '🌐',
            '.css': '🎨',
            '.json': '📊',
            '.csv': '📊',
            '.xml': '📊'
        }
        return icon_map.get(extension, '📄')
    
    def _get_match_type_color(self) -> str:
        """Get color for match type badge"""
        if self.result.match_type == 'vector':
            return DinoPitColors.DINOPIT_ORANGE
        elif self.result.match_type == 'keyword':
            return DinoPitColors.DINOPIT_ORANGE
        else:  # hybrid
            return DinoPitColors.DINOPIT_FIRE
    
    def _get_button_style(self) -> str:
        """Get button stylesheet"""
        return f"""
            QPushButton {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QPushButton:pressed {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
            }}
        """
    
    def _format_snippet(self) -> str:
        """Format content snippet with search term highlighting"""
        content = self.result.content
        
        # Truncate if too long
        max_length = 300
        if len(content) > max_length:
            # Try to find a good break point
            break_point = content.rfind(' ', 0, max_length)
            if break_point > max_length * 0.8:
                content = content[:break_point] + "..."
            else:
                content = content[:max_length] + "..."
        
        # Escape HTML
        content = content.replace('&', '&amp;')
        content = content.replace('<', '&lt;')
        content = content.replace('>', '&gt;')
        
        # Highlight search terms (case-insensitive)
        if self.search_query:
            # Split query into words
            terms = self.search_query.lower().split()
            
            for term in terms:
                if len(term) > 2:  # Only highlight terms > 2 chars
                    # Case-insensitive replacement with highlighting
                    import re
                    pattern = re.compile(re.escape(term), re.IGNORECASE)
                    highlight_style = (
                        f'background-color: {DinoPitColors.DINOPIT_ORANGE}; '
                        f'color: white; padding: 1px 3px; border-radius: 2px;'
                    )
                    content = pattern.sub(
                        lambda m: f'<span style="{highlight_style}">'
                                  f'{m.group(0)}</span>',
                        content
                    )
        
        return content
    
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_path)
        super().mousePressEvent(event)
    
    def contextMenuEvent(self, event):
        """Show context menu"""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 5px;
            }}
            QMenu::item {{
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: 8px 20px;
                border-radius: 4px;
            }}
            QMenu::item:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                color: white;
            }}
        """)
        
        open_action = menu.addAction("📂 Open File")
        open_action.triggered.connect(
            lambda: self.open_requested.emit(self.file_path)
        )
        
        open_folder_action = menu.addAction("📁 Open Containing Folder")
        open_folder_action.triggered.connect(self._open_containing_folder)
        
        menu.addSeparator()
        
        copy_path_action = menu.addAction("📋 Copy Full Path")
        copy_path_action.triggered.connect(
            lambda: self.copy_path_requested.emit(self.file_path)
        )
        
        copy_name_action = menu.addAction("📝 Copy File Name")
        copy_name_action.triggered.connect(self._copy_file_name)
        
        menu.addSeparator()
        
        # Integration options
        create_note_action = menu.addAction("📝 Create Note from Result")
        create_note_action.triggered.connect(self._create_note_from_result)
        
        save_artifact_action = menu.addAction("💎 Save as Artifact")
        save_artifact_action.triggered.connect(self._save_as_artifact)
        
        menu.exec(event.globalPos())
    
    def _open_containing_folder(self):
        """Open the folder containing this file"""
        folder = os.path.dirname(self.file_path)
        try:
            os.startfile(folder)  # Windows
        except Exception:
            # Could show error or try other methods
            pass
    
    def _copy_file_name(self):
        """Copy just the file name to clipboard"""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(os.path.basename(self.file_path))
    
    def _create_note_from_result(self):
        """Create a note from this search result"""
        default_content = f"Content from: {self.file_path}"
        note_data = {
            'title': f"File: {os.path.basename(self.file_path)}",
            'content': self.result.content or default_content,
            'file_path': self.file_path,
            'chunk_index': self.result.chunk_index,
            'search_query': self.search_query
        }
        self.create_note_requested.emit(note_data)
    
    def _save_as_artifact(self):
        """Save this search result as an artifact"""
        default_content = f"Content from: {self.file_path}"
        artifact_data = {
            'title': f"Search Result: {os.path.basename(self.file_path)}",
            'content': self.result.content or default_content,
            'file_path': self.file_path,
            'chunk_index': self.result.chunk_index,
            'search_query': self.search_query,
            'score': self.result.score
        }
        self.save_as_artifact_requested.emit(artifact_data)


class FileSearchResultsWidget(QWidget):
    """Widget to display file search results"""
    
    # Signals
    file_selected = Signal(str)  # file_path
    file_open_requested = Signal(str)  # file_path
    copy_path_requested = Signal(str)  # file_path
    create_note_requested = Signal(dict)  # result data
    save_as_artifact_requested = Signal(dict)  # result data
    
    def __init__(self):
        super().__init__()
        self.logger = Logger()
        self._results: List[SearchResult] = []
        self._result_widgets: List[SearchResultItem] = []
        self._scaling_helper = get_scaling_helper()
        self._file_references: Dict[str, Dict[str, Any]] = {}
        
        self.setup_ui()
        self._load_file_references()
    
    def setup_ui(self):
        """Setup the results widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area for results
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        # Container for result items
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(5)
        
        # Empty state
        self.empty_label = QLabel("No search results")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: 16px;
            padding: 40px;
        """)
        self.results_layout.addWidget(self.empty_label)
        
        self.scroll_area.setWidget(self.results_container)
        layout.addWidget(self.scroll_area)
    
    def display_results(self, results: List[SearchResult],
                        search_query: str = "",
                        filter_referenced: bool = False):
        """Display search results
        
        Args:
            results: List of search results
            search_query: The search query string
            filter_referenced: If True, only show files referenced in
                notes/artifacts
        """
        # Clear existing results
        self.clear_results()
        
        # Filter results if needed
        if filter_referenced:
            results = [
                r for r in results
                if r.file_path in self._file_references
            ]
        
        self._results = results
        
        if not results:
            self.empty_label.show()
            if filter_referenced:
                self.empty_label.setText("No referenced files found")
            return
        
        self.empty_label.hide()
        
        # Create result widgets
        for result in results:
            # Get reference info
            ref_info = self._file_references.get(result.file_path, {})
            
            result_widget = SearchResultItem(
                result, search_query, ref_info
            )
            
            # Connect signals
            result_widget.clicked.connect(self._on_result_clicked)
            result_widget.open_requested.connect(self.file_open_requested.emit)
            result_widget.copy_path_requested.connect(
                self.copy_path_requested.emit
            )
            result_widget.create_note_requested.connect(
                self.create_note_requested.emit
            )
            result_widget.save_as_artifact_requested.connect(
                self.save_as_artifact_requested.emit
            )
            
            self._result_widgets.append(result_widget)
            self.results_layout.addWidget(result_widget)
        
        # Add stretch at end
        self.results_layout.addStretch()
    
    def clear_results(self):
        """Clear all results"""
        # Remove all result widgets
        for widget in self._result_widgets:
            widget.deleteLater()
        
        self._result_widgets.clear()
        self._results = []
        
        # Show empty state
        self.empty_label.show()
    
    def _on_result_clicked(self, file_path: str):
        """Handle result item click"""
        self.file_selected.emit(file_path)
        
        # Highlight selected item
        for widget in self._result_widgets:
            if widget.file_path == file_path:
                widget.setStyleSheet(f"""
                    SearchResultItem {{
                        background-color: {DinoPitColors.SOFT_ORANGE};
                        border: 2px solid {DinoPitColors.DINOPIT_ORANGE};
                        border-radius: 5px;
                        padding: 10px;
                        margin-bottom: 5px;
                    }}
                """)
            else:
                # Reset to normal style
                widget.setStyleSheet(f"""
                    SearchResultItem {{
                        background-color: {DinoPitColors.PANEL_BACKGROUND};
                        border: 1px solid {DinoPitColors.SOFT_ORANGE};
                        border-radius: 5px;
                        padding: 10px;
                        margin-bottom: 5px;
                    }}
                    SearchResultItem:hover {{
                        background-color: {DinoPitColors.MAIN_BACKGROUND};
                        border-color: {DinoPitColors.DINOPIT_ORANGE};
                    }}
                """)
    
    def _load_file_references(self):
        """Load information about where files are referenced"""
        try:
            # Import here to avoid circular imports
            from ...database.notes_db import NotesDatabase
            from ...database.artifacts_db import ArtifactsDatabase
            
            user = "default_user"  # TODO: Get current user
            
            # Get references from notes
            notes_db = NotesDatabase(user)
            all_notes = notes_db.get_all_notes()
            
            for note in all_notes:
                # Simple pattern to find file paths in content
                import re
                file_pattern = r'[A-Za-z]:[\\\/][\w\-_\\\/\.]+\.\w+'
                matches = re.findall(file_pattern, note.content)
                
                for file_path in matches:
                    # Normalize path
                    file_path = os.path.normpath(file_path)
                    
                    if file_path not in self._file_references:
                        self._file_references[file_path] = {
                            'in_notes': [],
                            'in_artifacts': []
                        }
                    
                    self._file_references[file_path]['in_notes'].append({
                        'note_id': note.id,
                        'note_title': note.title
                    })
            
            # Get references from artifacts
            artifacts_db = ArtifactsDatabase(user)
            # Get all artifacts using search
            all_artifacts = artifacts_db.search_artifacts(query="", limit=1000)
            
            for artifact in all_artifacts:
                # Check metadata for file references
                metadata = artifact.metadata or {}
                file_path = metadata.get('file_path')
                
                if file_path:
                    file_path = os.path.normpath(file_path)
                    
                    if file_path not in self._file_references:
                        self._file_references[file_path] = {
                            'in_notes': [],
                            'in_artifacts': []
                        }
                    
                    self._file_references[file_path]['in_artifacts'].append({
                        'artifact_id': artifact.id,
                        'artifact_name': artifact.name
                    })
                    
        except Exception as e:
            self.logger.error(f"Failed to load file references: {str(e)}")
            self._file_references = {}