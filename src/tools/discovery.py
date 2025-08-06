"""
Tool Discovery System

This module provides automatic discovery of tools from various sources:
- Python modules in specified directories
- Installed packages with tool entry points
- Configuration files listing tool modules
"""

import os
import sys
import logging
import importlib
import importlib.util
import inspect
try:
    from importlib.metadata import entry_points
except ImportError:
    # Fallback for Python < 3.8
    from importlib_metadata import entry_points
from pathlib import Path
from typing import Dict, List, Optional, Type, Set, Tuple, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .registry import ToolRegistry
import json
import yaml
from dataclasses import dataclass

from .base import BaseTool, ToolMetadata


logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """Result of a tool discovery operation"""
    tool_class: Optional[Type[BaseTool]]
    source: str  # 'filesystem', 'package', 'config'
    location: str  # file path, package name, or config path
    metadata: Optional[ToolMetadata] = None
    error: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if discovery result is valid"""
        return self.error is None and self.tool_class is not None


class ToolDiscovery:
    """
    Tool discovery system for automatic tool detection and loading
    
    This class provides methods to discover tools from:
    - Filesystem paths (Python modules)
    - Installed Python packages with entry points
    - Configuration files
    """
    
    # Entry point name for package discovery
    ENTRY_POINT_GROUP = "dinoair.tools"
    
    # Common tool file patterns
    DEFAULT_PATTERNS = [
        "*_tool.py",
        "*tool.py",
        "tool_*.py",
        "tools/*.py"
    ]
    
    def __init__(self, registry: Optional['ToolRegistry'] = None):
        """
        Initialize tool discovery system
        
        Args:
            registry: Optional ToolRegistry instance to use
        """
        self.registry = registry
        self._discovered_tools: Dict[str, DiscoveryResult] = {}
        self._discovery_paths: Set[Path] = set()
        self._excluded_names: Set[str] = {
            "__init__", "__pycache__", "test_", "_test"
        }
        self._cache: Dict[str, List[DiscoveryResult]] = {}
        
    def discover_from_paths(
        self,
        paths: List[str],
        patterns: Optional[List[str]] = None,
        recursive: bool = True
    ) -> List[DiscoveryResult]:
        """
        Discover tools from filesystem paths
        
        Args:
            paths: List of directory paths to search
            patterns: File patterns to match (uses defaults if None)
            recursive: Whether to search recursively
            
        Returns:
            List of discovery results
        """
        results = []
        patterns = patterns or self.DEFAULT_PATTERNS
        
        for path_str in paths:
            path = Path(path_str).resolve()
            
            if not path.exists():
                logger.warning(f"Discovery path does not exist: {path}")
                continue
                
            if path.is_file():
                # Single file discovery
                result = self._discover_from_file(path)
                if result:
                    results.extend(result)
            else:
                # Directory discovery
                for pattern in patterns:
                    if recursive:
                        matches = path.rglob(pattern)
                    else:
                        matches = path.glob(pattern)
                        
                    for file_path in matches:
                        if self._should_process_file(file_path):
                            file_results = self._discover_from_file(file_path)
                            if file_results:
                                results.extend(file_results)
                                
            self._discovery_paths.add(path)
            
        logger.info(
            f"Discovered {len(results)} tools from {len(paths)} paths"
        )
        return results
    
    def discover_from_packages(
        self,
        entry_point_group: Optional[str] = None
    ) -> List[DiscoveryResult]:
        """
        Discover tools from installed packages via entry points
        
        Args:
            entry_point_group: Entry point group name (uses default if None)
            
        Returns:
            List of discovery results
        """
        results = []
        group = entry_point_group or self.ENTRY_POINT_GROUP
        
        try:
            # Get entry points for the group
            if hasattr(entry_points(), 'select'):
                # Python 3.10+
                eps = entry_points().select(group=group)
            else:
                # Python 3.8-3.9
                eps = entry_points().get(group, [])
            
            for entry_point in eps:
                try:
                    # Load the entry point
                    tool_class = entry_point.load()
                    
                    # Verify it's a valid tool class
                    if (inspect.isclass(tool_class) and 
                            issubclass(tool_class, BaseTool) and
                            tool_class != BaseTool):
                        
                        result = DiscoveryResult(
                            tool_class=tool_class,
                            source='package',
                            location=f"{entry_point.dist}:{entry_point.name}"
                        )
                        
                        # Try to get metadata
                        try:
                            temp_instance = tool_class()
                            result.metadata = temp_instance.metadata
                            temp_instance.shutdown()
                        except Exception as e:
                            logger.warning(
                                f"Could not get metadata for "
                                f"{entry_point.name}: {e}"
                            )
                            
                        results.append(result)
                        logger.info(
                            f"Discovered tool from package: {entry_point.name}"
                        )
                        
                except Exception as e:
                    error_result = DiscoveryResult(
                        tool_class=None,
                        source='package',
                        location=str(entry_point),
                        error=str(e)
                    )
                    results.append(error_result)
                    logger.error(
                        f"Failed to load entry point {entry_point.name}: {e}"
                    )
                    
        except Exception as e:
            logger.error(f"Error discovering package tools: {e}")
            
        return results
    
    def discover_from_config(
        self,
        config_path: str,
        base_path: Optional[str] = None
    ) -> List[DiscoveryResult]:
        """
        Discover tools from a configuration file
        
        Args:
            config_path: Path to configuration file
            base_path: Base path for relative imports
            
        Returns:
            List of discovery results
        """
        results = []
        config_file = Path(config_path)
        
        if not config_file.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return results
            
        try:
            # Load configuration
            config = self._load_config(config_file)
            
            # Get tools section
            tools_config = config.get('tools', {})
            base_path = base_path or config.get('base_path', '')
            
            for tool_name, tool_info in tools_config.items():
                if isinstance(tool_info, str):
                    # Simple module path
                    module_path = tool_info
                    class_name = None
                else:
                    # Detailed configuration
                    module_path = tool_info.get('module')
                    class_name = tool_info.get('class')
                    # Config is handled at registration time
                    
                if not module_path:
                    continue
                    
                # Resolve relative paths
                if base_path and not module_path.startswith('.'):
                    module_path = os.path.join(base_path, module_path)
                    
                # Discover from module
                result = self._discover_from_module_path(
                    module_path, class_name
                )
                
                if result:
                    result.source = 'config'
                    result.location = f"{config_path}:{tool_name}"
                    results.append(result)
                    
        except Exception as e:
            logger.error(f"Failed to load config {config_path}: {e}")
            
        return results
    
    def _discover_from_file(self, file_path: Path) -> List[DiscoveryResult]:
        """Discover tools from a Python file"""
        results = []
        
        try:
            # Create module spec
            module_name = file_path.stem
            spec = importlib.util.spec_from_file_location(
                module_name, file_path
            )
            
            if not spec or not spec.loader:
                return results
                
            # Load module
            module = importlib.util.module_from_spec(spec)
            
            # Add parent directory to sys.path temporarily
            parent_dir = str(file_path.parent)
            sys_path_added = False
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
                sys_path_added = True
                
            try:
                spec.loader.exec_module(module)
                
                # Find tool classes
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                            issubclass(obj, BaseTool) and
                            obj != BaseTool and
                            obj.__module__ == module.__name__):
                        
                        result = DiscoveryResult(
                            tool_class=obj,
                            source='filesystem',
                            location=str(file_path)
                        )
                        
                        # Try to get metadata
                        try:
                            temp_instance = obj()
                            result.metadata = temp_instance.metadata
                            temp_instance.shutdown()
                        except Exception as e:
                            logger.warning(
                                f"Could not get metadata for {name}: {e}"
                            )
                            
                        results.append(result)
                        logger.debug(
                            f"Discovered tool {name} from {file_path}"
                        )
                        
            finally:
                # Clean up sys.path
                if sys_path_added:
                    sys.path.remove(parent_dir)
                    
        except Exception as e:
            logger.error(f"Failed to discover tools from {file_path}: {e}")
            error_result = DiscoveryResult(
                tool_class=None,
                source='filesystem',
                location=str(file_path),
                error=str(e)
            )
            results.append(error_result)
            
        return results
    
    def _discover_from_module_path(
        self,
        module_path: str,
        class_name: Optional[str] = None
    ) -> Optional[DiscoveryResult]:
        """Discover tool from module path"""
        try:
            # Import module
            if module_path.endswith('.py'):
                # File path
                file_path = Path(module_path)
                results = self._discover_from_file(file_path)
                if results and class_name:
                    # Filter by class name
                    for result in results:
                        if (result.tool_class and 
                                result.tool_class.__name__ == class_name):
                            return result
                elif results:
                    return results[0]
            else:
                # Module name
                module = importlib.import_module(module_path)
                
                if class_name:
                    # Get specific class
                    tool_class = getattr(module, class_name, None)
                    if (tool_class and inspect.isclass(tool_class) and
                            issubclass(tool_class, BaseTool)):
                        return DiscoveryResult(
                            tool_class=tool_class,
                            source='config',
                            location=f"{module_path}.{class_name}"
                        )
                else:
                    # Find first tool class
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and
                                issubclass(obj, BaseTool) and
                                obj != BaseTool):
                            return DiscoveryResult(
                                tool_class=obj,
                                source='config',
                                location=f"{module_path}.{name}"
                            )
                            
        except Exception as e:
            logger.error(f"Failed to import {module_path}: {e}")
            return DiscoveryResult(
                tool_class=None,
                source='config',
                location=module_path,
                error=str(e)
            )
            
        return None
    
    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed"""
        # Skip excluded patterns
        for excluded in self._excluded_names:
            if excluded in str(file_path):
                return False
                
        # Must be Python file
        if not file_path.suffix == '.py':
            return False
            
        # Must exist and be a file
        return file_path.exists() and file_path.is_file()
    
    def _load_config(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration from file"""
        content = config_file.read_text()
        
        if config_file.suffix in ['.json']:
            return json.loads(content)
        elif config_file.suffix in ['.yaml', '.yml']:
            try:
                return yaml.safe_load(content)
            except ImportError:
                logger.warning("PyYAML not installed, trying JSON")
                return json.loads(content)
        else:
            # Try JSON first, then YAML
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                try:
                    return yaml.safe_load(content)
                except Exception:
                    raise ValueError(f"Unknown config format: {config_file}")
    
    def register_discovered_tools(
        self,
        results: List[DiscoveryResult],
        auto_enable: bool = True,
        config_overrides: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Tuple[int, int]:
        """
        Register discovered tools with the registry
        
        Args:
            results: List of discovery results
            auto_enable: Whether to enable tools by default
            config_overrides: Configuration overrides by tool name
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        if not self.registry:
            logger.error("No registry available for registration")
            return 0, len(results)
            
        successful = 0
        failed = 0
        
        for result in results:
            if not result.is_valid:
                logger.warning(
                    f"Skipping invalid result from {result.location}: "
                    f"{result.error}"
                )
                failed += 1
                continue
                
            try:
                # Skip if no tool class
                if not result.tool_class:
                    failed += 1
                    continue
                    
                # Get tool name
                tool_name = (
                    result.metadata.name if result.metadata
                    else result.tool_class.__name__
                )
                
                # Get config override if available
                config = None
                if config_overrides and tool_name in config_overrides:
                    config = config_overrides[tool_name]
                    
                # Register tool
                if self.registry.register_tool(
                    result.tool_class,
                    name=tool_name,
                    config=config
                ):
                    successful += 1
                    
                    # Disable if requested
                    if not auto_enable:
                        self.registry.disable_tool(tool_name)
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(
                    f"Failed to register tool from {result.location}: {e}"
                )
                failed += 1
                
        logger.info(
            f"Registration complete: {successful} successful, {failed} failed"
        )
        return successful, failed
    
    def discover_and_register_all(
        self,
        paths: Optional[List[str]] = None,
        discover_packages: bool = True,
        config_files: Optional[List[str]] = None,
        auto_enable: bool = True
    ) -> Dict[str, Any]:
        """
        Discover and register tools from all sources
        
        Args:
            paths: Filesystem paths to search
            discover_packages: Whether to discover from packages
            config_files: Configuration files to load
            auto_enable: Whether to enable tools by default
            
        Returns:
            Summary of discovery results
        """
        all_results = []
        summary = {
            'filesystem': {'discovered': 0, 'registered': 0, 'failed': 0},
            'packages': {'discovered': 0, 'registered': 0, 'failed': 0},
            'configs': {'discovered': 0, 'registered': 0, 'failed': 0},
            'total': {'discovered': 0, 'registered': 0, 'failed': 0}
        }
        
        # Filesystem discovery
        if paths:
            fs_results = self.discover_from_paths(paths)
            all_results.extend(fs_results)
            summary['filesystem']['discovered'] = len(fs_results)
            
        # Package discovery
        if discover_packages:
            pkg_results = self.discover_from_packages()
            all_results.extend(pkg_results)
            summary['packages']['discovered'] = len(pkg_results)
            
        # Config file discovery
        if config_files:
            for config_file in config_files:
                cfg_results = self.discover_from_config(config_file)
                all_results.extend(cfg_results)
                summary['configs']['discovered'] += len(cfg_results)
                
        # Register all discovered tools
        if all_results and self.registry:
            registered, failed = self.register_discovered_tools(
                all_results, auto_enable
            )
            
            # Update summary
            for source in ['filesystem', 'packages', 'configs']:
                source_results = [
                    r for r in all_results if r.source == source[:-1]
                ]
                if source_results:
                    source_registered = sum(
                        1 for r in source_results if r.is_valid
                    )
                    summary[source]['registered'] = source_registered
                    summary[source]['failed'] = (
                        len(source_results) - source_registered
                    )
                    
            summary['total'] = {
                'discovered': len(all_results),
                'registered': registered,
                'failed': failed
            }
            
        return summary


# Convenience function for quick discovery
def discover_tools(
    paths: Optional[List[str]] = None,
    registry: Optional['ToolRegistry'] = None,
    auto_register: bool = True
) -> List[DiscoveryResult]:
    """
    Quick tool discovery function
    
    Args:
        paths: Paths to search (uses current directory if None)
        registry: Registry to use for registration
        auto_register: Whether to automatically register discovered tools
        
    Returns:
        List of discovery results
    """
    discovery = ToolDiscovery(registry)
    
    if paths is None:
        paths = ['.']
        
    results = discovery.discover_from_paths(paths)
    
    if auto_register and registry:
        discovery.register_discovered_tools(results)
        
    return results