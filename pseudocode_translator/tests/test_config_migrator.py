"""
Tests for configuration migration module
"""

import pytest
import json
import yaml
from pathlib import Path
from datetime import datetime
import shutil

from pseudocode_translator.config_migrator import (
    ConfigMigrator,
    MigrationLog,
    auto_migrate_config
)
from pseudocode_translator.config_schema import TranslatorConfigSchema


class TestMigrationLog:
    """Test MigrationLog class"""
    
    def test_initialization(self):
        """Test MigrationLog initialization"""
        log = MigrationLog(
            version_from="1.0",
            version_to="2.0",
            changes=[],
            warnings=[],
            timestamp=datetime.now()
        )
        
        assert log.version_from == "1.0"
        assert log.version_to == "2.0"
        assert len(log.changes) == 0
        assert len(log.warnings) == 0
        assert isinstance(log.timestamp, datetime)
    
    def test_add_change(self):
        """Test adding change records"""
        log = MigrationLog("1.0", "2.0", [], [], datetime.now())
        log.add_change("Moved temperature to llm.temperature")
        
        assert len(log.changes) == 1
        assert log.changes[0] == "Moved temperature to llm.temperature"
    
    def test_add_warning(self):
        """Test adding warnings"""
        log = MigrationLog("1.0", "2.0", [], [], datetime.now())
        log.add_warning("Unknown configuration option: custom_field")
        
        assert len(log.warnings) == 1
        assert "custom_field" in log.warnings[0]
    
    def test_to_dict(self):
        """Test converting to dictionary"""
        timestamp = datetime.now()
        log = MigrationLog(
            "1.0", "2.0", 
            ["change1"], ["warning1"], 
            timestamp
        )
        
        result = log.to_dict()
        
        assert result['version_from'] == "1.0"
        assert result['version_to'] == "2.0"
        assert result['changes'] == ["change1"]
        assert result['warnings'] == ["warning1"]
        assert result['timestamp'] == timestamp.isoformat()
    
    def test_format_report(self):
        """Test formatting migration report"""
        log = MigrationLog(
            "1.0", "2.0",
            ["Added llm section", "Moved temperature"],
            ["Unknown field ignored"],
            datetime.now()
        )
        
        report = log.format_report()
        
        assert "Configuration Migration Report" in report
        assert "From version: 1.0" in report
        assert "To version: 2.0" in report
        assert "Added llm section" in report
        assert "Moved temperature" in report
        assert "Unknown field ignored" in report


class TestConfigMigrator:
    """Test ConfigMigrator class"""
    
    def test_detect_version_explicit(self):
        """Test version detection with explicit _version field"""
        migrator = ConfigMigrator()
        
        config_dict = {"_version": "1.5"}
        version = migrator.detect_version(config_dict)
        
        assert version == "1.5"
    
    def test_detect_version_1_0(self):
        """Test detecting version 1.0 (flat structure)"""
        migrator = ConfigMigrator()
        
        config_dict = {
            "model_path": "./models",
            "temperature": 0.5,
            "max_tokens": 1024
        }
        
        version = migrator.detect_version(config_dict)
        assert version == "1.0"
    
    def test_detect_version_1_1(self):
        """Test detecting version 1.1 (has llm but no streaming)"""
        migrator = ConfigMigrator()
        
        config_dict = {
            "llm": {
                "model_path": "./models",
                "temperature": 0.5
            }
        }
        
        version = migrator.detect_version(config_dict)
        assert version == "1.1"
    
    def test_detect_version_1_2(self):
        """Test detecting version 1.2 (has llm and streaming but no model_configs)"""
        migrator = ConfigMigrator()
        
        config_dict = {
            "llm": {
                "model_path": "./models",
                "temperature": 0.5
            },
            "streaming": {
                "enable_streaming": True
            }
        }
        
        version = migrator.detect_version(config_dict)
        assert version == "1.2"
    
    def test_detect_version_current(self):
        """Test detecting current version"""
        migrator = ConfigMigrator()
        
        config_dict = {
            "llm": {
                "model_path": "./models",
                "model_configs": {
                    "qwen": {"name": "qwen", "enabled": True}
                }
            }
        }
        
        version = migrator.detect_version(config_dict)
        assert version == ConfigMigrator.CURRENT_VERSION
    
    def test_detect_version_unknown(self):
        """Test detecting unknown version"""
        migrator = ConfigMigrator()
        
        config_dict = {"unknown_structure": True}
        version = migrator.detect_version(config_dict)
        
        assert version == "unknown"
    
    def test_migrate_from_1_0(self, tmp_path):
        """Test migrating from version 1.0"""
        migrator = ConfigMigrator()
        
        # Create old format config
        config_file = tmp_path / "config.yaml"
        old_config = {
            "model_path": "./models",
            "model_file": "test.gguf",
            "temperature": 0.5,
            "n_threads": 8,
            "max_tokens": 512,
            "preserve_comments": True
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(old_config, f)
        
        # Migrate
        success, log = migrator.migrate(config_file, backup=True)
        
        assert success is True
        assert log.version_from == "1.0"
        assert log.version_to == ConfigMigrator.CURRENT_VERSION
        
        # Check migrated config
        with open(config_file, 'r') as f:
            new_config = yaml.safe_load(f)
        
        assert "llm" in new_config
        assert new_config["llm"]["temperature"] == 0.5
        assert new_config["llm"]["n_threads"] == 8
        assert new_config["llm"]["max_tokens"] == 512
        assert new_config["preserve_comments"] is True
        assert "streaming" in new_config
        assert "_version" in new_config
        
        # Check backup was created
        backup_files = list(tmp_path.glob("*.bak.*"))
        assert len(backup_files) == 1
    
    def test_migrate_from_1_1(self, tmp_path):
        """Test migrating from version 1.1"""
        migrator = ConfigMigrator()
        
        config_file = tmp_path / "config.json"
        old_config = {
            "llm": {
                "model_type": "gpt2",
                "temperature": 0.7,
                "n_ctx": 1024
            },
            "preserve_comments": True
        }
        
        with open(config_file, 'w') as f:
            json.dump(old_config, f)
        
        success, log = migrator.migrate(config_file)
        
        assert success is True
        assert log.version_from == "1.1"
        
        # Check migrated config
        with open(config_file, 'r') as f:
            new_config = json.load(f)
        
        assert "streaming" in new_config
        assert "model_configs" in new_config["llm"]
        assert "gpt2" in new_config["llm"]["model_configs"]
    
    def test_migrate_from_1_2(self, tmp_path):
        """Test migrating from version 1.2"""
        migrator = ConfigMigrator()
        
        config_file = tmp_path / "config.yaml"
        old_config = {
            "llm": {
                "model_type": "qwen",
                "models": {  # Old format
                    "qwen": {
                        "enabled": True,
                        "path": "/custom/path/qwen.gguf",
                        "params": {"temperature": 0.3}
                    }
                }
            },
            "streaming": {
                "chunk_size_bytes": 4096,  # Old field name
                "enable_compression": True,  # Old field name
                "max_buffer_mb": 100  # Old field name
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(old_config, f)
        
        success, log = migrator.migrate(config_file)
        
        assert success is True
        
        # Check migrated config
        with open(config_file, 'r') as f:
            new_config = yaml.safe_load(f)
        
        # Check model config migration
        assert "model_configs" in new_config["llm"]
        assert "models" not in new_config["llm"]
        assert new_config["llm"]["model_configs"]["qwen"]["model_path"] == "/custom/path/qwen.gguf"
        
        # Check streaming field renames
        assert new_config["streaming"]["chunk_size"] == 4096
        assert new_config["streaming"]["buffer_compression"] is True
        assert new_config["streaming"]["max_memory_mb"] == 100
        assert "chunk_size_bytes" not in new_config["streaming"]
    
    def test_migrate_current_version(self, tmp_path):
        """Test migrating config that's already current"""
        migrator = ConfigMigrator()
        
        config_file = tmp_path / "config.yaml"
        current_config = {
            "_version": ConfigMigrator.CURRENT_VERSION,
            "llm": {
                "model_type": "qwen",
                "model_configs": {}
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(current_config, f)
        
        success, log = migrator.migrate(config_file)
        
        assert success is True
        assert "already current version" in log.changes[0]
    
    def test_migrate_dry_run(self, tmp_path):
        """Test dry run migration"""
        migrator = ConfigMigrator()
        
        config_file = tmp_path / "config.yaml"
        old_config = {"model_path": "./models", "temperature": 0.5}
        
        with open(config_file, 'w') as f:
            yaml.dump(old_config, f)
        
        # Get original modification time
        original_mtime = config_file.stat().st_mtime
        
        # Dry run
        success, log = migrator.migrate(config_file, dry_run=True)
        
        assert success is True
        assert len(log.changes) > 0
        
        # File should not be modified
        assert config_file.stat().st_mtime == original_mtime
        
        # Original content should be unchanged
        with open(config_file, 'r') as f:
            content = yaml.safe_load(f)
        assert content == old_config
    
    def test_migrate_no_backup(self, tmp_path):
        """Test migration without backup"""
        migrator = ConfigMigrator()
        
        config_file = tmp_path / "config.yaml"
        old_config = {"model_path": "./models"}
        
        with open(config_file, 'w') as f:
            yaml.dump(old_config, f)
        
        success, log = migrator.migrate(config_file, backup=False)
        
        assert success is True
        
        # No backup should be created
        backup_files = list(tmp_path.glob("*.bak.*"))
        assert len(backup_files) == 0
    
    def test_migrate_generic(self, tmp_path):
        """Test generic migration for unknown format"""
        migrator = ConfigMigrator()
        
        config_file = tmp_path / "config.yaml"
        unknown_config = {
            "custom_field": "value",
            "temperature": 0.5,
            "model_path": "./models",
            "streaming": {
                "enable": True
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(unknown_config, f)
        
        success, log = migrator.migrate(config_file)
        
        assert success is True
        assert "generic migration" in log.warnings[0]
        
        # Check migrated config
        with open(config_file, 'r') as f:
            new_config = yaml.safe_load(f)
        
        assert new_config["llm"]["temperature"] == 0.5
        assert new_config["llm"]["model_path"] == "./models"
    
    def test_check_needs_migration(self, tmp_path):
        """Test checking if migration is needed"""
        migrator = ConfigMigrator()
        
        # Old version config
        old_config_file = tmp_path / "old.yaml"
        with open(old_config_file, 'w') as f:
            yaml.dump({"model_path": "./models"}, f)
        
        needs_migration, version = migrator.check_needs_migration(old_config_file)
        assert needs_migration is True
        assert version == "1.0"
        
        # Current version config
        current_config_file = tmp_path / "current.yaml"
        with open(current_config_file, 'w') as f:
            yaml.dump({"_version": ConfigMigrator.CURRENT_VERSION}, f)
        
        needs_migration, version = migrator.check_needs_migration(current_config_file)
        assert needs_migration is False
        assert version == ConfigMigrator.CURRENT_VERSION
    
    def test_batch_migrate(self, tmp_path):
        """Test batch migration of multiple files"""
        migrator = ConfigMigrator()
        
        # Create multiple config files
        configs = {
            "config1.yaml": {"model_path": "./models", "temperature": 0.5},
            "config2.yaml": {"llm": {"model_type": "gpt2"}},
            "config3.yaml": {"_version": ConfigMigrator.CURRENT_VERSION}
        }
        
        for filename, content in configs.items():
            with open(tmp_path / filename, 'w') as f:
                yaml.dump(content, f)
        
        # Also create a backup file that should be skipped
        with open(tmp_path / "config.yaml.bak", 'w') as f:
            yaml.dump({}, f)
        
        # Batch migrate
        results = migrator.batch_migrate(tmp_path, pattern="*.yaml")
        
        assert len(results) == 3
        
        # Check results
        assert results[str(tmp_path / "config1.yaml")][0] is True  # Success
        assert results[str(tmp_path / "config2.yaml")][0] is True
        assert results[str(tmp_path / "config3.yaml")][0] is True
        
        # config3 should not need migration
        log3 = results[str(tmp_path / "config3.yaml")][1]
        assert "No migration needed" in log3.changes[0]


class TestAutoMigrate:
    """Test auto_migrate_config function"""
    
    def test_auto_migrate_success(self, tmp_path):
        """Test successful auto migration"""
        config_file = tmp_path / "config.yaml"
        old_config = {
            "model_path": "./models",
            "temperature": 0.5
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(old_config, f)
        
        success, log = auto_migrate_config(config_file)
        
        assert success is True
        assert log is not None
        assert log.version_from == "1.0"
    
    def test_auto_migrate_no_migration_needed(self, tmp_path):
        """Test auto migration when no migration is needed"""
        config_file = tmp_path / "config.yaml"
        current_config = {
            "_version": ConfigMigrator.CURRENT_VERSION,
            "llm": {"model_type": "qwen"}
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(current_config, f)
        
        success, log = auto_migrate_config(config_file)
        
        assert success is True
        assert log is None  # No migration performed
    
    def test_auto_migrate_file_not_found(self, tmp_path):
        """Test auto migration with non-existent file"""
        config_file = tmp_path / "nonexistent.yaml"
        
        success, log = auto_migrate_config(config_file)
        
        assert success is False
        assert log is None


class TestMigrationValidation:
    """Test that migrated configs are valid"""
    
    def test_migrated_config_is_valid(self, tmp_path):
        """Test that configs migrated from all versions are valid"""
        migrator = ConfigMigrator()
        
        # Test configs from different versions
        test_configs = [
            # Version 1.0
            {
                "model_path": "./models",
                "temperature": 0.5,
                "n_threads": 4,
                "max_tokens": 1024
            },
            # Version 1.1
            {
                "llm": {
                    "model_type": "gpt2",
                    "temperature": 0.7
                }
            },
            # Version 1.2
            {
                "llm": {"model_type": "qwen"},
                "streaming": {"enable_streaming": True}
            }
        ]
        
        for i, old_config in enumerate(test_configs):
            config_file = tmp_path / f"config{i}.yaml"
            
            with open(config_file, 'w') as f:
                yaml.dump(old_config, f)
            
            # Migrate
            success, log = migrator.migrate(config_file)
            assert success is True
            
            # Load and validate migrated config
            with open(config_file, 'r') as f:
                migrated_config = yaml.safe_load(f)
            
            # Should be able to create a valid schema
            try:
                schema = TranslatorConfigSchema.from_dict(migrated_config)
                assert schema is not None
            except Exception as e:
                pytest.fail(f"Migrated config failed validation: {e}")


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_migrate_empty_config(self, tmp_path):
        """Test migrating empty configuration"""
        migrator = ConfigMigrator()
        
        config_file = tmp_path / "empty.yaml"
        with open(config_file, 'w') as f:
            yaml.dump({}, f)
        
        success, log = migrator.migrate(config_file)
        
        assert success is True
        
        # Should create default structure
        with open(config_file, 'r') as f:
            new_config = yaml.safe_load(f)
        
        assert "llm" in new_config
        assert "_version" in new_config
    
    def test_migrate_corrupted_file(self, tmp_path):
        """Test migrating corrupted file"""
        migrator = ConfigMigrator()
        
        config_file = tmp_path / "corrupted.yaml"
        with open(config_file, 'w') as f:
            f.write("invalid: yaml: content: [[[")
        
        success, log = migrator.migrate(config_file)
        
        assert success is False
        assert len(log.warnings) > 0
    
    def test_migrate_with_extra_fields(self, tmp_path):
        """Test migrating config with unknown fields"""
        migrator = ConfigMigrator()
        
        config_file = tmp_path / "extra.yaml"
        old_config = {
            "model_path": "./models",
            "unknown_field1": "value1",
            "custom_section": {
                "nested_unknown": "value2"
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(old_config, f)
        
        success, log = migrator.migrate(config_file)
        
        assert success is True
        # Unknown fields should be mentioned in warnings or ignored


if __name__ == "__main__":
    pytest.main([__file__, "-v"])