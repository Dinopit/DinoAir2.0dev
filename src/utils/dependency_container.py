"""
Dependency Injection Container for DinoAir 2.0
Manages dependencies and prevents circular dependency issues
"""

import threading
import inspect
from typing import Any, Dict, Optional, Type, TypeVar, Callable, Union, List
from enum import Enum
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .logger import Logger

logger = Logger()

T = TypeVar('T')


class Scope(Enum):
    """Dependency lifecycle scopes."""
    SINGLETON = "singleton"      # One instance for entire app
    TRANSIENT = "transient"      # New instance every time
    SCOPED = "scoped"           # One instance per scope/request


class LifecycleState(Enum):
    """States a dependency can be in."""
    REGISTERED = "registered"
    CREATING = "creating"
    CREATED = "created"
    DISPOSING = "disposing"
    DISPOSED = "disposed"


@dataclass
class DependencyInfo:
    """Information about a registered dependency."""
    name: str
    dependency_type: Type
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    scope: Scope = Scope.SINGLETON
    dependencies: List[str] = None
    state: LifecycleState = LifecycleState.REGISTERED
    initialization_order: int = 100  # Higher = later
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class DependencyResolutionError(Exception):
    """Raised when dependency resolution fails."""
    pass


class CircularDependencyError(DependencyResolutionError):
    """Raised when a circular dependency is detected."""
    pass


class DependencyContainer:
    """
    Dependency injection container that manages object lifecycles
    and resolves dependencies automatically.
    """
    
    def __init__(self):
        self._dependencies: Dict[str, DependencyInfo] = {}
        self._instances: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._resolution_stack: List[str] = []
        self._scoped_instances: Dict[str, Dict[str, Any]] = {}
        self._current_scope: Optional[str] = None
        
    def register_singleton(self, 
                          name: str, 
                          dependency_type: Type[T],
                          factory: Optional[Callable[[], T]] = None,
                          dependencies: Optional[List[str]] = None,
                          initialization_order: int = 100) -> 'DependencyContainer':
        """
        Register a singleton dependency.
        
        Args:
            name: Unique name for the dependency
            dependency_type: Type of the dependency
            factory: Optional factory function to create the instance
            dependencies: List of dependency names this depends on
            initialization_order: Order of initialization (higher = later)
        """
        return self._register(
            name, dependency_type, factory, Scope.SINGLETON, 
            dependencies, initialization_order
        )
        
    def register_transient(self,
                          name: str,
                          dependency_type: Type[T],
                          factory: Optional[Callable[[], T]] = None,
                          dependencies: Optional[List[str]] = None,
                          initialization_order: int = 100) -> 'DependencyContainer':
        """Register a transient dependency (new instance each time)."""
        return self._register(
            name, dependency_type, factory, Scope.TRANSIENT,
            dependencies, initialization_order
        )
        
    def register_scoped(self,
                       name: str,
                       dependency_type: Type[T],
                       factory: Optional[Callable[[], T]] = None,
                       dependencies: Optional[List[str]] = None,
                       initialization_order: int = 100) -> 'DependencyContainer':
        """Register a scoped dependency (one instance per scope)."""
        return self._register(
            name, dependency_type, factory, Scope.SCOPED,
            dependencies, initialization_order
        )
        
    def register_instance(self,
                         name: str,
                         instance: T,
                         dependencies: Optional[List[str]] = None) -> 'DependencyContainer':
        """Register an existing instance as a singleton."""
        with self._lock:
            dependency_info = DependencyInfo(
                name=name,
                dependency_type=type(instance),
                instance=instance,
                scope=Scope.SINGLETON,
                dependencies=dependencies or [],
                state=LifecycleState.CREATED
            )
            
            self._dependencies[name] = dependency_info
            self._instances[name] = instance
            
            logger.debug(f"Registered instance: {name}")
            return self
            
    def _register(self,
                 name: str,
                 dependency_type: Type,
                 factory: Optional[Callable],
                 scope: Scope,
                 dependencies: Optional[List[str]],
                 initialization_order: int) -> 'DependencyContainer':
        """Internal registration method."""
        with self._lock:
            if name in self._dependencies:
                raise DependencyResolutionError(f"Dependency '{name}' already registered")
                
            dependency_info = DependencyInfo(
                name=name,
                dependency_type=dependency_type,
                factory=factory,
                scope=scope,
                dependencies=dependencies or [],
                initialization_order=initialization_order
            )
            
            self._dependencies[name] = dependency_info
            logger.debug(f"Registered {scope.value} dependency: {name}")
            
            return self
            
    def resolve(self, name: str) -> Any:
        """
        Resolve a dependency by name.
        
        Args:
            name: Name of the dependency to resolve
            
        Returns:
            The resolved dependency instance
            
        Raises:
            DependencyResolutionError: If dependency cannot be resolved
            CircularDependencyError: If circular dependency detected
        """
        with self._lock:
            return self._resolve_internal(name)
            
    def resolve_type(self, dependency_type: Type[T]) -> T:
        """
        Resolve a dependency by type.
        
        Args:
            dependency_type: Type of the dependency to resolve
            
        Returns:
            The resolved dependency instance
        """
        with self._lock:
            # Find dependency by type
            for name, info in self._dependencies.items():
                if info.dependency_type == dependency_type:
                    return self._resolve_internal(name)
                    
            raise DependencyResolutionError(
                f"No dependency registered for type: {dependency_type}"
            )
            
    def _resolve_internal(self, name: str) -> Any:
        """Internal dependency resolution with circular dependency detection."""
        if name in self._resolution_stack:
            cycle = " -> ".join(self._resolution_stack + [name])
            raise CircularDependencyError(f"Circular dependency detected: {cycle}")
            
        if name not in self._dependencies:
            raise DependencyResolutionError(f"Unknown dependency: {name}")
            
        dependency_info = self._dependencies[name]
        
        # Check if instance already exists for singleton
        if dependency_info.scope == Scope.SINGLETON:
            if name in self._instances:
                return self._instances[name]
                
        # Check scoped instances
        elif dependency_info.scope == Scope.SCOPED:
            if self._current_scope and self._current_scope in self._scoped_instances:
                scoped_instances = self._scoped_instances[self._current_scope]
                if name in scoped_instances:
                    return scoped_instances[name]
                    
        # Create new instance
        try:
            self._resolution_stack.append(name)
            dependency_info.state = LifecycleState.CREATING
            
            instance = self._create_instance(dependency_info)
            dependency_info.state = LifecycleState.CREATED
            
            # Store instance based on scope
            if dependency_info.scope == Scope.SINGLETON:
                self._instances[name] = instance
            elif dependency_info.scope == Scope.SCOPED and self._current_scope:
                if self._current_scope not in self._scoped_instances:
                    self._scoped_instances[self._current_scope] = {}
                self._scoped_instances[self._current_scope][name] = instance
                
            return instance
            
        finally:
            self._resolution_stack.remove(name)
            
    def _create_instance(self, dependency_info: DependencyInfo) -> Any:
        """Create an instance of a dependency."""
        # Resolve dependencies first
        resolved_dependencies = {}
        for dep_name in dependency_info.dependencies:
            resolved_dependencies[dep_name] = self._resolve_internal(dep_name)
            
        # Use factory if provided
        if dependency_info.factory:
            try:
                # Check if factory needs resolved dependencies
                sig = inspect.signature(dependency_info.factory)
                if sig.parameters:
                    # Try to match parameters with resolved dependencies
                    kwargs = {}
                    for param_name in sig.parameters:
                        if param_name in resolved_dependencies:
                            kwargs[param_name] = resolved_dependencies[param_name]
                    return dependency_info.factory(**kwargs)
                else:
                    return dependency_info.factory()
            except Exception as e:
                raise DependencyResolutionError(
                    f"Factory failed for {dependency_info.name}: {e}"
                )
                
        # Use constructor
        try:
            constructor = dependency_info.dependency_type
            sig = inspect.signature(constructor)
            
            if not sig.parameters:
                # No parameters, simple construction
                return constructor()
            else:
                # Try to inject dependencies based on parameter names
                kwargs = {}
                for param_name, param in sig.parameters.items():
                    if param_name in resolved_dependencies:
                        kwargs[param_name] = resolved_dependencies[param_name]
                        
                return constructor(**kwargs)
                
        except Exception as e:
            raise DependencyResolutionError(
                f"Constructor failed for {dependency_info.name}: {e}"
            )
            
    def create_scope(self, scope_name: str = None) -> 'ScopeContext':
        """Create a new dependency scope context."""
        if scope_name is None:
            import uuid
            scope_name = str(uuid.uuid4())
            
        return ScopeContext(self, scope_name)
        
    def dispose_scope(self, scope_name: str):
        """Dispose of a dependency scope and its instances."""
        with self._lock:
            if scope_name in self._scoped_instances:
                scoped_instances = self._scoped_instances[scope_name]
                
                # Dispose instances in reverse creation order
                for instance in reversed(list(scoped_instances.values())):
                    self._dispose_instance(instance)
                    
                del self._scoped_instances[scope_name]
                logger.debug(f"Disposed scope: {scope_name}")
                
    def _dispose_instance(self, instance: Any):
        """Dispose of an instance if it has disposal methods."""
        try:
            if hasattr(instance, 'dispose'):
                instance.dispose()
            elif hasattr(instance, 'close'):
                instance.close()
            elif hasattr(instance, 'cleanup'):
                instance.cleanup()
        except Exception as e:
            logger.warning(f"Error disposing instance: {e}")
            
    def get_dependency_info(self, name: str) -> Optional[DependencyInfo]:
        """Get information about a registered dependency."""
        return self._dependencies.get(name)
        
    def list_dependencies(self) -> List[DependencyInfo]:
        """List all registered dependencies."""
        return list(self._dependencies.values())
        
    def validate_dependencies(self) -> List[str]:
        """
        Validate all dependencies can be resolved.
        
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        with self._lock:
            for name, info in self._dependencies.items():
                try:
                    # Check if all dependencies exist
                    for dep_name in info.dependencies:
                        if dep_name not in self._dependencies:
                            errors.append(
                                f"Dependency '{name}' requires unknown dependency '{dep_name}'"
                            )
                            
                    # Try to detect circular dependencies
                    try:
                        self._check_circular_dependency(name, set())
                    except CircularDependencyError as e:
                        errors.append(str(e))
                        
                except Exception as e:
                    errors.append(f"Error validating {name}: {e}")
                    
        return errors
        
    def _check_circular_dependency(self, name: str, visited: set):
        """Check for circular dependencies recursively."""
        if name in visited:
            raise CircularDependencyError(
                f"Circular dependency detected involving: {name}"
            )
            
        if name not in self._dependencies:
            return
            
        visited.add(name)
        
        for dep_name in self._dependencies[name].dependencies:
            self._check_circular_dependency(dep_name, visited.copy())
            
    def initialize_all(self) -> bool:
        """
        Initialize all singleton dependencies in proper order.
        
        Returns:
            True if all dependencies initialized successfully
        """
        logger.info("Initializing all dependencies...")
        
        try:
            # Get singletons sorted by initialization order
            singletons = [
                info for info in self._dependencies.values()
                if info.scope == Scope.SINGLETON
            ]
            singletons.sort(key=lambda x: x.initialization_order)
            
            # Initialize each singleton
            for info in singletons:
                try:
                    self.resolve(info.name)
                    logger.debug(f"Initialized: {info.name}")
                except Exception as e:
                    logger.error(f"Failed to initialize {info.name}: {e}")
                    return False
                    
            logger.info("All dependencies initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during dependency initialization: {e}")
            return False
            
    def dispose_all(self):
        """Dispose of all managed instances."""
        logger.info("Disposing all dependencies...")
        
        with self._lock:
            # Dispose scoped instances first
            for scope_name in list(self._scoped_instances.keys()):
                self.dispose_scope(scope_name)
                
            # Dispose singletons in reverse initialization order
            singletons = [
                (name, info) for name, info in self._dependencies.items()
                if info.scope == Scope.SINGLETON and name in self._instances
            ]
            singletons.sort(key=lambda x: x[1].initialization_order, reverse=True)
            
            for name, info in singletons:
                try:
                    instance = self._instances[name]
                    self._dispose_instance(instance)
                    info.state = LifecycleState.DISPOSED
                except Exception as e:
                    logger.warning(f"Error disposing {name}: {e}")
                    
            self._instances.clear()
            logger.info("All dependencies disposed")


class ScopeContext:
    """Context manager for dependency scopes."""
    
    def __init__(self, container: DependencyContainer, scope_name: str):
        self.container = container
        self.scope_name = scope_name
        self._previous_scope = None
        
    def __enter__(self):
        self._previous_scope = self.container._current_scope
        self.container._current_scope = self.scope_name
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.container.dispose_scope(self.scope_name)
        self.container._current_scope = self._previous_scope


# Global container instance
_container = None
_container_lock = threading.Lock()


def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    global _container
    
    if _container is None:
        with _container_lock:
            if _container is None:
                _container = DependencyContainer()
                
    return _container


def resolve(name: str) -> Any:
    """Convenience function to resolve from global container."""
    return get_container().resolve(name)


def resolve_type(dependency_type: Type[T]) -> T:
    """Convenience function to resolve by type from global container."""
    return get_container().resolve_type(dependency_type)