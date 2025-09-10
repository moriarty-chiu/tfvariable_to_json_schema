# Project Setup and Installation Guide

This guide will help you set up the Terraform Variable to JSON Schema Converter project with proper dependency management.

## Prerequisites

- Python 3.7 or later
- Git (for cloning the repository)

## Quick Setup

### Option 1: Automated Setup (Recommended)

Run the setup script to automatically create a virtual environment and install dependencies:

```bash
./setup.sh
```

### Option 2: Manual Setup

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   ```

2. **Activate virtual environment:**
   ```bash
   # On macOS/Linux:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Option 3: Using Makefile

```bash
# Set up everything
make setup

# Activate virtual environment
source venv/bin/activate

# Or set up development environment with additional tools
make dev-setup
```

## Dependency Overview

The project uses a tiered dependency approach:

### Core Dependencies
- `python-hcl2>=4.3.0` - Professional HCL parsing for Terraform files
- `jsonschema>=4.0.0` - JSON Schema validation and advanced features

### Optional Dependencies
- `jsonref>=1.1.0` - JSON Schema reference resolution for bundle_schema.py

### Development Dependencies (Optional)
- `pytest>=7.0.0` - Testing framework
- `black>=22.0.0` - Code formatting
- `isort>=5.10.0` - Import sorting
- `mypy>=1.0.0` - Type checking

## Usage

Once the environment is set up and activated:

### Convert Terraform Variables to JSON Schema
```bash
python scripts/terraform_to_json_schema.py input.tf
python scripts/terraform_to_json_schema.py input.tf -o output.json
```

### Bundle JSON Schemas
```bash
python schemas/bundle_schema.py input_schema.json
python schemas/bundle_schema.py input_schema.json -o bundled.json
```

## Graceful Degradation

The scripts are designed to work even without optional dependencies:

- Without `python-hcl2`: Basic HCL parsing with reduced functionality
- Without `jsonref`: Schema bundling without reference resolution
- Without `jsonschema`: Basic schema generation without validation

## Development Workflow

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Install development dependencies:**
   ```bash
   make dev-setup
   # OR
   pip install pytest black isort mypy
   ```

3. **Format code:**
   ```bash
   make format
   ```

4. **Run type checking:**
   ```bash
   make type-check
   ```

5. **Run tests:**
   ```bash
   make test
   ```

## Troubleshooting

### Virtual Environment Issues
```bash
# Remove and recreate virtual environment
make clean
make setup
```

### Permission Issues
```bash
# Make setup script executable
chmod +x setup.sh
```

### Dependency Conflicts
```bash
# Upgrade pip and reinstall
pip install --upgrade pip
pip install --force-reinstall -r requirements.txt
```

## Project Structure
```
tfvariable_to_json_schema/
├── scripts/
│   ├── terraform_to_json_schema.py    # Main conversion script
│   └── README.md                      # Script documentation
├── schemas/
│   ├── bundle_schema.py               # Schema bundling script
│   └── BUNDLE_SCHEMA_README.md        # Bundle script documentation
├── requirements.txt                   # Project dependencies
├── setup.sh                          # Automated setup script
├── Makefile                          # Development commands
└── .gitignore                        # Git ignore rules
```

## Environment Variables

No environment variables are required for basic functionality. All configuration is done through command-line arguments.

## Support

For issues related to:
- **Setup problems**: Check the troubleshooting section above
- **Dependency issues**: Ensure you're using Python 3.7+ and have an active virtual environment
- **Script usage**: Refer to the individual script documentation in their respective directories