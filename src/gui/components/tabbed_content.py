#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TabbedContentWidget class for the PySide6 application.
This widget displays the main tabbed content in the center area.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel,
    QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette
from typing import Union
from .enhanced_chat_tab import EnhancedChatTabWidget
from .signal_coordinator import SignalCoordinator
try:
    from src.gui.pages.settings_page import SettingsPage
    from src.gui.pages.notes_page import NotesPage
    from src.gui.pages.smart_timer_page import SmartTimerPage
    from src.gui.pages.appointments_page import AppointmentsPage
    from src.gui.pages.artifacts_page import ArtifactsPage
    from src.gui.pages.file_search_page import FileSearchPage
    from src.gui.pages.tasks_page import ProjectsPage as TasksPage
    from src.gui.pages.pseudocode_page import PseudocodePage
    from src.gui.pages.model_page import ModelPage
    from src.gui.pages.help_page import HelpPage
except ImportError:
    from ..pages.settings_page import SettingsPage
    from ..pages.notes_page import NotesPage
    from ..pages.smart_timer_page import SmartTimerPage
    from ..pages.appointments_page import AppointmentsPage
    from ..pages.artifacts_page import ArtifactsPage
    from ..pages.file_search_page import FileSearchPage
    from ..pages.tasks_page import ProjectsPage as TasksPage
    from ..pages.pseudocode_page import PseudocodePage
    from ..pages.model_page import ModelPage
    from ..pages.help_page import HelpPage
from src.input_processing.input_sanitizer import (
    InputPipeline, InputPipelineError
)
from src.utils.scaling import get_scaling_helper
from src.utils.colors import DinoPitColors
from src.utils.logger import Logger


class TabContentWidget(QWidget):
    """A single tab content widget."""
    
    def __init__(self, tab_name):
        """Initialize the tab content widget.
        
        Args:
            tab_name (str): The name of the tab
        """
        super().__init__()
        self.tab_name = tab_name
        self._scaling_helper = get_scaling_helper()
        
        # Create layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create content frame
        self.content_frame = QFrame()
        self.content_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.content_frame.setFrameShadow(QFrame.Shadow.Plain)
        self.content_frame.setLineWidth(1)
        
        # Set background color for content frame - DinoPit brand with blue
        palette = self.content_frame.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(52, 67, 89))
        self.content_frame.setPalette(palette)
        self.content_frame.setAutoFillBackground(True)
        
        # Create frame layout
        self.frame_layout = QVBoxLayout(self.content_frame)
        self.frame_layout.setContentsMargins(30, 30, 30, 30)
        self.frame_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create content label with DinoPit brand colors
        self.content_label = QLabel(
            f"{tab_name} content will be displayed here"
        )
        self.content_label.setStyleSheet("color: #FFFFFF;")
        self.content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_label_style()
        
        # Add label to frame layout
        self.frame_layout.addWidget(self.content_label)
        
        # Add frame to main layout
        main_layout.addWidget(self.content_frame)
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
    
    def _update_label_style(self):
        """Update the label style with current scaling."""
        font_size = self._scaling_helper.scaled_font_size(14)
        self.content_label.setStyleSheet(
            f"color: #FF6B35; "
            f"font-size: {font_size}px; "
            f"font-weight: 500;"
        )
    
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes."""
        self._update_label_style()


class TabbedContentWidget(QWidget):
    """Widget displaying the main tabbed content in the center area."""
    
    # Signals
    watchdog_control_requested = Signal(str)  # Forward from settings
    watchdog_config_changed = Signal(dict)    # Forward from settings
    
    def __init__(self, database_manager=None, main_window=None):
        """Initialize the tabbed content widget.
        
        Args:
            database_manager: DatabaseManager instance for database operations
            main_window: MainWindow instance for agent registry access
        """
        super().__init__()
        self.settings_page = None
        self.database_manager = database_manager
        self.main_window = main_window
        self._scaling_helper = get_scaling_helper()
        self.chat_tab = None
        self.chat_db = None
        
        # Initialize SignalCoordinator
        self.signal_coordinator = SignalCoordinator(self)
        
        # Initialize InputPipeline with enhanced security
        self.input_pipeline = InputPipeline(
            gui_feedback_hook=self._security_feedback,
            enable_enhanced_security=True,  # Enable 96.8% protection
            watchdog_ref=None,  # Will be set later
            main_window_ref=None  # Will be set later
        )
        
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Apply initial style
        self._update_tab_widget_style()
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
        # Define tabs based on the original design
        self.tabs = [
            {'id': 'chat', 'label': 'Chat'},
            {'id': 'pseudocode', 'label': 'Pseudocode Translator'},
            {'id': 'notes', 'label': 'Notes'},
            {'id': 'file_search', 'label': 'File Search'},
            {'id': 'project', 'label': 'Projects'},
            {'id': 'appointments', 'label': 'Appointments'},
            {'id': 'artifacts', 'label': 'Artifacts'},
            {'id': 'timer', 'label': 'Smart Timer'},
            {'id': 'model', 'label': 'Model'},
            {'id': 'settings', 'label': 'Settings'},
            {'id': 'help', 'label': 'Help'}
        ]
        
        # Create and add tabs
        for tab in self.tabs:
            if tab['id'] == 'chat':
                # Create placeholder chat tab
                # (will be replaced when DB is ready)
                tab_content = TabContentWidget(tab['label'])
                self.chat_tab_index = self.tab_widget.count()
            elif tab['id'] == 'settings':
                # Create the actual settings page
                self.settings_page = SettingsPage()
                # Connect settings signals to forward them
                self.settings_page.watchdog_control_requested.connect(
                    self.watchdog_control_requested.emit
                )
                self.settings_page.watchdog_config_changed.connect(
                    self.watchdog_config_changed.emit
                )
                tab_content = self.settings_page
            elif tab['id'] == 'notes':
                # Create the actual notes page
                tab_content = NotesPage()
            elif tab['id'] == 'file_search':
                # Create the file search page
                tab_content = FileSearchPage()
            elif tab['id'] == 'timer':
                # Create the smart timer page
                tab_content = SmartTimerPage()
            elif tab['id'] == 'appointments':
                # Create the appointments page
                tab_content = AppointmentsPage()
            elif tab['id'] == 'artifacts':
                # Create the artifacts page
                tab_content = ArtifactsPage()
            elif tab['id'] == 'project':
                # Create the projects page (using TasksPage)
                tab_content = TasksPage()
            elif tab['id'] == 'pseudocode':
                # Create the pseudocode translator page
                tab_content = PseudocodePage()
            elif tab['id'] == 'model':
                # Create the model page for Ollama integration
                tab_content = ModelPage(main_window=self.main_window)
            elif tab['id'] == 'help':
                # Create the help page
                tab_content = HelpPage()
            else:
                # Create regular tab content
                tab_content = TabContentWidget(tab['label'])
            self.tab_widget.addTab(tab_content, tab['label'])
            
            # Register page with signal coordinator
            self._register_page_with_coordinator(tab['id'], tab_content)
        
        # Set the first tab as active (Chat)
        self.tab_widget.setCurrentIndex(0)
        
        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # Add tab widget to main layout
        self.main_layout.addWidget(self.tab_widget)
        
        # Enable signal debugging in development mode
        if database_manager and hasattr(database_manager, 'is_debug'):
            from .signal_coordinator import SignalDebugger
            self.signal_debugger = SignalDebugger(self.signal_coordinator)
            # Enable debug mode if needed
            # self.signal_debugger.enable_debug_mode()
    
    def _update_tab_widget_style(self):
        """Update the tab widget style with current scaling."""
        s = self._scaling_helper  # Shorter alias for line length
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: {s.scaled_size(1)}px solid #34435A;
                background-color: #2B3A52;
            }}
            
            QTabBar::tab {{
                background-color: #FF6B35;
                color: white;
                padding: {s.scaled_size(10)}px {s.scaled_size(18)}px;
                margin-right: {s.scaled_size(1)}px;
                border-top-left-radius: {s.scaled_size(6)}px;
                border-top-right-radius: {s.scaled_size(6)}px;
                font-weight: 500;
                font-size: {s.scaled_font_size(13)}px;
                min-width: {s.scaled_size(80)}px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                font-weight: bold;
            }}
            
            QTabBar::tab:hover {{
                background-color: #FF4500;
                color: white;
            }}
        """)
    
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes."""
        self._update_tab_widget_style()
    
    def on_tab_changed(self, index):
        """Handle tab change event.
        
        Args:
            index (int): The index of the newly selected tab
        """
        tab_name = self.tabs[index]['label']
        logger = Logger()
        logger.debug(f"Tab changed to: {tab_name}")
        # In a real application, this would handle tab-specific logic
    
    def handle_chat_message(self, message):
        """Handle chat message from the chat tab.
        
        Args:
            message (str): The chat message sent by the user
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Chat message received: {message[:50]}...")
        
        # Use the enhanced chat tab if available
        chat_widget = (self.chat_tab if self.chat_tab
                       else self.tab_widget.widget(0))
        
        # Type assertion for better IDE support
        chat_widget: Union[EnhancedChatTabWidget, QWidget]
        
        if hasattr(chat_widget, 'add_message'):
            try:
                # Sanitize the message with enhanced security
                clean_message, intent = self.input_pipeline.run(message)
                
                # Log the sanitization result
                logger.info(f"Sanitized message: {clean_message}")
                logger.info(f"Detected intent: {intent}")
                
                # Display the clean message in chat if it was modified
                if clean_message != message:
                    # Message was modified for security
                    chat_widget.add_message(  # type: ignore
                        f"[Sanitized] {clean_message}",
                        is_user=True
                    )
                
                # Get AI response using the selected model
                response = self._generate_ai_response(
                    clean_message, chat_widget
                )
                
                chat_widget.add_message(  # type: ignore
                    response, is_user=False
                )
                
            except InputPipelineError as e:
                # Security violation detected
                error_msg = f"⚠️ Security Alert: {str(e)}"
                logger.error(f"Security error: {e}")
                chat_widget.add_message(  # type: ignore
                    error_msg, is_user=False
                )
            except Exception as e:
                # Other errors
                error_msg = f"❌ Error processing message: {str(e)}"
                logger.error(f"Processing error: {e}")
                chat_widget.add_message(  # type: ignore
                    error_msg, is_user=False
                )
    
    def _generate_ai_response(self, message: str, chat_widget):
        """Generate AI response using the selected model agent with tools.
        
        Args:
            message: The user's message
            chat_widget: The chat widget to get model info from
            
        Returns:
            str: The AI response
        """
        import logging
        import asyncio
        logger = logging.getLogger(__name__)
        
        # Initialize current_model to avoid unbound variable error
        current_model = "unknown model"
        
        try:
            # Get the currently selected model from chat widget
            current_model = None
            logger.info("DEBUG: _generate_ai_response called")
            logger.info(f"DEBUG: chat_widget type: {type(chat_widget)}")
            has_get_current_model = hasattr(chat_widget, 'get_current_model')
            logger.info(f"DEBUG: chat_widget has get_current_model: "
                        f"{has_get_current_model}")
            
            if has_get_current_model:
                current_model = chat_widget.get_current_model()
                logger.info(f"DEBUG: Current model from chat tab: "
                            f"'{current_model}'")
            else:
                logger.warning("DEBUG: chat_widget does not have "
                               "get_current_model method")
            
            # Also check if the chat widget has current_model attribute
            if hasattr(chat_widget, 'current_model'):
                attr_model = chat_widget.current_model
                logger.info(f"DEBUG: chat_widget.current_model attribute: "
                            f"'{attr_model}'")
                if not current_model:
                    current_model = attr_model
            
            # If no model selected, provide helpful message
            if not current_model:
                logger.warning("DEBUG: No model found, returning "
                               "selection message")
                return ("Please select a model in the Model tab first. "
                        "Go to the Model tab, choose a model, "
                        "then return here to chat.")
            
            # Try to get agent from registry first (preferred method)
            agent = None
            if self.main_window:
                agent = self.main_window.get_current_agent()
                logger.info(f"DEBUG: Retrieved agent from registry: "
                            f"{agent is not None}")
            else:
                logger.warning("DEBUG: main_window reference not available")
            
            # If agent from registry is available, use it (with tools)
            if agent and hasattr(agent, 'chat'):
                logger.info(f"DEBUG: Using registered OllamaAgent with tools "
                            f"for model: {current_model}")
                
                # Run async chat method in a new event loop
                try:
                    # Check if there's already an event loop running
                    try:
                        asyncio.get_running_loop()
                        # If we're in an event loop, use run_in_executor
                        # to avoid blocking
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as exec:
                            future = exec.submit(
                                self._run_agent_chat_sync, agent, message
                            )
                            # 60 second timeout
                            response_data = future.result(timeout=60)
                    except RuntimeError:
                        # No event loop running, we can use asyncio.run
                        response_data = asyncio.run(
                            agent.chat(message, use_tools=True)
                        )
                    
                    if response_data.get('success', False):
                        response = response_data.get('response', '')
                        tool_results = response_data.get('tool_results', [])
                        
                        # Format response with tool information if tools used
                        if tool_results:
                            tool_info = []
                            for result in tool_results:
                                tool_name = result.get('tool_name', 'unknown')
                                success = result.get('success', False)
                                if success:
                                    tool_info.append(f"✅ Used {tool_name}")
                                else:
                                    tool_info.append(f"❌ Failed {tool_name}")
                            
                            if tool_info:
                                tool_summary = " | ".join(tool_info)
                                response = (f"{response}\n\n"
                                            f"*Tools used: {tool_summary}*")
                        
                        resp_len = len(response)
                        tools_count = len(tool_results)
                        logger.info(f"DEBUG: Agent response length: "
                                    f"{resp_len}, tools used: {tools_count}")
                        
                        if response.strip():
                            return response
                        else:
                            return (f"No response generated from agent "
                                    f"with {current_model}. Please try again.")
                    else:
                        error = response_data.get('error', 'Unknown error')
                        logger.warning(f"DEBUG: Agent chat failed: {error}")
                        # Fall back to wrapper
                        
                except Exception as agent_error:
                    logger.warning(f"DEBUG: Agent chat failed with "
                                   f"exception: {agent_error}")
                    # Fall back to wrapper
            else:
                # No agent available from registry, will fall back to wrapper
                if agent is None:
                    logger.info("DEBUG: No agent available from registry, "
                                "using wrapper fallback")
                else:
                    logger.warning("DEBUG: Agent found but missing "
                                   "chat method")
            
            # Fallback to wrapper if agent not available or failed
            # Get the model page to access wrapper
            model_page = None
            for i, tab in enumerate(self.tabs):
                if tab['id'] == 'model':
                    model_page = self.tab_widget.widget(i)
                    break
            
            if not model_page:
                return (f"Model page not available for fallback. "
                        f"Using model: {current_model}")
            
            wrapper = getattr(model_page, 'ollama_wrapper', None)
            if not wrapper:
                return (f"Neither agent nor wrapper available. "
                        f"Using model: {current_model}")
                
            if not wrapper.is_ready:
                return (f"Ollama service not ready. Please check the "
                        f"Model tab. Selected model: {current_model}")
            
            logger.info(f"DEBUG: Falling back to OllamaWrapper "
                        f"for model: {current_model}")
            
            # Create simple chat messages list
            messages = [{"role": "user", "content": message}]
            
            # Generate streaming response
            response_parts = []
            for chunk in wrapper.stream_chat(
                messages, model=current_model, use_context=True
            ):
                response_parts.append(chunk)
            
            response = ''.join(response_parts)
            logger.info(f"DEBUG: Wrapper response length: {len(response)}")
            
            if response.strip():
                return response
            else:
                return (f"No response generated from {current_model}. "
                        f"Please try again.")
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return (f"Error generating response with {current_model}: "
                    f"{str(e)}")
    
    def _run_agent_chat_sync(self, agent, message):
        """Run agent chat in a new event loop (for thread execution)"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(agent.chat(message, use_tools=True))
        finally:
            loop.close()
    
    def get_current_tab(self):
        """Get the currently active tab.
        
        Returns:
            dict: The currently active tab information
        """
        current_index = self.tab_widget.currentIndex()
        if 0 <= current_index < len(self.tabs):
            return self.tabs[current_index]
        return None
    
    def get_settings_page(self):
        """Get the settings page widget.
        
        Returns:
            SettingsPage: The settings page widget or None
        """
        return self.settings_page
    
    def _security_feedback(self, message: str):
        """Handle security feedback from the InputPipeline.
        
        Args:
            message (str): Security feedback message
        """
        logger = Logger()
        logger.warning(f"[Security] {message}")
        # In a real app, this could update a status bar or show notifications
        
    def set_main_window_ref(self, main_window):
        """Set reference to main window for InputPipeline.
        
        Args:
            main_window: The main window instance
        """
        if self.input_pipeline:
            self.input_pipeline.main_window_ref = main_window
            
    def set_watchdog_ref(self, watchdog):
        """Set reference to watchdog for InputPipeline.
        
        Args:
            watchdog: The watchdog instance
        """
        if self.input_pipeline:
            self.input_pipeline.watchdog_ref = watchdog
            
    def set_chat_database(self, chat_db):
        """Set the chat database and create enhanced chat tab.
        
        Args:
            chat_db: ChatHistoryDatabase instance
        """
        self.chat_db = chat_db
        
        if self.chat_db and hasattr(self, 'chat_tab_index'):
            # Create enhanced chat tab
            self.chat_tab = EnhancedChatTabWidget(self.chat_db)
            self.chat_tab.message_sent.connect(self.handle_chat_message)
            
            # Replace placeholder with enhanced chat tab
            self.tab_widget.removeTab(self.chat_tab_index)
            self.tab_widget.insertTab(
                self.chat_tab_index,
                self.chat_tab,
                self.tabs[self.chat_tab_index]['label']
            )
            
            # Notify main window that chat tab is ready
            if self.main_window and hasattr(self.main_window, '_check_and_setup_signals'):
                # Use QTimer to ensure this happens after the widget is fully set up
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, self.main_window._check_and_setup_signals)
            
    def get_chat_tab(self):
        """Get the chat tab widget.
        
        Returns:
            EnhancedChatTabWidget or None
        """
        return self.chat_tab
    
    def _register_page_with_coordinator(self, page_id: str,
                                        page_widget: QWidget):
        """Register a page with the signal coordinator
        
        Args:
            page_id: The page identifier
            page_widget: The page widget instance
        """
        # Map tab IDs to coordinator page IDs
        id_mapping = {
            'artifacts': 'artifacts',
            'project': 'projects',  # Map 'project' tab to 'projects' page
            'notes': 'notes',
            'appointments': 'appointments',
            'file_search': 'file_search'
        }
        
        coordinator_id = id_mapping.get(page_id, page_id)
        
        # Only register actual page widgets, not placeholders
        if not isinstance(page_widget, TabContentWidget):
            self.signal_coordinator.register_page(coordinator_id, page_widget)
    
    def get_signal_coordinator(self):
        """Get the signal coordinator instance
        
        Returns:
            SignalCoordinator: The signal coordinator
        """
        return self.signal_coordinator