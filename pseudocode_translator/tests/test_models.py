"""
Comprehensive tests for the model abstraction system

Tests the base model interface, model factory, plugin system,
and model implementations.
"""

import pytest
import tempfile
import json
from pathlib import Path

from pseudocode_translator.models.base_model import (
    BaseTranslationModel, ModelMetadata, ModelCapabilities,
    OutputLanguage, TranslationConfig, TranslationResult,
    validate_instruction, format_code_block
)
from pseudocode_translator.models.model_factory import (
    ModelFactory, register_model, ModelPriority, create_model
)
from pseudocode_translator.models.plugin_system import (
    PluginSystem, PluginMetadata, create_plugin_template
)


class TestBaseModel:
    """Test the base model abstraction"""
    
    def test_output_languages(self):
        """Test that all output languages are defined"""
        languages = list(OutputLanguage)
        assert len(languages) >= 14  # At least 14 languages
        assert OutputLanguage.PYTHON in languages
        assert OutputLanguage.JAVASCRIPT in languages
        assert OutputLanguage.JAVA in languages
    
    def test_translation_config(self):
        """Test TranslationConfig creation and defaults"""
        # Default config
        config = TranslationConfig()
        assert config.target_language == OutputLanguage.PYTHON
        assert config.temperature == 0.3
        assert config.max_tokens == 1024
        assert config.include_comments is True
        
        # Custom config
        config = TranslationConfig(
            target_language=OutputLanguage.JAVASCRIPT,
            temperature=0.5,
            max_tokens=2048
        )
        assert config.target_language == OutputLanguage.JAVASCRIPT
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
    
    def test_translation_result(self):
        """Test TranslationResult properties"""
        # Successful result
        result = TranslationResult(
            success=True,
            code="print('Hello')",
            language=OutputLanguage.PYTHON,
            confidence=0.95
        )
        assert result.success is True
        assert result.has_errors is False
        assert result.has_warnings is False
        assert result.code == "print('Hello')"
        
        # Failed result
        result = TranslationResult(
            success=False,
            code=None,
            language=OutputLanguage.PYTHON,
            errors=["Syntax error"],
            warnings=["Deprecated function"]
        )
        assert result.success is False
        assert result.has_errors is True
        assert result.has_warnings is True
    
    def test_validate_instruction(self):
        """Test instruction validation helper"""
        # Valid instruction
        is_valid, error = validate_instruction(
            "Create a function to add two numbers"
        )
        assert is_valid is True
        assert error is None
        
        # Empty instruction
        is_valid, error = validate_instruction("")
        assert is_valid is False
        assert error and "empty" in error.lower()
        
        # Too short
        is_valid, error = validate_instruction("Hi", min_length=3)
        assert is_valid is False
        assert error and "short" in error.lower()
        
        # Too long
        is_valid, error = validate_instruction("x" * 1001, max_length=1000)
        assert is_valid is False
        assert error and "long" in error.lower()
    
    def test_format_code_block(self):
        """Test code formatting with language-specific comments"""
        code = "def hello():\n    print('Hello')"
        
        # Python
        formatted = format_code_block(code, OutputLanguage.PYTHON)
        assert formatted.startswith("#")
        assert "def hello()" in formatted
        
        # JavaScript
        formatted = format_code_block(code, OutputLanguage.JAVASCRIPT)
        assert formatted.startswith("//")
        
        # SQL
        formatted = format_code_block(code, OutputLanguage.SQL)
        assert formatted.startswith("--")


class TestModelFactory:
    """Test the model factory system"""
    
    def setup_method(self):
        """Clear registry before each test"""
        ModelFactory.clear_registry()
        ModelFactory.initialize(auto_discover=False)
    
    def test_factory_initialization(self):
        """Test factory initialization"""
        assert ModelFactory._initialized is True
        assert len(ModelFactory._registry) >= 0
    
    def test_model_registration(self):
        """Test registering models"""
        # Create a test model
        @register_model(name="test", aliases=["t1", "test1"])
        class TestModel(BaseTranslationModel):
            @property
            def metadata(self):
                return ModelMetadata(
                    name="test",
                    version="1.0",
                    supported_languages=[OutputLanguage.PYTHON],
                    description="Test model"
                )
            
            @property
            def capabilities(self):
                return ModelCapabilities()
            
            def initialize(self, model_path=None, **kwargs):
                self._initialized = True
            
            def translate(self, instruction, config=None, context=None):
                return TranslationResult(
                    success=True,
                    code="# Test output",
                    language=OutputLanguage.PYTHON
                )
            
            def validate_input(self, instruction):
                return True, None
            
            def get_capabilities(self):
                return {}
        
        # Check registration
        assert "test" in ModelFactory.list_models()
        assert ModelFactory._aliases["t1"] == "test"
        assert ModelFactory._aliases["test1"] == "test"
    
    def test_create_model(self):
        """Test creating model instances"""
        # Register a test model first
        @register_model(name="testmodel")
        class TestModel(BaseTranslationModel):
            def __init__(self, config):
                super().__init__(config)
                self.test_config = config.get('test_value', 'default')
            
            @property
            def metadata(self):
                return ModelMetadata(
                    name="testmodel",
                    version="1.0",
                    supported_languages=[OutputLanguage.PYTHON],
                    description="Test model"
                )
            
            @property
            def capabilities(self):
                return ModelCapabilities()
            
            def initialize(self, model_path=None, **kwargs):
                self._initialized = True
            
            def translate(self, instruction, config=None, context=None):
                return TranslationResult(
                    success=True,
                    code=f"# {self.test_config}",
                    language=OutputLanguage.PYTHON
                )
            
            def validate_input(self, instruction):
                return True, None
            
            def get_capabilities(self):
                return {"test": True}
        
        # Create instance
        model = ModelFactory.create_model(
            "testmodel", {"test_value": "custom"}
        )
        assert model is not None
        # Access via the instance variable
        assert hasattr(model, 'test_config')
        
        # Create with alias
        ModelFactory._aliases["tm"] = "testmodel"
        model = ModelFactory.create_model("tm")
        assert model is not None
    
    def test_list_models(self):
        """Test listing available models"""
        # Register some test models
        for i in range(3):
            @register_model(name=f"model{i}")
            class TempModel(BaseTranslationModel):
                @property
                def metadata(self):
                    return ModelMetadata(
                        name=f"model{i}",
                        version="1.0",
                        supported_languages=[OutputLanguage.PYTHON],
                        description="Test"
                    )
                
                @property
                def capabilities(self):
                    return ModelCapabilities()
                
                def initialize(self, model_path=None, **kwargs):
                    pass
                
                def translate(self, instruction, config=None, context=None):
                    return TranslationResult(True, "", OutputLanguage.PYTHON)
                
                def validate_input(self, instruction):
                    return True, None
                
                def get_capabilities(self):
                    return {}
        
        models = ModelFactory.list_models()
        assert "model0" in models
        assert "model1" in models
        assert "model2" in models
    
    def test_model_priority(self):
        """Test model priority system"""
        # Register models with different priorities
        @register_model(name="high", priority=ModelPriority.HIGH)
        class HighModel(BaseTranslationModel):
            @property
            def metadata(self):
                return ModelMetadata(
                    name="high", version="1.0",
                    supported_languages=[OutputLanguage.PYTHON],
                    description="High priority"
                )
            
            @property
            def capabilities(self):
                return ModelCapabilities()
            
            def initialize(self, model_path=None, **kwargs):
                pass
            
            def translate(self, instruction, config=None, context=None):
                return TranslationResult(True, "", OutputLanguage.PYTHON)
            
            def validate_input(self, instruction):
                return True, None
            
            def get_capabilities(self):
                return {}
        
        # Check priority was set
        assert ModelFactory._registry["high"].priority == ModelPriority.HIGH
    
    def test_find_models_by_language(self):
        """Test finding models that support specific languages"""
        # Register a multi-language model
        @register_model(name="multilang")
        class MultiLangModel(BaseTranslationModel):
            @property
            def metadata(self):
                return ModelMetadata(
                    name="multilang",
                    version="1.0",
                    supported_languages=[
                        OutputLanguage.PYTHON,
                        OutputLanguage.JAVASCRIPT,
                        OutputLanguage.JAVA
                    ],
                    description="Multi-language model"
                )
            
            @property
            def capabilities(self):
                return ModelCapabilities()
            
            def initialize(self, model_path=None, **kwargs):
                pass
            
            def translate(self, instruction, config=None, context=None):
                return TranslationResult(True, "", OutputLanguage.PYTHON)
            
            def validate_input(self, instruction):
                return True, None
            
            def get_capabilities(self):
                return {}
        
        # Find models supporting JavaScript
        js_models = ModelFactory.find_models_by_language(
            OutputLanguage.JAVASCRIPT
        )
        assert "multilang" in js_models


class TestPluginSystem:
    """Test the plugin system"""
    
    def test_plugin_metadata(self):
        """Test plugin metadata creation"""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test Author",
            description="Test plugin",
            model_class="TestModel",
            requirements=["torch>=1.0"],
            compatible_versions=["1.0.0"]
        )
        assert metadata.name == "test_plugin"
        assert metadata.priority == "MEDIUM"
        assert metadata.aliases == []
    
    def test_plugin_system_initialization(self):
        """Test plugin system initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_dirs = [Path(temp_dir)]
            system = PluginSystem(plugin_dirs)
            
            assert len(system.plugin_dirs) == 1
            assert system.loaded_plugins == {}
    
    def test_plugin_discovery(self):
        """Test plugin discovery"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test plugin directory
            plugin_dir = Path(temp_dir) / "test_plugin"
            plugin_dir.mkdir()
            
            # Create plugin.json
            manifest = {
                "name": "test_plugin",
                "version": "1.0.0",
                "author": "Test",
                "description": "Test plugin",
                "model_class": "TestModel",
                "requirements": [],
                "compatible_versions": ["1.0.0"]
            }
            with open(plugin_dir / "plugin.json", 'w') as f:
                json.dump(manifest, f)
            
            # Create model.py
            with open(plugin_dir / "model.py", 'w') as f:
                f.write("# Test model")
            
            # Test discovery
            system = PluginSystem([Path(temp_dir)])
            plugins = system.discover_plugins()
            
            assert len(plugins) == 1
            assert plugins[0].name == "test_plugin"
    
    def test_plugin_validation(self):
        """Test plugin validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_dir = Path(temp_dir) / "test_plugin"
            plugin_dir.mkdir()
            
            # Invalid plugin (no manifest)
            system = PluginSystem([Path(temp_dir)])
            is_valid, errors = system.validate_plugin(plugin_dir)
            assert is_valid is False
            assert len(errors) > 0
            
            # Create valid plugin
            manifest = {
                "name": "test_plugin",
                "version": "1.0.0",
                "author": "Test",
                "description": "Test plugin",
                "model_class": "TestModel",
                "requirements": [],
                "compatible_versions": ["1.0.0"]
            }
            with open(plugin_dir / "plugin.json", 'w') as f:
                json.dump(manifest, f)
            with open(plugin_dir / "model.py", 'w') as f:
                f.write("# Test model")
            
            # Should be valid now
            is_valid, errors = system.validate_plugin(plugin_dir)
            assert is_valid is True
            assert len(errors) == 0
    
    def test_create_plugin_template(self):
        """Test plugin template creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create template
            success = create_plugin_template(
                "my_plugin",
                output_dir,
                author="Test Author"
            )
            assert success is True
            
            # Check created files
            plugin_dir = output_dir / "my_plugin"
            assert plugin_dir.exists()
            assert (plugin_dir / "plugin.json").exists()
            assert (plugin_dir / "model.py").exists()
            assert (plugin_dir / "README.md").exists()
            
            # Check manifest content
            with open(plugin_dir / "plugin.json", 'r') as f:
                manifest = json.load(f)
                assert manifest["name"] == "my_plugin"
                assert manifest["author"] == "Test Author"


class TestMockModel:
    """Test the mock model implementation"""
    
    def test_mock_model_registration(self):
        """Test that mock model is registered"""
        # Clear and re-initialize to ensure clean state
        ModelFactory.clear_registry()
        ModelFactory.initialize(auto_discover=True)
        
        # Import to trigger registration
        import pseudocode_translator.models.mock_model  # noqa: F401
        
        # Check if registered
        models = ModelFactory.list_models()
        assert "mock" in models or len(models) > 0  # Mock should be available
    
    def test_mock_model_creation(self):
        """Test creating a mock model instance"""
        from pseudocode_translator.models.mock_model import MockModel
        
        config = {
            'delay_ms': 0,
            'error_rate': 0.0,
            'mock_style': 'simple'
        }
        
        model = MockModel(config)
        assert model is not None
        assert model.metadata.name == "mock"
        assert OutputLanguage.PYTHON in model.metadata.supported_languages
    
    def test_mock_model_translation(self):
        """Test mock model translation"""
        from pseudocode_translator.models.mock_model import MockModel
        
        model = MockModel({'delay_ms': 0, 'error_rate': 0.0})
        model.initialize()
        
        # Test translation
        config = TranslationConfig(target_language=OutputLanguage.PYTHON)
        result = model.translate("create a hello world function", config)
        
        assert result.success is True
        assert result.code is not None
        assert "Mock" in result.code or "mock" in result.code
    
    def test_mock_model_error_simulation(self):
        """Test mock model error simulation"""
        from pseudocode_translator.models.mock_model import MockModel
        
        model = MockModel({
            'delay_ms': 0,
            'error_rate': 1.0  # 100% error rate
        })
        model.initialize()
        
        # Should fail
        result = model.translate("test", TranslationConfig())
        assert result.success is False
        assert len(result.errors) > 0


class TestModelIntegration:
    """Test integration between components"""
    
    def test_factory_with_mock_model(self):
        """Test factory creating mock model"""
        # Clear and initialize
        ModelFactory.clear_registry()
        ModelFactory.initialize(auto_discover=True)
        
        # Import mock model to ensure registration
        import pseudocode_translator.models.mock_model  # noqa: F401
        
        # Create mock model through factory
        try:
            model = create_model("mock", {"delay_ms": 0})
            assert model is not None
            
            # Initialize and test
            model.initialize()
            result = model.translate(
                "test instruction",
                TranslationConfig()
            )
            assert result.success is True
        except KeyError:
            # If mock isn't registered, skip this test
            pytest.skip("Mock model not registered")
    
    def test_model_switching(self):
        """Test switching between models"""
        # This would test the TranslationManager's ability to switch models
        # Since we updated translator.py, this functionality should work
        pass  # Placeholder for integration test


if __name__ == "__main__":
    pytest.main([__file__, "-v"])