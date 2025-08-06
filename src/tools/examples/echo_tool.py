"""
Echo Tool - Simple example tool for testing

This tool demonstrates basic tool functionality by echoing text
with optional transformations.
"""

from typing import Dict, Any
from src.tools.base import BaseTool, ToolResult, ToolMetadata, ToolCategory


class EchoTool(BaseTool):
    """Echo tool that returns text with optional transformations"""
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata"""
        return ToolMetadata(
            name="echo_tool",
            version="1.0.0",
            description="Echo text with optional transformations",
            author="DinoAir Team",
            category=ToolCategory.UTILITY,
            tags=["text", "echo", "example"],
        )
    
    def initialize(self):
        """Initialize the tool (no special initialization needed)"""
        pass
    
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the echo tool
        
        Args:
            text: Text to echo
            transform: Optional transformation (upper, lower, reverse)
            
        Returns:
            ToolResult with the transformed text
        """
        text = kwargs.get('text', '')
        transform = kwargs.get('transform', None)
        
        # Apply transformation
        result = text
        if transform == 'upper':
            result = text.upper()
        elif transform == 'lower':
            result = text.lower()
        elif transform == 'reverse':
            result = text[::-1]
            
        return ToolResult(
            success=True,
            output=result,
            metadata={
                'original_text': text,
                'transform': transform or 'none',
                'length': len(result)
            }
        )
    
    def shutdown(self):
        """Cleanup (no resources to clean up)"""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Get parameter schema"""
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to echo"
                },
                "transform": {
                    "type": "string",
                    "enum": ["upper", "lower", "reverse"],
                    "description": "Optional text transformation"
                }
            },
            "required": ["text"]
        }