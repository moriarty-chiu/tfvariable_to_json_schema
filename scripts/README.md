# Terraform Variable to JSON Schema Generator

A general-purpose tool to convert Terraform variable definitions into JSON Schema format. This tool supports processing single files or entire directories and automatically extracts enum values from validation rules.

## Features

- Converts Terraform variables to JSON Schema format
- Supports all Terraform variable types:
  - Simple types: `string`, `number`, `bool`, `any`
  - Complex types: `list()`, `map()`, `set()`, `tuple()`, `object()`
  - Nested complex types
- Processes single files or entire directories
- Automatically extracts enum values from validation rules
- Improved error handling and debugging

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd tfvariable_to_json_schema/scripts

# Ensure you have Python 3 installed
python3 --version
```

## Usage

```bash
python3 terraform_to_json_schema.py <input> [options]
```

### Arguments

- `input`: Path to Terraform variables file or directory containing variables.tf files (required)
- `-o, --output`: Output JSON Schema file or directory path
- `--pretty`: Pretty print JSON output (always enabled in this version)
- `--debug`: Enable debug output

### Examples

```bash
# Convert a single variables.tf file
python3 terraform_to_json_schema.py ../modules/ecs/variables.tf

# Convert with custom output file
python3 terraform_to_json_schema.py ../modules/ecs/variables.tf -o schema.json

# Convert all variables.tf files in a directory
python3 terraform_to_json_schema.py ../modules

# Convert directory with custom output directory
python3 terraform_to_json_schema.py ../modules -o ../schemas

# Debug mode to see parsed variables
python3 terraform_to_json_schema.py ../modules/ecs/variables.tf --debug
```

## Supported Terraform Types

- Simple types: `string`, `number`, `bool`, `any`
- Complex types:
  - Lists: `list(string)`, `list(object({...}))`, etc.
  - Maps: `map(string)`, `map(object({...}))`, etc.
  - Sets: `set(string)`, `set(object({...}))`, etc.
  - Tuples: `tuple([string, number, bool])`, etc.
  - Objects: `object({ property = type })`
- Optional properties with defaults: `optional(type, default)`

## How It Works

### TerraformVariableParser

The `TerraformVariableParser` class handles parsing Terraform variable definitions:

1. Reads and processes the input file or directory
2. Removes comments while preserving string contents
3. Extracts variable blocks with proper brace matching
4. Parses each variable's:
   - Type (including complex nested types)
   - Description
   - Default values
   - Validation rules

### JSONSchemaGenerator

The `JSONSchemaGenerator` class converts parsed Terraform variables to JSON Schema:

1. Generates a base JSON Schema structure
2. Converts Terraform types to JSON Schema types:
   - `string` → `"type": "string"`
   - `number` → `"type": "number"`
   - `bool` → `"type": "boolean"`
   - `list(...)` → `"type": "array"` with `items` property
   - `set(...)` → `"type": "array"` with `items` property and `uniqueItems: true`
   - `tuple(...)` → `"type": "array"` with array of `items` schemas
   - `map(...)` → `"type": "object"` with `additionalProperties`
   - `object({...})` → `"type": "object"` with `properties`
3. Automatically extracts and applies enum constraints from validation rules
4. Adds id fields to appropriate object schemas

## Development

### Code Structure

- `TerraformVariableParser`: Handles parsing of Terraform files
- `JSONSchemaGenerator`: Converts parsed variables to JSON Schema
- `TerraformToJSONSchemaConverter`: Main converter class that handles both single files and directories
- `main()`: Command-line interface and entry point

### Extending Functionality

To add support for new Terraform types or modify the JSON Schema output:

1. Modify `_parse_terraform_type()` in `TerraformVariableParser` to handle new types
2. Update `_convert_terraform_type_to_schema()` in `JSONSchemaGenerator` to convert new types to JSON Schema

## License

MIT