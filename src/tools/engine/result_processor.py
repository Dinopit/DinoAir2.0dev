"""
Result Processor Module

This module provides strategies for processing tool execution results,
ensuring consistent output formatting across different tool types.
"""

import logging
import json
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto

logger = logging.getLogger(__name__)


class ProcessingStrategy(Enum):
    """Strategies for processing results"""
    PASSTHROUGH = auto()     # Return as-is
    JSON_FORMAT = auto()     # Format as JSON
    XML_FORMAT = auto()      # Format as XML  
    TEXT_FORMAT = auto()     # Format as text
    STRUCTURED = auto()      # Apply structured formatting
    CUSTOM = auto()          # Use custom processor


@dataclass
class ProcessedResult:
    """Processed result container"""
    original: Any
    processed: Any
    format: str
    metadata: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "original_type": type(self.original).__name__,
            "processed": self.processed,
            "format": self.format,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class ResultProcessor(ABC):
    """
    Abstract base class for result processors
    
    Result processors transform tool outputs into standardized formats,
    making them easier to consume by different systems.
    """
    
    @abstractmethod
    def process(
        self, result: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedResult:
        """
        Process a result
        
        Args:
            result: The result to process
            metadata: Optional metadata
            
        Returns:
            Processed result
        """
        pass
    
    @abstractmethod
    def can_process(self, result: Any) -> bool:
        """
        Check if this processor can handle the result
        
        Args:
            result: The result to check
            
        Returns:
            True if processor can handle this result type
        """
        pass
    
    def get_format_name(self) -> str:
        """Get the format name for this processor"""
        return self.__class__.__name__.replace('Processor', '').lower()


class StandardProcessor(ResultProcessor):
    """
    Standard processor that handles common result types
    
    This processor provides sensible defaults for most result types
    without requiring special handling.
    """
    
    def process(
        self, result: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedResult:
        """Process result using standard handling"""
        metadata = metadata or {}
        
        # Handle None
        if result is None:
            return ProcessedResult(
                original=result,
                processed=None,
                format="null",
                metadata=metadata,
                timestamp=datetime.now()
            )
            
        # Handle primitives
        if isinstance(result, (str, int, float, bool)):
            return ProcessedResult(
                original=result,
                processed=result,
                format=type(result).__name__,
                metadata=metadata,
                timestamp=datetime.now()
            )
            
        # Handle lists
        if isinstance(result, list):
            return ProcessedResult(
                original=result,
                processed=result,
                format="list",
                metadata={**metadata, "length": len(result)},
                timestamp=datetime.now()
            )
            
        # Handle dictionaries
        if isinstance(result, dict):
            return ProcessedResult(
                original=result,
                processed=result,
                format="dict",
                metadata={**metadata, "keys": list(result.keys())},
                timestamp=datetime.now()
            )
            
        # Handle objects with to_dict method
        if hasattr(result, 'to_dict'):
            try:
                processed = result.to_dict()
                return ProcessedResult(
                    original=result,
                    processed=processed,
                    format="object_dict",
                    metadata={
                        **metadata,
                        "class": result.__class__.__name__
                    },
                    timestamp=datetime.now()
                )
            except Exception as e:
                logger.warning(f"Failed to call to_dict: {e}")
                
        # Handle objects with __dict__
        if hasattr(result, '__dict__'):
            try:
                processed = {
                    k: v for k, v in result.__dict__.items()
                    if not k.startswith('_')
                }
                return ProcessedResult(
                    original=result,
                    processed=processed,
                    format="object_attributes",
                    metadata={
                        **metadata,
                        "class": result.__class__.__name__
                    },
                    timestamp=datetime.now()
                )
            except Exception as e:
                logger.warning(f"Failed to extract attributes: {e}")
                
        # Fallback to string representation
        return ProcessedResult(
            original=result,
            processed=str(result),
            format="string_repr",
            metadata={
                **metadata,
                "original_type": type(result).__name__
            },
            timestamp=datetime.now()
        )
        
    def can_process(self, result: Any) -> bool:
        """Standard processor can handle any type"""
        return True


class JSONProcessor(ResultProcessor):
    """
    JSON processor for formatting results as JSON
    
    This processor ensures results are JSON-serializable and
    provides pretty-printed output.
    """
    
    def __init__(self, indent: int = 2, sort_keys: bool = True):
        """
        Initialize JSON processor
        
        Args:
            indent: JSON indentation level
            sort_keys: Whether to sort dictionary keys
        """
        self.indent = indent
        self.sort_keys = sort_keys
        
    def process(
        self, result: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedResult:
        """Process result as JSON"""
        metadata = metadata or {}
        
        try:
            # First try direct JSON serialization
            json_str = json.dumps(
                result,
                indent=self.indent,
                sort_keys=self.sort_keys,
                default=str
            )
            
            return ProcessedResult(
                original=result,
                processed=json_str,
                format="json",
                metadata={
                    **metadata,
                    "serialized": True,
                    "size": len(json_str)
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.warning(f"Direct JSON serialization failed: {e}")
            
            # Try converting to serializable format
            serializable = self._make_serializable(result)
            
            try:
                json_str = json.dumps(
                    serializable,
                    indent=self.indent,
                    sort_keys=self.sort_keys
                )
                
                return ProcessedResult(
                    original=result,
                    processed=json_str,
                    format="json",
                    metadata={
                        **metadata,
                        "serialized": True,
                        "converted": True,
                        "size": len(json_str)
                    },
                    timestamp=datetime.now()
                )
                
            except Exception as e2:
                logger.error(f"JSON serialization failed: {e2}")
                
                # Fallback to error result
                error_data = {
                    "error": "JSON serialization failed",
                    "type": type(result).__name__,
                    "repr": str(result)[:1000]
                }
                
                return ProcessedResult(
                    original=result,
                    processed=json.dumps(error_data, indent=self.indent),
                    format="json_error",
                    metadata={
                        **metadata,
                        "error": str(e2)
                    },
                    timestamp=datetime.now()
                )
                
    def can_process(self, result: Any) -> bool:
        """Check if result can be JSON serialized"""
        try:
            json.dumps(result, default=str)
            return True
        except Exception:
            # Try with conversion
            try:
                serializable = self._make_serializable(result)
                json.dumps(serializable)
                return True
            except Exception:
                return False
                
    def _make_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format"""
        # Handle basic types
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
            
        # Handle datetime
        if isinstance(obj, datetime):
            return obj.isoformat()
            
        # Handle lists and tuples
        if isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
            
        # Handle dictionaries
        if isinstance(obj, dict):
            return {
                str(k): self._make_serializable(v)
                for k, v in obj.items()
            }
            
        # Handle sets
        if isinstance(obj, set):
            return list(obj)
            
        # Handle objects with to_dict
        if hasattr(obj, 'to_dict'):
            try:
                return self._make_serializable(obj.to_dict())
            except Exception:
                pass
                
        # Handle objects with __dict__
        if hasattr(obj, '__dict__'):
            try:
                return {
                    k: self._make_serializable(v)
                    for k, v in obj.__dict__.items()
                    if not k.startswith('_')
                }
            except Exception:
                pass
                
        # Fallback to string
        return str(obj)


class XMLProcessor(ResultProcessor):
    """
    XML processor for formatting results as XML
    
    This processor converts results into well-formed XML documents.
    """
    
    def __init__(self, root_tag: str = "result", indent: str = "  "):
        """
        Initialize XML processor
        
        Args:
            root_tag: Root element tag name
            indent: Indentation string
        """
        self.root_tag = root_tag
        self.indent = indent
        
    def process(
        self, result: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedResult:
        """Process result as XML"""
        metadata = metadata or {}
        
        try:
            # Create root element
            root = ET.Element(self.root_tag)
            
            # Add metadata as attributes
            if metadata:
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        root.set(str(key), str(value))
                        
            # Convert result to XML
            self._add_to_element(root, "data", result)
            
            # Convert to string
            xml_str = self._prettify_xml(root)
            
            return ProcessedResult(
                original=result,
                processed=xml_str,
                format="xml",
                metadata={
                    **metadata,
                    "root_tag": self.root_tag,
                    "size": len(xml_str)
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"XML processing failed: {e}")
            
            # Fallback to error XML
            error_root = ET.Element("error")
            error_root.text = str(e)
            
            return ProcessedResult(
                original=result,
                processed=ET.tostring(error_root, encoding='unicode'),
                format="xml_error",
                metadata={
                    **metadata,
                    "error": str(e)
                },
                timestamp=datetime.now()
            )
            
    def can_process(self, result: Any) -> bool:
        """Check if result can be converted to XML"""
        # Most types can be converted to XML in some form
        return True
        
    def _add_to_element(self, parent: ET.Element, tag: str, value: Any):
        """Add value to XML element"""
        # Sanitize tag name
        tag = self._sanitize_tag(tag)
        
        # Handle None
        if value is None:
            elem = ET.SubElement(parent, tag)
            elem.set("null", "true")
            return
            
        # Handle primitives
        if isinstance(value, (str, int, float, bool)):
            elem = ET.SubElement(parent, tag)
            elem.text = str(value)
            elem.set("type", type(value).__name__)
            return
            
        # Handle lists
        if isinstance(value, (list, tuple)):
            container = ET.SubElement(parent, tag)
            container.set("type", "array")
            container.set("length", str(len(value)))
            
            for i, item in enumerate(value):
                self._add_to_element(container, f"item_{i}", item)
            return
            
        # Handle dictionaries
        if isinstance(value, dict):
            container = ET.SubElement(parent, tag)
            container.set("type", "object")
            
            for key, val in value.items():
                self._add_to_element(container, str(key), val)
            return
            
        # Handle objects
        if hasattr(value, '__dict__'):
            container = ET.SubElement(parent, tag)
            container.set("type", "object")
            container.set("class", value.__class__.__name__)
            
            for attr, val in value.__dict__.items():
                if not attr.startswith('_'):
                    self._add_to_element(container, attr, val)
            return
            
        # Fallback to string
        elem = ET.SubElement(parent, tag)
        elem.text = str(value)
        elem.set("type", "string_repr")
        
    def _sanitize_tag(self, tag: str) -> str:
        """Sanitize tag name for XML"""
        # Replace invalid characters
        tag = str(tag)
        tag = ''.join(c if c.isalnum() or c in '_-' else '_' for c in tag)
        
        # Ensure it starts with a letter or underscore
        if tag and not (tag[0].isalpha() or tag[0] == '_'):
            tag = '_' + tag
            
        return tag or "element"
        
    def _prettify_xml(self, elem: ET.Element) -> str:
        """Pretty print XML"""
        from xml.dom import minidom
        
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        
        # Get pretty printed string
        pretty = reparsed.toprettyxml(indent=self.indent)
        
        # Remove extra blank lines
        lines = [line for line in pretty.split('\n') if line.strip()]
        
        # Skip XML declaration if present
        if lines and lines[0].startswith('<?xml'):
            lines = lines[1:]
            
        return '\n'.join(lines)


class CompositeProcessor(ResultProcessor):
    """
    Composite processor that tries multiple processors
    
    This processor can apply multiple processing strategies and
    return the best result.
    """
    
    def __init__(self, processors: Optional[List[ResultProcessor]] = None):
        """
        Initialize composite processor
        
        Args:
            processors: List of processors to try
        """
        self.processors = processors or [
            StandardProcessor(),
            JSONProcessor(),
            XMLProcessor()
        ]
        
    def process(
        self, result: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedResult:
        """Process using the first suitable processor"""
        metadata = metadata or {}
        
        for processor in self.processors:
            if processor.can_process(result):
                try:
                    return processor.process(result, metadata)
                except Exception as e:
                    logger.warning(
                        f"Processor {processor.__class__.__name__} failed: {e}"
                    )
                    continue
                    
        # All processors failed, use standard as fallback
        return StandardProcessor().process(result, metadata)
        
    def can_process(self, result: Any) -> bool:
        """Can process if any sub-processor can"""
        return any(p.can_process(result) for p in self.processors)
        
    def add_processor(self, processor: ResultProcessor):
        """Add a processor to the composite"""
        self.processors.append(processor)
        
    def remove_processor(self, processor_type: type):
        """Remove processors of a specific type"""
        self.processors = [
            p for p in self.processors
            if not isinstance(p, processor_type)
        ]


# Convenience functions

def process_result(
    result: Any,
    strategy: ProcessingStrategy = ProcessingStrategy.STRUCTURED,
    metadata: Optional[Dict[str, Any]] = None
) -> ProcessedResult:
    """
    Process a result using the specified strategy
    
    Args:
        result: The result to process
        strategy: Processing strategy to use
        metadata: Optional metadata
        
    Returns:
        Processed result
    """
    processors = {
        ProcessingStrategy.PASSTHROUGH: StandardProcessor(),
        ProcessingStrategy.JSON_FORMAT: JSONProcessor(),
        ProcessingStrategy.XML_FORMAT: XMLProcessor(),
        ProcessingStrategy.TEXT_FORMAT: StandardProcessor(),
        ProcessingStrategy.STRUCTURED: CompositeProcessor()
    }
    
    processor = processors.get(strategy, StandardProcessor())
    return processor.process(result, metadata)


def format_for_display(result: Any, max_length: int = 1000) -> str:
    """
    Format a result for display
    
    Args:
        result: The result to format
        max_length: Maximum string length
        
    Returns:
        Formatted string
    """
    # Try JSON first for nice formatting
    try:
        json_str = json.dumps(result, indent=2, default=str)
        if len(json_str) <= max_length:
            return json_str
        else:
            return json_str[:max_length-3] + "..."
    except Exception:
        # Fallback to string representation
        str_repr = str(result)
        if len(str_repr) <= max_length:
            return str_repr
        else:
            return str_repr[:max_length-3] + "..."


def extract_value(
    processed_result: ProcessedResult,
    path: str,
    default: Any = None
) -> Any:
    """
    Extract a value from a processed result using a path
    
    Args:
        processed_result: The processed result
        path: Dot-separated path (e.g., "data.user.name")
        default: Default value if path not found
        
    Returns:
        Extracted value or default
    """
    try:
        value = processed_result.processed
        
        # Handle JSON strings
        if isinstance(value, str) and processed_result.format == "json":
            value = json.loads(value)
            
        # Navigate path
        for part in path.split('.'):
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list):
                try:
                    index = int(part)
                    value = value[index] if 0 <= index < len(value) else None
                except ValueError:
                    value = None
            else:
                value = getattr(value, part, None)
                
            if value is None:
                return default
                
        return value
        
    except Exception as e:
        logger.warning(f"Failed to extract value at path '{path}': {e}")
        return default