#!/usr/bin/env python3
"""
JSON Schema Bundle Generator

This script resolves JSON schema references and bundles them into a single schema file.
Optimized for better error handling, flexibility, and maintainability.
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Union, Optional

# Optional dependency with fallback
try:
    import jsonref
except ImportError:
    print("Warning: jsonref library not found. Install with: pip install jsonref")
    jsonref = None


class SchemaBundler:
    """JSON Schema bundler with reference resolution"""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize the bundler with optional base path"""
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.base_uri = f"file://{self.base_path.absolute()}/"
    
    def to_plain(self, obj: Any) -> Any:
        """
        Recursively clean JsonRef or other non-serializable objects into normal dicts and lists.
        
        Args:
            obj: Object to clean (dict, list, or primitive)
            
        Returns:
            Cleaned object with resolved references
        """
        if isinstance(obj, dict):
            return {k: self.to_plain(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.to_plain(v) for v in obj]
        else:
            return obj
    
    def load_schema(self, schema_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load and validate a JSON schema file.
        
        Args:
            schema_path: Path to the schema file
            
        Returns:
            Parsed schema dictionary
            
        Raises:
            FileNotFoundError: If schema file doesn't exist
            json.JSONDecodeError: If schema file is invalid JSON
        """
        schema_file = Path(schema_path)
        
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")
        
        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                content = f.read()
                return json.loads(content)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in {schema_file}: {e.msg}", e.doc, e.pos)
    
    def resolve_references(self, schema_content: str) -> Dict[str, Any]:
        """
        Resolve JSON schema references using jsonref library.
        
        Args:
            schema_content: Raw JSON schema content as string
            
        Returns:
            Resolved schema dictionary
            
        Raises:
            ImportError: If jsonref library is not available
            Exception: If reference resolution fails
        """
        if jsonref is None:
            raise ImportError("jsonref library is required for reference resolution")
        
        try:
            resolved = jsonref.loads(schema_content, base_uri=self.base_uri, jsonschema=True)
            return self.to_plain(resolved)
        except Exception as e:
            raise Exception(f"Failed to resolve schema references: {str(e)}")
    
    def flatten_nested_properties(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten unnecessarily nested properties in the schema.
        
        This addresses cases where a property contains a nested structure with
        the same property name, which can be simplified.
        
        Args:
            schema: The schema to process
            
        Returns:
            Schema with flattened properties
        """
        if "properties" not in schema:
            return schema
        
        properties = schema["properties"]
        flattened_properties = {}
        
        for prop_name, prop_value in properties.items():
            if (
                isinstance(prop_value, dict)
                and "properties" in prop_value
                and prop_name in prop_value["properties"]
            ):
                # Flatten the nested property
                flattened_properties[prop_name] = prop_value["properties"][prop_name]
            else:
                # Keep the property as-is
                flattened_properties[prop_name] = prop_value
        
        schema["properties"] = flattened_properties
        return schema
    
    def set_all_properties_required(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set all top-level properties as required.
        
        Args:
            schema: The schema to modify
            
        Returns:
            Schema with all properties marked as required
        """
        if "properties" in schema:
            schema["required"] = list(schema["properties"].keys())
        return schema
    
    def bundle_schema(
        self, 
        input_file: Union[str, Path], 
        output_file: Union[str, Path],
        flatten_properties: bool = True,
        set_required: bool = True
    ) -> None:
        """
        Bundle a JSON schema with reference resolution.
        
        Args:
            input_file: Path to input schema file
            output_file: Path to output bundled schema file
            flatten_properties: Whether to flatten nested properties
            set_required: Whether to set all properties as required
            
        Raises:
            FileNotFoundError: If input file doesn't exist
            Exception: If bundling process fails
        """
        input_path = Path(input_file)
        output_path = Path(output_file)
        
        # Ensure input file exists
        if not input_path.exists():
            raise FileNotFoundError(f"Input schema file not found: {input_path}")
        
        try:
            # Read the input schema
            with open(input_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Resolve references if jsonref is available
            if jsonref is not None:
                schema = self.resolve_references(content)
            else:
                # Fallback to simple JSON loading
                schema = json.loads(content)
                print("Warning: References not resolved due to missing jsonref library")
            
            # Apply optional transformations
            if flatten_properties:
                schema = self.flatten_nested_properties(schema)
            
            if set_required:
                schema = self.set_all_properties_required(schema)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the bundled schema
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully bundled schema: {input_path} -> {output_path}")
            
        except Exception as e:
            raise Exception(f"Failed to bundle schema: {str(e)}")


def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(
        description="Bundle JSON schemas with reference resolution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s schema.json                    # Bundle to schema_bundled.json
  %(prog)s schema.json -o output.json     # Bundle to specific output file
  %(prog)s schema.json --no-flatten       # Skip property flattening
  %(prog)s schema.json --no-required      # Don't set all properties as required
        """
    )
    
    parser.add_argument(
        "input",
        help="Input JSON schema file path"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output bundled schema file path (default: input_bundled.json)"
    )
    
    parser.add_argument(
        "--no-flatten",
        action="store_true",
        help="Skip flattening of nested properties"
    )
    
    parser.add_argument(
        "--no-required",
        action="store_true",
        help="Don't automatically set all properties as required"
    )
    
    parser.add_argument(
        "--base-path",
        help="Base path for resolving relative schema references"
    )
    
    args = parser.parse_args()
    
    try:
        # Determine output file
        if args.output:
            output_file = args.output
        else:
            input_path = Path(args.input)
            output_file = input_path.parent / f"{input_path.stem}_bundled.json"
        
        # Create bundler
        bundler = SchemaBundler(args.base_path)
        
        # Bundle the schema
        bundler.bundle_schema(
            input_file=args.input,
            output_file=output_file,
            flatten_properties=not args.no_flatten,
            set_required=not args.no_required
        )
        
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())