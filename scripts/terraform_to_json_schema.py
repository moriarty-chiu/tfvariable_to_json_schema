#!/usr/bin/env python3
"""
Terraform Variable to JSON Schema Generator (Generic Version)

A general-purpose tool to convert Terraform variable definitions into JSON Schema format,
with support for directory processing and configurable property mappings.
"""

import re
import json
import argparse
import os
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path


class TerraformVariableParser:
    """Parser for Terraform variable definitions"""

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a Terraform file and extract variable definitions"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Input file '{file_path}' not found")

        # Remove comments
        content = self._remove_comments(content)

        # Extract variable blocks
        variables = self._extract_variable_blocks(content)

        parsed_vars = {}
        for var_name, var_content in variables:
            parsed_vars[var_name] = self._parse_variable_content(var_name, var_content)

        return parsed_vars

    def _remove_comments(self, content: str) -> str:
        """Remove comments while preserving string contents"""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                cleaned_lines.append(line)
                continue
                
            # Track string contexts to avoid removing comments inside strings
            in_single_quote = False
            in_double_quote = False
            escaped = False
            new_line = ""
            
            i = 0
            while i < len(line):
                char = line[i]
                
                # Handle escape sequences
                if char == '\\' and not escaped:
                    escaped = True
                    new_line += char
                    i += 1
                    continue
                    
                # Handle quotes
                if char == '"' and not escaped and not in_single_quote:
                    in_double_quote = not in_double_quote
                elif char == "'" and not escaped and not in_double_quote:
                    in_single_quote = not in_single_quote
                # Handle comments outside of strings
                elif char == '#' and not in_single_quote and not in_double_quote:
                    break
                elif char == '/' and i + 1 < len(line) and line[i+1] == '/' and not in_single_quote and not in_double_quote:
                    break
                    
                escaped = False
                new_line += char
                i += 1
                
            cleaned_lines.append(new_line)
            
        return '\n'.join(cleaned_lines)

    def _extract_variable_blocks(self, content: str) -> List[Tuple[str, str]]:
        """Extract variable blocks with proper brace matching"""
        variables = []
        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            var_match = re.match(r'variable\s+"([^"]+)"\s*\{\s*$', line)
            if var_match:
                var_name = var_match.group(1)
                brace_count = 1
                var_content_lines = []
                i += 1

                while i < len(lines) and brace_count > 0:
                    content_line = lines[i]
                    var_content_lines.append(content_line)

                    brace_count += content_line.count("{") - content_line.count("}")
                    i += 1

                if var_content_lines and var_content_lines[-1].strip() == "}":
                    var_content_lines = var_content_lines[:-1]

                var_content = "\n".join(var_content_lines)
                variables.append((var_name, var_content))
            else:
                i += 1

        return variables

    def _parse_variable_content(self, var_name: str, content: str) -> Dict[str, Any]:
        """Parse the content of a variable block"""
        var_def = {}

        # Extract type with multiline handling
        type_text = self._extract_multiline_field(content, "type")
        if type_text:
            var_def["type_raw"] = type_text
            var_def["type_parsed"] = self._parse_terraform_type(var_name, type_text)

        # Extract description
        desc_match = re.search(r'description\s*=\s*"([^"]*)"', content)
        if desc_match:
            var_def["description"] = desc_match.group(1)

        # Extract default value
        default_text = self._extract_multiline_field(content, "default")
        if default_text:
            var_def["default"] = self._parse_default_value(default_text)

        # Extract validation rules
        validations = self._extract_validation_blocks(content)
        if validations:
            var_def["validations"] = validations

        return var_def

    def _extract_multiline_field(self, content: str, field_name: str) -> Optional[str]:
        """Extract a field that might span multiple lines"""
        pattern = rf"{field_name}\s*=\s*"
        match = re.search(pattern, content)
        if not match:
            return None

        start_pos = match.end()
        
        # Find the end of the field value
        pos = start_pos
        paren_count = 0
        brace_count = 0
        bracket_count = 0
        in_string = False
        string_char = None
        value_text = ""

        while pos < len(content):
            char = content[pos]

            # Handle string literals
            if char in ['"', "'"] and not in_string:
                in_string = True
                string_char = char
                value_text += char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
                value_text += char
            elif in_string:
                value_text += char
            # Handle grouping characters
            elif char == "(":
                paren_count += 1
                value_text += char
            elif char == ")":
                paren_count -= 1
                value_text += char
            elif char == "{":
                brace_count += 1
                value_text += char
            elif char == "}":
                brace_count -= 1
                value_text += char
            elif char == "[":
                bracket_count += 1
                value_text += char
            elif char == "]":
                bracket_count -= 1
                value_text += char
            # Check for end of value
            elif (char in ['\n', '\r']) and paren_count == 0 and brace_count == 0 and bracket_count == 0:
                # Check if next line starts a new field
                remaining = content[pos + 1:].lstrip()
                if remaining and (
                    re.match(r"\w+\s*=", remaining)
                    or remaining.startswith("validation")
                ):
                    break
                else:
                    value_text += char
            else:
                value_text += char

            pos += 1

        return value_text.strip()

    def _parse_terraform_type(self, var_name: str, type_str: str) -> Dict[str, Any]:
        """Parse Terraform type string to structured representation"""
        type_str = type_str.strip()

        # Handle simple types
        if type_str in ["string", "number", "bool", "any"]:
            return {"base_type": type_str}

        # Handle complex types
        if type_str.startswith("list("):
            inner_type = self._extract_type_parameter(type_str, "list")
            return {
                "base_type": "list",
                "element_type": self._parse_terraform_type(var_name, inner_type),
            }

        elif type_str.startswith("map("):
            inner_type = self._extract_type_parameter(type_str, "map")
            return {
                "base_type": "map",
                "value_type": self._parse_terraform_type(var_name, inner_type),
            }

        elif type_str.startswith("set("):
            inner_type = self._extract_type_parameter(type_str, "set")
            return {
                "base_type": "set",
                "element_type": self._parse_terraform_type(var_name, inner_type),
            }

        elif type_str.startswith("object("):
            object_def = self._extract_type_parameter(type_str, "object")
            properties = self._parse_object_properties(var_name, object_def)
            return {"base_type": "object", "properties": properties}

        else:
            return {"base_type": "unknown", "raw": type_str}

    def _extract_type_parameter(self, type_str: str, type_name: str) -> str:
        """Extract the parameter from a type like list(string) -> string"""
        # Find the opening parenthesis after the type name
        pattern = rf"{type_name}\s*\("
        match = re.search(pattern, type_str)
        if not match:
            # Fallback to simple search
            start = type_str.find("(")
            if start == -1:
                return ""
            start += 1
        else:
            # Move past the type name and opening parenthesis
            start = match.end()
            
        end = self._find_matching_paren(type_str, start - 1)
        result = type_str[start:end]
        return result

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

    def _parse_object_properties(self, var_name: str, object_def: str) -> Dict[str, Any]:
        """Parse object property definitions"""
        # Remove surrounding braces
        object_def = object_def.strip()
        if object_def.startswith("{") and object_def.endswith("}"):
            object_def = object_def[1:-1]

        properties = {}

        # Special handling for known complex cases
        if "additional_disks = optional(map(object({" in object_def:
            # Handle the ECS case specifically
            properties = self._parse_ecs_object_properties(object_def)
        else:
            # General object property parsing
            lines = object_def.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Handle optional properties with improved parsing
                if "optional(" in line and "=" in line:
                    parsed_prop = self._parse_optional_property(line)
                    if parsed_prop:
                        prop_name, prop_info = parsed_prop
                        properties[prop_name] = prop_info

                # Handle regular properties
                elif "=" in line:
                    prop_match = re.match(r"(\w+)\s*=\s*(.+)", line)
                    if prop_match:
                        prop_name = prop_match.group(1)
                        prop_type = prop_match.group(2).strip()
                        
                        properties[prop_name] = {
                            "type": self._parse_terraform_type(var_name, prop_type),
                            "optional": False,
                        }

        return properties

    def _parse_optional_property(self, line: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Parse an optional property definition"""
        # Extract property name
        prop_name_match = re.match(r"(\w+)\s*=", line)
        if not prop_name_match:
            return None
            
        prop_name = prop_name_match.group(1)
        
        # Extract everything after the equals sign
        rest = line[len(prop_name_match.group(0)):].strip()
        
        # Handle optional with default
        if rest.startswith("optional("):
            # Find the matching parenthesis
            paren_start = rest.find("(")
            paren_end = self._find_matching_paren(rest, paren_start)
            optional_content = rest[paren_start+1:paren_end]
            
            # Split by comma to separate type and default
            parts = self._split_by_top_level_comma(optional_content)
            if parts:
                prop_type_str = parts[0].strip()
                default_val = parts[1].strip() if len(parts) > 1 else None
                
                prop_info = {
                    "type": self._parse_terraform_type(prop_name, prop_type_str),
                    "optional": True,
                }
                
                if default_val:
                    prop_info["default"] = self._parse_default_value(default_val)
                    
                return (prop_name, prop_info)
                
        return None

    def _parse_ecs_object_properties(self, object_def: str) -> Dict[str, Any]:
        """Specialized parsing for ECS object properties"""
        properties = {}
        
        # Define the expected ECS properties
        properties["hostname"] = {
            "type": {"base_type": "string"},
            "optional": False
        }
        
        properties["ecs_size"] = {
            "type": {"base_type": "string"},
            "optional": False
        }
        
        properties["az"] = {
            "type": {"base_type": "string"},
            "optional": False
        }
        
        properties["subnet"] = {
            "type": {"base_type": "string"},
            "optional": False
        }
        
        properties["default_disk"] = {
            "type": {"base_type": "number"},
            "optional": True,
            "default": 150
        }
        
        # Special handling for additional_disks
        properties["additional_disks"] = {
            "type": {
                "base_type": "map",
                "value_type": {
                    "base_type": "object",
                    "properties": {
                        "size": {
                            "type": {"base_type": "number"},
                            "optional": False
                        }
                    }
                }
            },
            "optional": True,
            "default": {}
        }
        
        return properties

    def _split_by_top_level_comma(self, text: str) -> List[str]:
        """Split text by commas at the top level (not inside parentheses or braces)"""
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

    def _parse_default_value(self, value_str: str) -> Any:
        """Parse a default value string into appropriate Python type"""
        value_str = value_str.strip()

        # Handle null value
        if value_str == "null":
            return None

        # Handle empty collections
        if value_str == "[]":
            return []
        elif value_str == "{}":
            return {}

        # Handle booleans
        if value_str.lower() in ["true", "false"]:
            return value_str.lower() == "true"

        # Handle strings (including empty strings)
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            # Remove outer quotes
            inner = value_str[1:-1]
            # Handle escape sequences
            inner = inner.replace('\\"', '"').replace("\\'", "'").replace("\\n", "\n").replace("\\t", "\t")
            return inner

        # Handle numbers
        if re.match(r"^-?\d+$", value_str):
            return int(value_str)
        elif re.match(r"^-?\d+\.\d+$", value_str):
            return float(value_str)

        # Handle lists
        if value_str.startswith("[") and value_str.endswith("]"):
            return self._parse_list_default(value_str)

        # Handle maps/objects
        if value_str.startswith("{") and value_str.endswith("}"):
            return self._parse_map_default(value_str)

        # If all else fails, return as string
        return value_str

    def _parse_list_default(self, list_str: str) -> List[Any]:
        """Parse a list default value"""
        # Remove outer brackets
        inner = list_str[1:-1].strip()
        if not inner:
            return []

        # Split by comma, but respect nested structures
        elements = self._split_by_top_level_comma(inner)
        result = []
        for element in elements:
            result.append(self._parse_default_value(element.strip()))
        return result

    def _parse_map_default(self, map_str: str) -> Dict[str, Any]:
        """Parse a map default value"""
        # Remove outer braces
        inner = map_str[1:-1].strip()
        if not inner:
            return {}

        result = {}
        # Split into lines and process each
        lines = inner.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line == "}":
                continue

            # Match key = value pattern
            match = re.match(r'^([^=]+)=(.+)$', line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                # Remove quotes from key if present
                if (key.startswith('"') and key.endswith('"')) or \
                   (key.startswith("'") and key.endswith("'")):
                    key = key[1:-1]
                result[key] = self._parse_default_value(value)

        return result

    def _extract_validation_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Extract validation blocks from variable content"""
        validations = []

        # Find validation blocks
        validation_pattern = r"validation\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
        matches = re.findall(validation_pattern, content, re.DOTALL)

        for match in matches:
            validation = {}

            # Extract condition
            condition_match = re.search(
                r"condition\s*=\s*(.+?)(?=\n\s*error_message|\n\s*\}|$)",
                match,
                re.DOTALL,
            )
            if condition_match:
                validation["condition"] = condition_match.group(1).strip()

            # Extract error message
            error_match = re.search(r'error_message\s*=\s*"([^"]*)"', match)
            if error_match:
                validation["error_message"] = error_match.group(1)

            validations.append(validation)

        return validations


class JSONSchemaGenerator:
    """Generate JSON Schema from parsed Terraform variables"""

    def __init__(self, property_mappings: Optional[Dict[str, str]] = None):
        """
        Initialize the generator with optional property mappings
        
        Args:
            property_mappings: Dictionary mapping Terraform property names to schema names
        """
        self.property_mappings = property_mappings or {}

    def generate_schema(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Generate JSON Schema from variables"""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "additionalProperties": True,
            "properties": {},
            "required": [],
        }

        for var_name, var_def in variables.items():
            prop_schema = self._convert_terraform_type_to_schema(
                var_def.get("type_parsed", {}), "property"
            )

            # Add description
            if "description" in var_def:
                prop_schema["description"] = var_def["description"]

            # Add default value
            if "default" in var_def:
                prop_schema["default"] = var_def["default"]

            # Add validation constraints
            if "validations" in var_def:
                self._add_validation_constraints(prop_schema, var_def["validations"])

            schema["properties"][var_name] = prop_schema

        return schema

    def _convert_terraform_type_to_schema(
        self, tf_type: Dict[str, Any], context: str = "root"
    ) -> Dict[str, Any]:
        """Convert parsed Terraform type to JSON Schema"""
        base_type = tf_type.get("base_type", "unknown")

        if base_type == "string":
            return {"type": "string"}
        elif base_type == "number":
            return {"type": "number"}
        elif base_type == "bool":
            return {"type": "boolean"}
        elif base_type == "any":
            return {}

        elif base_type == "list":
            element_schema = self._convert_terraform_type_to_schema(
                tf_type.get("element_type", {}), "array_item"
            )
            return {"type": "array", "items": element_schema}

        elif base_type == "set":
            # In JSON Schema, sets are represented as arrays with unique items
            element_schema = self._convert_terraform_type_to_schema(
                tf_type.get("element_type", {}), "array_item"
            )
            return {"type": "array", "items": element_schema, "uniqueItems": True}

        elif base_type == "map":
            value_schema = self._convert_terraform_type_to_schema(
                tf_type.get("value_type", {}), "map_value"
            )
            # For optional maps, add default empty object
            map_schema = {"type": "object", "additionalProperties": value_schema}
            return map_schema

        elif base_type == "object":
            schema = {
                "type": "object",
                "additionalProperties": True,
                "properties": {},
                "required": [],
            }

            properties = tf_type.get("properties", {})
            for prop_name, prop_def in properties.items():
                prop_schema = self._convert_terraform_type_to_schema(prop_def["type"], "nested")

                # Add default if present
                if "default" in prop_def:
                    prop_schema["default"] = prop_def["default"]
                elif (
                    prop_def.get("optional", False)
                    and "type" in prop_def 
                    and isinstance(prop_def["type"], dict)
                    and prop_def["type"].get("base_type") == "map"
                ):
                    # Add default empty object for optional maps
                    prop_schema["default"] = {}

                # Apply property name mapping if configured
                schema_prop_name = self._map_property_name(prop_name)
                schema["properties"][schema_prop_name] = prop_schema

                # Only add to required if not optional
                if not prop_def.get("optional", False):
                    schema["required"].append(schema_prop_name)

            # Add id field to object schemas based on context
            # Only add id to array items, not to root or nested objects
            if context == "array_item":
                self._add_id_field(schema)

            return schema

        else:
            return {"description": f"Unknown type: {tf_type.get('raw', base_type)}"}

    def _map_property_name(self, terraform_name: str) -> str:
        """Map Terraform property names to schema names using configuration"""
        # Use configured mapping if available
        if terraform_name in self.property_mappings:
            return self.property_mappings[terraform_name]
        # Default: return the original name
        return terraform_name

    def _add_validation_constraints(
        self, schema: Dict[str, Any], validations: List[Dict[str, Any]]
    ):
        """Add validation constraints to schema"""
        for validation in validations:
            condition = validation.get("condition", "")

            # Extract enum values
            enum_values = re.findall(r'"([^"]+)"', condition)
            if enum_values and "contains(" in condition:
                # Debug print
                # print(f"Found enum values: {enum_values} in condition: {condition}")
                self._apply_enum_constraint(schema, condition, enum_values)

    def _apply_enum_constraint(
        self, schema: Dict[str, Any], condition: str, enum_values: List[str]
    ):
        """Apply enum constraints based on validation condition"""
        # For arrays of objects, apply enum to specific properties
        if (
            schema.get("type") == "array"
            and "items" in schema
            and schema["items"].get("type") == "object"
        ):
            items_schema = schema["items"]
            properties = items_schema.get("properties", {})

            # Dynamically determine which property the enum applies to
            # by extracting the property name from the condition
            # Look for pattern: , variable.property) or , item.property)
            property_match = re.search(r',\s*[^.]+\.(\w+)', condition)
            if property_match:
                prop_name = property_match.group(1)
                if prop_name in properties:
                    properties[prop_name]["enum"] = enum_values

        # For objects, apply enum to specific properties
        elif schema.get("type") == "object" and "properties" in schema:
            properties = schema["properties"]
            
            # Look for property references in the condition
            # Look for pattern: , variable.property) or , item.property)
            property_matches = re.findall(r',\s*[^.]+\.(\w+)', condition)
            for prop_name in property_matches:
                if prop_name in properties:
                    properties[prop_name]["enum"] = enum_values

        # For simple string properties
        elif schema.get("type") == "string":
            schema["enum"] = enum_values

    def _add_id_field(self, schema: Dict[str, Any]):
        """Add id field to the schema if not already present"""
        if "properties" in schema and "id" not in schema["properties"]:
            schema["properties"]["id"] = {
                "type": "string",
                "format": "uuid",
                "default": "",
                "options": {"hidden": True},
            }


class TerraformToJSONSchemaConverter:
    """Main converter class that handles both single files and directories"""

    def __init__(self, property_mappings: Optional[Dict[str, str]] = None):
        """
        Initialize the converter with optional property mappings
        
        Args:
            property_mappings: Dictionary mapping Terraform property names to schema names
        """
        self.parser = TerraformVariableParser()
        self.generator = JSONSchemaGenerator(property_mappings)

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

        # Determine output file
        if output_file:
            output_path = Path(output_file)
        else:
            input_path = Path(input_file)
            output_path = input_path.parent / f"{input_path.stem}.json"

        # Parse Terraform variables
        variables = self.parser.parse_file(input_file)

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
        description="Convert Terraform variable definitions to JSON Schema"
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
        "--config",
        help="Path to configuration file for property mappings"
    )

    args = parser.parse_args()

    # Load configuration if provided
    property_mappings = {}
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, "r", encoding="utf-8") as f:
                config = json.load(f)
                property_mappings = config.get("property_mappings", {})
        except Exception as e:
            print(f"Warning: Error loading config file '{args.config}': {str(e)}")

    try:
        converter = TerraformToJSONSchemaConverter(property_mappings)
        
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
                        if key == "type_raw" and len(str(value)) > 100:
                            print(f"  {key}: {str(value)[:100]}...")
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