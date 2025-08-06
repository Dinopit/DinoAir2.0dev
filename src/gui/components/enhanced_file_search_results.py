"""
Enhanced File Search Results Widget with animations and improved UX
"""

import os
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QHBoxLayout, QMenu,
    QGraphicsOpacityEffect, QToolTip
)
from PySide6.QtCore import (
    Signal, Qt, QPropertyAnimation, QEasingCurve,
    QParallelAnimationGroup, QSequentialAnimationGroup,
    QTimer, QPoint, QRect
)
from PySide6.QtGui import (
    QFontMetrics, QPainter, QPixmap, QKeyEvent,
    QEnterEvent, QCursor
)

from ...rag.vector_search import SearchResult
from ...utils.colors import DinoPitColors
from ...utils.logger import Logger
from ...utils.scaling import get_scaling_helper


class AnimatedSearchResultItem(QFrame):
    """Search result item with animations and enhanced tooltips"""
    
    # Signals
    clicked = Signal(str)  # file_path
    open_requested = Signal(str)  # file_path
    copy_path_requested = Signal(str)  # file_path
    create_note_requested = Signal(dict)  # result data
    save_as_artifact_requested = Signal(dict)  # result data
    
    def __init__(self, result: SearchResult, search_query: str,
                 ref_info: Optional[dict] = None, index: int = 0):
        super().__init__()
        self.result = result
        self.search_query = search_query
        self.file_path = result.file_path
        self.ref_info = ref_info or {}
        self.index = index  # For staggered animations
        self._scaling_helper = get_scaling_helper()
        self._is_hovered = False
        self._is_selected = False
        
        # Animation components
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)
        
        self.setup_ui()
        self.setup_animations()
        self.setup_tooltips()
        
        # Start entrance animation
        QTimer.singleShot(50 * index, self.animate_in)
    
    def setup_ui(self):
        """Setup the result item UI with enhanced styling"""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._update_style()
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # File info header with animations
        header_layout = QHBoxLayout()
        
        # File icon and name
        file_name = os.path.basename(self.file_path)
        file_ext = os.path.splitext(file_name)[1].lower()
        file_icon = self._get_file_icon(file_ext)
        
        self.file_label = QLabel(f"{file_icon} {file_name}")
        self.file_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-weight: bold;
            font-size: 14px;
        """)
        header_layout.addWidget(self.file_label)
        
        # Animated relevance score
        self.score_label = QLabel(f"Score: {self.result.score:.2%}")
        self.score_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: 12px;
            padding: 2px 8px;
            background-color: {DinoPitColors.MAIN_BACKGROUND};
            border-radius: 10px;
        """)
        header_layout.addWidget(self.score_label)
        
        header_layout.addStretch()
        
        # Match type badge with tooltip
        match_type = self.result.match_type.capitalize()
        self.match_badge = QLabel(match_type)
        self.match_badge.setStyleSheet(f"""
            color: white;
            font-size: 11px;
            padding: 2px 6px;
            background-color: {self._get_match_type_color()};
            border-radius: 3px;
        """)
        header_layout.addWidget(self.match_badge)
        
        # Reference badge with enhanced tooltip
        if self.ref_info:
            ref_count = len(self.ref_info.get('in_notes', [])) + \
                       len(self.ref_info.get('in_artifacts', []))
            if ref_count > 0:
                self.ref_badge = QLabel(f"📌 {ref_count}")
                self.ref_badge.setCursor(Qt.CursorShape.WhatsThisCursor)
                self.ref_badge.setStyleSheet(f"""
                    color: white;
                    font-size: 11px;
                    padding: 2px 6px;
                    background-color: {DinoPitColors.DINOPIT_ORANGE};
                    border-radius: 3px;
                """)
                header_layout.addWidget(self.ref_badge)
        
        layout.addLayout(header_layout)
        
        # File path with ellipsis
        self.path_label = QLabel(self._elide_path(self.file_path))
        self.path_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: 12px;
        """)
        self.path_label.setWordWrap(False)
        layout.addWidget(self.path_label)
        
        # Content snippet with highlighting
        if self.result.content:
            self.snippet_label = QLabel(self._format_snippet())
            self.snippet_label.setStyleSheet(f"""
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: 13px;
                padding: 8px;
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border-radius: 4px;
                margin-top: 5px;
            """)
            self.snippet_label.setWordWrap(True)
            self.snippet_label.setTextFormat(Qt.TextFormat.RichText)
            
            # Limit height
            font_metrics = QFontMetrics(self.snippet_label.font())
            max_lines = 4
            self.snippet_label.setMaximumHeight(
                font_metrics.lineSpacing() * max_lines + 16
            )
            
            layout.addWidget(self.snippet_label)
        
        # Action buttons with hover effects
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.open_button = self._create_animated_button("📂 Open", "Open file in default application")
        self.open_button.clicked.connect(
            lambda: self.open_requested.emit(self.file_path)
        )
        button_layout.addWidget(self.open_button)
        
        self.copy_button = self._create_animated_button("📋 Copy Path", "Copy full file path to clipboard")
        self.copy_button.clicked.connect(
            lambda: self.copy_path_requested.emit(self.file_path)
        )
        button_layout.addWidget(self.copy_button)
        
        button_layout.addStretch()
        
        # Chunk info
        self.chunk_info = QLabel(f"Chunk {self.result.chunk_index + 1}")
        self.chunk_info.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: 11px;
        """)
        self.chunk_info.setToolTip(
            f"This is chunk {self.result.chunk_index + 1} of the file\n"
            f"Position: {self.result.start_pos}-{self.result.end_pos}"
        )
        button_layout.addWidget(self.chunk_info)
        
        layout.addLayout(button_layout)
    
    def setup_animations(self):
        """Setup animation effects"""
        # Fade in animation
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Hover animation
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def setup_tooltips(self):
        """Setup comprehensive tooltips"""
        # Main widget tooltip
        self.setToolTip(
            f"<b>{os.path.basename(self.file_path)}</b><br>"
            f"<i>{self.file_path}</i><br><br>"
            f"<b>Relevance:</b> {self.result.score:.1%}<br>"
            f"<b>Match Type:</b> {self.result.match_type}<br>"
            f"<b>File Type:</b> {self.result.file_type or 'Unknown'}<br><br>"
            f"<i>Click to select • Right-click for more options</i>"
        )
        
        # Score tooltip
        self.score_label.setToolTip(
            f"Relevance score: {self.result.score:.1%}<br>"
            f"Higher scores indicate better matches<br><br>"
            f"<b>Score Breakdown:</b><br>"
            f"⭐⭐⭐⭐⭐ 90-100% Excellent<br>"
            f"⭐⭐⭐⭐ 70-89% Good<br>"
            f"⭐⭐⭐ 50-69% Fair<br>"
            f"⭐⭐ 30-49% Weak"
        )
        
        # Match type tooltip
        match_descriptions = {
            'vector': 'Semantic similarity based on meaning',
            'keyword': 'Exact keyword matches found',
            'hybrid': 'Combined semantic and keyword matching'
        }
        self.match_badge.setToolTip(
            f"<b>{self.result.match_type.capitalize()} Match</b><br>"
            f"{match_descriptions.get(self.result.match_type, '')}"
        )
        
        # Reference badge tooltip
        if hasattr(self, 'ref_badge'):
            ref_details = []
            if self.ref_info.get('in_notes'):
                ref_details.append(f"📝 Referenced in {len(self.ref_info['in_notes'])} notes")
            if self.ref_info.get('in_artifacts'):
                ref_details.append(f"💎 Referenced in {len(self.ref_info['in_artifacts'])} artifacts")
            
            self.ref_badge.setToolTip(
                "<b>File References</b><br>" + 
                "<br>".join(ref_details) +
                "<br><br><i>This file is linked to other content</i>"
            )
    
    def _create_animated_button(self, text: str, tooltip: str) -> QPushButton:
        """Create a button with hover animations"""
        button = QPushButton(text)
        button.setStyleSheet("color: #FFFFFF;")
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(self._get_button_style())
        
        # Add hover effect
        button.installEventFilter(self)
        
        return button
    
    def _get_file_icon(self, extension: str) -> str:
        """Get emoji icon for file type"""
        icon_map = {
            '.pdf': '📑', '.docx': '📄', '.doc': '📄',
            '.txt': '📝', '.md': '📝', '.py': '🐍',
            '.js': '🟨', '.java': '☕', '.cpp': '⚙️',
            '.c': '⚙️', '.cs': '🔷', '.html': '🌐',
            '.css': '🎨', '.json': '📊', '.csv': '📊',
            '.xml': '📊', '.zip': '📦', '.rar': '📦'
        }
        return icon_map.get(extension, '📄')
    
    def _elide_path(self, path: str, max_width: int = 400) -> str:
        """Elide long paths with ellipsis"""
        metrics = QFontMetrics(self.path_label.font() if hasattr(self, 'path_label') else self.font())
        return metrics.elidedText(path, Qt.TextElideMode.ElideMiddle, max_width)
    
    def _format_snippet(self) -> str:
        """Format content snippet with search term highlighting"""
        content = self.result.content
        
        # Truncate if too long
        max_length = 300
        if len(content) > max_length:
            break_point = content.rfind(' ', 0, max_length)
            if break_point > max_length * 0.8:
                content = content[:break_point] + "..."
            else:
                content = content[:max_length] + "..."
        
        # Escape HTML
        content = content.replace('&', '&amp;')
        content = content.replace('<', '&lt;')
        content = content.replace('>', '&gt;')
        
        # Highlight search terms with animation-ready spans
        if self.search_query:
            terms = self.search_query.lower().split()
            
            for term in terms:
                if len(term) > 2:
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
    
    def _get_match_type_color(self) -> str:
        """Get color for match type badge"""
        colors = {
            'vector': DinoPitColors.PRIMARY_TEXT,
            'keyword': DinoPitColors.DINOPIT_ORANGE,
            'hybrid': DinoPitColors.DINOPIT_FIRE
        }
        return colors.get(self.result.match_type, DinoPitColors.SOFT_ORANGE)
    
    def _get_button_style(self) -> str:
        """Get animated button stylesheet"""
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
    
    def _update_style(self):
        """Update widget style based on state"""
        if self._is_selected:
            border_color = DinoPitColors.DINOPIT_ORANGE
            bg_color = DinoPitColors.SOFT_ORANGE
            border_width = 2
        elif self._is_hovered:
            border_color = DinoPitColors.DINOPIT_ORANGE
            bg_color = DinoPitColors.MAIN_BACKGROUND
            border_width = 1
        else:
            border_color = DinoPitColors.SOFT_ORANGE
            bg_color = DinoPitColors.PANEL_BACKGROUND
            border_width = 1
        
        self.setStyleSheet(f"""
            AnimatedSearchResultItem {{
                background-color: {bg_color};
                border: {border_width}px solid {border_color};
                border-radius: 5px;
                padding: 10px;
                margin-bottom: 5px;
            }}
        """)
    
    def animate_in(self):
        """Animate the widget entrance"""
        self.fade_in.start()
    
    def enterEvent(self, event: QEnterEvent):
        """Handle mouse enter with animation"""
        self._is_hovered = True
        self._update_style()
        
        # Subtle scale animation
        current_geo = self.geometry()
        expanded = current_geo.adjusted(-2, -2, 2, 2)
        self.hover_animation.setStartValue(current_geo)
        self.hover_animation.setEndValue(expanded)
        self.hover_animation.start()
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave with animation"""
        self._is_hovered = False
        self._update_style()
        
        # Return to normal size
        current_geo = self.geometry()
        normal = current_geo.adjusted(2, 2, -2, -2)
        self.hover_animation.setStartValue(current_geo)
        self.hover_animation.setEndValue(normal)
        self.hover_animation.start()
        
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_path)
        super().mousePressEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard navigation"""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Space:
            self.clicked.emit(self.file_path)
        elif event.key() == Qt.Key.Key_O and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.open_requested.emit(self.file_path)
        elif event.key() == Qt.Key.Key_C and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.copy_path_requested.emit(self.file_path)
        else:
            super().keyPressEvent(event)
    
    def set_selected(self, selected: bool):
        """Set selection state with animation"""
        self._is_selected = selected
        self._update_style()
        
        # Pulse animation for selection
        if selected:
            pulse = QPropertyAnimation(self.opacity_effect, b"opacity")
            pulse.setDuration(200)
            pulse.setStartValue(0.7)
            pulse.setEndValue(1.0)
            pulse.setEasingCurve(QEasingCurve.Type.InOutQuad)
            pulse.start()
    
    def contextMenuEvent(self, event):
        """Show enhanced context menu"""
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
            QMenu::separator {{
                height: 1px;
                background-color: {DinoPitColors.SOFT_ORANGE};
                margin: 5px 0;
            }}
        """)
        
        # Actions with tooltips
        open_action = menu.addAction("📂 Open File")
        open_action.setToolTip("Open file in default application")
        open_action.triggered.connect(
            lambda: self.open_requested.emit(self.file_path)
        )
        
        open_folder_action = menu.addAction("📁 Open Containing Folder")
        open_folder_action.setToolTip("Open the folder containing this file")
        open_folder_action.triggered.connect(self._open_containing_folder)
        
        menu.addSeparator()
        
        copy_path_action = menu.addAction("📋 Copy Full Path")
        copy_path_action.setToolTip("Copy the complete file path")
        copy_path_action.triggered.connect(
            lambda: self.copy_path_requested.emit(self.file_path)
        )
        
        copy_name_action = menu.addAction("📝 Copy File Name")
        copy_name_action.setToolTip("Copy just the file name")
        copy_name_action.triggered.connect(self._copy_file_name)
        
        menu.addSeparator()
        
        create_note_action = menu.addAction("📝 Create Note from Result")
        create_note_action.setToolTip("Create a new note with this content")
        create_note_action.triggered.connect(self._create_note_from_result)
        
        save_artifact_action = menu.addAction("💎 Save as Artifact")
        save_artifact_action.setToolTip("Save this result as an artifact")
        save_artifact_action.triggered.connect(self._save_as_artifact)
        
        # Show menu with fade animation
        menu.setWindowOpacity(0)
        menu.show()
        
        fade_in = QPropertyAnimation(menu, b"windowOpacity")
        fade_in.setDuration(150)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)
        fade_in.start()
        
        menu.exec(event.globalPos())
    
    def _open_containing_folder(self):
        """Open the folder containing this file"""
        folder = os.path.dirname(self.file_path)
        try:
            os.startfile(folder)  # Windows
        except Exception:
            pass
    
    def _copy_file_name(self):
        """Copy just the file name to clipboard"""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(os.path.basename(self.file_path))
        
        # Show tooltip confirmation
        QToolTip.showText(
            QCursor.pos(),
            "✓ File name copied!",
            self,
            self.rect(),
            2000
        )
    
    def _create_note_from_result(self):
        """Create a note from this search result"""
        note_data = {
            'title': f"File: {os.path.basename(self.file_path)}",
            'content': self.result.content,
            'file_path': self.file_path,
            'chunk_index': self.result.chunk_index,
            'search_query': self.search_query
        }
        self.create_note_requested.emit(note_data)
    
    def _save_as_artifact(self):
        """Save this search result as an artifact"""
        artifact_data = {
            'title': f"Search Result: {os.path.basename(self.file_path)}",
            'content': self.result.content,
            'file_path': self.file_path,
            'chunk_index': self.result.chunk_index,
            'search_query': self.search_query,
            'score': self.result.score
        }
        self.save_as_artifact_requested.emit(artifact_data)


class EnhancedFileSearchResultsWidget(QWidget):
    """Enhanced widget to display file search results with animations"""
    
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
        self._result_widgets: List[AnimatedSearchResultItem] = []
        self._selected_index = -1
        self._scaling_helper = get_scaling_helper()
        self._file_references: Dict[str, Dict[str, Any]] = {}
        
        self.setup_ui()
        self._load_file_references()
        
        # Enable keyboard navigation
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def setup_ui(self):
        """Setup the enhanced results widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area with custom styling
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
        
        # Empty state with illustration
        self.empty_widget = self._create_empty_state()
        self.results_layout.addWidget(self.empty_widget)
        
        self.scroll_area.setWidget(self.results_container)
        layout.addWidget(self.scroll_area)
    
    def _create_empty_state(self) -> QWidget:
        """Create an illustrated empty state"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Simple illustration using emojis
        illustration = QLabel("🔍")
        illustration.setStyleSheet("""
            font-size: 64px;
            color: #CCCCCC;
        """)
        illustration.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(illustration)
        
        # Empty state text
        self.empty_label = QLabel("No search results")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: 16px;
            padding: 20px;
        """)
        layout.addWidget(self.empty_label)
        
        # Helpful tip
        tip_label = QLabel("Try adjusting your search terms or filters")
        tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-size: 12px;
            font-style: italic;
        """)
        layout.addWidget(tip_label)
        
        return widget
    
    def display_results(self, results: List[SearchResult],
                        search_query: str = "",
                        filter_referenced: bool = False):
        """Display search results with staggered animations"""
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
            self.empty_widget.show()
            if filter_referenced:
                self.empty_label.setText("No referenced files found")
            return
        
        self.empty_widget.hide()
        
        # Create result widgets with staggered animations
        for i, result in enumerate(results):
            ref_info = self._file_references.get(result.file_path, {})
            
            result_widget = AnimatedSearchResultItem(
                result, search_query, ref_info, i
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
        
        # Select first result
        if self._result_widgets:
            self._selected_index = 0
            self._result_widgets[0].set_selected(True)
            self._result_widgets[0].setFocus()
    
    def clear_results(self):
        """Clear all results with fade out animation"""
        # Animate out existing widgets
        for widget in self._result_widgets:
            fade_out = QPropertyAnimation(
                widget.graphicsEffect(), b"opacity"
            )
            fade_out.setDuration(150)
            fade_out.setStartValue(1)
            fade_out.setEndValue(0)
            fade_out.finished.connect(widget.deleteLater)
            fade_out.start()
        
        self._result_widgets.clear()
        self._results = []
        self._selected_index = -1
        
        # Show empty state
        self.empty_widget.show()
    
    def _on_result_clicked(self, file_path: str):
        """Handle result item click"""
        self.file_selected.emit(file_path)
        
        # Update selection
        for i, widget in enumerate(self._result_widgets):
            if widget.file_path == file_path:
                self._selected_index = i
                widget.set_selected(True)
                widget.setFocus()
            else:
                widget.set_selected(False)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard navigation"""
        if not self._result_widgets:
            super().keyPressEvent(event)
            return
        
        if event.key() == Qt.Key.Key_Down:
            # Move selection down
            if self._selected_index < len(self._result_widgets) - 1:
                self._selected_index += 1
                self._update_selection()
        
        elif event.key() == Qt.Key.Key_Up:
            # Move selection up
            if self._selected_index > 0:
                self._selected_index -= 1
                self._update_selection()
        
        elif event.key() == Qt.Key.Key_Home:
            # Jump to first
            self._selected_index = 0
            self._update_selection()
        
        elif event.key() == Qt.Key.Key_End:
            # Jump to last
            self._selected_index = len(self._result_widgets) - 1
            self._update_selection()
        
        else:
            super().keyPressEvent(event)
    
    def _update_selection(self):
        """Update visual selection and ensure visibility"""
        for i, widget in enumerate(self._result_widgets):
            widget.set_selected(i == self._selected_index)
            
            if i == self._selected_index:
                widget.setFocus()
                # Ensure visible in scroll area
                self.scroll_area.ensureWidgetVisible(widget)
                # Emit selection signal
                self.file_selected.emit(widget.file_path)
    
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
    
    def get_allowed_directories(self) -> List[str]:
        """Stub method for compatibility"""
        return []
    
    def get_excluded_directories(self) -> List[str]:
        """Stub method for compatibility"""
        return []