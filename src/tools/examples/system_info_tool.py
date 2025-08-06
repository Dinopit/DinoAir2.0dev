"""
System Information Tool

A simple tool that provides system information to the AI model,
demonstrating basic tool functionality and integration.
"""

import os
import platform
import psutil
import logging
from typing import Dict, Any
from datetime import datetime

from src.tools.base import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult,
    ToolStatus, ToolCategory, ParameterType
)

logger = logging.getLogger(__name__)


class SystemInfoTool(BaseTool):
    """
    System information tool that provides details about the current system
    """
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata"""
        return ToolMetadata(
            name="system_info",
            version="1.0.0",
            description="Get system information including OS, hardware, and resource usage",
            author="DinoAir Team",
            category=ToolCategory.SYSTEM,
            tags=["system", "info", "hardware", "os"],
            parameters=[
                ToolParameter(
                    name="info_type",
                    type=ParameterType.ENUM,
                    description="Type of system information to retrieve",
                    required=False,
                    default="overview",
                    enum_values=["overview", "os", "hardware", "memory", "disk", "network"],
                    example="overview"
                ),
                ToolParameter(
                    name="detailed",
                    type=ParameterType.BOOLEAN,
                    description="Include detailed information",
                    required=False,
                    default=False,
                    example=True
                )
            ],
            capabilities={
                "async_support": False,
                "streaming": False,
                "cancellable": False,
                "progress_reporting": False,
                "batch_processing": False,
                "caching": True,
                "stateful": False
            },
            examples=[
                {
                    "name": "Get system overview",
                    "description": "Get basic system information",
                    "parameters": {
                        "info_type": "overview"
                    }
                },
                {
                    "name": "Get detailed memory info",
                    "description": "Get detailed memory usage information",
                    "parameters": {
                        "info_type": "memory",
                        "detailed": True
                    }
                }
            ]
        )
    
    def initialize(self):
        """Initialize the tool"""
        logger.info("SystemInfoTool initialized")
        self._cache = {}
        
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute system information retrieval
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            ToolResult with system information
        """
        try:
            info_type = kwargs.get('info_type', 'overview')
            detailed = kwargs.get('detailed', False)
            
            # Check cache for non-volatile info
            cache_key = f"{info_type}:{detailed}"
            if info_type in ['os', 'hardware'] and cache_key in self._cache:
                return ToolResult(
                    success=True,
                    output=self._cache[cache_key],
                    metadata={"cached": True}
                )
            
            # Get system information
            if info_type == 'overview':
                result = self._get_overview(detailed)
            elif info_type == 'os':
                result = self._get_os_info(detailed)
            elif info_type == 'hardware':
                result = self._get_hardware_info(detailed)
            elif info_type == 'memory':
                result = self._get_memory_info(detailed)
            elif info_type == 'disk':
                result = self._get_disk_info(detailed)
            elif info_type == 'network':
                result = self._get_network_info(detailed)
            else:
                return ToolResult(
                    success=False,
                    errors=[f"Unknown info type: {info_type}"],
                    status=ToolStatus.FAILED
                )
            
            # Cache static information
            if info_type in ['os', 'hardware']:
                self._cache[cache_key] = result
            
            return ToolResult(
                success=True,
                output=result,
                metadata={
                    "info_type": info_type,
                    "detailed": detailed,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"System info retrieval failed: {e}")
            return ToolResult(
                success=False,
                errors=[str(e)],
                status=ToolStatus.FAILED
            )
    
    def _get_overview(self, detailed: bool) -> Dict[str, Any]:
        """Get system overview"""
        info = {
            "system": platform.system(),
            "platform": platform.platform(),
            "architecture": platform.architecture()[0],
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "memory_usage_percent": psutil.virtual_memory().percent,
            "cpu_usage_percent": psutil.cpu_percent(interval=1),
            "uptime_seconds": psutil.boot_time()
        }
        
        if detailed:
            info.update({
                "os_release": platform.release(),
                "os_version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "disk_usage": self._get_disk_usage_summary()
            })
        
        return info
    
    def _get_os_info(self, detailed: bool) -> Dict[str, Any]:
        """Get operating system information"""
        info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "platform": platform.platform(),
            "architecture": platform.architecture(),
            "machine": platform.machine(),
            "hostname": platform.node()
        }
        
        if detailed:
            info.update({
                "processor": platform.processor(),
                "python_implementation": platform.python_implementation(),
                "python_version": platform.python_version(),
                "python_compiler": platform.python_compiler(),
                "environment_variables": dict(os.environ) if detailed else {}
            })
        
        return info
    
    def _get_hardware_info(self, detailed: bool) -> Dict[str, Any]:
        """Get hardware information"""
        info = {
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "memory_total": psutil.virtual_memory().total,
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "swap_total": psutil.swap_memory().total,
            "swap_total_gb": round(psutil.swap_memory().total / (1024**3), 2)
        }
        
        if detailed:
            try:
                info.update({
                    "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                    "disk_partitions": [
                        {
                            "device": partition.device,
                            "mountpoint": partition.mountpoint,
                            "fstype": partition.fstype
                        }
                        for partition in psutil.disk_partitions()
                    ],
                    "network_interfaces": list(psutil.net_if_addrs().keys())
                })
            except Exception as e:
                info["detailed_info_error"] = str(e)
        
        return info
    
    def _get_memory_info(self, detailed: bool) -> Dict[str, Any]:
        """Get memory usage information"""
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        info = {
            "virtual_memory": {
                "total": vm.total,
                "available": vm.available,
                "used": vm.used,
                "free": vm.free,
                "percent": vm.percent,
                "total_gb": round(vm.total / (1024**3), 2),
                "available_gb": round(vm.available / (1024**3), 2),
                "used_gb": round(vm.used / (1024**3), 2)
            },
            "swap_memory": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent,
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2)
            }
        }
        
        if detailed:
            info["virtual_memory"].update({
                "buffers": getattr(vm, 'buffers', 0),
                "cached": getattr(vm, 'cached', 0),
                "shared": getattr(vm, 'shared', 0)
            })
            
            info["swap_memory"].update({
                "sin": swap.sin,
                "sout": swap.sout
            })
        
        return info
    
    def _get_disk_info(self, detailed: bool) -> Dict[str, Any]:
        """Get disk usage information"""
        partitions = psutil.disk_partitions()
        disk_info = {}
        
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info[partition.device] = {
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": round((usage.used / usage.total) * 100, 2),
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2)
                }
            except (PermissionError, OSError):
                disk_info[partition.device] = {
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "error": "Access denied"
                }
        
        if detailed:
            try:
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    disk_info["io_stats"] = {
                        "read_count": disk_io.read_count,
                        "write_count": disk_io.write_count,
                        "read_bytes": disk_io.read_bytes,
                        "write_bytes": disk_io.write_bytes,
                        "read_time": disk_io.read_time,
                        "write_time": disk_io.write_time
                    }
            except Exception as e:
                disk_info["io_stats_error"] = str(e)
        
        return disk_info
    
    def _get_network_info(self, detailed: bool) -> Dict[str, Any]:
        """Get network information"""
        info = {
            "interfaces": {}
        }
        
        # Network interfaces
        for interface, addresses in psutil.net_if_addrs().items():
            info["interfaces"][interface] = []
            for addr in addresses:
                addr_info = {
                    "family": addr.family.name,
                    "address": addr.address
                }
                if addr.netmask:
                    addr_info["netmask"] = addr.netmask
                if addr.broadcast:
                    addr_info["broadcast"] = addr.broadcast
                info["interfaces"][interface].append(addr_info)
        
        if detailed:
            try:
                # Network I/O statistics
                net_io = psutil.net_io_counters()
                if net_io:
                    info["io_stats"] = {
                        "bytes_sent": net_io.bytes_sent,
                        "bytes_recv": net_io.bytes_recv,
                        "packets_sent": net_io.packets_sent,
                        "packets_recv": net_io.packets_recv,
                        "errin": net_io.errin,
                        "errout": net_io.errout,
                        "dropin": net_io.dropin,
                        "dropout": net_io.dropout
                    }
                
                # Per-interface statistics
                per_nic = psutil.net_io_counters(pernic=True)
                info["per_interface_stats"] = {
                    interface: {
                        "bytes_sent": stats.bytes_sent,
                        "bytes_recv": stats.bytes_recv,
                        "packets_sent": stats.packets_sent,
                        "packets_recv": stats.packets_recv
                    }
                    for interface, stats in per_nic.items()
                }
            except Exception as e:
                info["detailed_stats_error"] = str(e)
        
        return info
    
    def _get_disk_usage_summary(self) -> Dict[str, Any]:
        """Get a summary of disk usage across all partitions"""
        total_size = 0
        total_used = 0
        total_free = 0
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                total_size += usage.total
                total_used += usage.used
                total_free += usage.free
            except (PermissionError, OSError):
                continue
        
        return {
            "total_gb": round(total_size / (1024**3), 2),
            "used_gb": round(total_used / (1024**3), 2),
            "free_gb": round(total_free / (1024**3), 2),
            "usage_percent": round((total_used / total_size) * 100, 2) if total_size > 0 else 0
        }
    
    def shutdown(self):
        """Cleanup resources"""
        logger.info("SystemInfoTool shutting down")
        self._cache.clear()