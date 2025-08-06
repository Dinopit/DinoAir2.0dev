"""
Time Tool - Current time and date utilities

This tool provides current time and date information in various formats
for AI-assisted tasks.
"""

import logging
from datetime import datetime
from src.tools.base import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult,
    ToolStatus, ToolCategory, ParameterType
)

logger = logging.getLogger(__name__)


class TimeTool(BaseTool):
    """
    Time and date utility tool
    
    This tool provides current time and date information including:
    - Current timestamp
    - Formatted date/time strings
    - ISO format timestamps
    """
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata"""
        return ToolMetadata(
            name="time_tool",
            version="1.0.0",
            description="Get current time and date in various formats",
            author="DinoAir Team",
            category=ToolCategory.UTILITY,
            tags=["time", "date", "timestamp", "datetime"],
            parameters=[
                ToolParameter(
                    name="format",
                    type=ParameterType.ENUM,
                    description="Time format to return",
                    required=False,
                    default="iso",
                    enum_values=["iso", "human", "timestamp", "date_only",
                                 "time_only"],
                    example="human"
                )
            ],
            capabilities={
                "async_support": False,
                "streaming": False,
                "cancellable": False,
                "progress_reporting": False,
                "batch_processing": False,
                "caching": False,
                "stateful": False
            },
            examples=[
                {
                    "name": "Current time (human readable)",
                    "description": "Get current time in human readable format",
                    "parameters": {
                        "format": "human"
                    },
                    "expected_output": "2024-01-01 12:30:45"
                },
                {
                    "name": "ISO timestamp",
                    "description": "Get current time in ISO format",
                    "parameters": {
                        "format": "iso"
                    },
                    "expected_output": "2024-01-01T12:30:45.123456"
                }
            ]
        )
    
    def initialize(self):
        """Initialize the tool"""
        logger.info("TimeTool initialized")
        self._call_count = 0
        
    def execute(self, **kwargs) -> ToolResult:
        """
        Get current time in specified format
        
        Args:
            format: Format for time output (iso, human, timestamp, 
                   date_only, time_only)
            
        Returns:
            ToolResult with current time
        """
        try:
            time_format = kwargs.get('format', 'iso')
            now = datetime.now()
            
            # Format time based on request
            if time_format == 'iso':
                result = now.isoformat()
            elif time_format == 'human':
                result = now.strftime('%Y-%m-%d %H:%M:%S')
            elif time_format == 'timestamp':
                result = int(now.timestamp())
            elif time_format == 'date_only':
                result = now.strftime('%Y-%m-%d')
            elif time_format == 'time_only':
                result = now.strftime('%H:%M:%S')
            else:
                return ToolResult(
                    success=False,
                    errors=[f"Unsupported format: {time_format}"],
                    status=ToolStatus.FAILED
                )
            
            self._call_count += 1
            
            return ToolResult(
                success=True,
                output=result,
                metadata={
                    'format': time_format,
                    'timestamp': now.timestamp(),
                    'call_count': self._call_count
                }
            )
            
        except Exception as e:
            logger.error(f"Time operation failed: {e}")
            return ToolResult(
                success=False,
                errors=[str(e)],
                status=ToolStatus.FAILED
            )
    
    def shutdown(self):
        """Cleanup tool resources"""
        logger.info(f"TimeTool shutting down. Called {self._call_count} times")