"""
Schema Validation Utilities

This module provides utilities for validating tool metadata and
parameters against JSON schemas.
"""

import json
import logging
from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path
try:
    from jsonschema import Draft7Validator, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    ValidationError = Exception
    Draft7Validator = None


logger = logging.getLogger(__name__)


class SchemaValidator:
    """
    Validator for tool metadata and parameters using JSON Schema
    """
    
    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize the validator
        
        Args:
            schema_path: Path to the schema file (uses default if not provided)
        """
        if not HAS_JSONSCHEMA:
            logger.warning(
                "jsonschema package not installed. "
                "Schema validation will be limited."
            )
        
        # Set default schema path
        if schema_path is None:
            schema_path = Path(__file__).parent / "tool_metadata_schema.json"
        
        self.schema_path = schema_path
        self._schema: Optional[Dict[str, Any]] = None
        self._validator: Optional[Any] = None
        
        # Load schema
        self._load_schema()
    
    def _load_schema(self):
        """Load the JSON schema"""
        try:
            with open(self.schema_path, 'r') as f:
                self._schema = json.load(f)
            
            if HAS_JSONSCHEMA and Draft7Validator:
                self._validator = Draft7Validator(self._schema)
            
            logger.debug(f"Loaded schema from {self.schema_path}")
            
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            self._schema = None
            self._validator = None
    
    def validate_metadata(
        self, metadata: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate tool metadata against schema
        
        Args:
            metadata: Tool metadata dictionary
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        if not self._schema:
            return False, ["Schema not loaded"]
        
        errors = []
        
        # Use jsonschema if available
        if HAS_JSONSCHEMA and self._validator:
            try:
                self._validator.validate(metadata)
                return True, []
            except ValidationError:
                # Collect all validation errors
                for error in self._validator.iter_errors(metadata):
                    path = " -> ".join(str(p) for p in error.path)
                    if path:
                        errors.append(f"{path}: {error.message}")
                    else:
                        errors.append(error.message)
                return False, errors
        else:
            # Basic validation without jsonschema
            return self._basic_validate(metadata)
    
    def _basic_validate(
        self, metadata: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Basic validation without jsonschema library
        
        Args:
            metadata: Tool metadata dictionary
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check required fields
        required_fields = [
            "name", "version", "description", "author", "category"
        ]
        
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Required field '{field}' is missing")
        
        # Validate field types and patterns
        if "name" in metadata:
            if not isinstance(metadata["name"], str):
                errors.append("Field 'name' must be a string")
            elif not metadata["name"]:
                errors.append("Field 'name' cannot be empty")
            elif not metadata["name"][0].isalpha():
                errors.append("Field 'name' must start with a letter")
        
        if "version" in metadata:
            if not isinstance(metadata["version"], str):
                errors.append("Field 'version' must be a string")
            else:
                # Basic semver pattern check
                import re
                if not re.match(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$', 
                                metadata["version"]):
                    errors.append(
                        "Field 'version' must follow semantic versioning"
                    )
        
        if "category" in metadata:
            valid_categories = [
                "transformation", "analysis", "generation", "utility",
                "integration", "system", "debug", "custom"
            ]
            if metadata["category"] not in valid_categories:
                errors.append(
                    f"Field 'category' must be one of: "
                    f"{', '.join(valid_categories)}"
                )
        
        if "parameters" in metadata:
            if not isinstance(metadata["parameters"], list):
                errors.append("Field 'parameters' must be an array")
            else:
                for i, param in enumerate(metadata["parameters"]):
                    param_errors = self._validate_parameter(param, i)
                    errors.extend(param_errors)
        
        return len(errors) == 0, errors
    
    def _validate_parameter(
        self, param: Dict[str, Any], index: int
    ) -> List[str]:
        """
        Validate a single parameter definition
        
        Args:
            param: Parameter dictionary
            index: Parameter index in array
            
        Returns:
            List of error messages
        """
        errors = []
        prefix = f"Parameter[{index}]"
        
        # Check required fields
        required = ["name", "type", "description"]
        for field in required:
            if field not in param:
                errors.append(f"{prefix}: Required field '{field}' is missing")
        
        # Validate types
        if "type" in param:
            valid_types = [
                "string", "integer", "float", "boolean", "array",
                "object", "file_path", "url", "enum", "any"
            ]
            if param["type"] not in valid_types:
                errors.append(
                    f"{prefix}: Invalid type '{param['type']}'. "
                    f"Must be one of: {', '.join(valid_types)}"
                )
        
        # Validate enum values
        if param.get("type") == "enum" and "enum_values" not in param:
            errors.append(
                f"{prefix}: Parameters of type 'enum' must have 'enum_values'"
            )
        
        return errors
    
    def validate_parameter_value(
        self,
        param_def: Dict[str, Any],
        value: Any
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a parameter value against its definition
        
        Args:
            param_def: Parameter definition
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        param_type = param_def.get("type", "any")
        
        # Check required
        if value is None:
            if param_def.get("required", True):
                return False, "Required parameter is missing"
            return True, None
        
        # Type validation
        type_validators = {
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: (
                isinstance(v, int) and not isinstance(v, bool)
            ),
            "float": lambda v: (
                isinstance(v, (int, float)) and not isinstance(v, bool)
            ),
            "boolean": lambda v: isinstance(v, bool),
            "array": lambda v: isinstance(v, list),
            "object": lambda v: isinstance(v, dict),
            "any": lambda v: True
        }
        
        validator = type_validators.get(param_type)
        if validator and not validator(value):
            return False, f"Value must be of type {param_type}"
        
        # Additional validations
        if param_type == "string":
            if "pattern" in param_def:
                import re
                if not re.match(param_def["pattern"], value):
                    return False, (
                        f"Value does not match pattern: {param_def['pattern']}"
                    )
        
        elif param_type in ["integer", "float"]:
            if "min_value" in param_def and value < param_def["min_value"]:
                return False, f"Value must be >= {param_def['min_value']}"
            if "max_value" in param_def and value > param_def["max_value"]:
                return False, f"Value must be <= {param_def['max_value']}"
        
        elif param_type == "enum":
            enum_values = param_def.get("enum_values", [])
            if enum_values and value not in enum_values:
                return False, f"Value must be one of: {enum_values}"
        
        return True, None
    
    def create_parameter_schema(
        self, param_def: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create JSON Schema for a parameter definition
        
        Args:
            param_def: Parameter definition
            
        Returns:
            JSON Schema object
        """
        schema: Dict[str, Any] = {
            "description": param_def.get("description", "")
        }
        
        param_type = param_def.get("type", "any")
        
        # Map to JSON Schema types
        type_mapping = {
            "string": "string",
            "integer": "integer",
            "float": "number",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
            "file_path": "string",
            "url": "string",
            "any": ["string", "number", "boolean", "object", "array", "null"]
        }
        
        schema["type"] = type_mapping.get(param_type, "string")
        
        # Add constraints
        if "enum_values" in param_def:
            schema["enum"] = param_def["enum_values"]
        
        if "min_value" in param_def:
            schema["minimum"] = param_def["min_value"]
        
        if "max_value" in param_def:
            schema["maximum"] = param_def["max_value"]
        
        if "pattern" in param_def:
            schema["pattern"] = param_def["pattern"]
        
        if "default" in param_def:
            schema["default"] = param_def["default"]
        
        # Special formats
        if param_type == "file_path":
            schema["format"] = "file-path"
        elif param_type == "url":
            schema["format"] = "uri"
        
        return schema
    
    def generate_tool_schema(
        self, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate complete JSON Schema for a tool
        
        Args:
            metadata: Tool metadata
            
        Returns:
            JSON Schema object
        """
        # Build parameter schemas
        properties = {}
        required = []
        
        for param in metadata.get("parameters", []):
            param_name = param["name"]
            properties[param_name] = self.create_parameter_schema(param)
            
            if param.get("required", True):
                required.append(param_name)
        
        # Create tool schema
        tool_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": metadata.get("name", "Tool"),
            "description": metadata.get("description", ""),
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False
        }
        
        return tool_schema


# Convenience functions

def validate_tool_metadata(
    metadata: Dict[str, Any],
    schema_path: Optional[Path] = None
) -> Tuple[bool, List[str]]:
    """
    Validate tool metadata
    
    Args:
        metadata: Tool metadata dictionary
        schema_path: Optional path to schema file
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    validator = SchemaValidator(schema_path)
    return validator.validate_metadata(metadata)


def validate_parameter_value(
    param_def: Dict[str, Any],
    value: Any
) -> Tuple[bool, Optional[str]]:
    """
    Validate a parameter value
    
    Args:
        param_def: Parameter definition
        value: Value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = SchemaValidator()
    return validator.validate_parameter_value(param_def, value)


def create_tool_schema(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create JSON Schema for a tool
    
    Args:
        metadata: Tool metadata
        
    Returns:
        JSON Schema object
    """
    validator = SchemaValidator()
    return validator.generate_tool_schema(metadata)