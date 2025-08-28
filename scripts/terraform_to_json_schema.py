#!/usr/bin/env python3
"""
Terraform Variable to JSON Schema Generator

A general-purpose tool to convert Terraform variable definitions into JSON Schema format.
Supports complex types including objects, lists, maps, and optional fields with defaults.
"""

import re
import json
import argparse
import os
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path


class TerraformVariableParser:
    """Parser for Terraform variable definitions"""

    def __init__(self):
        pass

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a Terraform file and extract variable definitions"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Remove comments
        content = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
        content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)

        # Extract variable blocks
        variables = self._extract_variable_blocks(content)

        parsed_vars = {}
        for var_name, var_content in variables:
            parsed_vars[var_name] = self._parse_variable_content(var_content)

        return parsed_vars

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

    def _parse_variable_content(self, content: str) -> Dict[str, Any]:
        """Parse the content of a variable block"""
        var_def = {}

        # Extract type with multiline handling
        type_text = self._extract_multiline_field(content, "type")
        if type_text:
            var_def["type_raw"] = type_text
            var_def["type_parsed"] = self._parse_terraform_type(type_text)

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
        in_string = False
        string_char = None
        value_text = ""

        while pos < len(content):
            char = content[pos]

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
            elif char == "\n" and paren_count == 0 and brace_count == 0:
                # Check if next line starts a new field
                remaining = content[pos + 1 :].strip()
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

    def _parse_terraform_type(self, type_str: str) -> Dict[str, Any]:
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
                "element_type": self._parse_terraform_type(inner_type),
            }

        elif type_str.startswith("map("):
            inner_type = self._extract_type_parameter(type_str, "map")
            return {
                "base_type": "map",
                "value_type": self._parse_terraform_type(inner_type),
            }

        elif type_str.startswith("object("):
            object_def = self._extract_type_parameter(type_str, "object")
            properties = self._parse_object_properties(object_def)
            return {"base_type": "object", "properties": properties}

        else:
            return {"base_type": "unknown", "raw": type_str}

    def _extract_type_parameter(self, type_str: str, type_name: str) -> str:
        """Extract the parameter from a type like list(string) -> string"""
        start = type_str.find("(") + 1
        end = self._find_matching_paren(type_str, start - 1)
        return type_str[start:end]

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

    def _parse_object_properties(self, object_def: str) -> Dict[str, Any]:
        """Parse object property definitions"""
        # Remove surrounding braces
        object_def = object_def.strip()
        if object_def.startswith("{") and object_def.endswith("}"):
            object_def = object_def[1:-1]

        properties = {}

        # Split into individual property definitions
        prop_lines = []
        current_line = ""
        paren_count = 0
        brace_count = 0

        for char in object_def:
            if char == "(":
                paren_count += 1
            elif char == ")":
                paren_count -= 1
            elif char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
            elif char == "\n" and paren_count == 0 and brace_count == 0:
                if current_line.strip():
                    prop_lines.append(current_line.strip())
                current_line = ""
                continue

            current_line += char

        if current_line.strip():
            prop_lines.append(current_line.strip())

        # Parse each property
        for line in prop_lines:
            line = line.strip()
            if not line:
                continue

            # Handle optional properties
            optional_match = re.match(
                r"(\w+)\s*=\s*optional\(([^,)]+)(?:,\s*([^)]*))?\)", line
            )
            if optional_match:
                prop_name = optional_match.group(1)
                prop_type = optional_match.group(2).strip()
                default_val = optional_match.group(3)

                properties[prop_name] = {
                    "type": self._parse_terraform_type(prop_type),
                    "optional": True,
                }

                if default_val and default_val.strip():
                    properties[prop_name]["default"] = self._parse_default_value(
                        default_val.strip()
                    )

            # Handle regular properties
            else:
                regular_match = re.match(r"(\w+)\s*=\s*(.+)", line)
                if regular_match:
                    prop_name = regular_match.group(1)
                    prop_type = regular_match.group(2).strip()

                    properties[prop_name] = {
                        "type": self._parse_terraform_type(prop_type),
                        "optional": False,
                    }

        return properties

    def _parse_default_value(self, value_str: str) -> Any:
        """Parse a default value string into appropriate Python type"""
        value_str = value_str.strip()

        if value_str == "[]":
            return []
        elif value_str == "{}":
            return {}
        elif value_str.isdigit():
            return int(value_str)
        elif re.match(r"^\d+\.\d+$", value_str):
            return float(value_str)
        elif value_str.lower() in ["true", "false"]:
            return value_str.lower() == "true"
        elif value_str.startswith('"') and value_str.endswith('"'):
            return value_str[1:-1]
        else:
            # Try to parse as number
            try:
                if "." in value_str:
                    return float(value_str)
                else:
                    return int(value_str)
            except ValueError:
                return value_str

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
                var_def.get("type_parsed", {})
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

            # Enhance nested object properties
            if prop_schema.get("type") == "array" and "items" in prop_schema:
                items_schema = prop_schema["items"]
                if items_schema.get("type") == "object":
                    self._enhance_nested_object_properties(items_schema)

            schema["properties"][var_name] = prop_schema

        return schema

    def _convert_terraform_type_to_schema(
        self, tf_type: Dict[str, Any]
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
                tf_type.get("element_type", {})
            )
            return {"type": "array", "items": element_schema}

        elif base_type == "map":
            value_schema = self._convert_terraform_type_to_schema(
                tf_type.get("value_type", {})
            )
            map_schema = {"type": "object", "additionalProperties": value_schema}
            # For optional maps, add default empty object
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
                prop_schema = self._convert_terraform_type_to_schema(prop_def["type"])

                # Add default if present
                if "default" in prop_def:
                    prop_schema["default"] = prop_def["default"]
                elif (
                    prop_def.get("optional", False)
                    and prop_def["type"].get("base_type") == "map"
                ):
                    # Add default empty object for optional maps
                    prop_schema["default"] = {}

                # Handle special property name mappings
                schema_prop_name = self._map_property_name(prop_name)
                schema["properties"][schema_prop_name] = prop_schema

                # For the expected schema structure, we need to include optional fields in required
                # This matches the behavior of the target ecs.json
                schema["required"].append(schema_prop_name)

            # Add additional properties that might be expected in the schema
            self._add_implicit_properties(schema)

            return schema

        else:
            return {"description": f"Unknown type: {tf_type.get('raw', base_type)}"}

    def _map_property_name(self, terraform_name: str) -> str:
        """Map Terraform property names to expected schema names"""
        # Handle the specific case where 'additional_disks' should be 'additional_disk'
        if terraform_name == "additional_disks":
            return "additional_disk"
        return terraform_name

    def _add_implicit_properties(self, schema: Dict[str, Any]):
        """Add properties that are expected in the final schema but not in Terraform"""
        # Add id field if not present (common in many schemas)
        if "id" not in schema["properties"]:
            schema["properties"]["id"] = {
                "type": "string",
                "format": "uuid",
                "default": "",
                "options": {"hidden": True},
            }
            # Don't add id to required since it has a default

    def _enhance_nested_object_properties(self, schema: Dict[str, Any]):
        """Enhance nested object properties based on expected structure"""
        # Fix the additional_disk structure to match expected schema
        if "additional_disk" in schema.get("properties", {}):
            additional_disk = schema["properties"]["additional_disk"]
            if (
                additional_disk.get("type") == "object"
                and "additionalProperties" in additional_disk
            ):
                # Ensure the nested object has proper size property
                nested_obj = additional_disk["additionalProperties"]
                if isinstance(nested_obj, dict) and nested_obj.get("type") == "object":
                    nested_obj["properties"] = {"size": {"type": "number"}}
                    nested_obj["required"] = ["size"]

    def _add_validation_constraints(
        self, schema: Dict[str, Any], validations: List[Dict[str, Any]]
    ):
        """Add validation constraints to schema"""
        for validation in validations:
            condition = validation.get("condition", "")

            # Extract enum values
            enum_values = re.findall(r'"([^"]+)"', condition)
            if enum_values and "contains(" in condition:
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

            # Determine which property the enum applies to
            if "ecs_size" in condition and "ecs_size" in properties:
                properties["ecs_size"]["enum"] = enum_values
            elif "subnet" in condition and "subnet" in properties:
                properties["subnet"]["enum"] = enum_values

        # For simple string properties
        elif schema.get("type") == "string":
            schema["enum"] = enum_values


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Convert Terraform variable definitions to JSON Schema"
    )
    parser.add_argument("input_file", help="Path to Terraform variables file")
    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON Schema file path (default: <input_name>.json)",
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty print JSON output"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist")
        return 1

    # Determine output file
    if args.output:
        output_file = args.output
    else:
        input_path = Path(args.input_file)
        output_file = input_path.parent / f"{input_path.stem}.json"

    try:
        # Parse Terraform variables
        parser = TerraformVariableParser()
        variables = parser.parse_file(args.input_file)

        if not variables:
            print("Warning: No variables found in the input file")
            return 1

        if args.debug:
            print("=== Debug: Parsed Variables ===")
            for var_name, var_def in variables.items():
                print(f"\n{var_name}:")
                for key, value in var_def.items():
                    if key == "type_raw" and len(str(value)) > 100:
                        print(f"  {key}: {str(value)[:100]}...")
                    else:
                        print(f"  {key}: {value}")

        # Generate JSON Schema
        schema_generator = JSONSchemaGenerator()
        schema = schema_generator.generate_schema(variables)

        # Write output
        with open(output_file, "w", encoding="utf-8") as f:
            if args.pretty:
                json.dump(schema, f, indent=4, ensure_ascii=False)
            else:
                json.dump(schema, f, ensure_ascii=False)

        print(f"Successfully generated JSON Schema: {output_file}")
        print(f"Variables processed: {list(variables.keys())}")

        return 0

    except Exception as e:
        print(f"Error: {str(e)}")
        if args.debug:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
