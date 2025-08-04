#!/usr/bin/env python3
"""
Simplified configuration management CLI tool

Provides commands for managing configurations for the Pseudocode Translator.
"""

import argparse
import sys
import os
import json
import yaml
from pathlib import Path
from typing import Optional, List
import logging

from .config import ConfigManager, ConfigProfile

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class ConfigTool:
    """Configuration management tool"""
    
    def __init__(self):
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser"""
        parser = argparse.ArgumentParser(
            prog='config_tool',
            description='Configuration tool for Pseudocode Translator',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Add verbosity flag
        parser.add_argument(
            '-v', '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
        
        # Create subcommands
        subparsers = parser.add_subparsers(
            dest='command',
            help='Available commands'
        )
        
        # Validate command
        validate_parser = subparsers.add_parser(
            'validate',
            help='Validate a configuration file'
        )
        validate_parser.add_argument(
            'config_file',
            help='Path to configuration file'
        )
        
        # Generate command
        generate_parser = subparsers.add_parser(
            'generate',
            help='Generate a new configuration file'
        )
        generate_parser.add_argument(
            '-o', '--output',
            default='config.yaml',
            help='Output file path (default: config.yaml)'
        )
        generate_parser.add_argument(
            '-p', '--profile',
            choices=['development', 'production', 'testing', 'custom'],
            default='development',
            help='Configuration profile (default: development)'
        )
        generate_parser.add_argument(
            '--format',
            choices=['yaml', 'json'],
            default='yaml',
            help='Output format (default: yaml)'
        )
        
        # Check command
        check_parser = subparsers.add_parser(
            'check',
            help='Check configuration and environment'
        )
        check_parser.add_argument(
            'config_file',
            nargs='?',
            help='Path to configuration file (optional)'
        )
        check_parser.add_argument(
            '--env',
            action='store_true',
            help='Check environment variables'
        )
        
        # Wizard command
        wizard_parser = subparsers.add_parser(
            'wizard',
            help='Interactive configuration wizard'
        )
        wizard_parser.add_argument(
            '-o', '--output',
            default='config.yaml',
            help='Output file path (default: config.yaml)'
        )
        
        # Info command
        info_parser = subparsers.add_parser(
            'info',
            help='Show configuration information'
        )
        info_parser.add_argument(
            'config_file',
            help='Path to configuration file'
        )
        
        # Upgrade command (for old configs)
        upgrade_parser = subparsers.add_parser(
            'upgrade',
            help='Upgrade old configuration to new format'
        )
        upgrade_parser.add_argument(
            'config_file',
            help='Path to old configuration file'
        )
        upgrade_parser.add_argument(
            '-o', '--output',
            help='Output file path (default: overwrite input)'
        )
        upgrade_parser.add_argument(
            '--backup',
            action='store_true',
            default=True,
            help='Create backup of original file (default: true)'
        )
        
        return parser
    
    def run(self, args: Optional[List[str]] = None):
        """Run the configuration tool"""
        parsed_args = self.parser.parse_args(args)
        
        if parsed_args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        if not parsed_args.command:
            self.parser.print_help()
            return 1
        
        # Execute command
        command_map = {
            'validate': self.cmd_validate,
            'generate': self.cmd_generate,
            'check': self.cmd_check,
            'wizard': self.cmd_wizard,
            'info': self.cmd_info,
            'upgrade': self.cmd_upgrade
        }
        
        command_func = command_map.get(parsed_args.command)
        if command_func:
            try:
                return command_func(parsed_args)
            except Exception as e:
                logger.error(f"Error: {e}")
                if parsed_args.verbose:
                    import traceback
                    traceback.print_exc()
                return 1
        else:
            logger.error(f"Unknown command: {parsed_args.command}")
            return 1
    
    def cmd_validate(self, args) -> int:
        """Validate configuration file"""
        config_path = Path(args.config_file)
        
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return 1
        
        logger.info(f"Validating configuration: {config_path}")
        
        try:
            # Load configuration
            config = ConfigManager.load(config_path)
            
            # Validate
            errors = config.validate()
            
            if errors:
                print("\nValidation errors found:")
                print("-" * 40)
                for error in errors:
                    print(f"  ✗ {error}")
                return 1
            else:
                print("\n✓ Configuration is valid")
                return 0
                
        except Exception as e:
            logger.error(f"Failed to validate: {e}")
            return 1
    
    def cmd_generate(self, args) -> int:
        """Generate new configuration file"""
        output_path = Path(args.output)
        
        # Check if file exists
        if output_path.exists():
            response = input(
                f"File {output_path} already exists. Overwrite? [y/N]: "
            )
            if response.lower() != 'y':
                logger.info("Generation cancelled")
                return 1
        
        logger.info(f"Generating {args.profile} configuration")
        
        # Create configuration based on profile
        profile_map = {
            'development': ConfigProfile.DEVELOPMENT,
            'production': ConfigProfile.PRODUCTION,
            'testing': ConfigProfile.TESTING,
            'custom': ConfigProfile.CUSTOM
        }
        
        profile = profile_map[args.profile]
        
        if profile == ConfigProfile.CUSTOM:
            # Use wizard for custom profile
            config = ConfigManager.create_wizard()
        else:
            config = ConfigManager.create_profile(profile)
        
        # Save configuration
        try:
            ConfigManager.save(config, output_path)
            logger.info(f"Configuration generated: {output_path}")
            return 0
        except Exception as e:
            logger.error(f"Failed to generate configuration: {e}")
            return 1
    
    def cmd_check(self, args) -> int:
        """Check configuration and environment"""
        print("Configuration Check")
        print("=" * 50)
        
        # Check configuration file if provided
        if args.config_file:
            config_path = Path(args.config_file)
            if config_path.exists():
                info = ConfigManager.get_config_info(str(config_path))
                print(f"\nConfiguration File: {info['path']}")
                print(f"Version: {info['version']}")
                print(f"Valid: {'Yes' if info['is_valid'] else 'No'}")
                needs_migration = 'Yes' if info['needs_migration'] else 'No'
                print(f"Needs Migration: {needs_migration}")
                
                if info['issues']:
                    print("\nIssues:")
                    for issue in info['issues']:
                        print(f"  - {issue}")
            else:
                print(f"\nConfiguration file not found: {config_path}")
        else:
            # Check default configuration
            default_path = ConfigManager.DEFAULT_CONFIG_PATH
            if default_path.exists():
                print(f"\nDefault configuration found: {default_path}")
                info = ConfigManager.get_config_info()
                print(f"Valid: {'Yes' if info['is_valid'] else 'No'}")
            else:
                print("\nNo default configuration found")
                print(f"Create one with: config_tool generate "
                      f"-o {default_path}")
        
        # Check environment variables if requested
        if args.env:
            print("\n\nEnvironment Variables")
            print("-" * 50)
            
            env_vars = [
                'PSEUDOCODE_LLM_MODEL_TYPE',
                'PSEUDOCODE_LLM_TEMPERATURE',
                'PSEUDOCODE_LLM_THREADS',
                'PSEUDOCODE_LLM_GPU_LAYERS',
                'PSEUDOCODE_STREAMING_ENABLED',
                'PSEUDOCODE_STREAMING_CHUNK_SIZE',
                'PSEUDOCODE_VALIDATE_IMPORTS',
                'PSEUDOCODE_CHECK_UNDEFINED_VARS'
            ]
            
            found_any = False
            for var in env_vars:
                value = os.getenv(var)
                if value:
                    print(f"  {var}={value}")
                    found_any = True
            
            if not found_any:
                print("  No configuration environment variables set")
        
        return 0
    
    def cmd_wizard(self, args) -> int:
        """Interactive configuration wizard"""
        try:
            config = ConfigManager.create_wizard()
            
            # Save configuration
            output_path = Path(args.output)
            ConfigManager.save(config, output_path)
            
            print(f"\nConfiguration saved to: {output_path}")
            print(f"\nYou can validate it with: "
                  f"config_tool validate {output_path}")
            return 0
            
        except KeyboardInterrupt:
            print("\n\nWizard cancelled")
            return 1
        except Exception as e:
            logger.error(f"Wizard failed: {e}")
            return 1
    
    def cmd_info(self, args) -> int:
        """Show configuration information"""
        config_path = Path(args.config_file)
        
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return 1
        
        try:
            # Load configuration
            config = ConfigManager.load(config_path)
            
            print("Configuration Information")
            print("=" * 50)
            print(f"File: {config_path}")
            print(f"Format: {config_path.suffix[1:].upper()}")
            
            # Get file stats
            stats = config_path.stat()
            print(f"Size: {stats.st_size} bytes")
            
            print("\nSettings:")
            print(f"  Model Type: {config.llm.model_type}")
            print(f"  Model Path: {config.llm.model_path}")
            print(f"  Context Size: {config.llm.n_ctx}")
            print(f"  Temperature: {config.llm.temperature}")
            print(f"  Threads: {config.llm.n_threads}")
            print(f"  GPU Layers: {config.llm.n_gpu_layers}")
            
            print("\nEnabled Models:")
            for name, model in config.llm.models.items():
                if model.enabled:
                    print(f"  - {name}")
            
            print("\nStreaming:")
            print(f"  Enabled: {config.streaming.enabled}")
            print(f"  Chunk Size: {config.streaming.chunk_size} bytes")
            
            print("\nValidation:")
            print(f"  Validate Imports: {config.validate_imports}")
            print(f"  Check Undefined Vars: {config.check_undefined_vars}")
            print(f"  Allow Unsafe Operations: "
                  f"{config.allow_unsafe_operations}")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return 1
    
    def cmd_upgrade(self, args) -> int:
        """Upgrade old configuration format"""
        config_path = Path(args.config_file)
        
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return 1
        
        output_path = Path(args.output) if args.output else config_path
        
        logger.info(f"Upgrading configuration: {config_path}")
        
        try:
            # Load old config
            with open(config_path, 'r') as f:
                if config_path.suffix in ['.yaml', '.yml']:
                    old_data = yaml.safe_load(f)
                else:
                    old_data = json.load(f)
            
            # Check version
            version = old_data.get('_version', old_data.get('version', '1.0'))
            
            if version == '3.0':
                logger.info("Configuration is already in the new format")
                return 0
            
            # Create backup if requested
            if args.backup and output_path == config_path:
                backup_path = config_path.with_suffix(
                    f"{config_path.suffix}.bak"
                )
                import shutil
                shutil.copy2(config_path, backup_path)
                logger.info(f"Created backup: {backup_path}")
            
            # Upgrade configuration
            logger.info(f"Upgrading from version {version} to 3.0")
            
            # Try to load with our new system (it handles migration)
            config = ConfigManager.load(config_path)
            
            # Save in new format
            ConfigManager.save(config, output_path)
            
            logger.info(f"Configuration upgraded successfully: {output_path}")
            print("\nUpgrade complete!")
            print(f"Old version: {version}")
            print("New version: 3.0")
            
            # Validate the new config
            errors = config.validate()
            if errors:
                print("\nWarning: The upgraded configuration has "
                      "validation issues:")
                for error in errors:
                    print(f"  - {error}")
                print("\nYou may want to fix these manually or "
                      "regenerate the config.")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to upgrade configuration: {e}")
            return 1


def main():
    """Main entry point"""
    tool = ConfigTool()
    sys.exit(tool.run())


if __name__ == '__main__':
    main()