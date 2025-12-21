"""
Utility functions for converting JSON Schema to Pydantic models.

This module provides helpers to dynamically generate Pydantic models from JSON Schema
definitions stored in the event registry, enabling type-safe event payload construction
and validation.
"""
from typing import Any, Dict, Optional, Tuple, Type, Union, get_args, get_origin, List
from pydantic import create_model, Field, ValidationError
from soorma_common import BaseDTO, EventDefinition


def json_schema_to_pydantic(
    schema: Dict[str, Any],
    model_name: str = "DynamicModel",
    base_class: Type[BaseDTO] = BaseDTO
) -> Type[BaseDTO]:
    """
    Convert a JSON Schema (Draft 7) to a Pydantic model dynamically.
    
    This function creates a Pydantic model class that inherits from BaseDTO,
    providing automatic camelCase JSON serialization and validation.
    
    Args:
        schema: JSON Schema dictionary (must be type "object")
        model_name: Name for the generated Pydantic model class
        base_class: Base class to inherit from (default: BaseDTO)
        
    Returns:
        A dynamically created Pydantic model class
        
    Raises:
        ValueError: If schema is not of type "object" or is invalid
        
    Example:
        >>> schema = {
        ...     "type": "object",
        ...     "properties": {
        ...         "user_name": {"type": "string"},
        ...         "age": {"type": "integer"}
        ...     },
        ...     "required": ["user_name"]
        ... }
        >>> UserModel = json_schema_to_pydantic(schema, "User")
        >>> user = UserModel(user_name="Alice", age=30)
        >>> user.model_dump_json()  # Will use camelCase: {"userName": "Alice", "age": 30}
    """
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a dictionary")
    
    schema_type = schema.get("type")
    if schema_type != "object":
        raise ValueError(f"Only 'object' type schemas are supported, got: {schema_type}")
    
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    
    if not properties:
        # Empty object schema
        return create_model(model_name, __base__=base_class)
    
    # Build field definitions for Pydantic
    field_definitions = {}
    
    for field_name, field_schema in properties.items():
        field_type = _json_type_to_python_type(field_schema, f"{model_name}_{field_name}")
        
        # Determine if field is required
        is_required = field_name in required_fields
        
        # Get field metadata
        description = field_schema.get("description", "")
        
        # Set default value
        if is_required:
            default = ...  # Ellipsis means required in Pydantic
        else:
            # Optional fields default to None
            default = None
            # Wrap type in Optional
            field_type = Optional[field_type]
        
        # Create Field with metadata
        field_definitions[field_name] = (
            field_type,
            Field(default=default, description=description)
        )
    
    # Create the model dynamically
    return create_model(
        model_name,
        __base__=base_class,
        **field_definitions
    )


def _json_type_to_python_type(
    field_schema: Dict[str, Any],
    nested_name: str = "NestedModel"
) -> Type:
    """
    Recursively convert JSON Schema types to Python types.
    """
    json_type = field_schema.get("type")
    
    if json_type == "string":
        return str
    elif json_type == "integer":
        return int
    elif json_type == "number":
        return float
    elif json_type == "boolean":
        return bool
    elif json_type == "array":
        item_schema = field_schema.get("items", {})
        item_type = _json_type_to_python_type(item_schema, f"{nested_name}_Item")
        return List[item_type]
    elif json_type == "object":
        # Recursive call for nested objects
        return json_schema_to_pydantic(field_schema, nested_name)
    else:
        # Fallback for unknown types or 'any'
        return Any


def pydantic_to_json_schema(model_class: Type[BaseDTO]) -> Dict[str, Any]:
    """
    Convert a Pydantic model to JSON Schema.
    
    Args:
        model_class: Pydantic model class
        
    Returns:
        JSON Schema dictionary
    """
    return model_class.model_json_schema()


def create_event_models(event_def: EventDefinition) -> Tuple[Type[BaseDTO], Optional[Type[BaseDTO]]]:
    """
    Create Pydantic models for an event's payload and response.
    
    Args:
        event_def: Event definition from registry
        
    Returns:
        Tuple of (PayloadModel, ResponseModel)
        ResponseModel will be None if no response schema is defined.
    """
    # Create payload model
    payload_model_name = f"{_snake_to_pascal(event_def.event_name)}Payload"
    payload_model = json_schema_to_pydantic(
        event_def.payload_schema,
        payload_model_name
    )
    
    # Create response model if exists
    response_model = None
    if event_def.response_schema:
        response_model_name = f"{_snake_to_pascal(event_def.event_name)}Response"
        response_model = json_schema_to_pydantic(
            event_def.response_schema,
            response_model_name
        )
        
    return payload_model, response_model


def validate_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a dictionary against a JSON schema using Pydantic.
    
    Args:
        data: Data to validate
        schema: JSON schema to validate against
        
    Returns:
        Validated data (potentially with type coercion)
        
    Raises:
        ValidationError: If validation fails
    """
    DynamicModel = json_schema_to_pydantic(schema)
    model_instance = DynamicModel.model_validate(data)
    return model_instance.model_dump(by_alias=True)


def get_schema_field_names(schema: Dict[str, Any]) -> List[str]:
    """Get list of field names from a schema."""
    return list(schema.get("properties", {}).keys())


def get_required_fields(schema: Dict[str, Any]) -> List[str]:
    """Get list of required fields from a schema."""
    return schema.get("required", [])


def is_valid_json_schema(schema: Dict[str, Any]) -> bool:
    """Check if a dictionary is a valid JSON schema object."""
    return (
        isinstance(schema, dict) and 
        schema.get("type") == "object" and 
        "properties" in schema
    )


def _snake_to_pascal(snake_str: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in snake_str.replace(".", "_").split("_"))
