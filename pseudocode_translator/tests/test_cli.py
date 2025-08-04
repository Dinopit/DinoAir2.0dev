"""
Unit Tests for Command-Line Interface

This module tests the config_tool CLI functionality including all commands,
argument parsing, and error handling.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import json
import yaml
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_tool import ConfigTool
from config import ConfigManager, ConfigProfile, TranslatorConfig


class TestConfigTool(unittest.TestCase):
    """Test the ConfigTool CLI interface"""
    
    def setUp(self):
        """Set up test environment"""
        self.tool = ConfigTool()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = Path(self.temp_dir) / "test_config.yaml"
    
    def tearDown(self):
        """Clean up test environment"""
        # Clean up temporary files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_parser_creation(self):
        """Test that argument parser is created correctly"""
        parser = self.tool._create_parser()
        self.assertIsNotNone(parser)
        
        # Check main arguments
        actions = {action.dest for action in parser._actions}
        self.assertIn('verbose', actions)
        self.assertIn('command', actions)
    
    def test_no_command(self):
        """Test behavior when no command is provided"""
        with patch('sys.stdout') as mock_stdout:
            result = self.tool.run([])
            self.assertEqual(result, 1)
    
    def test_validate_command_success(self):
        """Test validate command with valid configuration"""
        # Create a valid config file
        config_data = {
            '_version': '3.0',
            'llm': {
                'model_type': 'qwen',
                'model_path': 'models/test.gguf',
                'temperature': 0.7,
                'n_ctx': 2048,
                'n_threads': 4,
                'n_gpu_layers': 0,
                'max_tokens': 1000,
                'models': {}
            },
            'streaming': {
                'enabled': False,
                'chunk_size': 4096
            },
            'validate_imports': True,
            'check_undefined_vars': True,
            'allow_unsafe_operations': False
        }
        
        with open(self.temp_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Test validate command
        with patch('builtins.print') as mock_print:
            result = self.tool.run(['validate', str(self.temp_file)])
            self.assertEqual(result, 0)
            
            # Check for success message
            print_calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(
                any('Configuration is valid' in call for call in print_calls)
            )
    
    def test_validate_command_invalid_file(self):
        """Test validate command with non-existent file"""
        non_existent = self.temp_dir + '/non_existent.yaml'
        
        with patch('logging.Logger.error') as mock_error:
            result = self.tool.run(['validate', non_existent])
            self.assertEqual(result, 1)
            mock_error.assert_called()
    
    def test_validate_command_invalid_config(self):
        """Test validate command with invalid configuration"""
        # Create an invalid config file (missing required fields)
        config_data = {
            '_version': '3.0',
            'llm': {
                # Missing required fields
                'temperature': 0.7
            }
        }
        
        with open(self.temp_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Mock validation to return errors
        with patch.object(TranslatorConfig, 'validate') as mock_validate:
            mock_validate.return_value = ['Missing model_type', 'Invalid path']
            
            with patch('builtins.print') as mock_print:
                result = self.tool.run(['validate', str(self.temp_file)])
                self.assertEqual(result, 1)
                
                # Check error messages were printed
                print_calls = [str(call) for call in mock_print.call_args_list]
                self.assertTrue(
                    any('Validation errors found' in call for call in print_calls)
                )
    
    def test_generate_command_basic(self):
        """Test generate command with basic options"""
        output_file = Path(self.temp_dir) / 'generated_config.yaml'
        
        with patch('builtins.print'):
            result = self.tool.run([
                'generate',
                '-o', str(output_file),
                '-p', 'development'
            ])
            self.assertEqual(result, 0)
            self.assertTrue(output_file.exists())
    
    def test_generate_command_overwrite_prompt(self):
        """Test generate command with existing file (user declines overwrite)"""
        # Create existing file
        self.temp_file.write_text("existing content")
        
        with patch('builtins.input', return_value='n'):
            result = self.tool.run([
                'generate',
                '-o', str(self.temp_file),
                '-p', 'production'
            ])
            self.assertEqual(result, 1)
            # File should still have original content
            self.assertEqual(self.temp_file.read_text(), "existing content")
    
    def test_generate_command_overwrite_confirm(self):
        """Test generate command with existing file (user confirms overwrite)"""
        # Create existing file
        self.temp_file.write_text("existing content")
        
        with patch('builtins.input', return_value='y'):
            result = self.tool.run([
                'generate',
                '-o', str(self.temp_file),
                '-p', 'testing'
            ])
            self.assertEqual(result, 0)
            # File should be overwritten
            self.assertNotEqual(self.temp_file.read_text(), "existing content")
    
    def test_generate_command_json_format(self):
        """Test generate command with JSON output format"""
        output_file = Path(self.temp_dir) / 'config.json'
        
        result = self.tool.run([
            'generate',
            '-o', str(output_file),
            '--format', 'json'
        ])
        self.assertEqual(result, 0)
        
        # Verify JSON format
        with open(output_file, 'r') as f:
            data = json.load(f)
            self.assertIn('_version', data)
            self.assertIn('llm', data)
    
    def test_generate_command_custom_profile(self):
        """Test generate command with custom profile (triggers wizard)"""
        output_file = Path(self.temp_dir) / 'custom_config.yaml'
        
        # Mock wizard to return a config
        mock_config = MagicMock()
        with patch.object(ConfigManager, 'create_wizard', return_value=mock_config):
            with patch.object(ConfigManager, 'save'):
                result = self.tool.run([
                    'generate',
                    '-o', str(output_file),
                    '-p', 'custom'
                ])
                self.assertEqual(result, 0)
                ConfigManager.create_wizard.assert_called_once()
    
    def test_check_command_with_file(self):
        """Test check command with specific config file"""
        # Create a config file
        config_data = {
            '_version': '3.0',
            'llm': {'model_type': 'qwen'},
            'streaming': {'enabled': True}
        }
        
        with open(self.temp_file, 'w') as f:
            yaml.dump(config_data, f)
        
        with patch('builtins.print') as mock_print:
            result = self.tool.run(['check', str(self.temp_file)])
            self.assertEqual(result, 0)
            
            # Check output contains config info
            print_calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(
                any('Configuration File:' in call for call in print_calls)
            )
    
    def test_check_command_no_file(self):
        """Test check command without specific file"""
        with patch('builtins.print') as mock_print:
            with patch.object(Path, 'exists', return_value=False):
                result = self.tool.run(['check'])
                self.assertEqual(result, 0)
                
                # Check output mentions no default config
                print_calls = [str(call) for call in mock_print.call_args_list]
                self.assertTrue(
                    any('No default configuration found' in call 
                        for call in print_calls)
                )
    
    def test_check_command_with_env(self):
        """Test check command with environment variable checking"""
        # Set some environment variables
        os.environ['PSEUDOCODE_LLM_MODEL_TYPE'] = 'test_model'
        os.environ['PSEUDOCODE_LLM_TEMPERATURE'] = '0.5'
        
        try:
            with patch('builtins.print') as mock_print:
                result = self.tool.run(['check', '--env'])
                self.assertEqual(result, 0)
                
                # Check env vars were printed
                print_calls = [str(call) for call in mock_print.call_args_list]
                self.assertTrue(
                    any('PSEUDOCODE_LLM_MODEL_TYPE=test_model' in call 
                        for call in print_calls)
                )
        finally:
            # Clean up env vars
            del os.environ['PSEUDOCODE_LLM_MODEL_TYPE']
            del os.environ['PSEUDOCODE_LLM_TEMPERATURE']
    
    def test_wizard_command_success(self):
        """Test wizard command successful completion"""
        output_file = Path(self.temp_dir) / 'wizard_config.yaml'
        
        # Mock wizard interaction
        mock_config = MagicMock()
        with patch.object(ConfigManager, 'create_wizard', return_value=mock_config):
            with patch.object(ConfigManager, 'save'):
                with patch('builtins.print') as mock_print:
                    result = self.tool.run(['wizard', '-o', str(output_file)])
                    self.assertEqual(result, 0)
                    
                    # Check success message
                    print_calls = [str(call) for call in mock_print.call_args_list]
                    self.assertTrue(
                        any('Configuration saved to:' in call 
                            for call in print_calls)
                    )
    
    def test_wizard_command_cancelled(self):
        """Test wizard command when user cancels"""
        with patch.object(ConfigManager, 'create_wizard', 
                         side_effect=KeyboardInterrupt):
            with patch('builtins.print') as mock_print:
                result = self.tool.run(['wizard'])
                self.assertEqual(result, 1)
                
                # Check cancellation message
                print_calls = [str(call) for call in mock_print.call_args_list]
                self.assertTrue(
                    any('Wizard cancelled' in call for call in print_calls)
                )
    
    def test_info_command(self):
        """Test info command"""
        # Create a config file with known content
        config_data = {
            '_version': '3.0',
            'llm': {
                'model_type': 'qwen',
                'model_path': '/path/to/model.gguf',
                'temperature': 0.7,
                'n_ctx': 2048,
                'n_threads': 4,
                'n_gpu_layers': 10,
                'max_tokens': 1000,
                'models': {
                    'qwen': {'enabled': True, 'name': 'qwen'},
                    'gpt': {'enabled': False, 'name': 'gpt'}
                }
            },
            'streaming': {
                'enabled': True,
                'chunk_size': 8192
            },
            'validate_imports': True,
            'check_undefined_vars': False,
            'allow_unsafe_operations': False
        }
        
        with open(self.temp_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Mock the config loading
        mock_config = TranslatorConfig()
        mock_config.llm.model_type = 'qwen'
        mock_config.llm.model_path = '/path/to/model.gguf'
        mock_config.llm.temperature = 0.7
        mock_config.llm.n_ctx = 2048
        mock_config.llm.n_threads = 4
        mock_config.llm.n_gpu_layers = 10
        mock_config.llm.models = {
            'qwen': MagicMock(enabled=True),
            'gpt': MagicMock(enabled=False)
        }
        mock_config.streaming.enabled = True
        mock_config.streaming.chunk_size = 8192
        mock_config.validate_imports = True
        mock_config.check_undefined_vars = False
        mock_config.allow_unsafe_operations = False
        
        with patch.object(ConfigManager, 'load', return_value=mock_config):
            with patch('builtins.print') as mock_print:
                result = self.tool.run(['info', str(self.temp_file)])
                self.assertEqual(result, 0)
                
                # Check various info was printed
                print_calls = [str(call) for call in mock_print.call_args_list]
                self.assertTrue(
                    any('Model Type: qwen' in call for call in print_calls)
                )
                self.assertTrue(
                    any('Temperature: 0.7' in call for call in print_calls)
                )
                self.assertTrue(
                    any('Streaming:' in call for call in print_calls)
                )
    
    def test_upgrade_command_already_new(self):
        """Test upgrade command on already upgraded config"""
        # Create a v3.0 config
        config_data = {
            '_version': '3.0',
            'llm': {'model_type': 'qwen'}
        }
        
        with open(self.temp_file, 'w') as f:
            yaml.dump(config_data, f)
        
        with patch('logging.Logger.info') as mock_info:
            result = self.tool.run(['upgrade', str(self.temp_file)])
            self.assertEqual(result, 0)
            
            # Check message about already being new format
            info_calls = [str(call) for call in mock_info.call_args_list]
            self.assertTrue(
                any('already in the new format' in call for call in info_calls)
            )
    
    def test_upgrade_command_old_version(self):
        """Test upgrade command on old version config"""
        # Create an old version config
        old_config_data = {
            'version': '1.0',
            'model': {
                'type': 'qwen',
                'path': 'model.gguf'
            }
        }
        
        with open(self.temp_file, 'w') as f:
            yaml.dump(old_config_data, f)
        
        # Mock the upgrade process
        new_config = MagicMock()
        new_config.validate.return_value = []  # No validation errors
        
        with patch.object(ConfigManager, 'load', return_value=new_config):
            with patch.object(ConfigManager, 'save'):
                with patch('builtins.print') as mock_print:
                    result = self.tool.run(['upgrade', str(self.temp_file)])
                    self.assertEqual(result, 0)
                    
                    # Check upgrade messages
                    print_calls = [str(call) for call in mock_print.call_args_list]
                    self.assertTrue(
                        any('Upgrade complete!' in call for call in print_calls)
                    )
    
    def test_upgrade_command_with_backup(self):
        """Test upgrade command creates backup"""
        # Create a config file
        config_data = {'version': '1.0', 'model': {'type': 'test'}}
        
        with open(self.temp_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Mock the upgrade
        new_config = MagicMock()
        new_config.validate.return_value = []
        
        with patch.object(ConfigManager, 'load', return_value=new_config):
            with patch.object(ConfigManager, 'save'):
                with patch('shutil.copy2') as mock_copy:
                    result = self.tool.run([
                        'upgrade', 
                        str(self.temp_file),
                        '--backup'
                    ])
                    self.assertEqual(result, 0)
                    
                    # Check backup was created
                    mock_copy.assert_called_once()
                    backup_path = mock_copy.call_args[0][1]
                    self.assertTrue(str(backup_path).endswith('.yaml.bak'))
    
    def test_upgrade_command_with_output(self):
        """Test upgrade command with different output file"""
        # Create input file
        config_data = {'version': '1.0', 'model': {'type': 'test'}}
        
        with open(self.temp_file, 'w') as f:
            yaml.dump(config_data, f)
        
        output_file = Path(self.temp_dir) / 'upgraded_config.yaml'
        
        # Mock the upgrade
        new_config = MagicMock()
        new_config.validate.return_value = []
        
        with patch.object(ConfigManager, 'load', return_value=new_config):
            with patch.object(ConfigManager, 'save') as mock_save:
                result = self.tool.run([
                    'upgrade',
                    str(self.temp_file),
                    '-o', str(output_file)
                ])
                self.assertEqual(result, 0)
                
                # Check save was called with output path
                save_path = mock_save.call_args[0][1]
                self.assertEqual(str(save_path), str(output_file))
    
    def test_verbose_flag(self):
        """Test verbose flag enables debug logging"""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Run with verbose flag
            self.tool.run(['-v', 'check'])
            
            # Check debug level was set
            mock_logger.setLevel.assert_called_with(logging.DEBUG)
    
    def test_error_handling_with_verbose(self):
        """Test error handling with verbose flag shows traceback"""
        # Create an invalid command that will cause an error
        with patch.object(ConfigManager, 'load', side_effect=Exception("Test error")):
            with patch('traceback.print_exc') as mock_traceback:
                result = self.tool.run(['-v', 'validate', 'nonexistent.yaml'])
                self.assertEqual(result, 1)
                
                # In verbose mode, traceback should be printed
                mock_traceback.assert_called()
    
    def test_unknown_command(self):
        """Test handling of unknown command"""
        with patch('logging.Logger.error') as mock_error:
            result = self.tool.run(['unknown_command'])
            self.assertEqual(result, 1)
            
            # Check error message
            error_calls = [str(call) for call in mock_error.call_args_list]
            self.assertTrue(
                any('Unknown command' in call for call in error_calls)
            )
    
    def test_main_entry_point(self):
        """Test main() function entry point"""
        with patch.object(ConfigTool, 'run', return_value=0) as mock_run:
            with patch('sys.exit') as mock_exit:
                from config_tool import main
                main()
                
                mock_run.assert_called_once()
                mock_exit.assert_called_with(0)


class TestCLIIntegration(unittest.TestCase):
    """Integration tests for CLI with actual file operations"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.tool = ConfigTool()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_full_workflow(self):
        """Test complete workflow: generate -> validate -> info -> upgrade"""
        config_file = Path(self.temp_dir) / 'workflow_config.yaml'
        
        # Step 1: Generate config
        result = self.tool.run([
            'generate',
            '-o', str(config_file),
            '-p', 'development'
        ])
        self.assertEqual(result, 0)
        self.assertTrue(config_file.exists())
        
        # Step 2: Validate config
        result = self.tool.run(['validate', str(config_file)])
        self.assertEqual(result, 0)
        
        # Step 3: Get info
        with patch('builtins.print'):
            result = self.tool.run(['info', str(config_file)])
            self.assertEqual(result, 0)
        
        # Step 4: Check (including env)
        with patch('builtins.print'):
            result = self.tool.run(['check', str(config_file), '--env'])
            self.assertEqual(result, 0)
    
    def test_config_formats(self):
        """Test handling of different config formats"""
        # Test YAML format
        yaml_file = Path(self.temp_dir) / 'config.yaml'
        result = self.tool.run([
            'generate',
            '-o', str(yaml_file),
            '--format', 'yaml'
        ])
        self.assertEqual(result, 0)
        
        # Verify YAML format
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
            self.assertIsInstance(data, dict)
        
        # Test JSON format
        json_file = Path(self.temp_dir) / 'config.json'
        result = self.tool.run([
            'generate',
            '-o', str(json_file),
            '--format', 'json'
        ])
        self.assertEqual(result, 0)
        
        # Verify JSON format
        with open(json_file, 'r') as f:
            data = json.load(f)
            self.assertIsInstance(data, dict)
    
    def test_all_profiles(self):
        """Test generation with all available profiles"""
        profiles = ['development', 'production', 'testing']
        
        for profile in profiles:
            output_file = Path(self.temp_dir) / f'{profile}_config.yaml'
            
            result = self.tool.run([
                'generate',
                '-o', str(output_file),
                '-p', profile
            ])
            
            self.assertEqual(result, 0, f"Failed to generate {profile} profile")
            self.assertTrue(output_file.exists())
            
            # Validate each generated config
            result = self.tool.run(['validate', str(output_file)])
            self.assertEqual(result, 0, f"{profile} config validation failed")


if __name__ == '__main__':
    unittest.main()