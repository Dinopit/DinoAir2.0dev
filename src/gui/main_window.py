#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DinoPit Studios GUI - Main Window
Main window class containing all GUI components with DinoPit Studios branding.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QStatusBar, QLabel, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QAction, QKeySequence, QIcon

# Import custom widgets
from .components.enhanced_chat_history import EnhancedChatHistoryWidget
from .components.tabbed_content import TabbedContentWidget
from .components.artifact_panel import ArtifactsWidget
from .components.notification_widget import NotificationWidget, AlertLevel
from .components.metrics_widget import MetricsWidget

# Import utilities
from src.utils.config_loader import ConfigLoader
from src.utils.scaling import get_scaling_helper
from src.utils.window_state import window_state_manager
from src.utils.colors import DinoPitColors


class MainWindow(QMainWindow):
    """Main window of the DinoPit Studios GUI application."""
    
    def __init__(self):
        """Initialize the main window with DinoPit Studios theme."""
        super().__init__()
        
        # Initialize references
        self.watchdog_ref = None
        self.config_loader = ConfigLoader()
        self.app_instance = None
        self._scaling_helper = get_scaling_helper()
        self.db_manager = None  # Will be set by app
        self.chat_db = None  # Will be set when db_manager is available
        
        # Set window properties
        self.setWindowTitle("DinoPit Studios GUI")
        # Use scaled initial size
        self.resize(
            self._scaling_helper.scaled_size(1200),
            self._scaling_helper.scaled_size(800)
        )
        
        # Restore window state
        window_state_manager.restore_window_state(self)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create status bar
        self._create_status_bar()
        
        # Create system tray
        self._create_system_tray()
        
        # Connect to zoom change signal
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
        # Create central widget and main layout
        self.central_widget = QWidget()
        # DinoPit brand with desaturated blue background
        self.central_widget.setStyleSheet("background-color: #2B3A52;")
        self.setCentralWidget(self.central_widget)
        
        # Create main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Use font metrics for consistent spacing
        font_metrics = self.fontMetrics()
        margin = font_metrics.height() // 2  # Half line height
        
        self.main_layout.setContentsMargins(margin, margin, margin, margin)
        self.main_layout.setSpacing(margin)
        
        # Create content layout (for the three main panels)
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(margin)
        
        # Create widgets
        # Chat history will be created after db_manager is set
        self.chat_history = None
        self.tabbed_content = TabbedContentWidget()
        self.artifacts = ArtifactsWidget()
        
        # Set main window reference for security pipeline
        self.tabbed_content.set_main_window_ref(self)
        
        # Connect tabbed content signals for watchdog control
        self.tabbed_content.watchdog_control_requested.connect(
            self.handle_watchdog_control
        )
        self.tabbed_content.watchdog_config_changed.connect(
            self.handle_watchdog_config_change
        )
        
        # Add placeholder for chat history (will be replaced when DB is ready)
        self.chat_history_placeholder = QLabel("Loading chat history...")
        self.chat_history_placeholder.setFixedWidth(300)
        self.chat_history_placeholder.setStyleSheet("""
            background-color: #344359;
            color: white;
            padding: 20px;
        """)
        self.content_layout.addWidget(self.chat_history_placeholder)
        # Give more space to tabbed content
        self.content_layout.addWidget(self.tabbed_content, 1)
        self.content_layout.addWidget(self.artifacts)
        
        # Add content layout to main layout - give more space to content
        self.main_layout.addLayout(self.content_layout, 1)
        
        # Create bottom panel splitter for notifications and metrics
        self.bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        # Reduced height for more compact bottom panel (150-200px scaled)
        self.bottom_splitter.setMaximumHeight(
            self._scaling_helper.scaled_size(175)
        )
        
        # Create notification widget (initially hidden)
        self.notification_widget = NotificationWidget()
        self.notification_widget.hide()
        
        # Create metrics widget (initially hidden)
        self.metrics_widget = MetricsWidget()
        # Remove width constraint to allow horizontal stretching
        # self.metrics_widget.setMaximumWidth(
        #     self._scaling_helper.scaled_size(400)
        # )
        self.metrics_widget.hide()
        
        # Add widgets to bottom splitter
        self.bottom_splitter.addWidget(self.notification_widget)
        self.bottom_splitter.addWidget(self.metrics_widget)
        
        # Set initial proportions based on window width
        self._update_bottom_splitter_sizes()
        
        # Add bottom splitter to main layout
        self.main_layout.addWidget(self.bottom_splitter)
        self.bottom_splitter.hide()  # Hide entire bottom panel initially
        
        # Connect splitter moved signal to save state
        self.bottom_splitter.splitterMoved.connect(
            self._save_bottom_splitter_state
        )
        
        # Restore bottom splitter state if available
        self._restore_bottom_splitter_state()
        
        # Restore saved zoom level
        self._restore_zoom_level()
        
    def _update_bottom_splitter_sizes(self):
        """Set bottom splitter proportions based on window width."""
        total_width = self.width()
        self.bottom_splitter.setSizes([
            int(total_width * 0.7),  # 70% for notifications
            int(total_width * 0.3)   # 30% for metrics
        ])
    
    def resizeEvent(self, event):
        """Handle resize events to update splitter proportions."""
        super().resizeEvent(event)
        if hasattr(self, 'bottom_splitter'):
            self._update_bottom_splitter_sizes()
        
    def watchdog_alert_handler(self, level: AlertLevel, message: str):
        """Handle watchdog alerts by displaying them in the GUI.
        
        This method serves as the alert_callback for the Watchdog system.
        It receives alerts and displays them in the GUI notification panel.
        
        Args:
            level: AlertLevel enum indicating severity
            message: The alert message to display
        """
        # Show bottom splitter and notification widget if hidden
        if self.bottom_splitter.isHidden():
            self.bottom_splitter.show()
        if self.notification_widget.isHidden():
            self.notification_widget.show()
            
        # Add the notification
        self.notification_widget.add_notification(level, message)
        
        # Log the alert as well
        if hasattr(self, 'logger'):
            log_method = {
                AlertLevel.INFO: self.logger.info,
                AlertLevel.WARNING: self.logger.warning,
                AlertLevel.CRITICAL: self.logger.critical
            }.get(level, self.logger.info)
            log_method(f"Watchdog Alert: {message}")
            
    def watchdog_metrics_handler(self, metrics):
        """Handle watchdog metrics updates for real-time display.
        
        This method serves as the metrics_callback for the Watchdog system.
        It receives SystemMetrics objects and updates the GUI display.
        The MetricsWidget.update_metrics slot is thread-safe by default.
        
        Args:
            metrics: SystemMetrics object from Watchdog
        """
        # Show bottom splitter and metrics widget if hidden
        if self.bottom_splitter.isHidden():
            self.bottom_splitter.show()
        if self.metrics_widget.isHidden():
            self.metrics_widget.show()
            
        # Directly call the update_metrics slot - Qt handles thread safety
        # The @Slot decorator in MetricsWidget ensures thread-safe execution
        self.metrics_widget.update_metrics(metrics)
            
    def toggle_notifications(self):
        """Toggle the visibility of the notification panel."""
        if self.notification_widget.isVisible():
            self.notification_widget.hide()
            # Hide bottom splitter if both panels are hidden
            if self.metrics_widget.isHidden():
                self.bottom_splitter.hide()
        else:
            self.bottom_splitter.show()
            self.notification_widget.show()
            
    def toggle_metrics(self):
        """Toggle the visibility of the metrics panel."""
        if self.metrics_widget.isVisible():
            self.metrics_widget.hide()
            # Hide bottom splitter if both panels are hidden
            if self.notification_widget.isHidden():
                self.bottom_splitter.hide()
        else:
            self.bottom_splitter.show()
            self.metrics_widget.show()
            
    def clear_notifications(self):
        """Clear all notifications from the panel."""
        self.notification_widget.clear_all()
        
    def set_logger(self, logger):
        """Set the logger instance for the main window.
        
        Args:
            logger: The logger instance to use
        """
        self.logger = logger
        
    def set_watchdog_config(self, max_processes: int):
        """Set watchdog configuration values for the metrics display.
        
        Args:
            max_processes: Maximum allowed DinoAir processes
        """
        self.metrics_widget.set_max_processes(max_processes)
        
    def set_app_instance(self, app_instance):
        """Set reference to the main application instance.
        
        This allows the MainWindow to access the watchdog instance
        and control it based on user actions in the settings page.
        
        Args:
            app_instance: The DinoAirApp instance
        """
        self.app_instance = app_instance
        self.watchdog_ref = app_instance.watchdog if app_instance else None
        
        # Pass watchdog reference to tabbed content for security pipeline
        self.tabbed_content.set_watchdog_ref(self.watchdog_ref)
        
        # Pass watchdog reference to settings page
        settings_page = self.tabbed_content.get_settings_page()
        if settings_page:
            settings_page.set_watchdog_reference(self.watchdog_ref)
            
    def set_database_manager(self, db_manager):
        """Set the database manager and initialize chat components.
        
        Args:
            db_manager: The DatabaseManager instance
        """
        self.db_manager = db_manager
        
        if self.db_manager:
            # Import here to avoid circular imports
            from ..database.chat_history_db import ChatHistoryDatabase
            
            # Create chat database manager
            self.chat_db = ChatHistoryDatabase(self.db_manager)
            
            # Create enhanced chat history widget
            self.chat_history = EnhancedChatHistoryWidget(self.chat_db)
            
            # Replace placeholder with actual widget
            if hasattr(self, 'chat_history_placeholder'):
                # Get index of placeholder
                index = self.content_layout.indexOf(
                    self.chat_history_placeholder
                )
                # Remove placeholder
                self.content_layout.removeWidget(self.chat_history_placeholder)
                self.chat_history_placeholder.deleteLater()
                # Insert chat history at same position
                self.content_layout.insertWidget(index, self.chat_history)
                
            # Connect chat history to tabbed content
            self.chat_history.session_selected.connect(
                self._on_chat_session_selected
            )
            
            # Update tabbed content with chat database
            self.tabbed_content.set_chat_database(self.chat_db)
            
    def set_db_manager(self, db_manager):
        """Alias for set_database_manager for backward compatibility.
        
        Args:
            db_manager: The DatabaseManager instance
        """
        self.set_database_manager(db_manager)
            
    def _on_chat_session_selected(self, session_id: str):
        """Handle chat session selection from history.
        
        Args:
            session_id: The selected session ID
        """
        # Switch to chat tab
        self.tabbed_content.tab_widget.setCurrentIndex(0)
        
        # Load the session in chat tab
        chat_tab = self.tabbed_content.get_chat_tab()
        if chat_tab:
            chat_tab.load_session(session_id)
            
    def handle_watchdog_control(self, action: str):
        """Handle watchdog control requests from settings page.
        
        Args:
            action: The control action ('start', 'stop', 'restart')
        """
        if not self.app_instance:
            return
            
        if action == 'start':
            self._start_watchdog()
        elif action == 'stop':
            self._stop_watchdog()
        elif action == 'restart':
            self._restart_watchdog()
            
    def _start_watchdog(self):
        """Start the watchdog monitoring."""
        try:
            if self.watchdog_ref and not self.watchdog_ref._monitoring:
                self.watchdog_ref.start_monitoring()
                # Update settings page reference
                settings_page = (
                    self.tabbed_content.get_settings_page()
                )
                if settings_page:
                    settings_page.set_watchdog_reference(
                        self.watchdog_ref
                    )
            elif not self.watchdog_ref and self.app_instance:
                # Create new watchdog instance
                if hasattr(self.app_instance, 'initialize_watchdog'):
                    self.app_instance.initialize_watchdog()
                    if hasattr(self.app_instance, 'watchdog'):
                        self.watchdog_ref = self.app_instance.watchdog
                        if self.watchdog_ref:
                            self.watchdog_ref.start_monitoring()
                            # Update settings page reference
                            settings_page = (
                                self.tabbed_content.get_settings_page()
                            )
                            if settings_page:
                                settings_page.set_watchdog_reference(
                                    self.watchdog_ref
                                )
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Failed to start watchdog: {e}")
                
    def _stop_watchdog(self):
        """Stop the watchdog monitoring."""
        try:
            if self.watchdog_ref and self.watchdog_ref._monitoring:
                self.watchdog_ref.stop_monitoring()
                # Don't clear the reference, keep it for status display
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Failed to stop watchdog: {e}")
                
    def _restart_watchdog(self):
        """Restart the watchdog with new configuration."""
        self._stop_watchdog()
        # Small delay to ensure clean shutdown
        QTimer.singleShot(100, self._start_watchdog)
        
    def handle_watchdog_config_change(self, config: dict):
        """Handle watchdog configuration changes from settings page.
        
        Args:
            config: Dictionary with new watchdog configuration
        """
        if not self.watchdog_ref:
            return
            
        # Update watchdog configuration
        if 'vram_threshold_percent' in config:
            self.watchdog_ref.vram_threshold = config['vram_threshold_percent']
        if 'max_dinoair_processes' in config:
            self.watchdog_ref.max_processes = config['max_dinoair_processes']
            # Update metrics widget
            self.metrics_widget.set_max_processes(
                config['max_dinoair_processes']
            )
        if 'check_interval_seconds' in config:
            self.watchdog_ref.check_interval = config['check_interval_seconds']
        if 'self_terminate_on_critical' in config:
            self.watchdog_ref.self_terminate_on_critical = (
                config['self_terminate_on_critical']
            )
    
    def _save_bottom_splitter_state(self):
        """Save the bottom splitter state when it changes."""
        if self.bottom_splitter.isVisible():
            window_state_manager.save_splitter_from_widget(
                "main_bottom", self.bottom_splitter
            )
    
    def _restore_bottom_splitter_state(self):
        """Restore the bottom splitter state if available."""
        saved_state = window_state_manager.get_splitter_state("main_bottom")
        if saved_state:
            # Don't restore if the splitter is hidden
            if not self.bottom_splitter.isHidden():
                window_state_manager.restore_splitter_to_widget(
                    "main_bottom", self.bottom_splitter
                )
    
    def _create_menu_bar(self):
        """Create the application menu bar with zoom controls."""
        menubar = self.menuBar()
        
        # Create View menu
        view_menu = menubar.addMenu("&View")
        
        # Zoom In action
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self._zoom_in)
        view_menu.addAction(zoom_in_action)
        
        # Zoom Out action
        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self._zoom_out)
        view_menu.addAction(zoom_out_action)
        
        # Reset Zoom action
        reset_zoom_action = QAction("&Reset Zoom", self)
        reset_zoom_action.setShortcut(QKeySequence("Ctrl+0"))
        reset_zoom_action.triggered.connect(self._reset_zoom)
        view_menu.addAction(reset_zoom_action)
        
        # Separator
        view_menu.addSeparator()
        
        # File Search shortcut
        file_search_action = QAction("&File Search", self)
        file_search_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        file_search_action.triggered.connect(self._open_file_search)
        view_menu.addAction(file_search_action)
        
        # Separator
        view_menu.addSeparator()
        
        # Custom zoom levels submenu
        zoom_submenu = view_menu.addMenu("&Zoom Level")
        
        # Predefined zoom levels
        zoom_levels = [75, 100, 125, 150, 200]
        for level in zoom_levels:
            action = QAction(f"{level}%", self)
            action.triggered.connect(
                lambda checked, lv=level: self._set_zoom_level(lv / 100.0)
            )
            zoom_submenu.addAction(action)
    
    def _create_status_bar(self):
        """Create the status bar with zoom indicator."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Create zoom indicator label
        self.zoom_label = QLabel()
        self.zoom_label.setStyleSheet("color: #FFFFFF;")
        self._update_zoom_label()
        
        # Add zoom label to status bar (permanent widget on the right)
        self.status_bar.addPermanentWidget(self.zoom_label)
    
    def _update_zoom_label(self):
        """Update the zoom indicator in the status bar."""
        zoom_level = self._scaling_helper.get_current_zoom_level()
        self.zoom_label.setText(f"Zoom: {int(zoom_level * 100)}%")
    
    def _zoom_in(self):
        """Handle zoom in action."""
        self._scaling_helper.zoom_in()
    
    def _zoom_out(self):
        """Handle zoom out action."""
        self._scaling_helper.zoom_out()
    
    def _reset_zoom(self):
        """Handle reset zoom action."""
        self._scaling_helper.reset_zoom()
    
    def _set_zoom_level(self, level: float):
        """Set a specific zoom level."""
        self._scaling_helper.set_zoom_level(level)
    
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes."""
        # Update zoom label
        self._update_zoom_label()
        
        # Save new zoom level to window state
        window_state_manager.save_zoom_level(zoom_level)
        
        # Refresh all UI elements
        self._refresh_scaled_ui()
    
    def _refresh_scaled_ui(self):
        """Refresh all UI elements that use scaled values."""
        # Update font metrics-based margins and spacing
        font_metrics = self.fontMetrics()
        margin = font_metrics.height() // 2
        
        self.main_layout.setContentsMargins(margin, margin, margin, margin)
        self.main_layout.setSpacing(margin)
        self.content_layout.setSpacing(margin)
        
        # Update bottom splitter max height (compact layout)
        self.bottom_splitter.setMaximumHeight(
            self._scaling_helper.scaled_size(175)
        )
        
        # Metrics widget has no width constraint for horizontal layout
        # Removed the setMaximumWidth call
        
        # Force style refresh on all widgets by re-applying stylesheets
        # This ensures any scaled values in stylesheets are updated
        self._refresh_widget_styles(self.central_widget)
        
        # Force layout update
        self.central_widget.updateGeometry()
        self.update()
    
    def _refresh_widget_styles(self, widget: QWidget):
        """Recursively refresh widget stylesheets."""
        # Get current stylesheet
        current_style = widget.styleSheet()
        
        # If widget has a stylesheet, force refresh by toggling
        if current_style:
            widget.setStyleSheet("")
            widget.setStyleSheet(current_style)
        
        # Recursively refresh child widgets
        for child in widget.findChildren(QWidget):
            # Skip if we've already processed this widget
            # (findChildren returns all descendants, not just direct children)
            if child.parent() == widget:
                self._refresh_widget_styles(child)
    
    def _restore_zoom_level(self):
        """Restore saved zoom level from window state."""
        saved_zoom = window_state_manager.get_zoom_level()
        if saved_zoom is not None:
            try:
                zoom_level = float(saved_zoom)
                self._scaling_helper.set_zoom_level(zoom_level)
            except (ValueError, TypeError):
                # Invalid saved value, use default
                pass
    
    def _open_file_search(self):
        """Open the File Search tab."""
        # Find the File Search tab index
        for i, tab in enumerate(self.tabbed_content.tabs):
            if tab['id'] == 'file_search':
                self.tabbed_content.tab_widget.setCurrentIndex(i)
                break
    
    def _create_system_tray(self):
        """Create system tray icon and menu."""
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.logger.warning("System tray not available")
            return
        
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Set icon (use a simple colored icon for now)
        icon = QIcon()
        # Create a simple pixmap for the icon
        from PySide6.QtGui import QPixmap, QPainter, QBrush
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(DinoPitColors.DINOPIT_ORANGE))
        painter.drawEllipse(0, 0, 16, 16)
        painter.end()
        icon.addPixmap(pixmap)
        self.tray_icon.setIcon(icon)
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Show/Hide action
        show_action = QAction("Show/Hide", self)
        show_action.triggered.connect(self._toggle_window)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        # Quick Search action
        quick_search_action = QAction("🔍 Quick Search", self)
        quick_search_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        quick_search_action.triggered.connect(self._show_quick_search)
        tray_menu.addAction(quick_search_action)
        
        # File Search action
        file_search_action = QAction("📁 Open File Search", self)
        file_search_action.triggered.connect(self._open_file_search_from_tray)
        tray_menu.addAction(file_search_action)
        
        tray_menu.addSeparator()
        
        # Indexing status action (disabled, just for display)
        self.indexing_status_action = QAction("📊 Indexing: Idle", self)
        self.indexing_status_action.setEnabled(False)
        tray_menu.addAction(self.indexing_status_action)
        
        tray_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        tray_menu.addAction(exit_action)
        
        # Set menu and show icon
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("DinoAir - File Search Ready")
        
        # Connect double-click to show/hide
        self.tray_icon.activated.connect(self._on_tray_activated)
        
        # Show the tray icon
        self.tray_icon.show()
    
    def _toggle_window(self):
        """Toggle window visibility."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
    
    def _show_quick_search(self):
        """Show quick search dialog."""
        # First, ensure the window is visible
        if not self.isVisible():
            self.show()
            self.raise_()
            self.activateWindow()
        
        # Then open file search
        self._open_file_search()
        
        # Focus on search input if available
        for i, tab in enumerate(self.tabbed_content.tabs):
            if tab['id'] == 'file_search':
                file_search_page = self.tabbed_content.tab_widget.widget(i)
                if hasattr(file_search_page, 'search_input'):
                    search_input = getattr(file_search_page, 'search_input')
                    search_input.setFocus()
                    search_input.selectAll()
                break
    
    def _open_file_search_from_tray(self):
        """Open file search from system tray."""
        # Show window first
        if not self.isVisible():
            self.show()
            self.raise_()
            self.activateWindow()
        
        # Then open file search
        self._open_file_search()
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_window()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self._show_quick_search()
    
    def update_indexing_status(self, status: str, details: str = ""):
        """Update indexing status in system tray.
        
        Args:
            status: Status text (e.g., "Indexing", "Idle", "Error")
            details: Optional details for tooltip
        """
        if hasattr(self, 'indexing_status_action'):
            self.indexing_status_action.setText(f"📊 Indexing: {status}")
        
        if hasattr(self, 'tray_icon'):
            tooltip = f"DinoAir - {status}"
            if details:
                tooltip += f"\n{details}"
            self.tray_icon.setToolTip(tooltip)
    
    def show_tray_notification(self, title: str, message: str,
                               icon: QSystemTrayIcon.MessageIcon =
                               QSystemTrayIcon.MessageIcon.Information):
        """Show a system tray notification.
        
        Args:
            title: Notification title
            message: Notification message
            icon: Icon type for the notification
        """
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, icon, 5000)
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event to save state."""
        # Check if we should minimize to tray instead
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            # Just hide the window instead of closing
            event.ignore()
            self.hide()
            self.show_tray_notification(
                "DinoAir Minimized",
                "DinoAir is still running in the system tray.",
                QSystemTrayIcon.MessageIcon.Information
            )
        else:
            # Actually close
            window_state_manager.save_window_state(self)
            # Save current zoom level
            window_state_manager.save_zoom_level(
                self._scaling_helper.get_current_zoom_level()
            )
            event.accept()
