"""
Tests for the model manager system
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List

from pseudocode_translator.models.manager import (
    ModelManager, ModelInstance
)
from pseudocode_translator.models.base import (
    BaseModel, ModelCapabilities, ModelMetadata, ModelFormat
)
from pseudocode_translator.models.registry import ModelRegistry, register_model


# Create a mock model for testing
class MockModel(BaseModel):
    """Mock model implementation for testing"""
    
    # Class variable to track instances
    instances_created = 0
    
    def __init__(self, config):
        super().__init__(config)
        MockModel.instances_created += 1
        self.initialized_path = None
    
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
        self.initialized_path = model_path
    
    def generate(self,
                 prompt: str,
                 max_tokens: int = 512,
                 temperature: float = 0.3,
                 top_p: float = 0.9,
                 top_k: int = 40,
                 stop_sequences: Optional[List[str]] = None,
                 **kwargs) -> str:
        """Generate mock response"""
        if not self._initialized:
            raise RuntimeError("Model not initialized")
        return f"Mock response to: {prompt}"
    
    def translate_instruction(self, instruction: str, context=None) -> str:
        """Translate instruction to code"""
        return f"# Mock translation of: {instruction}"
    
    def shutdown(self) -> None:
        """Cleanup mock resources"""
        self._initialized = False
        self._model = None


class TestModelManager:
    """Test the ModelManager class"""
    
    def setup_method(self):
        """Setup for each test"""
        # Clear registry and reset mock model counter
        ModelRegistry.clear()
        MockModel.instances_created = 0
        
        # Register the mock model
        ModelRegistry.register(MockModel, "mock", ["test"])
        
        # Create manager with test config
        self.config = {
            "model_dir": "/test/models",
            "max_loaded_models": 2,
            "model_ttl_minutes": 60,
            "default_model": "mock"
        }
        self.manager = ModelManager(self.config)
    
    def teardown_method(self):
        """Cleanup after each test"""
        # Shutdown manager
        if hasattr(self, 'manager'):
            self.manager.shutdown()
    
    def test_initialization(self):
        """Test manager initialization"""
        assert self.manager.config == self.config
        assert len(self.manager._instances) == 0
        assert self.manager.default_model == "mock"
        assert self.manager.max_loaded_models == 2
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_load_model(self, mock_exists):
        """Test loading a model"""
        mock_exists.return_value = True
        
        # Load model
        model = self.manager.load_model("mock")
        
        assert model is not None
        assert isinstance(model, MockModel)
        assert model._initialized
        assert "mock" in self.manager._instances
        
        # Check model path
        expected_path = Path("/test/models/mock/*.gguf")
        assert model.initialized_path == expected_path
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_load_model_with_custom_path(self, mock_exists):
        """Test loading a model with custom path"""
        mock_exists.return_value = True
        custom_path = Path("/custom/path/model.gguf")
        
        model = self.manager.load_model("mock", custom_path)
        
        # Cast to MockModel to access initialized_path
        assert isinstance(model, MockModel)
        assert model.initialized_path == custom_path
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_load_model_already_loaded(self, mock_exists):
        """Test loading an already loaded model"""
        mock_exists.return_value = True
        
        # Load model first time
        model1 = self.manager.load_model("mock")
        instances_after_first = MockModel.instances_created
        
        # Load same model again via get_model
        model2 = self.manager.get_model("mock")
        
        # Should return same instance
        assert model1 is model2
        assert MockModel.instances_created == instances_after_first
    
    def test_get_model(self):
        """Test getting a model"""
        # Get non-existent model with auto_load=False should raise
        with pytest.raises(RuntimeError, match="not loaded"):
            self.manager.get_model("mock", auto_load=False)
        
        # Get with auto_load=True should load it
        with patch('pseudocode_translator.models.manager.Path.exists',
                   return_value=True):
            model = self.manager.get_model("mock", auto_load=True)
            assert isinstance(model, MockModel)
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_unload_model(self, mock_exists):
        """Test unloading a model"""
        mock_exists.return_value = True
        
        # Load model
        self.manager.load_model("mock")
        assert "mock" in self.manager._instances
        
        # Unload model
        self.manager.unload_model("mock")
        assert "mock" not in self.manager._instances
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_switch_default_model(self, mock_exists):
        """Test switching default model"""
        mock_exists.return_value = True
        
        # Register another model
        ModelRegistry.register(MockModel, "mock2")
        
        # Switch default
        self.manager.switch_default_model("mock2")
        assert self.manager.default_model == "mock2"
        
        # Test switching to non-existent model
        with pytest.raises(KeyError, match="not found"):
            self.manager.switch_default_model("nonexistent")
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_list_loaded_models(self, mock_exists):
        """Test listing loaded models"""
        mock_exists.return_value = True
        
        # Initially empty
        assert self.manager.list_loaded_models() == []
        
        # Load models
        self.manager.load_model("mock")
        ModelRegistry.register(MockModel, "mock2", ["test2"])
        self.manager.load_model("mock2")
        
        loaded = self.manager.list_loaded_models()
        assert len(loaded) == 2
        
        # Check structure
        assert all('name' in m for m in loaded)
        assert all('loaded_at' in m for m in loaded)
        assert all('last_used' in m for m in loaded)
        assert all('usage_count' in m for m in loaded)
        
        names = [m['name'] for m in loaded]
        assert "mock" in names
        assert "mock2" in names
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    @patch('psutil.virtual_memory')
    def test_memory_pressure_eviction(self, mock_memory, mock_exists):
        """Test model eviction under memory pressure"""
        mock_exists.return_value = True
        mock_memory.return_value = MagicMock(available=5 * 1024**3)
        
        # Create manager with max 1 model
        manager = ModelManager({"max_loaded_models": 1, "model_dir": "/test"})
        
        # Register two models
        ModelRegistry.register(MockModel, "model1")
        ModelRegistry.register(MockModel, "model2")
        
        # Load first model
        manager.load_model("model1")
        assert "model1" in manager._instances
        
        # Load second model - should evict first
        manager.load_model("model2")
        assert "model2" in manager._instances
        assert "model1" not in manager._instances
        
        manager.shutdown()
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_cleanup_old_models(self, mock_exists):
        """Test time-based model cleanup"""
        mock_exists.return_value = True
        
        # Create manager with short TTL
        manager = ModelManager({
            "model_ttl_minutes": 0.01,  # 0.6 seconds
            "model_dir": "/test"
        })
        
        # Load model
        manager.load_model("mock")
        instance = manager._instances["mock"]
        
        # Model should be loaded
        assert "mock" in manager._instances
        
        # Manually set last_used to past
        instance.last_used = datetime.now() - timedelta(minutes=1)
        
        # Clean up old models
        cleaned = manager.cleanup_old_models()
        
        # Model should be evicted
        assert cleaned == 1
        assert "mock" not in manager._instances
        
        manager.shutdown()
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_get_model_health(self, mock_exists):
        """Test model health checking"""
        mock_exists.return_value = True
        
        # Check health of non-loaded model
        health = self.manager.get_model_health("mock")
        assert health['status'] == 'not_loaded'
        
        # Load model
        self.manager.load_model("mock")
        
        # Check healthy model
        health = self.manager.get_model_health("mock")
        assert health['status'] == 'healthy'
        assert health['model'] == 'mock'
        assert 'loaded_at' in health
        assert 'last_used' in health
        assert 'usage_count' in health
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_shutdown(self, mock_exists):
        """Test manager shutdown"""
        mock_exists.return_value = True
        
        # Load models
        self.manager.load_model("mock")
        ModelRegistry.register(MockModel, "mock2")
        self.manager.load_model("mock2")
        
        # Shutdown
        self.manager.shutdown()
        
        # All models should be unloaded
        assert len(self.manager._instances) == 0
    
    def test_model_instance_update_usage(self):
        """Test ModelInstance usage tracking"""
        model = MockModel({})
        instance = ModelInstance(
            model=model,
            loaded_at=datetime.now(),
            last_used=datetime.now() - timedelta(minutes=5)
        )
        
        old_time = instance.last_used
        old_count = instance.usage_count
        
        instance.update_usage()
        
        assert instance.last_used > old_time
        assert instance.usage_count == old_count + 1
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_get_memory_usage(self, mock_exists):
        """Test memory usage reporting"""
        mock_exists.return_value = True
        
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value = MagicMock(
                total=16 * 1024**3,
                available=8 * 1024**3,
                percent=50.0
            )
            
            # Load a model
            self.manager.load_model("mock")
            
            usage = self.manager.get_memory_usage()
            
            assert usage['total_gb'] == 16.0
            assert usage['available_gb'] == 8.0
            assert usage['used_percent'] == 50.0
            assert usage['models_loaded'] == 1
            assert usage['estimated_model_usage_gb'] == 2.0  # From MockModel
    
    @patch('psutil.virtual_memory')
    def test_check_memory_availability(self, mock_memory):
        """Test memory availability checking"""
        # Mock low memory
        mock_memory.return_value = MagicMock(available=0.5 * 1024**3)  # 0.5GB
        
        # Should raise error for insufficient memory
        with pytest.raises(RuntimeError, match="Insufficient memory"):
            self.manager._check_memory_availability("mock")
    
    def test_error_handling_during_load(self):
        """Test error handling when model fails to load"""
        # Create a model that fails to initialize
        @register_model(name="failing")
        class FailingModel(MockModel):
            def initialize(self, model_path: Path, **kwargs):
                raise RuntimeError("Initialization failed")
        
        # Try to load failing model with mocked path
        with patch('pseudocode_translator.models.manager.Path.exists',
                   return_value=True):
            with pytest.raises(RuntimeError,
                               match="Failed to initialize model"):
                self.manager.load_model("failing")
        
        # Model should not be in loaded models
        assert "failing" not in self.manager._instances
    
    def test_model_not_found(self):
        """Test loading non-existent model"""
        with pytest.raises(KeyError, match="not found"):
            self.manager.load_model("nonexistent")
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_check_all_health(self, mock_exists):
        """Test checking health of all models"""
        mock_exists.return_value = True
        
        # Load multiple models
        self.manager.load_model("mock")
        ModelRegistry.register(MockModel, "mock2")
        self.manager.load_model("mock2")
        
        # Check all health
        all_health = self.manager.check_all_health()
        
        assert len(all_health) == 2
        assert all_health['mock']['status'] == 'healthy'
        assert all_health['mock2']['status'] == 'healthy'
    
    @patch('pseudocode_translator.models.manager.Path.exists')
    def test_model_path_discovery(self, mock_exists):
        """Test model path discovery logic"""
        mock_exists.return_value = True
        
        # Test with configured path
        config = {
            "model_dir": "/test/models",
            "model_paths": {
                "mock": "/custom/mock.gguf"
            }
        }
        manager = ModelManager(config)
        
        model = manager.load_model("mock")
        # Cast to MockModel to access initialized_path
        assert isinstance(model, MockModel)
        assert model.initialized_path == Path("/custom/mock.gguf")
        
        manager.shutdown()