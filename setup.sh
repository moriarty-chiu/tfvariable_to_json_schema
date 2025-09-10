#!/bin/bash

# Setup script for Terraform Variable to JSON Schema Converter
# This script sets up a Python virtual environment and installs dependencies

set -e  # Exit on any error

PROJECT_NAME="tfvariable_to_json_schema"
VENV_DIR="venv"
PYTHON_CMD="python3"

echo "🚀 Setting up $PROJECT_NAME..."

# Check if Python 3 is available
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.7 or later and try again"
    exit 1
fi

# Display Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "✅ Found $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv $VENV_DIR
    echo "✅ Virtual environment created in $VENV_DIR/"
else
    echo "✅ Virtual environment already exists in $VENV_DIR/"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source $VENV_DIR/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Dependencies installed successfully"
else
    echo "⚠️  No requirements.txt found, skipping dependency installation"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To activate the virtual environment manually:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To run the scripts:"
echo "  # Convert Terraform variables to JSON Schema"
echo "  python scripts/terraform_to_json_schema.py input.tf"
echo ""
echo "  # Bundle JSON schemas with reference resolution"
echo "  python schemas/bundle_schema.py input_schema.json"
echo ""
echo "To deactivate the virtual environment:"
echo "  deactivate"
echo ""
echo "Happy coding! 🐍"