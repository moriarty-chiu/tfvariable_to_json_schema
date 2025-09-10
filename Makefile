# Makefile for Terraform Variable to JSON Schema Converter

.PHONY: help setup install clean test lint run-example

# Default target
help:
	@echo "Terraform Variable to JSON Schema Converter"
	@echo ""
	@echo "Available targets:"
	@echo "  help        Show this help message"
	@echo "  setup       Set up virtual environment and install dependencies"
	@echo "  install     Install dependencies only (requires active venv)"
	@echo "  clean       Remove virtual environment and temporary files"
	@echo "  test        Run tests (if available)"
	@echo "  lint        Run code linting (requires dev dependencies)"
	@echo "  run-example Run example conversion (requires sample files)"
	@echo ""
	@echo "Quick start:"
	@echo "  make setup    # Set up everything"
	@echo "  source venv/bin/activate  # Activate virtual environment"
	@echo ""

# Set up virtual environment and install dependencies
setup:
	@echo "Setting up virtual environment..."
	python3 -m venv venv
	@echo "Activating virtual environment and installing dependencies..."
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	@echo "Setup complete! Run 'source venv/bin/activate' to activate the environment."

# Install dependencies only (assumes venv is already active)
install:
	pip install --upgrade pip
	pip install -r requirements.txt

# Clean up virtual environment and temporary files
clean:
	@echo "Cleaning up..."
	rm -rf venv/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.json" -path "./schemas/*" -delete
	find . -type f -name "*.json" -path "./modules/*" -delete
	@echo "Cleanup complete!"

# Run tests (placeholder for future test implementation)
test:
	@echo "Running tests..."
	@if [ -f "pytest" ]; then \
		python -m pytest tests/ -v; \
	else \
		echo "No tests found. Tests can be added to a 'tests/' directory."; \
	fi

# Run linting (requires dev dependencies)
lint:
	@echo "Running code linting..."
	@if command -v black >/dev/null 2>&1; then \
		black --check scripts/ schemas/; \
	else \
		echo "black not installed. Install with: pip install black"; \
	fi
	@if command -v isort >/dev/null 2>&1; then \
		isort --check-only scripts/ schemas/; \
	else \
		echo "isort not installed. Install with: pip install isort"; \
	fi

# Run example conversion (placeholder)
run-example:
	@echo "Running example conversion..."
	@echo "This target requires sample Terraform files."
	@echo "Create a sample variables.tf file and run:"
	@echo "  python scripts/terraform_to_json_schema.py variables.tf"

# Development helper targets
.PHONY: dev-setup format type-check

# Set up development environment with all optional dependencies
dev-setup: setup
	@echo "Installing development dependencies..."
	./venv/bin/pip install pytest pytest-cov black isort mypy
	@echo "Development setup complete!"

# Format code
format:
	@if command -v black >/dev/null 2>&1; then \
		black scripts/ schemas/; \
	else \
		echo "black not installed. Install with: pip install black"; \
	fi
	@if command -v isort >/dev/null 2>&1; then \
		isort scripts/ schemas/; \
	else \
		echo "isort not installed. Install with: pip install isort"; \
	fi

# Run type checking
type-check:
	@if command -v mypy >/dev/null 2>&1; then \
		mypy scripts/ schemas/; \
	else \
		echo "mypy not installed. Install with: pip install mypy"; \
	fi