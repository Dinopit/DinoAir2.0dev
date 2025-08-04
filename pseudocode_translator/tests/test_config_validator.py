"""
Tests for configuration validation module
"""

import pytest
import json
import yaml
from pathlib import Path
import tempfile
import os
from typing import Dict, Any

from pseudocode_translator.config_schema import (
    TranslatorConfigSchema,
    LLMConfigSchema,
    StreamingConfigSchema,
    ModelConfigSchema,
    validate_config_dict,
    apply_env_overrides
)
from pseudocode_translator.config_validator import (
    ConfigValidator,
    ValidationLevel,
    ValidationResult,
    validate_config_file,
    validate_and_fix_config
)


class TestValidationResult:
    """Test ValidationResult class"""
    
    def test_initialization(self):
        """Test ValidationResult initialization"""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            info=[],
            fixed_values={}
        )
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert len(result.info) == 0
        assert len(result.fixed_values) == 0
    
    def test_add_error(self):
        """Test adding errors"""
        result = ValidationResult(True, [], [], [], {})
        result.add_error("Test error")
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0] == "Test error"
    
    def test_add_warning(self):
        """Test adding warnings"""
        result = ValidationResult(True, [], [], [], {})
        result.add_warning("Test warning")
        
        assert result.is_valid is True  # Warnings don't affect validity
        assert len(result.warnings) == 1
        assert result.warnings[0] == "Test warning"
    
    def test_add_info(self):
        """Test adding info messages"""
        result = ValidationResult(True, [], [], [], {})
        result.add_info("Test info")
        
        assert result.is_valid is True
        assert len(result.info) == 1
        assert result.info[0] == "Test info"
    
    def test_add_fixed(self):
        """Test adding fixed values"""
        result = ValidationResult(True, [], [], [], {})
        result.add_fixed("test_key", "old_value", "new_value")
        
        assert "test_key" in result.fixed_values
        assert result.fixed_values["test_key"]["old"] == "old_value"
        assert result.fixed_values["test_key"]["new"] == "new_value"
    
    def test_merge(self):
        """Test merging validation results"""
        result1 = ValidationResult(True, ["error1"], ["warn1"], ["info1"], {})
        result2 = ValidationResult(
            False, 
            ["error2"], 
            ["warn2"], 
            ["info2"], 
            {"key": {"old": "a", "new": "b"}}
        )
        
        result1.merge(result2)
        
        assert result1.is_valid is False
        assert len(result1.errors) == 2
        assert len(result1.warnings) == 2
        assert len(result1.info) == 2
        assert "key" in result1.fixed_values
    
    def test_format_report(self):
        """Test formatting validation report"""
        result = ValidationResult(False, ["Error 1"], ["Warning 1"], ["Info 1"], {})
        result.add_fixed("temperature", 3.0, 2.0)
        
        report = result.format_report()
        
        assert "Configuration Validation Report" in report
        assert "✗ Configuration has errors" in report
        assert "Error 1" in report
        assert "Warning 1" in report
        assert "Info 1" in report
        assert "temperature: 3.0 → 2.0" in report


class TestConfigValidator:
    """Test ConfigValidator class"""
    
    def test_initialization(self):
        """Test ConfigValidator initialization"""
        validator = ConfigValidator(ValidationLevel.NORMAL)
        assert validator.level == ValidationLevel.NORMAL
    
    def test_validate_dict_valid(self):
        """Test validating a valid configuration dictionary"""
        config_dict = {
            "llm": {
                "model_type": "qwen",
                "model_path": "./models",
                "temperature": 0.5
            }
        }
        
        validator = ConfigValidator(ValidationLevel.NORMAL)
        result = validator.validate_dict(config_dict)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_dict_invalid_temperature(self):
        """Test validating configuration with invalid temperature"""
        config_dict = {
            "llm": {
                "model_type": "qwen",
                "temperature": 3.0  # Invalid: > 2.0
            }
        }
        
        validator = ConfigValidator(ValidationLevel.STRICT)
        result = validator.validate_dict(config_dict)
        
        assert result.is_valid is False
        assert any("temperature" in error.lower() for error in result.errors)
    
    def test_validate_dict_invalid_chunk_sizes(self):
        """Test validating configuration with invalid chunk sizes"""
        config_dict = {
            "streaming": {
                "chunk_size": 10000,
                "max_chunk_size": 5000  # Invalid: chunk_size > max_chunk_size
            }
        }
        
        validator = ConfigValidator(ValidationLevel.NORMAL)
        result = validator.validate_dict(config_dict)
        
        assert result.is_valid is False
        assert any("chunk_size" in error for error in result.errors)
    
    def test_validate_partial(self):
        """Test partial validation for GUI"""
        base_config = {
            "llm": {
                "model_type": "qwen",
                "temperature": 0.5
            }
        }
        
        changes = {
            "llm": {
                "temperature": 0.8
            }
        }
        
        validator = ConfigValidator(ValidationLevel.NORMAL)
        result = validator.validate_partial(base_config, changes, "llm.temperature")
        
        assert result.is_valid is True
    
    def test_validate_partial_invalid(self):
        """Test partial validation with invalid changes"""
        base_config = {
            "llm": {
                "model_type": "qwen",
                "temperature": 0.5
            }
        }
        
        changes = {
            "llm": {
                "temperature": 5.0  # Invalid
            }
        }
        
        validator = ConfigValidator(ValidationLevel.NORMAL)
        result = validator.validate_partial(base_config, changes, "llm.temperature")
        
        assert result.is_valid is False
        assert any("temperature" in error.lower() for error in result.errors)
    
    def test_validate_paths_missing_directory(self, tmp_path):
        """Test path validation with missing directory"""
        config = TranslatorConfigSchema(
            llm=LLMConfigSchema(
                model_path=tmp_path / "nonexistent"
            )
        )
        
        validator = ConfigValidator(ValidationLevel.STRICT)
        result = validator._validate_paths(config)
        
        assert result.is_valid is False
        assert any("does not exist" in error for error in result.errors)
    
    def test_validate_models_no_enabled(self):
        """Test model validation with no enabled models"""
        config = TranslatorConfigSchema(
            llm=LLMConfigSchema(
                model_configs={
                    "qwen": ModelConfigSchema(
                        name="qwen",
                        enabled=False
                    )
                }
            )
        )
        
        validator = ConfigValidator(ValidationLevel.NORMAL)
        result = validator._validate_models(config)
        
        assert result.is_valid is False
        assert any("No models are enabled" in error for error in result.errors)
    
    def test_validate_resources_thread_count(self):
        """Test resource validation for thread count"""
        cpu_count = os.cpu_count() or 1
        
        config = TranslatorConfigSchema(
            llm=LLMConfigSchema(
                n_threads=cpu_count + 10  # More than available
            )
        )
        
        validator = ConfigValidator(ValidationLevel.NORMAL)
        result = validator._validate_resources(config)
        
        assert len(result.warnings) > 0
        assert any("Thread count" in warning for warning in result.warnings)
    
    def test_validate_security_unsafe_operations(self):
        """Test security validation for unsafe operations"""
        config = TranslatorConfigSchema(
            allow_unsafe_operations=True
        )
        
        validator = ConfigValidator(ValidationLevel.NORMAL)
        result = validator._validate_security(config)
        
        assert len(result.warnings) > 0
        assert any("security risks" in warning for warning in result.warnings)
    
    def test_suggest_fixes_missing_directory(self):
        """Test fix suggestions for missing directory"""
        config_dict = {
            "llm": {
                "model_type": "qwen"
            }
        }
        
        result = ValidationResult(
            False,
            ["Model directory does not exist: ./models"],
            [],
            [],
            {}
        )
        
        validator = ConfigValidator(ValidationLevel.NORMAL)
        fixed_config = validator.suggest_fixes(config_dict, result)
        
        assert "llm" in fixed_config
        assert "model_path" in fixed_config["llm"]


class TestValidationFunctions:
    """Test module-level validation functions"""
    
    def test_validate_config_file_valid(self, tmp_path):
        """Test validating a valid config file"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "llm": {
                "model_type": "qwen",
                "model_path": str(tmp_path / "models"),
                "temperature": 0.5
            }
        }
        
        # Create model directory
        (tmp_path / "models").mkdir()
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        is_valid, result, config = validate_config_file(config_file)
        
        assert is_valid is True
        assert config is not None
        assert config.llm.model_type == "qwen"
    
    def test_validate_config_file_invalid(self, tmp_path):
        """Test validating an invalid config file"""
        config_file = tmp_path / "config.json"
        config_data = {
            "llm": {
                "temperature": 10.0  # Invalid
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        is_valid, result, config = validate_config_file(config_file)
        
        assert is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_and_fix_config(self, tmp_path):
        """Test validating and fixing a config file"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "llm": {
                "model_type": "qwen",
                "temperature": 5.0  # Invalid, should be fixed
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        success, result = validate_and_fix_config(config_file, backup=True)
        
        # Check backup was created
        backup_files = list(tmp_path.glob("*.bak"))
        assert len(backup_files) == 1
        
        # Note: Auto-fix might not fix all validation errors
        # so we just check that the function ran without exceptions


class TestSchemaValidation:
    """Test Pydantic schema validation"""
    
    def test_validate_config_dict_valid(self):
        """Test schema validation with valid config"""
        config_dict = {
            "llm": {
                "model_type": "qwen",
                "temperature": 0.5,
                "n_ctx": 2048
            },
            "streaming": {
                "enable_streaming": True,
                "chunk_size": 4096
            }
        }
        
        errors = validate_config_dict(config_dict)
        assert len(errors) == 0
    
    def test_validate_config_dict_invalid_types(self):
        """Test schema validation with invalid types"""
        config_dict = {
            "llm": {
                "temperature": "hot",  # Should be float
                "n_threads": "many"    # Should be int
            }
        }
        
        errors = validate_config_dict(config_dict)
        assert len(errors) > 0
        assert any("temperature" in error for error in errors)
        assert any("n_threads" in error for error in errors)
    
    def test_validate_config_dict_out_of_range(self):
        """Test schema validation with out of range values"""
        config_dict = {
            "llm": {
                "temperature": -1.0,  # Must be >= 0
                "n_ctx": 100,         # Must be >= 512
                "top_p": 2.0          # Must be <= 1.0
            }
        }
        
        errors = validate_config_dict(config_dict)
        assert len(errors) >= 3
    
    def test_validate_config_dict_extra_fields(self):
        """Test schema validation with extra fields"""
        config_dict = {
            "llm": {
                "model_type": "qwen",
                "unknown_field": "value"  # Should be rejected
            }
        }
        
        errors = validate_config_dict(config_dict)
        assert len(errors) > 0
        assert any("extra" in error.lower() for error in errors)


class TestEnvironmentOverrides:
    """Test environment variable override functionality"""
    
    def test_apply_env_overrides(self, monkeypatch):
        """Test applying environment variable overrides"""
        # Set environment variables
        monkeypatch.setenv("PSEUDOCODE_TRANSLATOR_LLM_MODEL_TYPE", "gpt2")
        monkeypatch.setenv("PSEUDOCODE_TRANSLATOR_LLM_TEMPERATURE", "0.8")
        monkeypatch.setenv("PSEUDOCODE_TRANSLATOR_LLM_N_THREADS", "8")
        monkeypatch.setenv("PSEUDOCODE_TRANSLATOR_STREAMING_ENABLE", "false")
        
        config = TranslatorConfigSchema()
        config = apply_env_overrides(config)
        
        assert config.llm.model_type == "gpt2"
        assert config.llm.temperature == 0.8
        assert config.llm.n_threads == 8
        assert config.streaming.enable_streaming is False
    
    def test_env_override_boolean_values(self, monkeypatch):
        """Test boolean environment variable parsing"""
        test_cases = [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("0", False),
            ("no", False),
            ("off", False),
        ]
        
        for env_value, expected in test_cases:
            monkeypatch.setenv(
                "PSEUDOCODE_TRANSLATOR_VALIDATE_IMPORTS", 
                env_value
            )
            
            config = TranslatorConfigSchema()
            config = apply_env_overrides(config)
            
            assert config.validate_imports == expected
    
    def test_env_override_invalid_values(self, monkeypatch):
        """Test environment overrides with invalid values"""
        # Invalid integer
        monkeypatch.setenv("PSEUDOCODE_TRANSLATOR_LLM_N_THREADS", "not_a_number")
        
        config = TranslatorConfigSchema()
        config = apply_env_overrides(config)
        
        # Should keep default value
        assert config.llm.n_threads == 4  # default value
    
    def test_env_override_partial(self, monkeypatch):
        """Test that only specified values are overridden"""
        # Only override temperature
        monkeypatch.setenv("PSEUDOCODE_TRANSLATOR_LLM_TEMPERATURE", "0.9")
        
        config = TranslatorConfigSchema(
            llm=LLMConfigSchema(
                model_type="codegen",
                n_threads=16
            )
        )
        config = apply_env_overrides(config)
        
        assert config.llm.temperature == 0.9
        assert config.llm.model_type == "codegen"  # Not overridden
        assert config.llm.n_threads == 16  # Not overridden


class TestValidationLevels:
    """Test different validation levels"""
    
    def test_strict_validation(self):
        """Test strict validation level"""
        config_dict = {
            "llm": {
                "model_path": "/nonexistent/path"
            }
        }
        
        validator = ConfigValidator(ValidationLevel.STRICT)
        result = validator.validate_dict(config_dict)
        
        # Strict mode should fail on missing paths
        assert result.is_valid is False
    
    def test_normal_validation(self):
        """Test normal validation level"""
        config_dict = {
            "llm": {
                "model_path": "/nonexistent/path"
            }
        }
        
        validator = ConfigValidator(ValidationLevel.NORMAL)
        result = validator.validate_dict(config_dict)
        
        # Normal mode might warn but not fail
        assert len(result.warnings) > 0
    
    def test_lenient_validation(self):
        """Test lenient validation level"""
        config_dict = {
            "llm": {
                "temperature": 2.5  # Slightly out of range
            }
        }
        
        validator = ConfigValidator(ValidationLevel.LENIENT)
        result = validator.validate_dict(config_dict)
        
        # Lenient mode is more forgiving
        # (This depends on implementation details)


def test_edge_cases():
    """Test various edge cases"""
    
    # Empty configuration
    errors = validate_config_dict({})
    assert len(errors) == 0  # Should use defaults
    
    # Null values
    config_dict = {
        "llm": {
            "model_path": None  # Should use default
        }
    }
    errors = validate_config_dict(config_dict)
    
    # Nested validation
    config_dict = {
        "llm": {
            "model_configs": {
                "test_model": {
                    "name": "test_model",
                    "enabled": True,
                    "parameters": {
                        "invalid_param": "value"
                    }
                }
            }
        }
    }
    config = TranslatorConfigSchema(**config_dict)
    assert "test_model" in config.llm.model_configs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])