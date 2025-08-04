"""
Comprehensive tests for the simplified configuration system
"""

import os
import json
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from pseudocode_translator.config import (
    Config, LLMConfig, StreamingConfig, ModelConfig,
    ConfigManager, ConfigProfile, TranslatorConfig,
    load_config, save_config, validate_config
)


class TestModelConfig:
    """Test ModelConfig dataclass"""
    
    def test_default_values(self):
        """Test default model configuration values"""
        config = ModelConfig(name="test")
        assert config.name == "test"
        assert config.enabled is True
        assert config.model_path is None
        assert config.temperature == 0.3
        assert config.max_tokens == 1024
        assert config.auto_download is False
    
    def test_validation_valid(self):
        """Test validation with valid values"""
        config = ModelConfig(
            name="test",
            temperature=1.0,
            max_tokens=2048
        )
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validation_invalid(self):
        """Test validation with invalid values"""
        # Invalid temperature
        config = ModelConfig(name="test", temperature=3.0)
        errors = config.validate()
        assert len(errors) == 1
        assert "Temperature must be between" in errors[0]
        
        # Invalid max_tokens
        config = ModelConfig(name="test", max_tokens=100000)
        errors = config.validate()
        assert len(errors) == 1
        assert "max_tokens must be between" in errors[0]
        
        # Empty name
        config = ModelConfig(name="")
        errors = config.validate()
        assert len(errors) == 1
        assert "Model name cannot be empty" in errors[0]


class TestLLMConfig:
    """Test LLMConfig dataclass"""
    
    def test_default_values(self):
        """Test default LLM configuration values"""
        config = LLMConfig()
        assert config.model_type == "qwen"
        assert config.model_path == "./models"
        assert config.n_ctx == 2048
        assert config.n_threads == 4
        assert config.n_gpu_layers == 0
        assert config.temperature == 0.3
        assert config.max_tokens == 1024
        assert config.cache_enabled is True
        assert config.timeout_seconds == 30
        assert len(config.models) == 1
        assert "qwen" in config.models
    
    def test_post_init_creates_default_model(self):
        """Test that __post_init__ creates a default model"""
        config = LLMConfig(model_type="gpt2")
        assert "gpt2" in config.models
        assert config.models["gpt2"].name == "gpt2"
        assert config.models["gpt2"].temperature == 0.3
    
    def test_backward_compatibility_model_configs(self):
        """Test backward compatibility with model_configs"""
        config = LLMConfig(
            model_configs={
                "test": {
                    "enabled": True,
                    "model_path": "/path/to/model",
                    "parameters": {
                        "temperature": 0.5,
                        "max_tokens": 512
                    },
                    "auto_download": True
                }
            }
        )
        assert "test" in config.models
        assert config.models["test"].temperature == 0.5
        assert config.models["test"].max_tokens == 512
        assert config.models["test"].auto_download is True
    
    def test_validation_valid(self):
        """Test validation with valid values"""
        config = LLMConfig()
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validation_invalid(self):
        """Test validation with invalid values"""
        config = LLMConfig(
            n_ctx=100,  # Too small
            n_threads=50,  # Too many
            temperature=3.0  # Too high
        )
        errors = config.validate()
        assert len(errors) >= 3
        assert any("n_ctx" in e for e in errors)
        assert any("n_threads" in e for e in errors)
        assert any("temperature" in e for e in errors)
    
    def test_get_model_config(self):
        """Test getting model configuration"""
        config = LLMConfig()
        config.models["test"] = ModelConfig(
            name="test",
            temperature=0.7
        )
        
        # Get existing model
        model = config.get_model_config("test")
        assert model.name == "test"
        assert model.temperature == 0.7
        
        # Get non-existing model (returns default)
        model = config.get_model_config("nonexistent")
        assert model.name == "nonexistent"
        assert model.temperature == 0.3
    
    def test_get_model_path(self):
        """Test getting model path"""
        config = LLMConfig(model_path="/models")
        
        # Default path structure
        path = config.get_model_path("test")
        assert path == Path("/models/test/test.gguf")
        
        # Backward compatibility for qwen
        config.model_file = "custom.gguf"
        path = config.get_model_path("qwen")
        assert path == Path("/models/qwen-7b/custom.gguf")
        
        # Custom model path
        config.models["custom"] = ModelConfig(
            name="custom",
            model_path="/custom/path/model.bin"
        )
        path = config.get_model_path("custom")
        assert path == Path("/custom/path/model.bin")
    
    def test_add_model_config(self):
        """Test adding model configuration (backward compatibility)"""
        config = LLMConfig()
        
        # Mock ModelConfigSchema
        mock_schema = MagicMock()
        mock_schema.name = "new_model"
        mock_schema.enabled = True
        mock_schema.temperature = 0.8
        mock_schema.max_tokens = 2048
        
        config.add_model_config(mock_schema)
        
        assert "new_model" in config.models
        assert config.models["new_model"].temperature == 0.8
        assert config.models["new_model"].max_tokens == 2048


class TestStreamingConfig:
    """Test StreamingConfig dataclass"""
    
    def test_default_values(self):
        """Test default streaming configuration values"""
        config = StreamingConfig()
        assert config.enabled is True
        assert config.chunk_size == 4096
        assert config.max_memory_mb == 100
    
    def test_backward_compatibility_enable_streaming(self):
        """Test backward compatibility with enable_streaming"""
        config = StreamingConfig(enable_streaming=False)
        assert config.enabled is False
    
    def test_validation_valid(self):
        """Test validation with valid values"""
        config = StreamingConfig(
            chunk_size=1024,
            max_memory_mb=50
        )
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validation_invalid(self):
        """Test validation with invalid values"""
        config = StreamingConfig(
            chunk_size=100,  # Too small
            max_memory_mb=2000  # Too large
        )
        errors = config.validate()
        assert len(errors) == 2
        assert any("chunk_size" in e for e in errors)
        assert any("max_memory_mb" in e for e in errors)


class TestConfig:
    """Test main Config dataclass"""
    
    def test_default_values(self):
        """Test default configuration values"""
        config = Config()
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.streaming, StreamingConfig)
        assert config.preserve_comments is True
        assert config.preserve_docstrings is True
        assert config.use_type_hints is True
        assert config.indent_size == 4
        assert config.max_line_length == 88
        assert config.validate_imports is True
        assert config.check_undefined_vars is True
        assert config.allow_unsafe_operations is False
        assert config.version == "3.0"
    
    def test_validation_valid(self):
        """Test validation with valid configuration"""
        config = Config()
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validation_invalid(self):
        """Test validation with invalid values"""
        config = Config(
            indent_size=3,  # Should be 2, 4, or 8
            max_line_length=200  # Too long
        )
        errors = config.validate()
        assert len(errors) >= 2
        assert any("indent_size" in e for e in errors)
        assert any("max_line_length" in e for e in errors)
    
    def test_apply_env_overrides(self):
        """Test environment variable overrides"""
        env_vars = {
            "PSEUDOCODE_LLM_MODEL_TYPE": "gpt2",
            "PSEUDOCODE_LLM_TEMPERATURE": "0.7",
            "PSEUDOCODE_LLM_THREADS": "8",
            "PSEUDOCODE_LLM_GPU_LAYERS": "10",
            "PSEUDOCODE_STREAMING_ENABLED": "false",
            "PSEUDOCODE_STREAMING_CHUNK_SIZE": "8192",
            "PSEUDOCODE_VALIDATE_IMPORTS": "false",
            "PSEUDOCODE_CHECK_UNDEFINED_VARS": "true"
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            config.apply_env_overrides()
            
            assert config.llm.model_type == "gpt2"
            assert config.llm.temperature == 0.7
            assert config.llm.n_threads == 8
            assert config.llm.n_gpu_layers == 10
            assert config.streaming.enabled is False
            assert config.streaming.chunk_size == 8192
            assert config.validate_imports is False
            assert config.check_undefined_vars is True
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        config = Config()
        data = config.to_dict()
        
        assert isinstance(data, dict)
        assert "llm" in data
        assert "streaming" in data
        assert data["version"] == "3.0"
        assert isinstance(data["llm"]["model_path"], str)
    
    def test_from_dict(self):
        """Test creation from dictionary"""
        data = {
            "llm": {
                "model_type": "custom",
                "temperature": 0.5,
                "models": {
                    "custom": {
                        "name": "custom",
                        "temperature": 0.5
                    }
                }
            },
            "streaming": {
                "enabled": False,
                "chunk_size": 8192
            },
            "indent_size": 2
        }
        
        config = Config.from_dict(data)
        assert config.llm.model_type == "custom"
        assert config.llm.temperature == 0.5
        assert config.streaming.enabled is False
        assert config.streaming.chunk_size == 8192
        assert config.indent_size == 2


class TestConfigManager:
    """Test ConfigManager functions"""
    
    def test_create_profile_development(self):
        """Test creating development profile"""
        config = ConfigManager.create_profile(ConfigProfile.DEVELOPMENT)
        assert config.llm.temperature == 0.5
        assert config.llm.timeout_seconds == 60
        assert config.validate_imports is False
    
    def test_create_profile_production(self):
        """Test creating production profile"""
        config = ConfigManager.create_profile(ConfigProfile.PRODUCTION)
        assert config.llm.temperature == 0.3
        assert config.llm.n_gpu_layers == 20
        assert config.validate_imports is True
    
    def test_create_profile_testing(self):
        """Test creating testing profile"""
        config = ConfigManager.create_profile(ConfigProfile.TESTING)
        assert config.llm.n_ctx == 512
        assert config.llm.max_tokens == 256
        assert config.streaming.enabled is False
    
    def test_load_default_config(self):
        """Test loading default configuration"""
        config = ConfigManager.load()
        assert isinstance(config, Config)
        assert config.llm.model_type == "qwen"
    
    def test_load_from_yaml(self):
        """Test loading configuration from YAML file"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            yaml.dump({
                "llm": {"model_type": "test"},
                "version": "3.0"
            }, f)
            temp_path = f.name
        
        try:
            config = ConfigManager.load(temp_path)
            assert config.llm.model_type == "test"
        finally:
            os.unlink(temp_path)
    
    def test_load_from_json(self):
        """Test loading configuration from JSON file"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump({
                "llm": {"model_type": "test"},
                "version": "3.0"
            }, f)
            temp_path = f.name
        
        try:
            config = ConfigManager.load(temp_path)
            assert config.llm.model_type == "test"
        finally:
            os.unlink(temp_path)
    
    def test_save_to_yaml(self):
        """Test saving configuration to YAML file"""
        config = Config()
        config.llm.model_type = "test"
        
        with tempfile.NamedTemporaryFile(
            suffix='.yaml', delete=False
        ) as f:
            temp_path = f.name
        
        try:
            ConfigManager.save(config, temp_path)
            
            with open(temp_path, 'r') as f:
                data = yaml.safe_load(f)
            
            assert data["llm"]["model_type"] == "test"
            assert data["version"] == "3.0"
        finally:
            os.unlink(temp_path)
    
    def test_save_to_json(self):
        """Test saving configuration to JSON file"""
        config = Config()
        config.llm.model_type = "test"
        
        with tempfile.NamedTemporaryFile(
            suffix='.json', delete=False
        ) as f:
            temp_path = f.name
        
        try:
            ConfigManager.save(config, temp_path)
            
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert data["llm"]["model_type"] == "test"
            assert data["version"] == "3.0"
        finally:
            os.unlink(temp_path)
    
    def test_upgrade_config(self):
        """Test configuration upgrade from old version"""
        config = Config()
        ConfigManager._upgrade_config(config, "1.0")
        
        # Should have default model
        assert config.llm.model_type in config.llm.models
    
    def test_get_config_info(self):
        """Test getting configuration info"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            yaml.dump({
                "llm": {"model_type": "test"},
                "version": "3.0"
            }, f)
            temp_path = f.name
        
        try:
            info = ConfigManager.get_config_info(temp_path)
            assert info["exists"] is True
            assert info["version"] == "3.0"
            assert info["is_valid"] is True
            assert info["needs_migration"] is False
        finally:
            os.unlink(temp_path)
    
    def test_get_config_info_old_version(self):
        """Test getting info for old configuration"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            yaml.dump({
                "llm": {"model_type": "test"},
                "_version": "2.0"
            }, f)
            temp_path = f.name
        
        try:
            info = ConfigManager.get_config_info(temp_path)
            assert info["version"] == "2.0"
            assert info["needs_migration"] is True
        finally:
            os.unlink(temp_path)
    
    def test_add_model_config(self):
        """Test adding model configuration"""
        config = Config()
        ConfigManager.add_model_config(
            config,
            "new_model",
            model_path="/path/to/model",
            parameters={"temperature": 0.8},
            auto_download=True
        )
        
        assert "new_model" in config.llm.models
        assert config.llm.models["new_model"].temperature == 0.8
        assert config.llm.models["new_model"].auto_download is True


class TestTranslatorConfig:
    """Test TranslatorConfig backward compatibility wrapper"""
    
    def test_properties(self):
        """Test property access"""
        wrapper = TranslatorConfig()
        assert wrapper.preserve_comments is True
        assert wrapper.preserve_docstrings is True
        assert wrapper.use_type_hints is True
        assert wrapper.indent_size == 4
        assert wrapper.max_line_length == 88
        assert wrapper.validate_imports is True
        assert wrapper.check_undefined_vars is True
        assert wrapper.allow_unsafe_operations is False
    
    def test_nested_access(self):
        """Test nested configuration access"""
        wrapper = TranslatorConfig()
        assert isinstance(wrapper.llm, LLMConfig)
        assert isinstance(wrapper.streaming, StreamingConfig)
        assert wrapper.llm.model_type == "qwen"
    
    def test_load_from_file(self):
        """Test loading from file (backward compatibility)"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            yaml.dump({
                "llm": {"model_type": "test"},
                "version": "3.0"
            }, f)
            temp_path = f.name
        
        try:
            wrapper = TranslatorConfig.load_from_file(temp_path)
            assert wrapper.llm.model_type == "test"
        finally:
            os.unlink(temp_path)
    
    def test_save_to_file(self):
        """Test saving to file (backward compatibility)"""
        wrapper = TranslatorConfig()
        wrapper.llm.model_type = "test"
        
        with tempfile.NamedTemporaryFile(
            suffix='.yaml', delete=False
        ) as f:
            temp_path = f.name
        
        try:
            wrapper.save_to_file(temp_path)
            
            with open(temp_path, 'r') as f:
                data = yaml.safe_load(f)
            
            assert data["llm"]["model_type"] == "test"
        finally:
            os.unlink(temp_path)
    
    def test_validate_config(self):
        """Test validation (backward compatibility)"""
        wrapper = TranslatorConfig()
        is_valid, errors = wrapper.validate_config()
        assert is_valid is True
        assert len(errors) == 0
    
    def test_get_model_config(self):
        """Test getting model config (backward compatibility)"""
        wrapper = TranslatorConfig()
        config = wrapper.get_model_config("qwen")
        assert config["name"] == "qwen"
        assert config["temperature"] == 0.3


class TestBackwardCompatibility:
    """Test backward compatibility functions"""
    
    def test_load_config(self):
        """Test deprecated load_config function"""
        with patch('pseudocode_translator.config.ConfigManager.load') as mock:
            mock.return_value = Config()
            config = load_config()
            assert isinstance(config, TranslatorConfig)
            mock.assert_called_once()
    
    def test_save_config(self):
        """Test deprecated save_config function"""
        wrapper = TranslatorConfig()
        with patch('pseudocode_translator.config.ConfigManager.save') as mock:
            save_config(wrapper, "test.yaml")
            mock.assert_called_once()
    
    def test_validate_config(self):
        """Test deprecated validate_config function"""
        wrapper = TranslatorConfig()
        with patch(
            'pseudocode_translator.config.ConfigManager.validate'
        ) as mock:
            mock.return_value = []
            errors = validate_config(wrapper)
            assert errors == []
            mock.assert_called_once()


class TestConfigurationIntegration:
    """Integration tests for configuration system"""
    
    def test_full_config_lifecycle(self):
        """Test full configuration lifecycle"""
        # Create config
        config = ConfigManager.create_profile(ConfigProfile.DEVELOPMENT)
        
        # Modify it
        config.llm.model_type = "custom"
        config.llm.models["custom"] = ModelConfig(
            name="custom",
            temperature=0.7
        )
        
        # Save it
        with tempfile.NamedTemporaryFile(
            suffix='.yaml', delete=False
        ) as f:
            temp_path = f.name
        
        try:
            ConfigManager.save(config, temp_path)
            
            # Load it back
            loaded = ConfigManager.load(temp_path)
            
            # Verify
            assert loaded.llm.model_type == "custom"
            assert "custom" in loaded.llm.models
            assert loaded.llm.models["custom"].temperature == 0.7
            
            # Validate
            errors = loaded.validate()
            assert len(errors) == 0
        finally:
            os.unlink(temp_path)
    
    def test_migration_from_old_format(self):
        """Test migration from old configuration format"""
        old_config = {
            "model_path": "./models",
            "temperature": 0.5,
            "n_threads": 8,
            "_version": "1.0"
        }
        
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            yaml.dump(old_config, f)
            temp_path = f.name
        
        try:
            # Load old config (should auto-upgrade)
            config = ConfigManager.load(temp_path)
            
            # Verify upgraded
            assert config.llm.model_path == "./models"
            assert config.llm.temperature == 0.5
            assert config.llm.n_threads == 8
            assert config.version == "3.0"
        finally:
            os.unlink(temp_path)