"""
Model Page - Ollama LLM interface for DinoAir 2.0
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QComboBox, QLabel, QProgressBar, QGroupBox,
    QSlider, QSpinBox, QTabWidget, QMenu,
    QLineEdit, QScrollArea, QFrame, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QObject
from PySide6.QtGui import QFont, QTextCursor

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Import the Ollama wrapper first (critical for ModelPage functionality)
try:
    from src.agents.ollama_wrapper import (
        OllamaWrapper, OllamaStatus, ChatMessage, GenerationResponse
    )
    OLLAMA_AVAILABLE = True
except ImportError as e:
    OLLAMA_AVAILABLE = False
    OllamaWrapper = None
    OllamaStatus = None
    ChatMessage = None
    GenerationResponse = None
    logger.error(f"[ModelPage] Ollama wrapper import failed: {e}")

# Import the Agent System separately; it's optional for basic wrapper use
try:
    from src.agents.ollama_agent import OllamaAgent, create_ollama_agent
    from src.agents.agent_manager import (
        get_agent_manager, initialize_agent_system, sync_chat_with_agent
    )
    from src.tools.basic_tools import AVAILABLE_TOOLS
    AGENT_SYSTEM_AVAILABLE = True
except ImportError as e:
    AGENT_SYSTEM_AVAILABLE = False
    OllamaAgent = None
    create_ollama_agent = None
    get_agent_manager = None
    initialize_agent_system = None
    sync_chat_with_agent = None
    AVAILABLE_TOOLS = {}
    logger.warning(f"[ModelPage] Agent system import failed, continuing with wrapper only: {e}")


class ModelDownloadThread(QThread):
    """Thread for downloading models without blocking UI"""
    progress = Signal(int, float, float, str)  # percent, downloaded_gb, total_gb, status
    finished = Signal(bool, str)  # success, error_message
    
    def __init__(self, wrapper, model_name):
        super().__init__()
        self.wrapper = wrapper
        self.model_name = model_name
        
    def run(self):
        """Run the model download"""
        try:
            def progress_callback(downloaded, total, status):
                # Calculate percentage to avoid integer overflow
                percent = 0
                if total > 0:
                    percent = min(100, int((downloaded / total) * 100))
                
                # Convert to GB for display
                downloaded_gb = downloaded / (1024 * 1024 * 1024)
                total_gb = total / (1024 * 1024 * 1024)
                
                self.progress.emit(percent, downloaded_gb, total_gb, status)
            
            # Use pull_model for consistency with Ollama CLI
            success = self.wrapper.pull_model(
                self.model_name,
                progress_callback=progress_callback
            )
            
            if success:
                self.finished.emit(True, "")
            else:
                self.finished.emit(False, "Download failed")
                
        except ConnectionError as e:
            logger.error(f"Model download failed - connection error: {e}")
            self.finished.emit(False, "Connection error. Please check your internet connection and try again.")
        except TimeoutError as e:
            logger.error(f"Model download failed - timeout: {e}")
            self.finished.emit(False, "Download timed out. The model may be large or server busy.")
        except Exception as e:
            logger.error(f"Model download failed: {e}", exc_info=True)
            self.finished.emit(False, f"Unexpected error: {str(e)}")


class GenerationThread(QThread):
    """Thread for text generation without blocking UI"""
    text_chunk = Signal(str)  # streaming text chunks
    finished = Signal(bool, str)  # success, error_message
    
    def __init__(self, wrapper, mode, prompt_or_messages,
                 model=None, **kwargs):
        super().__init__()
        self.wrapper = wrapper
        self.mode = mode  # 'generate' or 'chat'
        self.prompt_or_messages = prompt_or_messages
        self.model = model
        self.kwargs = kwargs
        self._stop_requested = False
    
    def stop(self):
        """Request the thread to stop"""
        self._stop_requested = True
        
    def run(self):
        """Run the generation"""
        try:
            if self.mode == 'generate':
                # Streaming generation
                for chunk in self.wrapper.stream_generate(
                    self.prompt_or_messages, 
                    model=self.model,
                    **self.kwargs
                ):
                    if self._stop_requested:
                        break
                    self.text_chunk.emit(chunk)
            else:  # chat mode
                # Streaming chat
                for chunk in self.wrapper.stream_chat(
                    self.prompt_or_messages,
                    model=self.model,
                    use_context=True,
                    **self.kwargs
                ):
                    if self._stop_requested:
                        break
                    self.text_chunk.emit(chunk)
                    
            self.finished.emit(True, "")
            
        except ConnectionError as e:
            logger.error(f"Text generation failed - connection error: {e}")
            self.finished.emit(False, "Connection error. Please check Ollama service status.")
        except TimeoutError as e:
            logger.error(f"Text generation failed - timeout: {e}")
            self.finished.emit(False, "Generation timed out. The model may be too large or busy.")
        except Exception as e:
            logger.error(f"Text generation failed: {e}", exc_info=True)
            self.finished.emit(False, f"Unexpected error: {str(e)}")


class ChatMessageWidget(QFrame):
    """Widget for displaying a single chat message"""
    
    def __init__(self, message: str, is_user: bool = True):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.NoFrame)  # Remove frame for cleaner look
        self.message = message  # Store original message
        self.is_user = is_user
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)  # More padding for readability
        layout.setSpacing(8)  # More space between role and message
        
        # Role label
        role_label = QLabel("User" if is_user else "Assistant")
        role_font = QFont()
        role_font.setBold(True)
        role_font.setPointSize(10)  # Slightly smaller role text
        role_label.setFont(role_font)
        
        # Message text
        self.message_text = QLabel(message)
        self.message_text.setWordWrap(True)
        self.message_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        
        # Set message font for better readability
        message_font = QFont()
        message_font.setPointSize(11)  # Slightly larger message text
        self.message_text.setFont(message_font)
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Style based on role with softer borders and shadows
        if is_user:
            self.setStyleSheet("""
                ChatMessageWidget {
                    background-color: #e8f4fd;
                    border: none;
                    border-radius: 8px;
                    margin: 4px 8px;
                }
                QLabel {
                    color: #1a1a1a;
                    background-color: transparent;
                    padding: 2px;
                }
            """)
            role_label.setStyleSheet("color: #1565c0;")
        else:
            self.setStyleSheet("""
                ChatMessageWidget {
                    background-color: #f5f0f8;
                    border: none;
                    border-radius: 8px;
                    margin: 4px 8px;
                }
                QLabel {
                    color: #1a1a1a;
                    background-color: transparent;
                    padding: 2px;
                }
            """)
            role_label.setStyleSheet("color: #6a1b9a;")
        
        layout.addWidget(role_label)
        layout.addWidget(self.message_text)
    
    def update_message(self, message: str):
        """Update the message text"""
        self.message = message
        self.message_text.setText(message)
    
    def _show_context_menu(self, position):
        """Show context menu for message actions"""
        menu = QMenu(self)
        
        # Copy action
        copy_action = menu.addAction("Copy Message")
        copy_action.triggered.connect(self._copy_message)
        
        # Copy as markdown
        copy_md_action = menu.addAction("Copy as Markdown")
        copy_md_action.triggered.connect(self._copy_as_markdown)
        
        menu.exec(self.mapToGlobal(position))
    
    def _copy_message(self):
        """Copy message to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.message)
    
    def _copy_as_markdown(self):
        """Copy message as markdown"""
        clipboard = QApplication.clipboard()
        role = "**User:**" if self.is_user else "**Assistant:**"
        clipboard.setText(f"{role}\n{self.message}")


class ModelPage(QWidget):
    """Model page widget for Ollama integration"""
    
    # Signal emitted when a model is selected
    model_selected = Signal(str)
    
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window  # Reference to MainWindow for agent registry
        self.ollama_wrapper = None
        self.agent = None
        self.download_thread = None
        self.generation_thread = None
        self.status_timer = None
        
        # Initialize wrapper (independent of optional Agent System)
        if OllamaWrapper is not None:
            try:
                self.ollama_wrapper = OllamaWrapper()
                logger.info("[ModelPage] OllamaWrapper initialized successfully")
            except Exception as e:
                logger.error(f"[ModelPage] Failed to initialize OllamaWrapper: {e}", exc_info=True)
        
        # Initialize agent system
        self.agent_manager = None
        self.agent_initialized = False
        if AGENT_SYSTEM_AVAILABLE and get_agent_manager:
            try:
                self.agent_manager = get_agent_manager()
                logger.info("[ModelPage] Agent manager obtained")
                # Initialize in background thread to avoid blocking UI
                self._initialize_agent_system()
            except ImportError as e:
                logger.error(f"[ModelPage] Agent system not available: {e}")
                # Update UI to show fallback mode
                QTimer.singleShot(100, lambda: self._on_agent_status_change("failed"))
            except Exception as e:
                logger.error(f"[ModelPage] Failed to get agent manager: {e}", exc_info=True)
                # Update UI to show fallback mode
                QTimer.singleShot(100, lambda: self._on_agent_status_change("failed"))
                
        self.setup_ui()
        
        # Start status checking timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_service_status)
        self.status_timer.start(10000)  # Check every 10 seconds (was 5)
        
        # Initial status check and auto-start attempt
        self._initial_service_check()
        
        # Notify main window that model page is ready
        self._notify_ready()
    
    def _notify_ready(self):
        """Notify main window that model page is ready for signal connections"""
        if (self.main_window and
            hasattr(self.main_window, '_check_and_setup_signals')):
            # Use QTimer to ensure this happens after full initialization
            QTimer.singleShot(200, self.main_window._check_and_setup_signals)
    
    def update_agent_with_tools(self, tool_registry):
        """Update existing agent with newly available tool registry.
        
        This method is called by MainWindow when tool_registry becomes available
        after the GUI has been created, ensuring existing agents get access to tools.
        
        Args:
            tool_registry: The ToolRegistry instance
        """
        try:
            logger.info(f"[ModelPage] Updating agent with tool registry: {tool_registry is not None}")
            
            # If we have an existing agent, we need to recreate it with the tool registry
            # since BaseAgent creates ToolAIAdapter during initialization
            if self.agent and tool_registry:
                current_model = self.agent.get_current_model() if hasattr(self.agent, 'get_current_model') else None
                if current_model:
                    logger.info(f"[ModelPage] Recreating agent with model '{current_model}' and tool registry")
                    
                    # Clear the old agent registration
                    if self.main_window:
                        self.main_window.register_agent('current', None)
                    
                    # Create new agent with tool registry
                    self.agent = OllamaAgent(
                        ollama_wrapper=self.ollama_wrapper,
                        model_name=current_model,
                        tool_registry=tool_registry  # Now we have the tool registry!
                    )
                    
                    # Initialize the new agent in background
                    import asyncio
                    import threading
                    
                    def init_new_agent():
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        try:
                            success = loop.run_until_complete(self.agent.initialize())
                            if success:
                                logger.info("[ModelPage] Agent recreated with tools successfully")
                                # Register the new agent with MainWindow
                                if self.main_window:
                                    self.main_window.register_agent('current', self.agent)
                                    logger.info("[ModelPage] New agent registered with MainWindow")
                                
                                # Update tools status display
                                tool_count = len(tool_registry.list_tools())
                                QTimer.singleShot(0, lambda: self._update_tools_status(tool_count))
                            else:
                                logger.error("[ModelPage] Failed to initialize new agent with tools")
                        except Exception as e:
                            logger.error(f"[ModelPage] New agent initialization failed: {e}")
                    
                    # Run in background thread
                    thread = threading.Thread(target=init_new_agent, daemon=True)
                    thread.start()
                else:
                    logger.warning("[ModelPage] Cannot recreate agent - no current model")
            else:
                logger.info("[ModelPage] No existing agent to update or no tool registry provided")
                
        except Exception as e:
            logger.error(f"[ModelPage] Error updating agent with tools: {e}")
    
    def _initialize_agent_system(self):
        """Initialize the agent system in background"""
        import asyncio
        import threading
        
        def init_thread():
            try:
                # Create new event loop for this thread (proper isolation)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Initialize agent system
                    success = loop.run_until_complete(initialize_agent_system())
                    
                    if success:
                        # Create Ollama agent
                        agent_created = loop.run_until_complete(
                            self.agent_manager.create_ollama_agent(
                                name="main_ollama",
                                model_name=None  # Will be set when user selects model
                            )
                        )
                    
                        if agent_created:
                            self.agent_initialized = True
                            logger.info("[ModelPage] Agent system initialized successfully")
                            
                            # Add status callback
                            self.agent_manager.add_status_callback(self._on_agent_status_change)
                        else:
                            logger.error("[ModelPage] Failed to create Ollama agent")
                    else:
                        logger.error("[ModelPage] Failed to initialize agent system")
                        
                finally:
                    # Always clean up the event loop
                    loop.close()
                    
            except ImportError as e:
                logger.error(f"[ModelPage] Agent system dependencies missing: {e}")
                QTimer.singleShot(0, lambda: self._on_agent_status_change("failed"))
            except ConnectionError as e:
                logger.error(f"[ModelPage] Failed to connect to agent services: {e}")
                QTimer.singleShot(0, lambda: self._on_agent_status_change("failed"))
            except Exception as e:
                logger.error(f"[ModelPage] Agent initialization failed: {e}", exc_info=True)
                QTimer.singleShot(0, lambda: self._on_agent_status_change("failed"))
        
        # Start initialization in background thread with timeout
        thread = threading.Thread(target=init_thread, daemon=True)
        thread.start()
        
        # Set a timeout to ensure we don't get stuck
        def check_init_timeout():
            if not self.agent_initialized and hasattr(self, 'tools_status_label'):
                if self.tools_status_label.text() == "🔧 Tools: Initializing...":
                    logger.warning("[ModelPage] Agent initialization timed out, falling back to wrapper mode")
                    self._on_agent_status_change("timeout")
        
        QTimer.singleShot(10000, check_init_timeout)  # 10 second timeout
    
    def _on_agent_status_change(self, status: str):
        """Handle agent status changes"""
        logger.info(f"[ModelPage] Agent status: {status}")
        
        # Update tools status indicator
        if hasattr(self, 'tools_status_label'):
            if self.agent_initialized:
                if self.agent_manager and self.agent_manager.is_service_ready():
                    # Get tool info
                    tool_info = self.agent_manager.get_tool_info()
                    if 'statistics' in tool_info:
                        total_tools = tool_info['statistics'].get('total_tools', 0)
                        enabled_tools = tool_info['statistics'].get('enabled_tools', 0)
                        
                        self.tools_status_label.setText(f"🔧 Tools: {enabled_tools}/{total_tools} available")
                        self.tools_status_label.setStyleSheet("""
                            QLabel {
                                background-color: #d4edda;
                                border: 1px solid #c3e6cb;
                                padding: 5px 10px;
                                border-radius: 5px;
                                font-size: 12px;
                                color: #155724;
                            }
                        """)
                    else:
                        self.tools_status_label.setText("🔧 Tools: Ready (basic)")
                        self.tools_status_label.setStyleSheet("""
                            QLabel {
                                background-color: #d4edda;
                                border: 1px solid #c3e6cb;
                                padding: 5px 10px;
                                border-radius: 5px;
                                font-size: 12px;
                                color: #155724;
                            }
                        """)
                else:
                    self.tools_status_label.setText("🔧 Tools: Service not ready")
                    self.tools_status_label.setStyleSheet("""
                        QLabel {
                            background-color: #f8d7da;
                            border: 1px solid #f5c6cb;
                            padding: 5px 10px;
                            border-radius: 5px;
                            font-size: 12px;
                            color: #721c24;
                        }
                    """)
            else:
                self.tools_status_label.setText("🔧 Tools: No tools (fallback mode)")
                self.tools_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #fff3cd;
                        border: 1px solid #ffeaa7;
                        padding: 5px 10px;
                        border-radius: 5px;
                        font-size: 12px;
                        color: #856404;
                    }
                """)
        
    def setup_ui(self):
        """Setup the model page UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Ollama Model Interface")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Service status bar
        status_layout = QHBoxLayout()
        
        # Status indicator
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: red; font-size: 20px;")
        status_layout.addWidget(self.status_dot)
        
        self.status_label = QLabel("Service Status: Checking...")
        status_layout.addWidget(self.status_label)
        
        self.start_service_btn = QPushButton("Start Service")
        self.start_service_btn.clicked.connect(self._start_service)
        self.start_service_btn.setVisible(False)
        status_layout.addWidget(self.start_service_btn)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Tools status
        tools_layout = QHBoxLayout()
        self.tools_status_label = QLabel("🔧 Tools: Initializing...")
        self.tools_status_label.setStyleSheet("""
            QLabel {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 12px;
                color: #856404;
            }
        """)
        tools_layout.addWidget(self.tools_status_label)
        tools_layout.addStretch()
        layout.addLayout(tools_layout)
        
        # Model management section
        model_group = QGroupBox("Model Management")
        model_layout = QVBoxLayout(model_group)
        
        # Model selection
        model_select_layout = QHBoxLayout()
        model_select_layout.addWidget(QLabel("Current Model:"))
        
        self.model_combo = QComboBox()
        self.model_combo.setPlaceholderText("Select a model...")
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_select_layout.addWidget(self.model_combo)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_models)
        refresh_btn.setToolTip("Refresh the model list")
        model_select_layout.addWidget(refresh_btn)
        
        model_layout.addLayout(model_select_layout)
        
        # Model download
        download_layout = QHBoxLayout()
        download_layout.addWidget(QLabel("Download Model:"))
        
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("e.g., llama3.2, mistral")
        download_layout.addWidget(self.model_input)
        
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self._download_model)
        download_layout.addWidget(self.download_btn)
        
        model_layout.addLayout(download_layout)
        
        # Command interface
        command_layout = QVBoxLayout()
        command_label = QLabel("Ollama Command:")
        command_label.setToolTip(
            "Enter Ollama commands:\n"
            "• ollama run <model> - Download and run model\n"
            "• ollama pull <model> - Download model\n"
            "• ollama rm <model> - Remove model\n"
            "• ollama list - List all models"
        )
        command_layout.addWidget(command_label)
        
        command_input_layout = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("e.g., ollama run qwen3:4b")
        self.command_input.returnPressed.connect(self._execute_command)
        command_input_layout.addWidget(self.command_input)
        
        self.execute_btn = QPushButton("Execute")
        self.execute_btn.clicked.connect(self._execute_command)
        command_input_layout.addWidget(self.execute_btn)
        
        command_layout.addLayout(command_input_layout)
        model_layout.addLayout(command_layout)
        
        # Download progress
        self.download_progress = QProgressBar()
        self.download_progress.setVisible(False)
        model_layout.addWidget(self.download_progress)
        
        self.download_status = QLabel("")
        self.download_status.setVisible(False)
        self.download_status.setStyleSheet("")  # Reset style
        model_layout.addWidget(self.download_status)
        
        layout.addWidget(model_group)
        
        # Model management is the primary focus of this page
        # Chat functionality is handled by the main chat tab
        
        # Optional: Keep generation tab for direct model testing
        self.generation_widget = self._create_generation_tab()
        layout.addWidget(self.generation_widget)
        
        # Settings panel
        settings_group = QGroupBox("Generation Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # Temperature
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperature:"))
        
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 200)  # 0.0 to 2.0
        self.temp_slider.setValue(70)  # 0.7
        self.temp_slider.valueChanged.connect(self._update_temp_label)
        temp_layout.addWidget(self.temp_slider)
        
        self.temp_label = QLabel("0.7")
        temp_layout.addWidget(self.temp_label)
        
        settings_layout.addLayout(temp_layout)
        
        # Max tokens
        tokens_layout = QHBoxLayout()
        tokens_layout.addWidget(QLabel("Max Tokens:"))
        
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(50, 8192)
        self.max_tokens_spin.setValue(2048)
        self.max_tokens_spin.setSingleStep(50)
        tokens_layout.addWidget(self.max_tokens_spin)
        
        settings_layout.addLayout(tokens_layout)
        
        # Top-p
        top_p_layout = QHBoxLayout()
        top_p_layout.addWidget(QLabel("Top-p:"))
        
        self.top_p_slider = QSlider(Qt.Orientation.Horizontal)
        self.top_p_slider.setRange(0, 100)  # 0.0 to 1.0
        self.top_p_slider.setValue(90)  # 0.9
        self.top_p_slider.valueChanged.connect(self._update_top_p_label)
        top_p_layout.addWidget(self.top_p_slider)
        
        self.top_p_label = QLabel("0.9")
        top_p_layout.addWidget(self.top_p_label)
        
        settings_layout.addLayout(top_p_layout)
        
        # Top-k
        top_k_layout = QHBoxLayout()
        top_k_layout.addWidget(QLabel("Top-k:"))
        
        self.top_k_spin = QSpinBox()
        self.top_k_spin.setRange(1, 100)
        self.top_k_spin.setValue(40)
        top_k_layout.addWidget(self.top_k_spin)
        
        settings_layout.addLayout(top_k_layout)
        
        layout.addWidget(settings_group)
        
        # Check if Ollama is available
        if not OLLAMA_AVAILABLE:
            self._show_unavailable_message()
    
    def _update_tools_status(self, tool_count: int):
        """Update the tools status display"""
        if hasattr(self, 'tools_status_label'):
            if tool_count > 0:
                self.tools_status_label.setText(f"🔧 Tools: {tool_count} available")
                self.tools_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #d4edda;
                        border: 1px solid #c3e6cb;
                        padding: 5px 10px;
                        border-radius: 5px;
                        font-size: 12px;
                        color: #155724;
                    }
                """)
            else:
                self.tools_status_label.setText("🔧 Tools: No tools (fallback mode)")
                self.tools_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #fff3cd;
                        border: 1px solid #ffeaa7;
                        padding: 5px 10px;
                        border-radius: 5px;
                        font-size: 12px;
                        color: #856404;
                    }
                """)
            
        
    def _create_generation_tab(self):
        """Create the generation interface tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Input area
        input_group = QGroupBox("Prompt")
        input_layout = QVBoxLayout(input_group)
        
        self.generation_input = QTextEdit()
        self.generation_input.setPlaceholderText(
            "Enter your prompt here...\n\n"
            "Example: Write a Python function that calculates "
            "fibonacci numbers"
        )
        input_layout.addWidget(self.generation_input)
        
        layout.addWidget(input_group)
        
        # Generate button
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self._generate_text)
        layout.addWidget(self.generate_btn)
        
        # Output area
        output_group = QGroupBox("Generated Output")
        output_layout = QVBoxLayout(output_group)
        
        self.generation_output = QTextEdit()
        self.generation_output.setReadOnly(True)
        
        # Set monospace font for code
        code_font = QFont("Consolas, Monaco, 'Courier New', monospace")
        code_font.setPointSize(10)
        self.generation_output.setFont(code_font)
        
        output_layout.addWidget(self.generation_output)
        
        # Copy button
        copy_btn = QPushButton("Copy Output")
        copy_btn.clicked.connect(self._copy_generation_output)
        output_layout.addWidget(copy_btn)
        
        layout.addWidget(output_group)
        
        return widget
        
    def _initial_service_check(self):
        """Initial service check with auto-start attempt"""
        logger.info("[ModelPage] Performing initial service check")
        
        if not self.ollama_wrapper:
            logger.warning("[ModelPage] No wrapper available")
            self._set_status(OllamaStatus.NOT_INSTALLED
                             if OllamaStatus else None)
            return
            
        # Check current status
        status = self.ollama_wrapper.service_status
        logger.info(f"[ModelPage] Initial service status: {status}")
        
        # If not ready, attempt to start automatically
        if OllamaStatus and status == OllamaStatus.NOT_RUNNING:
            logger.info("[ModelPage] Service not running, attempting auto-start")
            self.status_label.setText("Service Status: Starting automatically...")
            
            # Use QTimer to start service after GUI is fully loaded
            QTimer.singleShot(1000, self._auto_start_service)
        else:
            self._set_status(status)
            # Refresh models on initial load if service is ready
            if OllamaStatus and status == OllamaStatus.READY:
                logger.info("[ModelPage] Service ready, refreshing models")
                self._refresh_models()
    
    def _auto_start_service(self):
        """Automatically start the Ollama service"""
        if self.ollama_wrapper:
            print("[ModelPage] Auto-starting Ollama service")
            success = self.ollama_wrapper.start_service()
            
            if success:
                print("[ModelPage] Service auto-started successfully")
                self._update_service_status()
                self._refresh_models()
                
                # Show success notification
                self.download_status.setVisible(True)
                self.download_status.setText("✓ Ollama service started automatically")
                self.download_status.setStyleSheet("color: green;")
                QTimer.singleShot(5000, lambda: self.download_status.setVisible(False))
            else:
                print("[ModelPage] Failed to auto-start service")
                self._update_service_status()
                
                # Show error notification
                self.download_status.setVisible(True)
                self.download_status.setText("⚠ Could not start Ollama service automatically. Click 'Start Service' to try manually.")
                self.download_status.setStyleSheet("color: orange;")
    
    def _update_service_status(self):
        """Update the service status display"""
        if not self.ollama_wrapper:
            self._set_status(OllamaStatus.NOT_INSTALLED
                             if OllamaStatus else None)
            return
        
        # Force a fresh check
        was_ready = self.ollama_wrapper.service_status == OllamaStatus.READY
        is_running = self.ollama_wrapper.is_service_running()
        
        # Update wrapper's internal status
        if is_running and not was_ready:
            print("[ModelPage] Service detected as running after being not ready")
            self._refresh_models()
            
        status = self.ollama_wrapper.service_status
        self._set_status(status)
        
    def _set_status(self, status):
        """Set the status display"""
        if OllamaStatus and status == OllamaStatus.READY:
            self.status_dot.setStyleSheet("color: green; font-size: 20px;")
            self.status_label.setText("Service Status: Ready")
            self.start_service_btn.setVisible(False)
            self._enable_controls(True)
        elif OllamaStatus and status == OllamaStatus.NOT_RUNNING:
            self.status_dot.setStyleSheet("color: orange; font-size: 20px;")
            self.status_label.setText("Service Status: Not Running")
            self.start_service_btn.setVisible(True)
            self._enable_controls(False)
        elif OllamaStatus and status == OllamaStatus.NOT_INSTALLED:
            self.status_dot.setStyleSheet("color: red; font-size: 20px;")
            self.status_label.setText("Service Status: Not Installed")
            self.start_service_btn.setVisible(False)
            self._enable_controls(False)
        elif OllamaStatus and status == OllamaStatus.ERROR:
            self.status_dot.setStyleSheet("color: red; font-size: 20px;")
            self.status_label.setText("Service Status: Error")
            self.start_service_btn.setVisible(True)
            self._enable_controls(False)
        else:  # CHECKING
            self.status_dot.setStyleSheet("color: yellow; font-size: 20px;")
            self.status_label.setText("Service Status: Checking...")
            self.start_service_btn.setVisible(False)
            self._enable_controls(False)
            
    def _enable_controls(self, enabled: bool):
        """Enable or disable controls based on service status"""
        self.model_combo.setEnabled(enabled)
        self.download_btn.setEnabled(enabled)
        self.generate_btn.setEnabled(enabled)
        
    def _start_service(self):
        """Attempt to start the Ollama service"""
        if self.ollama_wrapper:
            print("[ModelPage] Manual service start requested")
            self.status_label.setText("Service Status: Starting...")
            self.start_service_btn.setEnabled(False)
            
            # Start service in a delayed call to allow UI update
            QTimer.singleShot(100, self._perform_manual_start)
    
    def _perform_manual_start(self):
        """Perform the manual service start"""
        if self.ollama_wrapper:
            success = self.ollama_wrapper.start_service()
            
            if success:
                print("[ModelPage] Manual service start successful")
                self._update_service_status()
                self._refresh_models()
                
                # Show success notification
                self.download_status.setVisible(True)
                self.download_status.setText("✓ Ollama service started successfully")
                self.download_status.setStyleSheet("color: green;")
                QTimer.singleShot(5000, lambda: self.download_status.setVisible(False))
            else:
                print("[ModelPage] Manual service start failed")
                self.status_label.setText("Service Status: Failed to start")
                self.start_service_btn.setEnabled(True)
                
                # Show detailed error
                self.download_status.setVisible(True)
                self.download_status.setText("❌ Failed to start service. Check if Ollama is installed and accessible.")
                self.download_status.setStyleSheet("color: red;")
                
    def _refresh_models(self):
        """Refresh the list of available models"""
        logger.info("[ModelPage] _refresh_models: Starting model refresh")
        
        if not self.ollama_wrapper or not self.ollama_wrapper.is_ready:
            logger.warning("[ModelPage] _refresh_models: Wrapper not ready, skipping")
            return
            
        current_model = self.model_combo.currentText()
        logger.info(f"[ModelPage] _refresh_models: Current selection = '{current_model}'")
        
        # Clear existing items
        logger.info(f"[ModelPage] _refresh_models: Clearing combo box (had {self.model_combo.count()} items)")
        self.model_combo.clear()
        
        # Get models from wrapper
        models = self.ollama_wrapper.list_models()
        logger.info(f"[ModelPage] _refresh_models: Got {len(models)} models from wrapper")
        
        # Add placeholder if no models
        if not models:
            logger.warning("[ModelPage] _refresh_models: No models found, adding placeholder")
            self.model_combo.addItem("No models installed - use 'ollama pull' to download")
            self.model_combo.setEnabled(False)
            
            # Show helpful message in download status
            self.download_status.setVisible(True)
            self.download_status.setText("ℹ No models found. Try: ollama pull llama3.2:1b")
            self.download_status.setStyleSheet("color: blue;")
        else:
            self.model_combo.setEnabled(True)
            # Add each model
            for idx, model in enumerate(models):
                model_display = f"{model.name}:{model.tag}"
                logger.info(f"[ModelPage] _refresh_models: Adding model {idx}: '{model_display}' (name='{model.name}', tag='{model.tag}')")
                self.model_combo.addItem(model_display)
            
            # Restore selection if possible
            if current_model:
                index = self.model_combo.findText(current_model)
                logger.info(f"[ModelPage] _refresh_models: Trying to restore '{current_model}', found at index {index}")
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
                else:
                    logger.info(f"[ModelPage] _refresh_models: Previous selection '{current_model}' not found")
            
            # Select first model if none selected
            if self.model_combo.currentIndex() == -1 and self.model_combo.count() > 0:
                logger.info("[ModelPage] _refresh_models: No selection, selecting first model")
                # Temporarily disconnect signal to avoid corruption issue
                self.model_combo.currentTextChanged.disconnect(self._on_model_changed)
                self.model_combo.setCurrentIndex(0)
                # Get the actual model name and set it directly
                first_model = self.model_combo.currentText()
                logger.info(f"[ModelPage] _refresh_models: Setting first model directly: '{first_model}'")
                if first_model and self.ollama_wrapper:
                    self.ollama_wrapper.set_model(first_model)
                # Reconnect signal
                self.model_combo.currentTextChanged.connect(self._on_model_changed)
        
        logger.info(f"[ModelPage] _refresh_models: Finished. Combo box now has {self.model_combo.count()} items")
                
    def _on_model_changed(self, model_name: str):
        """Handle model selection change with OllamaAgent and tool discovery"""
        logger.info(f"[ModelPage] _on_model_changed called with: '{model_name}'")
        logger.info(f"[ModelPage] model_name type: {type(model_name)}")
        logger.info(f"[ModelPage] model_name length: {len(model_name) if model_name else 0}")
        logger.info(f"[ModelPage] model_name repr: {repr(model_name)}")
        
        # Get all combo box info
        logger.info(f"[ModelPage] Current combo box text: '{self.model_combo.currentText()}'")
        logger.info(f"[ModelPage] Current combo box index: {self.model_combo.currentIndex()}")
        
        current_idx = self.model_combo.currentIndex()
        if current_idx >= 0:
            logger.info(f"[ModelPage] Combo box item at current index: '{self.model_combo.itemText(current_idx)}'")
        
        # Log all items in combo box
        logger.info(f"[ModelPage] Total items in combo box: {self.model_combo.count()}")
        for i in range(self.model_combo.count()):
            logger.info(f"[ModelPage]   Item {i}: '{self.model_combo.itemText(i)}'")
        
        # Check for corruption patterns
        if model_name and model_name.startswith(":"):
            logger.warning(f"[ModelPage] WARNING: Model name starts with colon, likely corrupted!")
            # Try to get the correct value from combo box
            correct_name = self.model_combo.currentText()
            logger.info(f"[ModelPage] Attempting to use currentText() instead: '{correct_name}'")
            if correct_name and not correct_name.startswith(":"):
                model_name = correct_name
                logger.info(f"[ModelPage] Using corrected model name: '{model_name}'")
        
        if model_name and model_name != "Select a model..." and not model_name.startswith("No models"):
            # Create OllamaAgent with tool discovery
            if OLLAMA_AVAILABLE and OllamaAgent:
                try:
                    logger.info(f"[ModelPage] Creating OllamaAgent with model: '{model_name}'")
                    
                    # Discover available tools
                    tools = []
                    if AVAILABLE_TOOLS:
                        for tool_name, tool_func in AVAILABLE_TOOLS.items():
                            tool_info = {
                                "name": tool_name,
                                "function": tool_func,
                                "description": tool_func.__doc__ or f"Tool function: {tool_name}"
                            }
                            tools.append(tool_info)
                            logger.info(f"[ModelPage] Discovered tool: {tool_name}")
                    
                    # Clear any previous agent registration
                    if self.main_window:
                        self.main_window.register_agent('current', None)
                    
                    # Create agent with tools
                    # Get tool registry from main window
                    tool_registry = None
                    if self.main_window and hasattr(self.main_window, 'tool_registry'):
                        tool_registry = self.main_window.tool_registry
                        logger.info(f"[ModelPage] Got tool registry from main window: {tool_registry is not None}")
                    else:
                        logger.warning("[ModelPage] No tool registry available from main window")
                    
                    self.agent = OllamaAgent(
                        ollama_wrapper=self.ollama_wrapper,
                        model_name=model_name,
                        tool_registry=tool_registry  # Pass the tool registry!
                    )
                    
                    logger.info(f"[ModelPage] OllamaAgent created successfully with {len(tools)} tools")
                    
                    # Initialize the agent
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Initialize agent in background
                    def init_agent():
                        try:
                            success = loop.run_until_complete(self.agent.initialize())
                            if success:
                                logger.info("[ModelPage] Agent initialized successfully")
                                # Register agent with MainWindow for reliable sharing
                                if self.main_window:
                                    self.main_window.register_agent('current', self.agent)
                                    logger.info("[ModelPage] Agent registered with MainWindow")
                                    
                                    # Synchronize with chat tab
                                    chat_tab = self.main_window.get_chat_tab()
                                    if chat_tab and hasattr(chat_tab, 'set_current_model'):
                                        chat_tab.set_current_model(model_name)
                                        logger.info(f"[ModelPage] Chat tab synchronized with model: {model_name}")
                                    else:
                                        logger.warning(f"[ModelPage] Could not sync with chat tab - tab: {chat_tab}, has method: {hasattr(chat_tab, 'set_current_model') if chat_tab else False}")
                                        
                                # Update tools status
                                QTimer.singleShot(0, lambda: self._update_tools_status(len(tools)))
                            else:
                                logger.error("[ModelPage] Failed to initialize agent")
                        except Exception as e:
                            logger.error(f"[ModelPage] Agent initialization failed: {e}")
                    
                    import threading
                    thread = threading.Thread(target=init_agent, daemon=True)
                    thread.start()
                    
                except Exception as e:
                    logger.error(f"[ModelPage] Failed to create OllamaAgent: {e}")
                    self.agent = None
            
            # Fallback to wrapper if agent creation failed
            if self.ollama_wrapper and not self.agent:
                logger.info(f"[ModelPage] Falling back to wrapper.set_model with: '{model_name}'")
                self.ollama_wrapper.set_model(model_name)
            
            # Emit signal to notify other components
            logger.info(f"[ModelPage] DEBUG: Emitting model_selected signal with: '{model_name}'")
            logger.info(f"[ModelPage] DEBUG: Signal connected receivers: {self.model_selected.receivers}")
            self.model_selected.emit(model_name)
            logger.info(f"[ModelPage] DEBUG: Signal emission completed")
            
            # Also trigger signal setup check in case connections weren't ready before
            if (self.main_window and
                hasattr(self.main_window, '_check_and_setup_signals')):
                QTimer.singleShot(50, self.main_window._check_and_setup_signals)
        else:
            logger.warning(f"[ModelPage] Skipping model set - model_name: '{model_name}'")
            
    def _download_model(self):
        """Start model download"""
        model_name = self.model_input.text().strip()
        if not model_name:
            return
            
        if not self.ollama_wrapper or not self.ollama_wrapper.is_ready:
            return
            
        # Disable download button
        self.download_btn.setEnabled(False)
        self.download_progress.setVisible(True)
        self.download_status.setVisible(True)
        self.download_status.setText(f"Downloading {model_name}...")
        
        # Create and start download thread
        self.download_thread = ModelDownloadThread(
            self.ollama_wrapper, model_name
        )
        self.download_thread.progress.connect(self._update_download_progress)
        self.download_thread.finished.connect(self._download_finished)
        self.download_thread.start()
    
    def _execute_command(self):
        """Execute an Ollama CLI command"""
        command = self.command_input.text().strip()
        if not command:
            return
            
        if not self.ollama_wrapper or not self.ollama_wrapper.is_ready:
            self._show_command_error("Ollama service is not ready")
            return
            
        # Parse the command
        parts = command.split()
        if len(parts) < 2 or parts[0].lower() != "ollama":
            self._show_command_error(
                "Invalid command. Use format: ollama <command> [args]"
            )
            return
            
        cmd = parts[1].lower()
        
        # Handle different commands
        if cmd in ["run", "pull"]:
            if len(parts) < 3:
                self._show_command_error(
                    f"Model name required for '{cmd}' command"
                )
                return
            model_name = parts[2]
            self._execute_pull_command(model_name)
            
        elif cmd == "rm" or cmd == "remove":
            if len(parts) < 3:
                self._show_command_error(
                    "Model name required for 'rm' command"
                )
                return
            model_name = parts[2]
            self._execute_remove_command(model_name)
            
        elif cmd == "list" or cmd == "ls":
            self._refresh_models()
            self._show_command_success("Model list refreshed")
            
        else:
            self._show_command_error(f"Unknown command: '{cmd}'")
    
    def _execute_pull_command(self, model_name: str):
        """Execute a pull/run command"""
        # Disable execute button
        self.execute_btn.setEnabled(False)
        self.download_progress.setVisible(True)
        self.download_status.setVisible(True)
        self.download_status.setText(f"Pulling {model_name}...")
        
        # Create and start download thread using pull_model
        self.download_thread = ModelDownloadThread(
            self.ollama_wrapper, model_name
        )
        self.download_thread.progress.connect(self._update_download_progress)
        self.download_thread.finished.connect(
            lambda success, error: self._command_download_finished(
                success, error, model_name
            )
        )
        self.download_thread.start()
    
    def _execute_remove_command(self, model_name: str):
        """Execute a remove command"""
        # Confirm removal
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove model '{model_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.execute_btn.setEnabled(False)
            self.download_status.setVisible(True)
            self.download_status.setText(f"Removing {model_name}...")
            
            # Run removal in a separate thread
            QTimer.singleShot(100, lambda: self._perform_removal(model_name))
    
    def _perform_removal(self, model_name: str):
        """Perform the actual model removal"""
        if not self.ollama_wrapper:
            self._show_command_error("Ollama wrapper not available")
            self.execute_btn.setEnabled(True)
            return
            
        success = self.ollama_wrapper.remove_model(model_name)
        
        if success:
            self._show_command_success(
                f"Model '{model_name}' removed successfully"
            )
            self._refresh_models()
        else:
            self._show_command_error(f"Failed to remove model '{model_name}'")
            
        self.execute_btn.setEnabled(True)
        QTimer.singleShot(3000, lambda: self.download_status.setVisible(False))
    
    def _command_download_finished(self, success: bool, error: str,
                                   model_name: str):
        """Handle command-initiated download completion"""
        self.execute_btn.setEnabled(True)
        self.download_progress.setVisible(False)
        
        if success:
            self.download_status.setText(
                f"Model '{model_name}' downloaded successfully!"
            )
            self.command_input.clear()
            self._refresh_models()
            # Auto-select the new model
            index = self.model_combo.findText(model_name)
            if index == -1:
                # Try with :latest tag
                index = self.model_combo.findText(f"{model_name}:latest")
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
        else:
            self.download_status.setText(
                f"Failed to download '{model_name}': {error}"
            )
            
        # Hide status after 3 seconds
        QTimer.singleShot(3000, lambda: self.download_status.setVisible(False))
    
    def _show_command_error(self, message: str):
        """Show command error message"""
        self.download_status.setVisible(True)
        self.download_status.setText(f"Error: {message}")
        self.download_status.setStyleSheet("color: red;")
        QTimer.singleShot(3000, lambda: self.download_status.setVisible(False))
    
    def _show_command_success(self, message: str):
        """Show command success message"""
        self.download_status.setVisible(True)
        self.download_status.setText(message)
        self.download_status.setStyleSheet("color: green;")
        QTimer.singleShot(3000, lambda: self.download_status.setVisible(False))
        
    def _update_download_progress(self, percent: int, downloaded_gb: float,
                                  total_gb: float, status: str):
        """Update download progress display"""
        self.download_progress.setValue(percent)
        
        if total_gb > 0:
            # Display in GB for large files, MB for smaller ones
            if total_gb >= 1.0:
                self.download_status.setText(
                    f"{status} - {downloaded_gb:.2f}/{total_gb:.2f} GB ({percent}%)"
                )
            else:
                # Convert back to MB for files < 1GB
                downloaded_mb = downloaded_gb * 1024
                total_mb = total_gb * 1024
                self.download_status.setText(
                    f"{status} - {downloaded_mb:.1f}/{total_mb:.1f} MB ({percent}%)"
                )
        else:
            self.download_status.setText(status)
            
    def _download_finished(self, success: bool, error: str):
        """Handle download completion"""
        self.download_btn.setEnabled(True)
        self.download_progress.setVisible(False)
        
        if success:
            self.download_status.setText("Download completed successfully!")
            self.download_status.setStyleSheet("color: green;")
            self.model_input.clear()
            self._refresh_models()
        else:
            self.download_status.setText(f"Download failed: {error}")
            self.download_status.setStyleSheet("color: red;")
            
        # Hide status after 3 seconds
        QTimer.singleShot(3000, lambda: self.download_status.setVisible(False))
        
                
    def _generate_text(self):
        """Generate text from prompt"""
        prompt = self.generation_input.toPlainText().strip()
        if not prompt:
            return
            
        if not self.ollama_wrapper or not self.ollama_wrapper.is_ready:
            return
            
        # Clear output
        self.generation_output.clear()
        
        # Disable generate button
        self.generate_btn.setEnabled(False)
        
        # Check if a model is selected
        current_model = self.model_combo.currentText()
        if not current_model or current_model == "Select a model..." or current_model.startswith("No models"):
            self.generation_output.setText("Error: Please select a model first")
            self.generate_btn.setEnabled(True)
            return
        
        # Get generation parameters
        params = self._get_generation_params()
        
        # Start generation thread
        self.generation_thread = GenerationThread(
            self.ollama_wrapper,
            'generate',
            prompt,
            model=current_model,
            **params
        )
        self.generation_thread.text_chunk.connect(
            self._update_generation_output
        )
        self.generation_thread.finished.connect(self._generation_finished)
        self.generation_thread.start()
        
    def _update_generation_output(self, chunk: str):
        """Update streaming generation output"""
        cursor = self.generation_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.generation_output.setTextCursor(cursor)
        
    def _generation_finished(self, success: bool, error: str):
        """Handle generation completion"""
        self.generate_btn.setEnabled(True)
        
        if not success and error:
            self.generation_output.append(f"\n\nError: {error}")
            
    def _copy_generation_output(self):
        """Copy generation output to clipboard"""
        output_text = self.generation_output.toPlainText()
        if output_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(output_text)
            
    def _get_generation_params(self) -> Dict[str, Any]:
        """Get current generation parameters"""
        return {
            'temperature': self.temp_slider.value() / 100.0,
            'max_tokens': self.max_tokens_spin.value(),
            'top_p': self.top_p_slider.value() / 100.0,
            'top_k': self.top_k_spin.value()
        }
        
    def _update_temp_label(self, value: int):
        """Update temperature label"""
        self.temp_label.setText(f"{value / 100.0:.1f}")
        
    def _update_top_p_label(self, value: int):
        """Update top-p label"""
        self.top_p_label.setText(f"{value / 100.0:.2f}")
        
    def _show_unavailable_message(self):
        """Show message when Ollama is not available"""
        self.status_label.setText("Ollama integration not available")
        self._enable_controls(False)
        
        # Show info in both tabs
        info_text = (
            "# Ollama Integration\n\n"
            "The Ollama integration is not available.\n"
            "Please ensure the Ollama Python library is installed:\n\n"
            "pip install ollama\n\n"
            "Features when available:\n"
            "- Local LLM execution\n"
            "- Multiple model support\n"
            "- Streaming generation\n"
            "- Chat with context management\n"
            "- Model download and management"
        )
        
        self.generation_input.setPlainText(info_text)
        self.generation_input.setReadOnly(True)