#!/usr/bin/env python3
"""
Terraform Variable to JSON Schema Generator (Truly Generic Version)
Using advanced libraries for maximum reliability and genericity
"""

import json
import argparse
import os
import sys
import re
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

# Try to import professional libraries
try:
    import hcl2
    from jsonschema import Draft7Validator, validators
except ImportError as e:
    print(f"Error: Required libraries not found. Please install them with: pip install python-hcl2 jsonschema")
    sys.exit(1)


class TerraformTypeParser:
    """Advanced parser for Terraform type expressions"""
    
    def __init__(self):
        """Initialize the parser"""
        self.required_fields = set()  # Track which fields are required
        self.optional_fields = set()  # Track which fields are optional
        self.current_depth = 0  # Track parsing depth to control ID generation
    
    def parse_type_expression(self, type_expr: str) -> Dict[str, Any]:
        """
        Parse a Terraform type expression into JSON Schema structure
        
        Args:
            type_expr: Terraform type expression string
            
        Returns:
            JSON Schema compatible dictionary with proper required field tracking
        """
        # Reset field tracking for this parse
        self.required_fields = set()
        self.optional_fields = set()
        self.current_depth = 0  # Reset depth for new parsing
        
        # Clean up the expression
        clean_expr = self._clean_expression(type_expr)
        
        # Parse the expression
        schema = self._parse_expression(clean_expr)
        
        # Add required/optional field information to schema
        if "properties" in schema and isinstance(schema["properties"], dict):
            required_list = []
            for field_name in schema["properties"].keys():
                if field_name not in self.optional_fields and field_name != "id":
                    required_list.append(field_name)
            if required_list:
                schema["required"] = required_list
        
        return schema
    
    def _clean_expression(self, expr: str) -> str:
        """Clean up a type expression"""
        # Remove outer interpolation wrappers
        while expr.startswith("${") and expr.endswith("}"):
            expr = expr[2:-1]
        
        return expr.strip()
    
    def _parse_expression(self, expr: str, field_name: str = None) -> Dict[str, Any]:
        """Parse a cleaned expression with field name context for tracking optional fields"""
        # Handle simple types
        if expr in ["string", "number", "bool", "any"]:
            return self._create_simple_type(expr)
        
        # Handle complex types
        # List type
        if expr.startswith("list("):
            inner_type = self._extract_inner_type(expr, "list")
            current_depth = getattr(self, 'current_depth', 0)
            self.current_depth = current_depth + 1  # Increase depth for nested parsing
            result = self._create_list_type(self._parse_expression(inner_type, field_name), current_depth)
            self.current_depth = current_depth  # Restore original depth
            return result
        
        # Map type
        if expr.startswith("map("):
            inner_type = self._extract_inner_type(expr, "map")
            return self._create_map_type(self._parse_expression(inner_type, field_name))
        
        # Set type
        if expr.startswith("set("):
            inner_type = self._extract_inner_type(expr, "set")
            return self._create_set_type(self._parse_expression(inner_type, field_name))
        
        # Object type
        if expr.startswith("object("):
            inner_content = self._extract_inner_type(expr, "object")
            current_depth = getattr(self, 'current_depth', 0)
            return self._create_object_type(self._parse_object_content(inner_content), current_depth)
        
        # Optional type - this is key for tracking required vs optional fields
        if expr.startswith("optional("):
            # Extract inner type and default value if present
            parts = self._extract_optional_parts(expr)
            inner_type = parts[0]
            default_value = parts[1] if len(parts) > 1 else None
            
            # Mark this field as optional
            if field_name:
                self.optional_fields.add(field_name)
            
            schema = self._parse_expression(inner_type, field_name)
            if default_value is not None:
                schema["default"] = self._parse_default_value(default_value)
            return schema
        
        # If we can't parse it, treat as string
        return {"type": "string"}
    
    def _extract_inner_type(self, expr: str, type_name: str) -> str:
        """Extract the inner type from a complex type expression"""
        # Find the opening parenthesis after the type name
        pattern = rf"{type_name}\s*\("
        match = re.search(pattern, expr)
        if not match:
            return "string"  # Default fallback
        
        start = match.end()
        end = self._find_matching_paren(expr, start - 1)
        return expr[start:end]
    
    def _extract_optional_parts(self, expr: str) -> List[str]:
        """Extract parts from optional(type, default) expression"""
        # Find the opening parenthesis
        start = expr.find("(")
        if start == -1:
            return ["string"]  # Default fallback
        
        end = self._find_matching_paren(expr, start)
        content = expr[start+1:end]
        
        # Split by comma, but respect nested structures
        parts = self._split_by_top_level_comma(content)
        return [part.strip() for part in parts]
    
    def _find_matching_paren(self, text: str, start_pos: int) -> int:
        """Find the matching closing parenthesis"""
        count = 1
        pos = start_pos + 1
        
        while pos < len(text) and count > 0:
            if text[pos] == "(":
                count += 1
            elif text[pos] == ")":
                count -= 1
            pos += 1
        
        return pos - 1
    
    def _split_by_top_level_comma(self, text: str) -> List[str]:
        """Split text by commas at the top level"""
        parts = []
        current_part = ""
        paren_count = 0
        brace_count = 0
        bracket_count = 0
        in_string = False
        string_char = None
        
        for char in text:
            if char in ['"', "'"] and not in_string:
                in_string = True
                string_char = char
                current_part += char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
                current_part += char
            elif in_string:
                current_part += char
            elif char == "(":
                paren_count += 1
                current_part += char
            elif char == ")":
                paren_count -= 1
                current_part += char
            elif char == "{":
                brace_count += 1
                current_part += char
            elif char == "}":
                brace_count -= 1
                current_part += char
            elif char == "[":
                bracket_count += 1
                current_part += char
            elif char == "]":
                bracket_count -= 1
                current_part += char
            elif char == "," and paren_count == 0 and brace_count == 0 and bracket_count == 0:
                parts.append(current_part.strip())
                current_part = ""
            else:
                current_part += char
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        return parts
    
    def _parse_object_content(self, content: str) -> Dict[str, Any]:
        """Parse object content into properties generically"""
        properties = {}
        
        # Store the current optional fields state
        parent_optional_fields = self.optional_fields.copy()
        # Reset for this object scope
        self.optional_fields = set()
        
        # Remove surrounding braces if present
        content = content.strip()
        if content.startswith("{") and content.endswith("}"):
            content = content[1:-1]
        
        # The HCL parser gives us content like:
        # "hostname": "string", "ecs_size": "string", "az": "string", ...
        import re
        
        # Split by commas at the top level (outside of nested structures)
        property_pairs = self._split_by_top_level_comma(content)
        
        for pair in property_pairs:
            pair = pair.strip()
            if not pair:
                continue
            
            # Parse each property assignment
            # Handle both "property": "type" and property: type formats
            colon_match = re.search(r'^\s*["\']?([^"\':]+)["\']?\s*:\s*(.+)$', pair)
            if colon_match:
                prop_name = colon_match.group(1).strip()
                prop_type_str = colon_match.group(2).strip()
                
                # Remove quotes from type string if present
                if (prop_type_str.startswith('"') and prop_type_str.endswith('"')) or \
                   (prop_type_str.startswith("'") and prop_type_str.endswith("'")):
                    prop_type_str = prop_type_str[1:-1]
                
                # Clean nested ${} interpolations
                prop_type_str = self._clean_expression(prop_type_str)
                
                # Parse the property type
                prop_schema = self._parse_expression(prop_type_str, prop_name)
                properties[prop_name] = prop_schema
        
        # Get the optional fields for this scope
        local_optional_fields = self.optional_fields.copy()
        
        # Restore parent scope
        self.optional_fields = parent_optional_fields
        
        # Build required list based on local scope
        required_list = []
        for prop_name in properties.keys():
            prop_schema = properties[prop_name]
            # A field is required if:
            # 1. It's not the id field (always optional)
            # 2. It doesn't have a default value
            # 3. It wasn't parsed from an optional() wrapper in this scope
            is_id_field = prop_name == "id"
            has_default = "default" in prop_schema
            is_optional = prop_name in local_optional_fields
            
            if not is_id_field and not has_default and not is_optional:
                required_list.append(prop_name)
        
        # Store required info in a way we can use it in _create_object_type
        # We'll attach this information to the properties dict
        properties["__required_fields__"] = required_list
        
        return properties
    
    def _parse_default_value(self, value_str: str) -> Any:
        """Parse a default value string"""
        value_str = value_str.strip()
        
        # Handle quoted strings
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]
        
        # Handle booleans
        if value_str.lower() in ["true", "false"]:
            return value_str.lower() == "true"
        
        # Handle null
        if value_str.lower() == "null":
            return None
        
        # Handle empty objects and arrays
        if value_str == "{}":
            return {}
        if value_str == "[]":
            return []
        
        # Handle numbers
        try:
            if "." in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass
        
        # Default to string
        return value_str
    
    def _create_simple_type(self, type_name: str) -> Dict[str, Any]:
        """Create schema for simple types"""
        if type_name == "string":
            return {"type": "string"}
        elif type_name == "number":
            return {"type": "number"}
        elif type_name == "bool":
            return {"type": "boolean"}
        elif type_name == "any":
            return {}
        else:
            return {"type": "string"}
    
    def _create_list_type(self, element_schema: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """Create schema for list type"""
        # Add UUID to array item objects only if they are at the top level (depth == 0)
        # This prevents redundant IDs in nested arrays like ingress/egress
        if element_schema.get("type") == "object" and depth == 0:
            self._add_id_field_to_schema(element_schema)
        return {"type": "array", "items": element_schema}
    
    def _add_id_field_to_schema(self, schema: Dict[str, Any]):
        """Add id field to the schema"""
        if "properties" in schema and "id" not in schema["properties"]:
            schema["properties"]["id"] = {
                "type": "string",
                "format": "uuid",
                "default": "",
                "options": {"hidden": True},
            }
            # Mark id as optional so it's not added to required fields
            self.optional_fields.add("id")
    
    def _find_property_end(self, content: str, start_pos: int) -> int:
        """Find the end of a property definition in object content"""
        paren_count = 0
        brace_count = 0
        bracket_count = 0
        in_string = False
        i = start_pos
        
        while i < len(content):
            char = content[i]
            
            if char == '"' and (i == 0 or content[i-1] != '\\'):
                in_string = not in_string
            elif not in_string:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                elif char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                elif (char.isalpha() or char == '_') and paren_count == 0 and brace_count == 0 and bracket_count == 0:
                    # Look ahead to see if this might be the start of a new property
                    lookahead = content[i:i+50]  # Look ahead 50 chars
                    if re.search(r'^\w+\s*=', lookahead):
                        return i
            i += 1
        
        return len(content)
    
    def _create_map_type(self, value_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Create schema for map type"""
        return {"type": "object", "additionalProperties": value_schema}
    
    def _create_set_type(self, element_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Create schema for set type"""
        return {"type": "array", "items": element_schema, "uniqueItems": True}
    
    def _create_object_type(self, properties: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """Create schema for object type with proper required field tracking"""
        # Extract required fields info if present
        required_list = properties.pop("__required_fields__", [])
        
        schema = {
            "type": "object",
            "additionalProperties": True,
            "properties": properties,
        }
        
        if required_list:
            schema["required"] = required_list
        
        return schema


class GenericTerraformParser:
    """Generic Terraform parser using professional libraries"""
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a Terraform file and extract variable definitions"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Input file '{file_path}' not found")
        
        # Parse HCL using professional library
        try:
            parsed = hcl2.loads(content)
        except Exception as e:
            raise Exception(f"Error parsing HCL file: {str(e)}")
        
        # Extract variable definitions using generic approach
        variables = self._extract_variables(parsed)
        
        return variables
    
    def _extract_variables(self, parsed_hcl: Dict[str, Any]) -> Dict[str, Any]:
        """Generic variable extraction from parsed HCL"""
        variables = {}
        
        # Look for variable blocks in the parsed structure
        if "variable" in parsed_hcl:
            for var_block in parsed_hcl["variable"]:
                if isinstance(var_block, dict):
                    for var_name, var_def in var_block.items():
                        if isinstance(var_def, dict):
                            variables[var_name] = self._process_variable_definition(var_def)
        
        return variables
    
    def _process_variable_definition(self, var_def: Dict[str, Any]) -> Dict[str, Any]:
        """Process a variable definition in a generic way"""
        processed = {}
        
        # Copy all fields generically
        for key, value in var_def.items():
            processed[key] = value
        
        return processed


class GenericJSONSchemaGenerator:
    """Truly generic JSON Schema generator"""
    
    def __init__(self, add_uuid_selectively: bool = True):
        """
        Initialize the generator with selective UUID addition
        
        Args:
            add_uuid_selectively: Add UUID only where semantically appropriate
        """
        self.add_uuid_selectively = add_uuid_selectively
        self.uuid_added_paths = set()  # Track where UUIDs have been added
        self.type_parser = TerraformTypeParser()
        self.current_nesting_level = 0  # Track nesting depth to avoid redundant IDs
    
    def generate_schema(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Generate JSON Schema from variables in a truly generic way"""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "additionalProperties": True,
            "properties": {},
            "required": [],
        }
        
        for var_name, var_def in variables.items():
            prop_schema = self._convert_to_schema(var_def, [var_name])
            
            # Add description if present
            if "description" in var_def:
                prop_schema["description"] = var_def["description"]
            
            # Add default value if present at variable level
            if "default" in var_def:
                prop_schema["default"] = var_def["default"]
            
            # Add validation constraints if present
            if "validation" in var_def:
                self._add_validation_constraints(prop_schema, var_def["validation"])
            
            schema["properties"][var_name] = prop_schema
            
            # For top-level variables, they are only required in JSON Schema if:
            # 1. They have no default value AND
            # 2. They are explicitly required in Terraform (no optional() wrapper)
            # However, in Terraform, variables without defaults are NOT automatically required
            # They become required only when used without a default value in the module call
            # So we should NOT add them to required list automatically
            # Only add to required if explicitly marked as required through validation or other means
            pass  # Don't automatically add variables to required list
        
        return schema
    
    def _is_type_optional(self, type_def: Any) -> bool:
        """Check if a type definition indicates the variable is optional"""
        if isinstance(type_def, str):
            # Simple heuristic: if type definition contains 'optional(', it's optional
            return "optional(" in type_def
        return False
    
    def _add_validation_constraints(self, schema: Dict[str, Any], validations: List[Dict[str, Any]]) -> None:
        """Add validation constraints to schema from Terraform validations"""
        if not validations:
            return
        
        for validation in validations:
            condition = validation.get("condition", "")
            error_message = validation.get("error_message", "")
            
            # Clean condition by removing ${} wrappers
            clean_condition = condition
            while clean_condition.startswith("${") and clean_condition.endswith("}"):
                clean_condition = clean_condition[2:-1]
            
            # Extract enum values from contains() functions with improved patterns
            self._extract_and_apply_enums(schema, clean_condition)
    
    def _extract_and_apply_enums(self, schema: Dict[str, Any], condition: str) -> None:
        """Extract enum values from validation conditions and apply them to the schema"""
        import re
        
        # Enhanced pattern to match contains() function calls with enum arrays
        # This handles multiple patterns:
        # 1. Direct: contains(["val1", "val2"], var.property)
        # 2. Simple iteration: contains(["val1", "val2"], item.property) 
        # 3. Flatten pattern: contains(["val1", "val2"], flattened_item.property)
        contains_patterns = [
            # Pattern 1: Standard contains with direct property access
            r'contains\s*\(\s*\[([^\]]+)\]\s*,\s*[^.]+\.(\w+)\s*\)',
            # Pattern 2: Contains within flatten iteration (most common in complex validation)
            r'contains\s*\(\s*\[([^\]]+)\]\s*,\s*(\w+)\.(\w+)\s*\)'
        ]
        
        all_matches = []
        for pattern in contains_patterns:
            matches = re.findall(pattern, condition)
            
            # Handle different match group structures
            for match in matches:
                if len(match) == 2:  # Pattern 1: (array_content, property_name)
                    array_content, property_name = match
                    all_matches.append((array_content, property_name))
                elif len(match) == 3:  # Pattern 2: (array_content, iterator_var, property_name)
                    array_content, iterator_var, property_name = match
                    all_matches.append((array_content, property_name))
        
        for array_content, property_name in all_matches:
            # Extract both quoted and unquoted values from the array content
            # First try quoted strings
            quoted_pattern = r'"([^"]+)"'
            enum_values = re.findall(quoted_pattern, array_content)
            
            # If no quoted strings found, try unquoted identifiers
            if not enum_values:
                # Split by comma and clean up each value
                unquoted_values = [v.strip() for v in array_content.split(',') if v.strip()]
                enum_values = [v for v in unquoted_values if v and not v.startswith('$')]
            
            if enum_values:
                # Apply enum to the appropriate property in the schema
                self._apply_enum_to_schema_property(schema, property_name, enum_values)
    
    def _apply_enum_to_schema_property(self, schema: Dict[str, Any], property_name: str, enum_values: List[str]) -> bool:
        """Apply enum values to a specific property in the schema structure"""
        
        def apply_enum_recursively(obj: Dict[str, Any], prop_name: str, values: List[str]) -> bool:
            """Recursively search for and apply enum to the specified property"""
            applied = False
            
            # Handle array schemas - recurse into items
            if obj.get("type") == "array" and "items" in obj:
                if apply_enum_recursively(obj["items"], prop_name, values):
                    applied = True
            
            # Check direct properties
            elif "properties" in obj and isinstance(obj["properties"], dict):
                properties = obj["properties"]
                if prop_name in properties and isinstance(properties[prop_name], dict):
                    properties[prop_name]["enum"] = values
                    applied = True
                
                # Also search in nested objects and arrays
                for nested_prop_name, prop_schema in properties.items():
                    if isinstance(prop_schema, dict):
                        # Check array items
                        if prop_schema.get("type") == "array" and "items" in prop_schema:
                            if apply_enum_recursively(prop_schema["items"], prop_name, values):
                                applied = True
                        # Check nested objects
                        elif prop_schema.get("type") == "object":
                            if apply_enum_recursively(prop_schema, prop_name, values):
                                applied = True
            
            return applied
        
        # Apply the enum starting from the root schema
        return apply_enum_recursively(schema, property_name, enum_values)
    
    def _convert_to_schema(self, value: Any, path: List[str]) -> Dict[str, Any]:
        """Convert any value to JSON Schema in a generic way"""
        path_str = ".".join(path)
        
        # Handle dictionaries (objects)
        if isinstance(value, dict):
            # Special handling for type definitions
            if "type" in value:
                schema = self._convert_type_definition(value["type"], path)
                # If the type parser tracked required fields, use them
                if hasattr(self.type_parser, 'required_fields') and hasattr(self.type_parser, 'optional_fields'):
                    if "properties" in schema and "required" not in schema:
                        required_list = []
                        for field_name in schema["properties"].keys():
                            if field_name not in self.type_parser.optional_fields and field_name != "id":
                                required_list.append(field_name)
                        if required_list:
                            schema["required"] = required_list
                return schema
            
            # Generic object handling
            schema = {
                "type": "object",
                "additionalProperties": True,
                "properties": {},
                "required": [],
            }
            
            for key, val in value.items():
                prop_path = path + [key]
                prop_schema = self._convert_to_schema(val, prop_path)
                schema["properties"][key] = prop_schema
                schema["required"].append(key)
            
            # Add UUID selectively based on path and context
            should_add_uuid = self.add_uuid_selectively and self._should_add_uuid(path, value)
            if should_add_uuid:
                self._add_id_field(schema)
                self.uuid_added_paths.add(path_str)
            
            return schema
        
        # Handle lists/arrays
        elif isinstance(value, list):
            if len(value) > 0:
                # Assume homogeneous array
                item_schema = self._convert_to_schema(value[0], path + ["item"])
                # Add UUID to array items
                if self.add_uuid_selectively:
                    self._add_id_field(item_schema)
                return {"type": "array", "items": item_schema}
            else:
                return {"type": "array", "items": {}}
        
        # Handle primitive types
        elif isinstance(value, str):
            return self._convert_string_to_schema(value, path)
        elif isinstance(value, (int, float)):
            return {"type": "number"}
        elif isinstance(value, bool):
            return {"type": "boolean"}
        elif value is None:
            return {}
        else:
            return {"type": "string"}  # Default fallback
    
    def _convert_type_definition(self, type_def: Any, path: List[str]) -> Dict[str, Any]:
        """Convert Terraform type definition to JSON Schema"""
        # Handle string type definitions
        if isinstance(type_def, str):
            # Use the type parser which handles optional fields correctly
            # Pass the path depth to control ID generation
            self.type_parser.current_depth = len(path)
            return self.type_parser.parse_type_expression(type_def)
        
        # Handle complex type definitions
        elif isinstance(type_def, dict):
            return self._convert_to_schema(type_def, path)
        
        # Handle list type definitions
        elif isinstance(type_def, list):
            return self._convert_to_schema(type_def, path)
        
        else:
            return {"type": "string"}  # Default fallback
    
    def _convert_string_to_schema(self, value: str, path: List[str]) -> Dict[str, Any]:
        """Convert string value to appropriate JSON Schema type"""
        # Try to infer type from string content
        value = value.strip()
        
        # Handle boolean strings
        if value.lower() in ["true", "false"]:
            return {"type": "boolean"}
        
        # Handle numeric strings
        try:
            if "." in value:
                float(value)
                return {"type": "number"}
            else:
                int(value)
                return {"type": "integer"}
        except ValueError:
            pass
        
        # Handle array strings
        if value.startswith("[") and value.endswith("]"):
            return {"type": "array", "items": {}}
        
        # Handle object strings
        if value.startswith("{") and value.endswith("}"):
            return {"type": "object", "additionalProperties": True}
        
        # Default to string
        return {"type": "string"}
    
    def _should_add_uuid(self, path: List[str], value: Dict[str, Any]) -> bool:
        """Determine if UUID should be added at this path"""
        # Add UUID only to the first level of arrays (variable-level arrays)
        # Do not add UUID to nested arrays like ingress/egress within nacl
        if len(path) > 0:
            # If the path ends with "item", it's likely an array element
            if path[-1] == "item":
                # Only add UUID if this is a top-level array (path length is 2: [var_name, "item"])
                return len(path) == 2
            
            # If we're processing array items, add UUID only for top-level arrays
            if len(path) >= 2 and path[-2] == "items":
                # Only add UUID if this is a top-level array (path length is 3: [var_name, "items", "item"])
                return len(path) == 3
        
        return False
    
    def _add_id_field(self, schema: Dict[str, Any]):
        """Add id field to the schema"""
        if "properties" in schema and "id" not in schema["properties"]:
            schema["properties"]["id"] = {
                "type": "string",
                "format": "uuid",
                "default": "",
                "options": {"hidden": True},
            }


class GenericTerraformToJSONSchemaConverter:
    """Truly generic converter using professional libraries"""
    
    def __init__(self, add_uuid_selectively: bool = True):
        """
        Initialize the converter
        
        Args:
            add_uuid_selectively: Add UUID only where semantically appropriate
        """
        self.parser = GenericTerraformParser()
        self.generator = GenericJSONSchemaGenerator(add_uuid_selectively)
    
    def convert_file(self, input_file: str, output_file: Optional[str] = None) -> str:
        """
        Convert a single Terraform variables file to JSON Schema
        
        Args:
            input_file: Path to the Terraform variables file
            output_file: Path to the output JSON Schema file (optional)
            
        Returns:
            Path to the generated JSON Schema file
        """
        # Validate input file
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file '{input_file}' does not exist")
        
        # Parse Terraform variables to get variable names
        variables = self.parser.parse_file(input_file)
        
        # Determine output file
        if output_file:
            output_path = Path(output_file)
        else:
            input_path = Path(input_file)
            # Use the first variable name as the filename, or fallback to "variables"
            if variables:
                # Get the first variable name
                var_name = next(iter(variables.keys()))
                output_filename = f"{var_name}.json"
            else:
                output_filename = "variables.json"
            output_path = input_path.parent / output_filename
        
        # Generate JSON Schema
        schema = self.generator.generate_schema(variables)
        
        # Write output
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=4, ensure_ascii=False)
        
        return str(output_path)
    
    def convert_directory(self, input_dir: str, output_dir: Optional[str] = None) -> List[str]:
        """
        Convert all Terraform variables files in a directory to JSON Schema
        
        Args:
            input_dir: Path to the directory containing Terraform files
            output_dir: Path to the output directory (optional, defaults to input_dir)
            
        Returns:
            List of paths to the generated JSON Schema files
        """
        input_path = Path(input_dir)
        if not input_path.exists() or not input_path.is_dir():
            raise ValueError(f"Input directory '{input_dir}' does not exist or is not a directory")
        
        # Determine output directory
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        else:
            output_path = input_path
        
        # Find all variables.tf files
        var_files = list(input_path.rglob("variables.tf"))
        if not var_files:
            print(f"No variables.tf files found in directory '{input_dir}'")
            return []
        
        generated_files = []
        for var_file in var_files:
            try:
                # Determine output file path
                relative_path = var_file.relative_to(input_path)
                output_file = output_path / relative_path.with_suffix(".json")
                
                # Create output directory if needed
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Convert file
                result = self.convert_file(str(var_file), str(output_file))
                generated_files.append(result)
                print(f"Converted '{var_file}' to '{result}'")
            except Exception as e:
                print(f"Error converting '{var_file}': {str(e)}")
        
        return generated_files


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Convert Terraform variable definitions to JSON Schema (Truly Generic Version)"
    )
    parser.add_argument(
        "input", 
        help="Path to Terraform variables file or directory containing variables.tf files"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON Schema file or directory path"
    )
    parser.add_argument(
        "--pretty", 
        action="store_true", 
        help="Pretty print JSON output (always enabled in this version)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug output"
    )
    parser.add_argument(
        "--no-uuid", 
        action="store_true", 
        help="Disable selective UUID field addition"
    )
    
    args = parser.parse_args()
    
    try:
        converter = GenericTerraformToJSONSchemaConverter(not args.no_uuid)
        
        # Check if input is a directory or file
        input_path = Path(args.input)
        if input_path.is_dir():
            # Process directory
            generated_files = converter.convert_directory(str(input_path), args.output)
            if generated_files:
                print(f"Successfully converted {len(generated_files)} files")
            else:
                print("No files were converted")
        else:
            # Process single file
            if not input_path.exists():
                print(f"Error: Input file '{args.input}' does not exist")
                return 1
                
            # Parse and debug if needed
            if args.debug:
                variables = converter.parser.parse_file(str(input_path))
                print("=== Debug: Parsed Variables ===")
                for var_name, var_def in variables.items():
                    print(f"\n{var_name}:")
                    for key, value in var_def.items():
                        if isinstance(value, str) and len(value) > 100:
                            print(f"  {key}: {value[:100]}...")
                        else:
                            print(f"  {key}: {value}")
                
            output_file = converter.convert_file(str(input_path), args.output)
            print(f"Successfully generated JSON Schema: {output_file}")
            
        return 0
    
    except Exception as e:
        print(f"Error: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())