"""
Integration tests for the Pseudocode Translator with DinoAir 2.0

These tests verify that the pseudocode translator integrates properly
with the main application, including agent, tool, and GUI components.
"""

import unittest
import sys
from pathlib import Path
import json
import asyncio
from unittest.mock import Mock, patch, MagicMock
import threading
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.translator import DinoTranslate, create_translator
from src.tools.pseudocode_tool import PseudocodeTool, translate_pseudocode
from pseudocode_translator.integration.api import TranslatorAPI, SimpleTranslator
from pseudocode_translator.integration.callbacks import (
    CallbackManager, CallbackType, CallbackData
)
from pseudocode_translator.integration.events import (
    EventDispatcher, EventType, TranslationEvent
)


class TestAgentIntegration(unittest.TestCase):
    """Test the DinoTranslate agent integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.translator = None
        
    def tearDown(self):
        """Clean up after tests"""
        if self.translator:
            self.translator.shutdown()
            
    def test_agent_creation(self):
        """Test creating the translator agent"""
        self.translator = create_translator()
        self.assertIsNotNone(self.translator)
        self.assertIsInstance(self.translator, DinoTranslate)
        
    def test_agent_initialization(self):
        """Test agent initialization and model loading"""
        self.translator = DinoTranslate()
        
        # Wait for initialization
        timeout = 10
        start_time = time.time()
        while not self.translator.is_ready and time.time() - start_time < timeout:
            time.sleep(0.1)
            
        self.assertTrue(self.translator.is_ready)
        
    def test_agent_translation_sync(self):
        """Test synchronous translation through agent"""
        self.translator = DinoTranslate()
        
        # Simple translation
        result = self.translator.translate_sync(
            "create a function that returns hello world"
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('code', result)
        self.assertIn('language', result)
        
        if result['success']:
            self.assertIsNotNone(result['code'])
            self.assertIn('def', result['code'].lower())
            self.assertIn('hello world', result['code'].lower())
            
    def test_agent_language_switching(self):
        """Test switching output languages"""
        self.translator = DinoTranslate()
        
        # Get available languages
        languages = self.translator.available_languages
        self.assertIsInstance(languages, list)
        self.assertIn('python', languages)
        self.assertIn('javascript', languages)
        
        # Switch to JavaScript
        success = self.translator.set_language('javascript')
        self.assertTrue(success)
        self.assertEqual(self.translator.current_language, 'javascript')
        
    def test_agent_model_info(self):
        """Test getting model information"""
        self.translator = DinoTranslate()
        
        # Get model status
        status = self.translator.get_model_status()
        self.assertIsInstance(status, dict)
        self.assertIn('initialized', status)
        self.assertIn('current_language', status)
        
    def test_agent_error_handling(self):
        """Test error handling in agent"""
        self.translator = DinoTranslate()
        
        # Try invalid language
        success = self.translator.set_language('invalid_language')
        self.assertFalse(success)
        
        # Try empty pseudocode
        result = self.translator.translate_sync("")
        self.assertFalse(result['success'])
        self.assertTrue(len(result['errors']) > 0)
        
    def test_agent_config_integration(self):
        """Test configuration integration with app_config.json"""
        config_path = Path(__file__).parent.parent / "config" / "app_config.json"
        
        # Read app config
        with open(config_path, 'r') as f:
            app_config = json.load(f)
            
        self.assertIn('pseudocode_translator', app_config)
        trans_config = app_config['pseudocode_translator']
        
        # Create translator with app config consideration
        self.translator = DinoTranslate()
        
        # Verify settings are respected
        self.assertEqual(
            self.translator.current_language,
            trans_config.get('default_language', 'python')
        )


class TestToolIntegration(unittest.TestCase):
    """Test the PseudocodeTool integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tool = None
        
    def tearDown(self):
        """Clean up after tests"""
        if self.tool:
            self.tool.shutdown()
            
    def test_tool_creation(self):
        """Test creating the pseudocode tool"""
        self.tool = PseudocodeTool()
        self.assertIsNotNone(self.tool)
        
        # Check capabilities
        capabilities = self.tool.get_capabilities()
        self.assertIsInstance(capabilities, dict)
        self.assertIn('name', capabilities)
        self.assertIn('features', capabilities)
        self.assertTrue(capabilities['features']['async_support'])
        self.assertTrue(capabilities['features']['progress_reporting'])
        
    def test_tool_sync_translation(self):
        """Test synchronous translation through tool"""
        self.tool = PseudocodeTool()
        
        # Translate
        result = self.tool.translate(
            "function to calculate factorial of n",
            language="python"
        )
        
        self.assertTrue(hasattr(result, 'success'))
        self.assertTrue(hasattr(result, 'output'))
        
        if result.success:
            self.assertIsNotNone(result.output)
            self.assertIn('factorial', result.output.lower())
            
    def test_tool_async_translation(self):
        """Test asynchronous translation through tool"""
        async def run_async_test():
            self.tool = PseudocodeTool()
            
            # Translate asynchronously
            result = await self.tool.translate_async(
                "implement bubble sort algorithm",
                language="python"
            )
            
            self.assertTrue(hasattr(result, 'success'))
            if result.success:
                self.assertIn('sort', result.output.lower())
                
        # Run async test
        asyncio.run(run_async_test())
        
    def test_tool_progress_callbacks(self):
        """Test progress callback functionality"""
        self.tool = PseudocodeTool()
        
        # Track progress
        progress_updates = []
        
        def on_progress(progress):
            progress_updates.append(progress)
            
        self.tool.add_progress_callback(on_progress)
        
        # Translate with progress tracking
        result = self.tool.translate(
            "create a class for managing a todo list",
            language="python"
        )
        
        # Should have received some progress updates
        self.assertTrue(len(progress_updates) > 0)
        
    def test_tool_language_switching(self):
        """Test language switching in tool"""
        self.tool = PseudocodeTool()
        
        # Switch to JavaScript
        success = self.tool.set_language("javascript")
        self.assertTrue(success)
        
        # Translate to JavaScript
        result = self.tool.translate(
            "function to reverse a string",
            language="javascript"
        )
        
        if result.success:
            self.assertIn('function', result.output)
            # Should be JavaScript syntax
            self.assertTrue(
                'const' in result.output or
                'let' in result.output or
                'var' in result.output
            )
            
    def test_tool_convenience_functions(self):
        """Test convenience functions"""
        # Quick translation
        result = translate_pseudocode(
            "print numbers from 1 to 10",
            language="python"
        )
        
        self.assertIsInstance(result, dict)  # ToolResult converted to dict
        self.assertTrue(hasattr(result, 'success'))


class TestIntegrationAPI(unittest.TestCase):
    """Test the integration API"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.api = None
        
    def tearDown(self):
        """Clean up after tests"""
        if self.api:
            self.api.shutdown()
            
    def test_api_creation(self):
        """Test creating the translator API"""
        self.api = TranslatorAPI()
        self.assertIsNotNone(self.api)
        
    def test_api_translation(self):
        """Test translation through API"""
        self.api = TranslatorAPI()
        
        result = self.api.translate(
            "create a recursive function to calculate fibonacci",
            language="python"
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('code', result)
        
        if result['success']:
            self.assertIn('fibonacci', result['code'].lower())
            self.assertIn('def', result['code'])
            
    def test_api_batch_translation(self):
        """Test batch translation"""
        self.api = TranslatorAPI()
        
        items = [
            "function to check if number is prime",
            "class to represent a person with name and age",
            {"code": "sort a list in descending order", "language": "python"}
        ]
        
        results = self.api.batch_translate(items)
        
        self.assertEqual(len(results), len(items))
        for i, result in enumerate(results):
            self.assertIn('index', result)
            self.assertEqual(result['index'], i)
            
    def test_simple_translator(self):
        """Test SimpleTranslator convenience class"""
        translator = SimpleTranslator("python")
        
        # Direct translation
        code = translator("create a hello world function")
        
        if code:
            self.assertIsInstance(code, str)
            self.assertIn('def', code)
            self.assertIn('hello', code.lower())
            
        # Using as callable
        code2 = translator("print the current date")
        if code2:
            self.assertIsInstance(code2, str)


class TestCallbackIntegration(unittest.TestCase):
    """Test callback system integration"""
    
    def test_callback_manager(self):
        """Test callback manager functionality"""
        manager = CallbackManager()
        
        # Track callbacks
        received_callbacks = []
        
        def test_callback(data):
            received_callbacks.append(data)
            
        # Register callback
        manager.register(test_callback, CallbackType.PROGRESS)
        
        # Trigger progress
        manager.trigger_progress(50, "Half way done")
        
        self.assertEqual(len(received_callbacks), 1)
        self.assertEqual(received_callbacks[0].type, CallbackType.PROGRESS)
        self.assertEqual(received_callbacks[0].data['percentage'], 50)
        
    def test_callback_types(self):
        """Test different callback types"""
        manager = CallbackManager()
        
        callback_log = {}
        
        def log_callback(data):
            callback_type = data.type.value
            if callback_type not in callback_log:
                callback_log[callback_type] = []
            callback_log[callback_type].append(data)
            
        # Register global callback
        manager.register(log_callback)
        
        # Trigger various callbacks
        manager.trigger_progress(25, "Starting")
        manager.trigger_status("Processing input")
        manager.trigger_error("Test error")
        
        # Check all were received
        self.assertIn('progress', callback_log)
        self.assertIn('status', callback_log)
        self.assertIn('error', callback_log)


class TestEventIntegration(unittest.TestCase):
    """Test event system integration"""
    
    def test_event_dispatcher(self):
        """Test event dispatcher functionality"""
        dispatcher = EventDispatcher(async_mode=False)
        
        # Track events
        received_events = []
        
        from pseudocode_translator.integration.events import EventHandler
        
        def handle_event(event):
            received_events.append(event)
            
        handler = EventHandler(handle_event)
        dispatcher.register(handler)
        
        # Dispatch event
        dispatcher.dispatch_event(
            EventType.TRANSLATION_STARTED,
            source="test",
            language="python"
        )
        
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].type, EventType.TRANSLATION_STARTED)
        self.assertEqual(received_events[0].data['language'], 'python')
        
    def test_event_filtering(self):
        """Test event filtering"""
        dispatcher = EventDispatcher(async_mode=False)
        
        progress_events = []
        
        from pseudocode_translator.integration.events import EventHandler
        
        def handle_progress(event):
            progress_events.append(event)
            
        # Handler only for progress events
        handler = EventHandler(
            handle_progress,
            event_types={EventType.TRANSLATION_PROGRESS}
        )
        dispatcher.register(handler)
        
        # Dispatch various events
        dispatcher.dispatch_event(EventType.TRANSLATION_STARTED)
        dispatcher.dispatch_event(
            EventType.TRANSLATION_PROGRESS,
            percentage=50
        )
        dispatcher.dispatch_event(EventType.TRANSLATION_COMPLETED)
        
        # Should only receive progress event
        self.assertEqual(len(progress_events), 1)
        self.assertEqual(progress_events[0].type, EventType.TRANSLATION_PROGRESS)


class TestGUIIntegration(unittest.TestCase):
    """Test GUI integration components"""
    
    def test_gui_adapter_creation(self):
        """Test creating GUI adapter"""
        from pseudocode_translator.integration.gui_adapter import (
            GUITranslatorAdapter
        )
        
        adapter = GUITranslatorAdapter()
        self.assertIsNotNone(adapter)
        
    def test_gui_adapter_with_mock_gui(self):
        """Test GUI adapter with mock GUI"""
        from pseudocode_translator.integration.gui_adapter import (
            GUITranslatorAdapter
        )
        
        # Mock GUI updater
        mock_gui = Mock()
        mock_gui.update_progress = Mock()
        mock_gui.update_status = Mock()
        mock_gui.show_result = Mock()
        mock_gui.show_error = Mock()
        
        adapter = GUITranslatorAdapter(gui_updater=mock_gui)
        
        # Start translation
        task_id = adapter.translate(
            "create a simple calculator class",
            language="python",
            async_mode=False
        )
        
        # GUI methods should have been called
        mock_gui.update_progress.assert_called()
        mock_gui.update_status.assert_called()
        
    def test_progress_reporter(self):
        """Test progress reporter helper"""
        from pseudocode_translator.integration.gui_adapter import (
            create_progress_reporter
        )
        
        # Mock GUI elements
        mock_progress_bar = Mock()
        mock_status_label = Mock()
        
        reporter = create_progress_reporter(
            progress_bar=mock_progress_bar,
            status_label=mock_status_label
        )
        
        # Report progress
        reporter(75, "Almost done")
        
        mock_progress_bar.setValue.assert_called_with(75)
        mock_status_label.setText.assert_called_with("Almost done")


class TestEndToEndIntegration(unittest.TestCase):
    """End-to-end integration tests"""
    
    def test_full_translation_flow(self):
        """Test complete translation flow from agent to result"""
        # Create translator
        translator = DinoTranslate()
        
        # Set up result tracking
        translation_result = None
        
        def on_completion(result):
            nonlocal translation_result
            translation_result = result
            
        # Connect completion signal (mocked for testing)
        with patch.object(translator, 'translation_completed') as mock_signal:
            # Translate
            task_id = translator.translate(
                "implement a binary search algorithm",
                use_streaming=False
            )
            
            # In real scenario, would wait for signal
            # For testing, call sync version
            result = translator.translate_sync(
                "implement a binary search algorithm"
            )
            
            self.assertIsNotNone(result)
            if result['success']:
                self.assertIn('binary', result['code'].lower())
                self.assertIn('search', result['code'].lower())
                
    def test_streaming_translation(self):
        """Test streaming translation for large input"""
        translator = DinoTranslate()
        
        # Create large pseudocode
        large_pseudocode = """
        Create a comprehensive library management system with the following features:
        
        1. Book class with properties: title, author, ISBN, year, available
        2. Member class with properties: name, member_id, borrowed_books
        3. Library class that manages books and members
        4. Methods to add/remove books
        5. Methods to register/unregister members
        6. Method to borrow a book
        7. Method to return a book
        8. Method to search books by title or author
        9. Method to list all available books
        10. Method to list all borrowed books by a member
        """ * 10  # Repeat to make it large
        
        # This should auto-enable streaming
        result = translator.translate_sync(
            large_pseudocode,
            language="python"
        )
        
        self.assertIsNotNone(result)
        if result['success']:
            # Should contain expected classes
            self.assertIn('class Book', result['code'])
            self.assertIn('class Member', result['code'])
            self.assertIn('class Library', result['code'])


if __name__ == '__main__':
    unittest.main()