"""
Help Page - Comprehensive documentation and assistance for DinoAir 2.0
"""

from typing import Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QFrame,
    QTreeWidget, QTreeWidgetItem, QLineEdit,
    QTextBrowser, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut

try:
    from src.utils.colors import DinoPitColors
    from src.utils.logger import Logger
    from src.utils.scaling import get_scaling_helper
except ImportError:
    from utils.colors import DinoPitColors
    from utils.logger import Logger
    from utils.scaling import get_scaling_helper


class CollapsibleSection(QFrame):
    """Collapsible section widget for organizing help content"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._is_expanded = True
        self._scaling_helper = get_scaling_helper()
        
        # Setup UI
        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 5px;
                margin-bottom: 5px;
            }}
        """)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        self.header_widget = QWidget()
        self.header_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px 4px 0 0;
            }}
        """)
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(10, 8, 10, 8)
        
        # Toggle button
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setFixedSize(20, 20)
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: white;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE_HOVER};
                border-radius: 2px;
            }}
        """)
        self.toggle_btn.clicked.connect(self.toggle)
        header_layout.addWidget(self.toggle_btn)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-weight: bold;
        """)
        header_layout.addWidget(self.title_label, 1)
        
        layout.addWidget(self.header_widget)
        
        # Content area
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border-radius: 0 0 4px 4px;
            }}
        """)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        
        layout.addWidget(self.content_widget)
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
    
    def toggle(self):
        """Toggle the expanded/collapsed state"""
        self._is_expanded = not self._is_expanded
        self.content_widget.setVisible(self._is_expanded)
        self.toggle_btn.setText("▼" if self._is_expanded else "▶")
    
    def add_content(self, widget: QWidget):
        """Add content to the collapsible section"""
        self.content_layout.addWidget(widget)
    
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes"""
        # Update any scaled elements if needed
        pass


class HelpPage(QWidget):
    """Help page with comprehensive documentation and assistance"""
    
    # Signals
    search_performed = Signal(str)
    topic_selected = Signal(str)
    
    def __init__(self):
        """Initialize the help page"""
        super().__init__()
        self.logger = Logger()
        self._scaling_helper = get_scaling_helper()
        self._current_topic = None
        self._search_results = []
        
        # Help content data
        self._help_content = self._initialize_help_content()
        
        self.setup_ui()
        self._load_default_content()
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
    
    def setup_ui(self):
        """Setup the help page UI"""
        layout = QVBoxLayout(self)
        
        # Use font metrics for consistent spacing
        font_metrics = self.fontMetrics()
        margin = font_metrics.height() // 2
        
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(0)
        
        # Create toolbar with search
        toolbar_container = self._create_toolbar()
        layout.addWidget(toolbar_container)
        
        # Create main content splitter
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                width: 2px;
            }}
        """)
        
        # Left panel - Table of contents
        toc_panel = self._create_toc_panel()
        self.content_splitter.addWidget(toc_panel)
        
        # Right panel - Content viewer
        content_panel = self._create_content_panel()
        self.content_splitter.addWidget(content_panel)
        
        # Set initial splitter proportions
        self.content_splitter.setSizes([300, 700])
        
        layout.addWidget(self.content_splitter)
    
    def _create_toolbar(self) -> QWidget:
        """Create the toolbar with search functionality"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        font_metrics = self.fontMetrics()
        spacing = font_metrics.height() // 4
        container_layout.setSpacing(spacing)
        
        # Header
        header = QLabel("📚 DinoAir 2.0 Help & Documentation")
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
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search help topics...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
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
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._perform_search)
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
            QPushButton:disabled {{
                background-color: #666666;
                color: #999999;
            }}
        """)
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self._clear_search)
        search_layout.addWidget(self.clear_button)
        
        container_layout.addLayout(search_layout)
        
        # Setup shortcuts
        self._setup_shortcuts()
        
        return container
    
    def _create_toc_panel(self) -> QWidget:
        """Create the table of contents panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # TOC header
        header = QLabel("Table of Contents")
        header.setStyleSheet(f"""
            background-color: {DinoPitColors.DINOPIT_ORANGE};
            color: white;
            padding: 10px;
            font-weight: bold;
            font-size: 16px;
            border-radius: 5px 5px 0 0;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # TOC tree
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderHidden(True)
        self.toc_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 0 0 5px 5px;
            }}
            QTreeWidget::item {{
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: 5px;
            }}
            QTreeWidget::item:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
            }}
            QTreeWidget::item:hover {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        
        # Populate TOC
        self._populate_toc()
        
        # Connect signals
        self.toc_tree.itemClicked.connect(self._on_toc_item_clicked)
        
        layout.addWidget(self.toc_tree)
        
        return panel
    
    def _create_content_panel(self) -> QWidget:
        """Create the content viewer panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Content header
        self.content_header = QLabel("Welcome to DinoAir 2.0 Help")
        self.content_header.setStyleSheet(f"""
            background-color: {DinoPitColors.DINOPIT_ORANGE};
            color: white;
            padding: 10px;
            font-weight: bold;
            font-size: 16px;
            border-radius: 5px 5px 0 0;
        """)
        self.content_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.content_header)
        
        # Content scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 0 0 5px 5px;
            }}
        """)
        
        # Content container
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(15)
        
        scroll_area.setWidget(self.content_container)
        layout.addWidget(scroll_area)
        
        return panel
    
    def _initialize_help_content(self) -> Dict[str, Dict]:
        """Initialize the help content structure"""
        return {
            "getting_started": {
                "title": "Getting Started",
                "icon": "🚀",
                "content": """
                    <h2>Welcome to DinoAir 2.0</h2>
                    <p>DinoAir 2.0 is a comprehensive modular note-taking application
                    with AI capabilities, designed to enhance productivity and
                    organization. This guide will help you get started
                    with all the powerful features.</p>
                    
                    <h3>First Steps</h3>
                    <ol>
                        <li><b>Configure Settings:</b> Go to the Settings tab to
                        set up your preferences and configure watchdog
                        protection</li>
                        <li><b>Choose AI Model:</b> Visit the Model tab to select
                        and download your preferred Ollama AI model</li>
                        <li><b>Create Your First Note:</b> Use the Notes tab to
                        start organizing your thoughts and ideas</li>
                        <li><b>Try the Chat:</b> Interact with AI in the Chat tab
                        for assistance and conversations</li>
                    </ol>
                    
                    <h3>Key Features</h3>
                    <ul>
                        <li><b>AI-powered chat assistance</b> - Get help and have
                        conversations with local LLMs</li>
                        <li><b>Advanced file search with RAG technology</b> - Find
                        content across your documents intelligently</li>
                        <li><b>Project and task management</b> - Organize your
                        work efficiently</li>
                        <li><b>Calendar and appointment scheduling</b> - Never miss
                        important events</li>
                        <li><b>Artifact storage and organization</b> - Keep your
                        digital assets organized</li>
                        <li><b>Pseudocode to real code translation</b> - Convert
                        ideas to working code</li>
                        <li><b>Smart timer for productivity</b> - Track time spent
                        on tasks</li>
                    </ul>
                    
                    <h3>System Requirements</h3>
                    <ul>
                        <li>Python 3.8 or higher</li>
                        <li>4GB RAM minimum (8GB recommended)</li>
                        <li>500MB storage for application</li>
                        <li>Ollama installed for AI features (optional)</li>
                    </ul>
                """
            },
            "pages": {
                "title": "Page Documentation",
                "icon": "📄",
                "subsections": {
                    "chat": {
                        "title": "Chat",
                        "content": """
                            <h3>Chat Interface</h3>
                            <p>The Chat page provides an AI-powered conversation interface using
                            local Ollama models.</p>
                            
                            <h4>Features:</h4>
                            <ul>
                                <li>Real-time AI responses with streaming</li>
                                <li>Conversation history management</li>
                                <li>Multiple AI model support</li>
                                <li>Context preservation across messages</li>
                                <li>Export chat sessions</li>
                            </ul>
                            
                            <h4>How to Use:</h4>
                            <ol>
                                <li>Ensure Ollama service is running (check Model tab)</li>
                                <li>Select your preferred model from the dropdown</li>
                                <li>Type your message in the input field</li>
                                <li>Press Enter or click Send</li>
                                <li>Wait for the AI response to stream in</li>
                                <li>Continue the conversation with context</li>
                            </ol>
                            
                            <h4>Tips:</h4>
                            <ul>
                                <li>Be specific in your questions for better responses</li>
                                <li>Use the Model tab to switch between different AI models</li>
                                <li>Clear context when starting a new topic</li>
                                <li>Save important conversations using the export feature</li>
                                <li>Adjust temperature in Model settings for creativity</li>
                            </ul>
                            
                            <h4>Code Example Request:</h4>
                            <pre>
User: Write a Python function to calculate fibonacci numbers
AI: Here's a Python function to calculate fibonacci numbers:

def fibonacci(n):
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    
    return fib

# Example usage:
# logger.debug(fibonacci(10))  # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
                            </pre>
                        """
                    },
                    "pseudocode": {
                        "title": "Pseudocode Translator",
                        "content": """
                            <h3>Pseudocode Translator</h3>
                            <p>Convert natural language pseudocode into working code in multiple programming languages.</p>
                            
                            <h4>Supported Languages:</h4>
                            <ul>
                                <li>Python</li>
                                <li>JavaScript</li>
                                <li>TypeScript</li>
                                <li>Java</li>
                                <li>C++</li>
                                <li>C#</li>
                                <li>Go</li>
                                <li>Rust</li>
                                <li>Ruby</li>
                                <li>PHP</li>
                            </ul>
                            
                            <h4>How to Use:</h4>
                            <ol>
                                <li>Enter your pseudocode in the input area</li>
                                <li>Select the target programming language</li>
                                <li>Click "Translate" or press Ctrl+Enter</li>
                                <li>Review the generated code</li>
                                <li>Copy the code to your project</li>
                            </ol>
                            
                            <h4>Example Pseudocode:</h4>
                            <pre>
function calculateArea(shape, dimensions)
    if shape is "circle" then
        return PI * dimensions.radius ^ 2
    else if shape is "rectangle" then
        return dimensions.width * dimensions.height
    else if shape is "triangle" then
        return 0.5 * dimensions.base * dimensions.height
    else
        return 0
    end if
end function
                            </pre>
                            
                            <h4>Tips:</h4>
                            <ul>
                                <li>Use clear, structured pseudocode</li>
                                <li>Define variables and their types when possible</li>
                                <li>Use consistent indentation</li>
                                <li>Include comments for complex logic</li>
                                <li>Review and adjust the generated code</li>
                            </ul>
                        """
                    },
                    "notes": {
                        "title": "Notes",
                        "content": """
                            <h3>Notes Management</h3>
                            <p>Create, organize, and search your notes efficiently with powerful features.</p>
                            
                            <h4>Features:</h4>
                            <ul>
                                <li>Rich text editing with formatting</li>
                                <li>Tag-based organization</li>
                                <li>Full-text search capabilities</li>
                                <li>Markdown support</li>
                                <li>Categories and folders</li>
                                <li>Export to various formats (PDF, HTML, Markdown)</li>
                                <li>Version history</li>
                                <li>Encryption for sensitive notes</li>
                            </ul>
                            
                            <h4>Keyboard Shortcuts:</h4>
                            <ul>
                                <li><code>Ctrl+N</code> - New note</li>
                                <li><code>Ctrl+S</code> - Save note</li>
                                <li><code>Ctrl+F</code> - Search notes</li>
                                <li><code>Ctrl+D</code> - Delete note</li>
                                <li><code>Ctrl+E</code> - Export note</li>
                                <li><code>Ctrl+Shift+T</code> - Add tag</li>
                            </ul>
                            
                            <h4>Organization Tips:</h4>
                            <ul>
                                <li>Use descriptive titles for easy searching</li>
                                <li>Apply relevant tags to group related notes</li>
                                <li>Create categories for different topics</li>
                                <li>Use markdown for structured content</li>
                                <li>Regular backups are automatically created</li>
                            </ul>
                            
                            <h4>Markdown Support:</h4>
                            <pre>
# Heading 1
## Heading 2
### Heading 3

**Bold text**
*Italic text*
`Code snippet`

- Bullet list
1. Numbered list

[Link text](https://example.com)
![Image alt text](image.jpg)
                            </pre>
                        """
                    },
                    "file_search": {
                        "title": "File Search",
                        "content": """
                            <h3>RAG-Powered File Search</h3>
                            <p>Search through your files using advanced RAG (Retrieval-Augmented Generation) technology.</p>
                            
                            <h4>Features:</h4>
                            <ul>
                                <li>Semantic search across documents</li>
                                <li>Support for multiple file types</li>
                                <li>Directory indexing and monitoring</li>
                                <li>Real-time search results</li>
                                <li>Content preview with highlighting</li>
                                <li>Smart ranking by relevance</li>
                            </ul>
                            
                            <h4>Supported File Types:</h4>
                            <ul>
                                <li><b>Documents:</b> PDF, DOCX, DOC, TXT, RTF</li>
                                <li><b>Code:</b> PY, JS, JAVA, CPP, C, CS, GO, RS, RB, PHP</li>
                                <li><b>Data:</b> CSV, JSON, XML, YAML</li>
                                <li><b>Web:</b> HTML, CSS, JSX, TSX</li>
                                <li><b>Markdown:</b> MD, MARKDOWN</li>
                            </ul>
                            
                            <h4>Search Modes:</h4>
                            <ul>
                                <li><b>Hybrid:</b> Combines semantic and keyword search for best results</li>
                                <li><b>Semantic:</b> Understands meaning and context</li>
                                <li><b>Keyword:</b> Traditional text matching</li>
                            </ul>
                            
                            <h4>How to Use:</h4>
                            <ol>
                                <li>Click "Add Directory" to index folders</li>
                                <li>Wait for indexing to complete</li>
                                <li>Enter your search query</li>
                                <li>Select search mode (Hybrid recommended)</li>
                                <li>Click Search or press Enter</li>
                                <li>Click on results to view file content</li>
                            </ol>
                            
                            <h4>Advanced Search Tips:</h4>
                            <ul>
                                <li>Use natural language queries</li>
                                <li>Be specific about what you're looking for</li>
                                <li>Try different search modes for different needs</li>
                                <li>Use filters to narrow results by file type</li>
                                <li>Re-index directories after major changes</li>
                            </ul>
                        """
                    },
                    "projects": {
                        "title": "Projects",
                        "content": """
                            <h3>Project Management</h3>
                            <p>Organize your work into projects and track tasks efficiently.</p>
                            
                            <h4>Features:</h4>
                            <ul>
                                <li>Create and manage multiple projects</li>
                                <li>Task tracking with status indicators</li>
                                <li>Project timelines and deadlines</li>
                                <li>Resource allocation</li>
                                <li>Progress visualization</li>
                                <li>Team collaboration notes</li>
                                <li>Export project reports</li>
                            </ul>
                            
                            <h4>Task States:</h4>
                            <ul>
                                <li>📋 <b>To Do</b> - Not started yet</li>
                                <li>🚀 <b>In Progress</b> - Currently working on</li>
                                <li>✅ <b>Completed</b> - Task finished</li>
                                <li>⏸️ <b>On Hold</b> - Temporarily paused</li>
                                <li>❌ <b>Cancelled</b> - No longer needed</li>
                            </ul>
                            
                            <h4>How to Use:</h4>
                            <ol>
                                <li>Click "New Project" to create a project</li>
                                <li>Add project details and description</li>
                                <li>Create tasks within the project</li>
                                <li>Assign priorities and deadlines</li>
                                <li>Update task status as you progress</li>
                                <li>Monitor overall project progress</li>
                            </ol>
                            
                            <h4>Best Practices:</h4>
                            <ul>
                                <li>Break large projects into smaller tasks</li>
                                <li>Set realistic deadlines</li>
                                <li>Update task status regularly</li>
                                <li>Use tags to categorize tasks</li>
                                <li>Review project progress weekly</li>
                                <li>Archive completed projects</li>
                            </ul>
                        """
                    },
                    "appointments": {
                        "title": "Appointments",
                        "content": """
                            <h3>Calendar & Appointments</h3>
                            <p>Manage your schedule with the integrated calendar system.</p>
                            
                            <h4>Features:</h4>
                            <ul>
                                <li>Interactive calendar view</li>
                                <li>Quick event creation</li>
                                <li>Event reminders and notifications</li>
                                <li>Recurring events support</li>
                                <li>Event categories and colors</li>
                                <li>Day, week, and month views</li>
                                <li>Export to standard calendar formats</li>
                            </ul>
                            
                            <h4>Event Types:</h4>
                            <ul>
                                <li>🏢 <b>Appointments</b> - Professional meetings</li>
                                <li>👥 <b>Meetings</b> - Team collaborations</li>
                                <li>📋 <b>Tasks</b> - Time-bound activities</li>
                                <li>🔔 <b>Reminders</b> - Important notifications</li>
                                <li>🎉 <b>Personal</b> - Non-work events</li>
                            </ul>
                            
                            <h4>Quick Add Syntax:</h4>
                            <pre>
Examples of natural language input:
- "Meeting with John at 2pm tomorrow"
- "Lunch at noon on Friday"
- "Project deadline next Monday"
- "Call client at 3:30pm"
- "Team standup every day at 9am"
                            </pre>
                            
                            <h4>Keyboard Shortcuts:</h4>
                            <ul>
                                <li><code>Ctrl+Shift+N</code> - New event</li>
                                <li><code>T</code> - Go to today</li>
                                <li><code>D/W/M</code> - Switch to Day/Week/Month view</li>
                                <li><code>Arrow Keys</code> - Navigate dates</li>
                                <li><code>Delete</code> - Delete selected event</li>
                            </ul>
                            
                            <h4>Tips:</h4>
                            <ul>
                                <li>Set reminders for important events</li>
                                <li>Use colors to categorize events</li>
                                <li>Double-click on a date to create event</li>
                                <li>Drag events to reschedule</li>
                                <li>Export calendar for backup</li>
                            </ul>
                        """
                    },
                    "artifacts": {
                        "title": "Artifacts",
                        "content": """
                            <h3>Artifact Storage</h3>
                            <p>Store and organize various types of content as artifacts.</p>
                            
                            <h4>Artifact Types:</h4>
                            <ul>
                                <li>📄 <b>Text documents</b> - Notes, drafts, templates</li>
                                <li>💻 <b>Code snippets</b> - Reusable code blocks</li>
                                <li>🖼️ <b>Images</b> - Screenshots, diagrams</li>
                                <li>📋 <b>Documents</b> - PDFs, Word files</li>
                                <li>📦 <b>Binary files</b> - Executables, archives</li>
                                <li>🔗 <b>Links</b> - Web bookmarks</li>
                            </ul>
                            
                            <h4>Features:</h4>
                            <ul>
                                <li>Collections for organization</li>
                                <li>Version history tracking</li>
                                <li>Encryption support for sensitive data</li>
                                <li>Tag-based categorization</li>
                                <li>Quick search and filtering</li>
                                <li>Export and sharing options</li>
                                <li>Automatic backups</li>
                            </ul>
                            
                            <h4>How to Use:</h4>
                            <ol>
                                <li>Click "New Artifact" to create</li>
                                <li>Choose the artifact type</li>
                                <li>Add content or upload file</li>
                                <li>Apply tags and categories</li>
                                <li>Set encryption if needed</li>
                                <li>Save to a collection</li>
                            </ol>
                            
                            <h4>Security Features:</h4>
                            <ul>
                                <li>AES-256 encryption for sensitive artifacts</li>
                                <li>Password protection</li>
                                <li>Secure deletion</li>
                                <li>Access logs</li>
                                <li>Automatic lock after inactivity</li>
                            </ul>
                            
                            <h4>Best Practices:</h4>
                            <ul>
                                <li>Use descriptive names</li>
                                <li>Organize into logical collections</li>
                                <li>Tag consistently</li>
                                <li>Enable encryption for sensitive data</li>
                                <li>Regular cleanup of old artifacts</li>
                            </ul>
                        """
                    },
                    "smart_timer": {
                        "title": "Smart Timer",
                        "content": """
                            <h3>Smart Timer</h3>
                            <p>Track time spent on tasks with the intelligent timer system.</p>
                            
                            <h4>Features:</h4>
                            <ul>
                                <li>Multiple named timers</li>
                                <li>Session logging and history</li>
                                <li>Automatic repeats</li>
                                <li>Time statistics and reports</li>
                                <li>Pomodoro technique support</li>
                                <li>Break reminders</li>
                                <li>Export time logs</li>
                            </ul>
                            
                            <h4>Timer Controls:</h4>
                            <ul>
                                <li>▶️ <b>Start/Pause</b> - Begin or pause timer</li>
                                <li>⏹️ <b>Stop</b> - Stop and save session</li>
                                <li>🔄 <b>Reset</b> - Clear current time</li>
                                <li>🗑️ <b>Delete</b> - Remove timer</li>
                            </ul>
                            
                            <h4>Pomodoro Technique:</h4>
                            <ol>
                                <li>Work for 25 minutes</li>
                                <li>Take a 5-minute break</li>
                                <li>Repeat 4 times</li>
                                <li>Take a longer 15-30 minute break</li>
                            </ol>
                            
                            <h4>Productivity Tips:</h4>
                            <ul>
                                <li>Track different activities separately</li>
                                <li>Set goals for daily work time</li>
                                <li>Review time logs weekly</li>
                                <li>Identify time-wasting activities</li>
                                <li>Use breaks to prevent burnout</li>
                                <li>Export reports for analysis</li>
                            </ul>
                            
                            <h4>Statistics Available:</h4>
                            <ul>
                                <li>Total time per task</li>
                                <li>Daily/weekly/monthly summaries</li>
                                <li>Average session duration</li>
                                <li>Most productive times</li>
                                <li>Break compliance</li>
                            </ul>
                        """
                    },
                    "model": {
                        "title": "Model",
                        "content": """
                            <h3>AI Model Selection</h3>
                            <p>Configure and manage AI models for various features.</p>
                            
                            <h4>Supported Models (via Ollama):</h4>
                            <ul>
                                <li><b>Llama 3.2:</b> Fast and efficient, good for general tasks</li>
                                <li><b>Mistral:</b> Balanced performance and quality</li>
                                <li><b>Gemma 2:</b> Google's efficient model</li>
                                <li><b>Qwen 2.5:</b> Excellent multilingual support</li>
                                <li><b>Phi 3:</b> Microsoft's compact model</li>
                                <li><b>Custom Models:</b> Load your own fine-tuned models</li>
                            </ul>
                            
                            <h4>Ollama Integration:</h4>
                            <ul>
                                <li>Automatic service management</li>
                                <li>Model downloading with progress</li>
                                <li>Performance monitoring</li>
                                <li>Custom model support</li>
                                <li>Resource usage tracking</li>
                            </ul>
                            
                            <h4>Configuration Options:</h4>
                            <ul>
                                <li><b>Temperature:</b> Controls creativity (0.0-2.0)</li>
                                <li><b>Max Tokens:</b> Response length limit</li>
                                <li><b>Top-p:</b> Nucleus sampling parameter</li>
                                <li><b>Top-k:</b> Limits vocabulary choices</li>
                                <li><b>Context Window:</b> Memory for conversations</li>
                            </ul>
                            
                            <h4>How to Download Models:</h4>
                            <ol>
                                <li>Ensure Ollama service is running</li>
                                <li>Enter model name (e.g., "llama3.2:1b")</li>
                                <li>Click Download or use command interface</li>
                                <li>Monitor download progress</li>
                                <li>Model auto-selects when ready</li>
                            </ol>
                            
                            <h4>Command Examples:</h4>
                            <pre>
ollama pull llama3.2:1b     # Download small model
ollama pull mistral:7b      # Download medium model
ollama list                 # List installed models
ollama rm modelname         # Remove a model
                            </pre>
                        """
                    },
                    "settings": {
                        "title": "Settings",
                        "content": """
                            <h3>Application Settings</h3>
                            <p>Customize DinoAir 2.0 to match your preferences.</p>
                            
                            <h4>Settings Categories:</h4>
                            
                            <h5>🐕 Watchdog Settings</h5>
                            <ul>
                                <li><b>Auto-Start:</b> Enable watchdog on startup</li>
                                <li><b>VRAM Threshold:</b> Set warning level (0-100%)</li>
                                <li><b>Max Processes:</b> Limit DinoAir instances</li>
                                <li><b>Check Interval:</b> Monitoring frequency</li>
                                <li><b>Emergency Shutdown:</b> Auto-terminate on critical</li>
                            </ul>
                            
                            <h5>🔍 File Search Settings</h5>
                            <ul>
                                <li><b>Max File Size:</b> Indexing limit (MB)</li>
                                <li><b>Chunk Size:</b> Text splitting size</li>
                                <li><b>Auto-Indexing:</b> Monitor file changes</li>
                                <li><b>File Types:</b> Include/exclude extensions</li>
                                <li><b>Directory Limits:</b> Access controls</li>
                            </ul>
                            
                            <h4>Watchdog Protection:</h4>
                            <p>The watchdog monitors system resources to prevent issues:</p>
                            <ul>
                                <li>Tracks VRAM usage to prevent GPU overload</li>
                                <li>Monitors process count</li>
                                <li>Prevents memory leaks</li>
                                <li>Auto-terminates on critical issues</li>
                                <li>Logs all actions for review</li>
                            </ul>
                            
                            <h4>Keyboard Shortcuts:</h4>
                            <ul>
                                <li><code>Ctrl+,</code> - Open settings</li>
                                <li><code>Ctrl+S</code> - Save settings</li>
                                <li><code>Ctrl+R</code> - Reset to defaults</li>
                            </ul>
                            
                            <h4>Tips:</h4>
                            <ul>
                                <li>Enable watchdog for stability</li>
                                <li>Set VRAM threshold based on your GPU</li>
                                <li>Exclude large binary files from search</li>
                                <li>Regular backups are recommended</li>
                            </ul>
                        """
                    }
                }
            },
            "keyboard_shortcuts": {
                "title": "Keyboard Shortcuts",
                "icon": "⌨️",
                "content": """
                    <h2>Keyboard Shortcuts</h2>
                    
                    <h3>Global Shortcuts</h3>
                    <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
                        <tr style="background-color: #FF9500; color: white;">
                            <th>Shortcut</th>
                            <th>Action</th>
                        </tr>
                        <tr>
                            <td><code>Ctrl+N</code></td>
                            <td>New (context-dependent)</td>
                        </tr>
                        <tr>
                            <td><code>Ctrl+S</code></td>
                            <td>Save current item</td>
                        </tr>
                        <tr>
                            <td><code>Ctrl+F</code></td>
                            <td>Search/Find</td>
                        </tr>
                        <tr>
                            <td><code>Ctrl+Shift+F</code></td>
                            <td>Open File Search</td>
                        </tr>
                        <tr>
                            <td><code>Delete</code></td>
                            <td>Delete selected item</td>
                        </tr>
                        <tr>
                            <td><code>F5</code></td>
                            <td>Refresh current view</td>
                        </tr>
                        <tr>
                            <td><code>Escape</code></td>
                            <td>Cancel/Close dialog</td>
                        </tr>
                    </table>
                    
                    <h3>Zoom Controls</h3>
                    <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
                        <tr style="background-color: #FF9500; color: white;">
                            <th>Shortcut</th>
                            <th>Action</th>
                        </tr>
                        <tr>
                            <td><code>Ctrl++</code></td>
                            <td>Zoom In</td>
                        </tr>
                        <tr>
                            <td><code>Ctrl+-</code></td>
                            <td>Zoom Out</td>
                        </tr>
                        <tr>
                            <td><code>Ctrl+0</code></td>
                            <td>Reset Zoom</td>
                        </tr>
                    </table>
                    
                    <h3>Navigation</h3>
                    <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
                        <tr style="background-color: #FF9500; color: white;">
                            <th>Shortcut</th>
                            <th>Action</th>
                        </tr>
                        <tr>
                            <td><code>Ctrl+Tab</code></td>
                            <td>Next tab</td>
                        </tr>
                        <tr>
                            <td><code>Ctrl+Shift+Tab</code></td>
                            <td>Previous tab</td>
                        </tr>
                        <tr>
                            <td><code>Alt+[1-9]</code></td>
                            <td>Go to tab N</td>
                        </tr>
                        <tr>
                            <td><code>Ctrl+,</code></td>
                            <td>Open Settings</td>
                        </tr>
                        <tr>
                            <td><code>F1</code></td>
                            <td>Open Help</td>
                        </tr>
                    </table>
                    
                    <h3>Page-Specific Shortcuts</h3>
                    
                    <h4>Notes Page</h4>
                    <ul>
                        <li><code>Ctrl+N</code> - New note</li>
                        <li><code>Ctrl+E</code> - Export note</li>
                        <li><code>Ctrl+Shift+T</code> - Add tag</li>
                    </ul>
                    
                    <h4>Appointments Page</h4>
                    <ul>
                        <li><code>Ctrl+Shift+N</code> - New event</li>
                        <li><code>T</code> - Go to today</li>
                        <li><code>D/W/M</code> - Day/Week/Month view</li>
                    </ul>
                    
                    <h4>Pseudocode Translator</h4>
                    <ul>
                        <li><code>Ctrl+Enter</code> - Translate code</li>
                        <li><code>Ctrl+Shift+C</code> - Copy output</li>
                    </ul>
                """
            },
            "troubleshooting": {
                "title": "Troubleshooting",
                "icon": "🔧",
                "content": """
                    <h2>Troubleshooting Guide</h2>
                    
                    <h3>Common Issues</h3>
                    
                    <h4>Ollama Service Not Starting</h4>
                    <p><b>Problem:</b> The Ollama service fails to start automatically.</p>
                    <p><b>Solutions:</b></p>
                    <ol>
                        <li>Check if Ollama is installed: <code>ollama --version</code></li>
                        <li>Start manually: <code>ollama serve</code></li>
                        <li>Check firewall settings for port 11434</li>
                        <li>Verify PATH environment variable includes Ollama</li>
                        <li>Try running as administrator (Windows)</li>
                    </ol>
                    
                    <h4>File Search Not Finding Documents</h4>
                    <p><b>Problem:</b> File search returns no results even for known content.</p>
                    <p><b>Solutions:</b></p>
                    <ol>
                        <li>Ensure directories are properly indexed</li>
                        <li>Check file type filters in settings</li>
                        <li>Verify directory permissions</li>
                        <li>Re-index directories: Settings > File Search > Re-index</li>
                        <li>Check if files exceed size limit</li>
                    </ol>
                    
                    <h4>High Memory Usage</h4>
                    <p><b>Problem:</b> Application uses excessive memory.</p>
                    <p><b>Solutions:</b></p>
                    <ol>
                        <li>Enable Watchdog in Settings</li>
                        <li>Close unused tabs</li>
                        <li>Clear chat history periodically</li>
                        <li>Reduce file search index size</li>
                        <li>Restart the application</li>
                        <li>Check for memory leaks in logs</li>
                    </ol>
                    
                    <h4>AI Model Not Responding</h4>
                    <p><b>Problem:</b> Chat or translation features don't generate responses.</p>
                    <p><b>Solutions:</b></p>
                    <ol>
                        <li>Check if model is downloaded</li>
                        <li>Verify Ollama service is running</li>
                        <li>Try a different model</li>
                        <li>Check system resources (RAM/VRAM)</li>
                        <li>Restart Ollama service</li>
                    </ol>
                    
                    <h4>Database Errors</h4>
                    <p><b>Problem:</b> Database connection or corruption issues.</p>
                    <p><b>Solutions:</b></p>
                    <ol>
                        <li>Check database file permissions</li>
                        <li>Use Settings > Database > Repair</li>
                        <li>Restore from automatic backup</li>
                        <li>Delete cache files in database folder</li>
                        <li>Reinstall if corruption persists</li>
                    </ol>
                    
                    <h4>Application Won't Start</h4>
                    <p><b>Problem:</b> DinoAir fails to launch.</p>
                    <p><b>Solutions:</b></p>
                    <ol>
                        <li>Check Python version (3.8+ required)</li>
                        <li>Verify all dependencies: <code>pip install -r requirements.txt</code></li>
                        <li>Delete config folder and restart</li>
                        <li>Check for port conflicts</li>
                        <li>Run in debug mode: <code>python main.py --debug</code></li>
                    </ol>
                    
                    <h3>Log Files</h3>
                    <p>Logs are stored in:</p>
                    <ul>
                        <li><b>Windows:</b> <code>%APPDATA%/DinoAir/logs/</code></li>
                        <li><b>macOS:</b> <code>~/Library/Application Support/DinoAir/logs/</code></li>
                        <li><b>Linux:</b> <code>~/.config/DinoAir/logs/</code></li>
                    </ul>
                    
                    <h3>Getting Help</h3>
                    <ul>
                        <li>Check the documentation first</li>
                        <li>Review log files for error messages</li>
                        <li>Submit issues on GitHub with logs</li>
                        <li>Include system information</li>
                    </ul>
                """
            },
            "about": {
                "title": "About DinoAir 2.0",
                "icon": "ℹ️",
                "content": """
                    <h2>About DinoAir 2.0</h2>
                    
                    <p><b>Version:</b> 2.0.0</p>
                    <p><b>Build Date:</b> January 2025</p>
                    <p><b>Developer:</b> DinoPit Studios</p>
                    <p><b>License:</b> MIT License with Ethical Use Clause</p>
                    
                    <h3>What's New in 2.0</h3>
                    <ul>
                        <li>Complete UI redesign with horizontal tabs</li>
                        <li>Enhanced AI integration with Ollama</li>
                        <li>RAG-powered file search capabilities</li>
                        <li>Improved project management features</li>
                        <li>Advanced security with watchdog protection</li>
                        <li>Better performance and stability</li>
                        <li>New pseudocode translator with 10+ languages</li>
                        <li>Smart timer with productivity tracking</li>
                    </ul>
                    
                    <h3>System Requirements</h3>
                    <ul>
                        <li><b>OS:</b> Windows 10/11, macOS 10.15+, Linux</li>
                        <li><b>Python:</b> 3.8 or higher</li>
                        <li><b>RAM:</b> 4GB minimum, 8GB recommended</li>
                        <li><b>Storage:</b> 500MB for application + data</li>
                        <li><b>GPU:</b> Optional, improves AI performance</li>
                    </ul>
                    
                    <h3>Technologies Used</h3>
                    <ul>
                        <li><b>Framework:</b> PySide6 (Qt for Python)</li>
                        <li><b>Database:</b> SQLite for local storage</li>
                        <li><b>AI Backend:</b> Ollama for LLM integration</li>
                        <li><b>Vector DB:</b> ChromaDB for semantic search</li>
                        <li><b>Languages:</b> Python, SQL</li>
                    </ul>
                    
                    <h3>Credits & Acknowledgments</h3>
                    <p>DinoAir 2.0 is built with the following open-source libraries:</p>
                    <ul>
                        <li>PySide6 - Qt bindings for Python</li>
                        <li>SQLite - Embedded database</li>
                        <li>Ollama - Local LLM runtime</li>
                        <li>ChromaDB - Vector database</li>
                        <li>LangChain - AI application framework</li>
                        <li>And many other amazing open-source projects</li>
                    </ul>
                    
                    <h3>Privacy & Security</h3>
                    <ul>
                        <li>All data stored locally</li>
                        <li>No cloud dependencies</li>
                        <li>AI models run on your machine</li>
                        <li>Encryption for sensitive data</li>
                        <li>Open source for transparency</li>
                    </ul>
                    
                    <h3>Support & Contact</h3>
                    <ul>
                        <li><b>GitHub:</b> <a href="#">github.com/dinopit/dinoair</a></li>
                        <li><b>Documentation:</b> <a href="#">docs.dinoair.com</a></li>
                        <li><b>Email:</b> support@dinopitstudios.com</li>
                        <li><b>Discord:</b> <a href="#">Join our community</a></li>
                    </ul>
                    
                    <h3>Legal</h3>
                    <p>DinoAir 2.0 is released under the MIT License with an Ethical Use Clause.
                    This software is provided "as is" without warranty of any kind.</p>
                    
                    <p><i>Thank you for using DinoAir 2.0!</i></p>
                """
            }
        }
    
    def _populate_toc(self):
        """Populate the table of contents tree"""
        self.toc_tree.clear()
        
        for key, section in self._help_content.items():
            # Create top-level item
            icon = section.get("icon", "📄")
            title = section.get("title", "Unknown")
            item = QTreeWidgetItem([f"{icon} {title}"])
            item.setData(0, Qt.ItemDataRole.UserRole, key)
            
            # Add subsections if they exist
            if "subsections" in section:
                for sub_key, subsection in section["subsections"].items():
                    sub_title = subsection.get("title", "Unknown")
                    sub_item = QTreeWidgetItem([f"  • {sub_title}"])
                    sub_item.setData(0, Qt.ItemDataRole.UserRole, f"{key}.{sub_key}")
                    item.addChild(sub_item)
            
            self.toc_tree.addTopLevelItem(item)
        
        # Expand all items by default
        self.toc_tree.expandAll()
    
    def _load_default_content(self):
        """Load the default help content"""
        self._load_content("getting_started")
    
    def _load_content(self, topic_key: str):
        """Load content for a specific topic"""
        # Clear existing content
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Parse topic key
        parts = topic_key.split(".")
        if len(parts) == 1:
            # Top-level section
            section = self._help_content.get(parts[0], {})
            content_html = section.get("content", "")
            title = section.get("title", "Unknown Topic")
        else:
            # Subsection
            section = self._help_content.get(parts[0], {})
            subsection = section.get("subsections", {}).get(parts[1], {})
            content_html = subsection.get("content", "")
            title = subsection.get("title", "Unknown Topic")
        
        # Update header
        self.content_header.setText(title)
        
        # Create content widget
        if content_html:
            content_browser = QTextBrowser()
            content_browser.setOpenExternalLinks(True)
            content_browser.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: transparent;
                    border: none;
                    color: {DinoPitColors.PRIMARY_TEXT};
                }}
                QTextBrowser h2 {{
                    color: {DinoPitColors.DINOPIT_ORANGE};
                }}
                QTextBrowser h3 {{
                    color: {DinoPitColors.SOFT_ORANGE};
                }}
                QTextBrowser h4 {{
                    color: {DinoPitColors.STUDIOS_CYAN};
                }}
                QTextBrowser h5 {{
                    color: {DinoPitColors.SECONDARY_TEXT};
                }}
                QTextBrowser pre {{
                    background-color: {DinoPitColors.PANEL_BACKGROUND};
                    padding: 10px;
                    border-radius: 5px;
                    font-family: 'Consolas', 'Monaco', monospace;
                }}
                QTextBrowser code {{
                    background-color: {DinoPitColors.PANEL_BACKGROUND};
                    padding: 2px 4px;
                    border-radius: 3px;
                    font-family: 'Consolas', 'Monaco', monospace;
                }}
                QTextBrowser table {{
                    border-collapse: collapse;
                    margin: 10px 0;
                }}
                QTextBrowser th, QTextBrowser td {{
                    border: 1px solid {DinoPitColors.SOFT_ORANGE};
                    padding: 8px;
                    text-align: left;
                }}
                QTextBrowser th {{
                    background-color: {DinoPitColors.SOFT_ORANGE};
                    font-weight: bold;
                }}
            """)
            content_browser.setHtml(content_html)
            self.content_layout.addWidget(content_browser)
        else:
            # No content found
            no_content_label = QLabel("No content available for this topic.")
            no_content_label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT};")
            no_content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(no_content_label)
        
        # Add stretch to push content to top
        self.content_layout.addStretch()
        
        # Update current topic
        self._current_topic = topic_key
        self.topic_selected.emit(title)
    
    def _on_toc_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle TOC item click"""
        topic_key = item.data(0, Qt.ItemDataRole.UserRole)
        if topic_key:
            self._load_content(topic_key)
    
    def _on_search_text_changed(self, text: str):
        """Handle search text changes"""
        self.clear_button.setEnabled(bool(text))
    
    def _perform_search(self):
        """Perform search across help content"""
        query = self.search_input.text().strip().lower()
        if not query:
            return
        
        # Clear current content
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Update header
        self.content_header.setText(f"Search Results for '{query}'")
        
        # Search through all content
        results = []
        for key, section in self._help_content.items():
            # Search in main section
            title = section.get("title", "").lower()
            content = section.get("content", "").lower()
            
            if query in title or query in content:
                results.append({
                    "key": key,
                    "title": section.get("title", "Unknown"),
                    "type": "section",
                    "relevance": 2 if query in title else 1
                })
            
            # Search in subsections
            if "subsections" in section:
                for sub_key, subsection in section["subsections"].items():
                    sub_title = subsection.get("title", "").lower()
                    sub_content = subsection.get("content", "").lower()
                    
                    if query in sub_title or query in sub_content:
                        results.append({
                            "key": f"{key}.{sub_key}",
                            "title": subsection.get("title", "Unknown"),
                            "type": "subsection",
                            "relevance": 2 if query in sub_title else 1
                        })
        
        # Sort by relevance
        results.sort(key=lambda x: x["relevance"], reverse=True)
        
        # Display results
        if results:
            results_label = QLabel(f"Found {len(results)} result(s):")
            results_label.setStyleSheet(f"""
                color: {DinoPitColors.PRIMARY_TEXT};
                font-weight: bold;
                margin-bottom: 10px;
            """)
            self.content_layout.addWidget(results_label)
            
            for result in results:
                # Create clickable result item
                result_btn = QPushButton(f"📄 {result['title']}")
                result_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {DinoPitColors.PANEL_BACKGROUND};
                        color: {DinoPitColors.PRIMARY_TEXT};
                        border: 1px solid {DinoPitColors.SOFT_ORANGE};
                        border-radius: 5px;
                        padding: 10px;
                        text-align: left;
                        font-size: 14px;
                    }}
                    QPushButton:hover {{
                        background-color: {DinoPitColors.SOFT_ORANGE};
                        color: white;
                    }}
                """)
                
                # Connect to load content
                result_key = result["key"]
                result_btn.clicked.connect(lambda checked, k=result_key: self._load_content(k))
                
                self.content_layout.addWidget(result_btn)
        else:
            no_results_label = QLabel("No results found.")
            no_results_label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT};")
            no_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(no_results_label)
        
        self.content_layout.addStretch()
        
        # Emit search signal
        self.search_performed.emit(query)
    
    def _clear_search(self):
        """Clear search and return to default content"""
        self.search_input.clear()
        self.clear_button.setEnabled(False)
        self._load_default_content()
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Ctrl+F to focus search
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.search_input.setFocus)
        
        # Escape to clear search
        escape_shortcut = QShortcut(QKeySequence("Escape"), self.search_input)
        escape_shortcut.activated.connect(self._clear_search)
    
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes"""
        # Update any scaled elements if needed
        pass