"""
Echo Tool - Simple tool for testing and validation

This tool echoes back input text, useful for testing the tool execution
pipeline.
"""

import logging
from datetime import datetime
from typing import Dict, Any

# Tool metadata
TOOL_NAME = "echo_tool"
TOOL_DESCRIPTION = ("Echoes back the provided text - useful for testing "
                    "tool execution pipeline")
TOOL_VERSION = "1.0.0"

logger = logging.getLogger(__name__)


def echo_tool(text: str) -> Dict[str, Any]:
    """
    Echo tool that returns the input text.
    
    Args:
        text: The text to echo back
        
    Returns:
        Dict containing the echoed text and metadata
    """
    try:
        logger.info(f"Echo tool called with text: '{text[:50]}...'")
        
        result = {
            "echo": text,
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "tool_name": TOOL_NAME,
            "version": TOOL_VERSION,
            "message": f"Successfully echoed {len(text)} characters"
        }
        
        logger.info("Echo tool completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Echo tool failed: {e}")
        return {
            "error": str(e),
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "tool_name": TOOL_NAME,
            "error_type": "EchoToolError"
        }


# Tool registry entry
def get_tool_info():
    """Get tool information for registration"""
    return {
        "name": TOOL_NAME,
        "description": TOOL_DESCRIPTION,
        "version": TOOL_VERSION,
        "function": echo_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to echo back"
                }
            },
            "required": ["text"]
        },
        "category": "testing",
        "tags": ["echo", "test", "validation", "pipeline"]
    }


# For direct imports
__all__ = ["echo_tool", "get_tool_info", "TOOL_NAME", "TOOL_DESCRIPTION"]