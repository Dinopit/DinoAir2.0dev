"""
Tests for the model registry system
"""

import pytest
from unittest.mock import Mock
from typing import Dict, Any, Optional
from pathlib import Path

# Import the components we're testing
from pseudocode_translator.models.base import (
    BaseModel, ModelCapabilities, ModelMetadata, ModelFormat
)
from pseudocode_translator.models.registry import (
    ModelRegistry, register_model, list_available_models,
    get_model, model_exists
)


# Create a mock model for testing
class MockModel(BaseModel):
    """Mock model implementation for testing"""
    
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
            format=ModelFormat.GGUF
        )
    
    @property
    def capabilities(self) -> ModelCapabilities:
        """Return mock capabilities"""
        return ModelCapabilities(
            supported_languages=["python"],
            max_context_length=2048,
            supports_code_completion=True,
            supports_translation=True,
            supports_refinement=True,
            supports_streaming=False,
            min_memory_gb=1.0,
            supports_gpu=True,
            requires_gpu=False
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
                 stop_sequences: Optional[list] = None,
                 **kwargs) -> str:
        """Generate mock response"""
        if not self._initialized:
            raise RuntimeError("Model not initialized")
        return f"Mock response to: {prompt}"
    
    def translate_instruction(self,
                              instruction: str,
                              context: Optional[Dict[str, Any]] = None) -> str:
        """Translate instruction to code"""
        return f"# Mock translation of: {instruction}"


class TestModelRegistry:
    """Test the ModelRegistry class"""
    
    def setup_method(self):
        """Reset the registry before each test"""
        # Clear the registry
        ModelRegistry.clear()
    
    def test_register_model(self):
        """Test registering a model"""
        # Register the model
        ModelRegistry.register(MockModel, "test_model", ["test", "mock"])
        
        # Check it was registered
        assert "test_model" in ModelRegistry._models
        assert ModelRegistry._models["test_model"] == MockModel
        
        # Check aliases
        assert "test" in ModelRegistry._aliases
        assert "mock" in ModelRegistry._aliases
        assert ModelRegistry._aliases["test"] == "test_model"
        assert ModelRegistry._aliases["mock"] == "test_model"
    
    def test_register_duplicate_model(self):
        """Test registering a model with duplicate name"""
        ModelRegistry.register(MockModel, "test_model")
        
        # Should not raise error for same class
        ModelRegistry.register(MockModel, "test_model")
        
        # But should raise for different class
        class OtherModel(MockModel):
            pass
        
        with pytest.raises(ValueError, match="already registered"):
            ModelRegistry.register(OtherModel, "test_model")
    
    def test_register_with_warning_for_duplicate_alias(self):
        """Test registering a model with duplicate alias logs warning"""
        ModelRegistry.register(MockModel, "model1", ["shared"])
        
        # Create another model
        class AnotherModel(MockModel):
            pass
        
        # Should succeed but log warning
        ModelRegistry.register(AnotherModel, "model2", ["shared", "unique"])
        
        # Check unique alias was registered
        assert ModelRegistry._aliases["unique"] == "model2"
    
    def test_get_model_class(self):
        """Test retrieving a model class"""
        ModelRegistry.register(MockModel, "test_model", ["test"])
        
        # Get by name
        assert ModelRegistry.get_model_class("test_model") == MockModel
        
        # Get by alias
        assert ModelRegistry.get_model_class("test") == MockModel
        
        # Get non-existent should raise KeyError
        with pytest.raises(KeyError, match="not found"):
            ModelRegistry.get_model_class("nonexistent")
    
    def test_create_model(self):
        """Test creating a model instance"""
        ModelRegistry.register(MockModel, "test_model")
        
        # Create instance
        config = {"temperature": 0.5}
        model = ModelRegistry.create_model("test_model", config)
        
        assert isinstance(model, MockModel)
        assert model.config == config
    
    def test_create_nonexistent_model(self):
        """Test creating a non-existent model"""
        with pytest.raises(KeyError, match="not found"):
            ModelRegistry.create_model("nonexistent", {})
    
    def test_list_models(self):
        """Test listing available models"""
        # Register some models
        ModelRegistry.register(MockModel, "model1", ["m1", "first"])
        
        class SecondModel(MockModel):
            pass
        ModelRegistry.register(SecondModel, "model2", ["m2", "second"])
        
        models = ModelRegistry.list_models()
        
        assert len(models) == 2
        assert "model1" in models
        assert "model2" in models
    
    def test_list_aliases(self):
        """Test listing model aliases"""
        ModelRegistry.register(MockModel, "test_model", ["test", "mock"])
        
        aliases = ModelRegistry.list_aliases()
        
        assert aliases["test"] == "test_model"
        assert aliases["mock"] == "test_model"
    
    def test_get_model_info(self):
        """Test getting model information"""
        ModelRegistry.register(MockModel, "test_model", ["test", "mock"])
        
        info = ModelRegistry.get_model_info("test_model")
        
        assert info["name"] == "mock"
        assert info["display_name"] == "Mock Model"
        assert info["version"] == "1.0"
        assert info["aliases"] == ["test", "mock"]
        
        # Test with alias
        info2 = ModelRegistry.get_model_info("test")
        assert info2["name"] == info["name"]
    
    def test_unregister_model(self):
        """Test unregistering a model"""
        ModelRegistry.register(MockModel, "test_model", ["test"])
        
        # Verify it's registered
        assert "test_model" in ModelRegistry._models
        
        # Unregister
        ModelRegistry.unregister("test_model")
        
        # Verify it's gone
        assert "test_model" not in ModelRegistry._models
        assert "test" not in ModelRegistry._aliases
    
    def test_find_models_by_capability(self):
        """Test finding models by capability"""
        # Register models with different capabilities
        ModelRegistry.register(MockModel, "python_model")
        
        # Find models supporting Python
        models = ModelRegistry.find_models_by_capability(language="python")
        assert "python_model" in models
        
        # Find models with specific context length
        models = ModelRegistry.find_models_by_capability(min_context=1024)
        assert "python_model" in models
        
        # Find models that don't match
        models = ModelRegistry.find_models_by_capability(language="javascript")
        assert len(models) == 0


class TestRegisterDecorator:
    """Test the @register_model decorator"""
    
    def setup_method(self):
        """Reset the registry before each test"""
        ModelRegistry.clear()
    
    def test_decorator_basic(self):
        """Test basic decorator usage"""
        @register_model(name="decorated_model")
        class DecoratedModel(MockModel):
            pass
        
        # Check it was registered
        assert "decorated_model" in ModelRegistry.list_models()
        assert (ModelRegistry.get_model_class("decorated_model") ==
                DecoratedModel)
    
    def test_decorator_with_aliases(self):
        """Test decorator with aliases"""
        @register_model(name="decorated_model", aliases=["dec", "decorated"])
        class DecoratedModel(MockModel):
            pass
        
        # Check aliases work
        assert ModelRegistry.get_model_class("dec") == DecoratedModel
        assert ModelRegistry.get_model_class("decorated") == DecoratedModel
    
    def test_decorator_preserves_class(self):
        """Test that decorator preserves the original class"""
        @register_model(name="test")
        class TestModel(MockModel):
            """Test model class"""
            custom_attr = "test"
        
        # Check class is unchanged
        assert TestModel.__name__ == "TestModel"
        assert TestModel.__doc__ == "Test model class"
        assert hasattr(TestModel, "custom_attr")
        assert getattr(TestModel, "custom_attr") == "test"


class TestModuleLevelFunctions:
    """Test module-level convenience functions"""
    
    def setup_method(self):
        """Reset the registry before each test"""
        ModelRegistry.clear()
    
    def test_list_available_models(self):
        """Test the list_available_models function"""
        ModelRegistry.register(MockModel, "model1")
        
        class Model2(MockModel):
            pass
        ModelRegistry.register(Model2, "model2")
        
        models = list_available_models()
        
        assert models == ["model1", "model2"]
    
    def test_get_model_function(self):
        """Test the get_model function"""
        ModelRegistry.register(MockModel, "test")
        
        model = get_model("test", {"temp": 0.5})
        
        assert isinstance(model, MockModel)
        assert model.config["temp"] == 0.5
    
    def test_model_exists_function(self):
        """Test the model_exists function"""
        ModelRegistry.register(MockModel, "test", ["alias"])
        
        # Check by name
        assert model_exists("test")
        
        # Check by alias
        assert model_exists("alias")
        
        # Check non-existent
        assert not model_exists("nonexistent")


class TestRegistryIntegration:
    """Test registry integration scenarios"""
    
    def setup_method(self):
        """Reset the registry before each test"""
        ModelRegistry.clear()
    
    def test_multiple_models(self):
        """Test registering and using multiple models"""
        # Define different model types
        @register_model(name="model_a", aliases=["a"])
        class ModelA(MockModel):
            model_type = "A"
            
            @property
            def metadata(self) -> ModelMetadata:
                meta = super().metadata
                meta.name = "model_a"
                meta.display_name = "Model A"
                return meta
        
        @register_model(name="model_b", aliases=["b"])
        class ModelB(MockModel):
            model_type = "B"
            
            @property
            def metadata(self) -> ModelMetadata:
                meta = super().metadata
                meta.name = "model_b"
                meta.display_name = "Model B"
                return meta
        
        # Create instances
        model_a = get_model("a")
        model_b = get_model("b")
        
        assert isinstance(model_a, ModelA)
        assert isinstance(model_b, ModelB)
        assert hasattr(model_a, "model_type")
        assert hasattr(model_b, "model_type")
        assert getattr(model_a.__class__, "model_type") == "A"
        assert getattr(model_b.__class__, "model_type") == "B"
    
    def test_model_lifecycle(self):
        """Test complete model lifecycle"""
        # Register model
        ModelRegistry.register(MockModel, "lifecycle_test")
        
        # Create instance
        model = ModelRegistry.create_model("lifecycle_test", {})
        
        # Initialize
        model.initialize(Path("/test/path"))
        assert model._initialized
        
        # Use model
        response = model.generate("Test prompt")
        assert "Mock response" in response
        
        # Get metadata
        meta = model.metadata
        assert meta.name == "mock"
        
        # Shutdown
        model.shutdown()
        assert not model._initialized
    
    def test_model_info_integration(self):
        """Test getting comprehensive model information"""
        ModelRegistry.register(MockModel, "info_test", ["alias1", "alias2"])
        
        # Get model info
        info = ModelRegistry.get_model_info("info_test")
        
        # Check all expected fields
        assert info["name"] == "mock"
        assert info["display_name"] == "Mock Model"
        assert info["description"] == "Mock model for testing"
        assert info["format"] == "gguf"
        assert info["capabilities"]["languages"] == ["python"]
        assert info["capabilities"]["max_context"] == 2048
        assert set(info["aliases"]) == {"alias1", "alias2"}
    
    def test_error_handling(self):
        """Test error handling in registry"""
        # Test invalid model class
        class NotAModel:
            pass
        
        with pytest.raises(ValueError, match="must inherit from BaseModel"):
            # Type ignore needed because we're testing invalid input
            ModelRegistry.register(NotAModel, "invalid")  # type: ignore
        
        # Test KeyError handling in get_model_class
        with pytest.raises(KeyError) as exc_info:
            ModelRegistry.get_model_class("nonexistent")
        
        assert "Available models:" in str(exc_info.value)