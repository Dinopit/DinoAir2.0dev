"""
Tests for the updated LLM interface with model management system
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from pseudocode_translator.llm_interface import LLMInterface
from pseudocode_translator.models.base import (
    BaseModel, ModelCapabilities, ModelMetadata, ModelFormat
)
from pseudocode_translator.models.registry import ModelRegistry
from pseudocode_translator.config import LLMConfig


# Create a mock model for testing
class MockModel(BaseModel):
    """Mock model implementation for testing"""
    
    def __init__(self, config):
        super().__init__(config)
        self.translation_count = 0
        self.refinement_count = 0
    
    @property
    def metadata(self) -> ModelMetadata:
        """Return mock metadata"""
        return ModelMetadata(
            name="mock",
            display_name="Mock Model",
            version="1.0",
            description="Mock model for testing",
            author="Test Suite",
            license="MIT",
            format=ModelFormat.GGUF,
            filename_pattern="*.gguf"
        )
    
    @property
    def capabilities(self) -> ModelCapabilities:
        """Return mock capabilities"""
        return ModelCapabilities(
            supported_languages=["python"],
            max_context_length=2048,
            min_memory_gb=1.0,
            recommended_memory_gb=2.0,
            model_size_gb=2.0
        )
    
    def initialize(self, model_path: Path, **kwargs) -> None:
        """Initialize the mock model"""
        self._initialized = True
        self._model = Mock()
    
    def generate(self,
                 prompt: str,
                 max_tokens: int = 512,
                 temperature: float = 0.3,
                 top_p: float = 0.9,
                 top_k: int = 40,
                 stop_sequences=None,
                 **kwargs) -> str:
        """Generate mock response"""
        if not self._initialized:
            raise RuntimeError("Model not initialized")
        return f"Generated: {prompt[:20]}..."
    
    def translate_instruction(self, instruction: str, context=None) -> str:
        """Translate instruction to code"""
        self.translation_count += 1
        return (f"# Translation {self.translation_count}\n"
                f"# {instruction}\nprint('Hello')")
    
    def refine_code(self, code: str, error_context: str,
                    max_attempts=1) -> str:
        """Refine code based on error"""
        self.refinement_count += 1
        return (f"# Refined {self.refinement_count}\n"
                f"{code}\n# Fixed: {error_context}")


class TestLLMInterfaceUpdated:
    """Test the updated LLM interface with model management"""
    
    def setup_method(self):
        """Setup for each test"""
        # Clear registry
        ModelRegistry.clear()
        
        # Register mock models
        ModelRegistry.register(MockModel, "mock", ["test"])
        ModelRegistry.register(MockModel, "mock2", ["test2"])
        
        # Create test config
        self.config = LLMConfig(
            model_type="mock",
            model_path="/test/models",
            model_file="mock.gguf",
            cache_enabled=True,
            temperature=0.5
        )
    
    def teardown_method(self):
        """Cleanup after each test"""
        # Clear registry
        ModelRegistry.clear()
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_initialization(self, mock_exists):
        """Test interface initialization"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        
        assert interface.config == self.config
        assert interface._model_name is None
        assert not interface._initialized
        assert interface._manager is not None
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_initialize_model(self, mock_exists):
        """Test model initialization"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        interface.initialize_model()
        
        assert interface._initialized
        assert interface.model is not None
        assert isinstance(interface.model, MockModel)
        assert interface._model_name == "mock"
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_translate(self, mock_exists):
        """Test translation"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        
        result = interface.translate("print hello world")
        
        assert result is not None
        assert "Translation 1" in result
        assert "print hello world" in result
        assert "print('Hello')" in result
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_refine_code(self, mock_exists):
        """Test code refinement"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        
        code = "print('test')"
        error = "SyntaxError"
        
        result = interface.refine_code(code, error)
        
        assert result is not None
        assert "Refined 1" in result
        assert code in result
        assert "Fixed: SyntaxError" in result
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_switch_model(self, mock_exists):
        """Test model switching"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        interface.initialize_model()
        
        # Initially using mock
        assert interface.get_current_model() == "mock"
        
        # Switch to mock2
        interface.switch_model("mock2")
        
        assert interface.get_current_model() == "mock2"
        assert interface.model is not None
        assert interface._initialized
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_list_available_models(self, mock_exists):
        """Test listing available models"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        
        models = interface.list_available_models()
        
        assert "mock" in models
        assert "mock2" in models
        assert len(models) == 2
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_get_current_model(self, mock_exists):
        """Test getting current model name"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        
        # Before initialization
        assert interface.get_current_model() is None
        
        # After initialization
        interface.initialize_model()
        assert interface.get_current_model() == "mock"
        
        # After switching
        interface.switch_model("mock2")
        assert interface.get_current_model() == "mock2"
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_get_model_info(self, mock_exists):
        """Test getting model information"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        
        # Before initialization
        info = interface.get_model_info()
        assert info["status"] == "not_initialized"
        assert info["model_name"] is None
        
        # After initialization
        interface.initialize_model()
        info = interface.get_model_info()
        
        assert info is not None
        assert info["name"] == "mock"
        assert info["initialized"] is True
        assert "cache_enabled" in info
        assert "manager_info" in info
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_model_not_initialized_error(self, mock_exists):
        """Test error when model not initialized with auto-init"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        
        # Should auto-initialize when trying to use
        result = interface.translate("test")
        assert result is not None  # Should work due to auto-initialization
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_shutdown(self, mock_exists):
        """Test cleanup"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        interface.initialize_model()
        
        assert interface._initialized
        
        interface.shutdown()
        
        # Model should be unloaded
        assert interface._current_model is None
        assert interface._model_name is None
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_backward_compatibility_properties(self, mock_exists):
        """Test backward compatibility properties"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        
        # Test _initialized property
        assert not interface._initialized
        interface.initialize_model()
        assert interface._initialized
        
        # Test model property
        assert interface.model is not None
        assert isinstance(interface.model, MockModel)
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_validation_levels(self, mock_exists):
        """Test different validation levels"""
        mock_exists.return_value = True
        
        # Test with strict validation
        config = LLMConfig(
            model_type="mock",
            model_path="/test/models",
            validation_level="strict"
        )
        interface = LLMInterface(config)
        interface.initialize_model()
        
        # Translate with strict validation
        result = interface.translate("test instruction")
        assert result is not None
        
        # Test with lenient validation
        config2 = LLMConfig(
            model_type="mock",
            model_path="/test/models",
            validation_level="lenient"
        )
        interface2 = LLMInterface(config2)
        interface2.initialize_model()
        
        result2 = interface2.translate("test instruction")
        assert result2 is not None
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_context_handling(self, mock_exists):
        """Test context handling in translation"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        interface.initialize_model()
        
        # Translate with context
        context = {"previous_code": "x = 10"}
        result = interface.translate("add 5 to x", context)
        
        assert result is not None
        assert "add 5 to x" in result
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_error_recovery(self, mock_exists):
        """Test error recovery mechanisms"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        interface.initialize_model()
        
        # Try to switch to non-existent model
        with pytest.raises(ValueError, match="not found"):
            interface.switch_model("nonexistent")
        
        # Interface should still be usable with original model
        assert interface.get_current_model() == "mock"
        result = interface.translate("test")
        assert result is not None
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_concurrent_usage(self, mock_exists):
        """Test thread safety of interface"""
        mock_exists.return_value = True
        
        import threading
        
        interface = LLMInterface(self.config)
        interface.initialize_model()
        
        results = []
        errors = []
        
        def translate_task(instruction):
            try:
                result = interface.translate(instruction)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(
                target=translate_task,
                args=(f"instruction {i}",)
            )
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # All translations should succeed
        assert len(errors) == 0
        assert len(results) == 10
        assert all("Translation" in r for r in results)
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_caching(self, mock_exists):
        """Test translation caching"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        interface.initialize_model()
        
        # First translation
        result1 = interface.translate("test instruction")
        
        # Reset translation count
        if isinstance(interface.model, MockModel):
            interface.model.translation_count = 0
        
        # Second translation of same instruction (should use cache)
        result2 = interface.translate("test instruction")
        
        # Results should be the same
        assert result1 == result2
        
        # Translation count should still be 0 (cache hit)
        if isinstance(interface.model, MockModel):
            assert interface.model.translation_count == 0
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_batch_translate(self, mock_exists):
        """Test batch translation"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        
        instructions = ["instruction 1", "instruction 2", "instruction 3"]
        results = interface.batch_translate(instructions)
        
        assert len(results) == 3
        assert all("Translation" in r for r in results)
        assert all("print('Hello')" in r for r in results)
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_warmup(self, mock_exists):
        """Test model warmup"""
        mock_exists.return_value = True
        
        interface = LLMInterface(self.config)
        
        # Warmup should initialize model if needed
        interface.warmup()
        
        assert interface._initialized
        assert interface.model is not None