"""
Resource Manager for DinoAir 2.0
Handles proper resource lifecycle management and shutdown sequencing
"""

import threading
import time
import weakref
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from .logger import Logger

logger = Logger()


class ResourceType(Enum):
    """Types of resources managed by the resource manager."""
    DATABASE = "database"
    THREAD = "thread"
    TIMER = "timer"
    WATCHDOG = "watchdog"
    FILE_HANDLE = "file_handle"
    NETWORK = "network"
    GUI_COMPONENT = "gui_component"
    CUSTOM = "custom"


class ResourceState(Enum):
    """States a resource can be in."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"
    ERROR = "error"


@dataclass
class ResourceInfo:
    """Information about a managed resource."""
    resource_id: str
    resource_type: ResourceType
    resource: Any
    cleanup_func: Optional[Callable] = None
    shutdown_timeout: float = 10.0
    priority: int = 100  # Lower number = higher priority (shutdown first)
    state: ResourceState = ResourceState.INITIALIZING
    created_at: datetime = field(default_factory=datetime.now)
    shutdown_at: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResourceManager:
    """
    Centralized resource management with proper shutdown sequencing.
    
    Manages lifecycle of all application resources and ensures proper
    cleanup order during application shutdown.
    """
    
    def __init__(self):
        self._resources: Dict[str, ResourceInfo] = {}
        self._lock = threading.RLock()
        self._shutdown_initiated = False
        self._shutdown_event = threading.Event()
        
        # Shutdown priorities (lower = shutdown first)
        self._shutdown_priorities = {
            ResourceType.GUI_COMPONENT: 10,
            ResourceType.TIMER: 20,
            ResourceType.WATCHDOG: 30,
            ResourceType.THREAD: 40,
            ResourceType.NETWORK: 50,
            ResourceType.FILE_HANDLE: 60,
            ResourceType.DATABASE: 70,
            ResourceType.CUSTOM: 80
        }
        
    def register_resource(self,
                         resource_id: str,
                         resource: Any,
                         resource_type: ResourceType,
                         cleanup_func: Optional[Callable] = None,
                         shutdown_timeout: float = 10.0,
                         priority: Optional[int] = None,
                         dependencies: Optional[List[str]] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a resource for management.
        
        Args:
            resource_id: Unique identifier for the resource
            resource: The actual resource object
            resource_type: Type of resource
            cleanup_func: Function to call for cleanup (optional)
            shutdown_timeout: Max time to wait for shutdown
            priority: Shutdown priority (lower = first)
            dependencies: List of resource IDs this depends on
            metadata: Additional metadata about the resource
        """
        with self._lock:
            if self._shutdown_initiated:
                logger.warning(f"Cannot register resource {resource_id} - shutdown in progress")
                return
                
            if priority is None:
                priority = self._shutdown_priorities.get(resource_type, 100)
                
            resource_info = ResourceInfo(
                resource_id=resource_id,
                resource_type=resource_type,
                resource=resource,
                cleanup_func=cleanup_func,
                shutdown_timeout=shutdown_timeout,
                priority=priority,
                dependencies=dependencies or [],
                metadata=metadata or {}
            )
            
            self._resources[resource_id] = resource_info
            resource_info.state = ResourceState.ACTIVE
            
            logger.info(f"Registered resource: {resource_id} ({resource_type.value})")
            
    def unregister_resource(self, resource_id: str) -> bool:
        """
        Unregister a resource from management.
        
        Args:
            resource_id: ID of resource to unregister
            
        Returns:
            True if resource was found and removed
        """
        with self._lock:
            if resource_id in self._resources:
                resource_info = self._resources[resource_id]
                
                # If resource is still active, try to shut it down
                if resource_info.state == ResourceState.ACTIVE:
                    self._shutdown_single_resource(resource_info)
                    
                del self._resources[resource_id]
                logger.info(f"Unregistered resource: {resource_id}")
                return True
            return False
            
    def get_resource(self, resource_id: str) -> Optional[Any]:
        """Get a managed resource by ID."""
        with self._lock:
            resource_info = self._resources.get(resource_id)
            return resource_info.resource if resource_info else None
            
    def get_resource_info(self, resource_id: str) -> Optional[ResourceInfo]:
        """Get resource information by ID."""
        with self._lock:
            return self._resources.get(resource_id)
            
    def list_resources(self, 
                      resource_type: Optional[ResourceType] = None) -> List[ResourceInfo]:
        """List all managed resources, optionally filtered by type."""
        with self._lock:
            resources = list(self._resources.values())
            if resource_type:
                resources = [r for r in resources if r.resource_type == resource_type]
            return resources
            
    def get_resource_status(self) -> Dict[str, Any]:
        """Get overall resource manager status."""
        with self._lock:
            status = {
                'total_resources': len(self._resources),
                'shutdown_initiated': self._shutdown_initiated,
                'resources_by_type': {},
                'resources_by_state': {}
            }
            
            for resource_info in self._resources.values():
                # Count by type
                type_name = resource_info.resource_type.value
                status['resources_by_type'][type_name] = (
                    status['resources_by_type'].get(type_name, 0) + 1
                )
                
                # Count by state
                state_name = resource_info.state.value
                status['resources_by_state'][state_name] = (
                    status['resources_by_state'].get(state_name, 0) + 1
                )
                
            return status
            
    def shutdown_all_resources(self, timeout: float = 30.0) -> bool:
        """
        Shutdown all managed resources in proper order.
        
        Args:
            timeout: Maximum time to wait for all shutdowns
            
        Returns:
            True if all resources were shutdown successfully
        """
        logger.info("Initiating resource manager shutdown...")
        
        with self._lock:
            if self._shutdown_initiated:
                logger.warning("Shutdown already in progress")
                return True
                
            self._shutdown_initiated = True
            self._shutdown_event.clear()
            
        start_time = time.time()
        success = True
        
        try:
            # Get resources sorted by shutdown priority and dependencies
            shutdown_order = self._calculate_shutdown_order()
            
            logger.info(f"Shutting down {len(shutdown_order)} resources...")
            
            for resource_info in shutdown_order:
                remaining_time = timeout - (time.time() - start_time)
                if remaining_time <= 0:
                    logger.error("Shutdown timeout exceeded")
                    success = False
                    break
                    
                individual_timeout = min(
                    resource_info.shutdown_timeout,
                    remaining_time
                )
                
                if not self._shutdown_single_resource(resource_info, individual_timeout):
                    logger.error(f"Failed to shutdown resource: {resource_info.resource_id}")
                    success = False
                    
            # Clean up any remaining resources
            with self._lock:
                failed_resources = [
                    r.resource_id for r in self._resources.values()
                    if r.state not in (ResourceState.SHUTDOWN, ResourceState.ERROR)
                ]
                
                if failed_resources:
                    logger.warning(f"Resources failed to shutdown cleanly: {failed_resources}")
                    success = False
                    
        except Exception as e:
            logger.error(f"Error during resource shutdown: {e}")
            success = False
            
        finally:
            self._shutdown_event.set()
            total_time = time.time() - start_time
            logger.info(f"Resource shutdown completed in {total_time:.2f}s (success: {success})")
            
        return success
        
    def _calculate_shutdown_order(self) -> List[ResourceInfo]:
        """Calculate the proper shutdown order considering priorities and dependencies."""
        with self._lock:
            resources = list(self._resources.values())
            
            # Filter to only active resources
            active_resources = [
                r for r in resources 
                if r.state == ResourceState.ACTIVE
            ]
            
            # Sort by priority first (lower priority number = shutdown first)
            active_resources.sort(key=lambda r: r.priority)
            
            # TODO: Add dependency resolution for more complex shutdown ordering
            # For now, simple priority-based ordering is sufficient
            
            return active_resources
            
    def _shutdown_single_resource(self, 
                                 resource_info: ResourceInfo,
                                 timeout: Optional[float] = None) -> bool:
        """
        Shutdown a single resource.
        
        Args:
            resource_info: Information about the resource to shutdown
            timeout: Maximum time to wait for shutdown
            
        Returns:
            True if shutdown was successful
        """
        if timeout is None:
            timeout = resource_info.shutdown_timeout
            
        resource_id = resource_info.resource_id
        logger.info(f"Shutting down resource: {resource_id}")
        
        try:
            resource_info.state = ResourceState.SHUTTING_DOWN
            start_time = time.time()
            
            # Call custom cleanup function if provided
            if resource_info.cleanup_func:
                logger.debug(f"Calling cleanup function for {resource_id}")
                resource_info.cleanup_func()
                
            # Try standard cleanup methods if no custom function
            else:
                resource = resource_info.resource
                
                # Try common cleanup methods
                if hasattr(resource, 'close'):
                    resource.close()
                elif hasattr(resource, 'shutdown'):
                    resource.shutdown()
                elif hasattr(resource, 'stop'):
                    resource.stop()
                elif hasattr(resource, 'quit'):
                    resource.quit()
                else:
                    logger.debug(f"No cleanup method found for {resource_id}")
                    
            # Mark as shutdown
            resource_info.state = ResourceState.SHUTDOWN
            resource_info.shutdown_at = datetime.now()
            
            elapsed = time.time() - start_time
            logger.info(f"Resource {resource_id} shutdown in {elapsed:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Error shutting down resource {resource_id}: {e}")
            resource_info.state = ResourceState.ERROR
            return False
            
    def wait_for_shutdown(self, timeout: float = 30.0) -> bool:
        """
        Wait for shutdown to complete.
        
        Args:
            timeout: Maximum time to wait
            
        Returns:
            True if shutdown completed within timeout
        """
        return self._shutdown_event.wait(timeout)
        
    def force_shutdown_resource(self, resource_id: str) -> bool:
        """
        Force shutdown of a specific resource.
        
        Args:
            resource_id: ID of resource to force shutdown
            
        Returns:
            True if resource was found and shutdown attempted
        """
        with self._lock:
            resource_info = self._resources.get(resource_id)
            if not resource_info:
                return False
                
            logger.warning(f"Force shutting down resource: {resource_id}")
            return self._shutdown_single_resource(resource_info, timeout=5.0)


# Global instance
_resource_manager = None
_manager_lock = threading.Lock()


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance."""
    global _resource_manager
    
    if _resource_manager is None:
        with _manager_lock:
            if _resource_manager is None:
                _resource_manager = ResourceManager()
                
    return _resource_manager


def register_resource(*args, **kwargs) -> None:
    """Convenience function to register a resource with the global manager."""
    get_resource_manager().register_resource(*args, **kwargs)


def shutdown_all_resources(*args, **kwargs) -> bool:
    """Convenience function to shutdown all resources via the global manager."""
    return get_resource_manager().shutdown_all_resources(*args, **kwargs)