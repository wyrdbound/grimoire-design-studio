# GRIMOIRE Design Studio

[![Tests](https://github.com/wyrdbound/grimoire-design-studio/workflows/Tests/badge.svg)](https://github.com/wyrdbound/grimoire-design-studio/actions/workflows/test.yml)
[![Code Quality](https://github.com/wyrdbound/grimoire-design-studio/workflows/Code%20Quality/badge.svg)](https://github.com/wyrdbound/grimoire-design-studio/actions/workflows/quality.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive design studio for creating, editing, and testing GRIMOIRE system YAML definitions.

## Overview

GRIMOIRE Design Studio is a desktop application built with PyQt6 that provides a complete integrated development environment for GRIMOIRE systems. It supports visual editing of models, flows, compendiums, and other GRIMOIRE components, along with real-time validation and flow execution capabilities.

## Features

- **Project Management**: Create and manage GRIMOIRE system projects
- **Visual Editors**:
  - YAML editor with syntax highlighting and validation
  - Visual flow designer for creating and editing flows
  - Model designer with attribute management
  - Compendium browser for content management
- **Real-time Validation**: Comprehensive YAML and business logic validation
- **Flow Execution**: Test flows with full Prefect integration
- **Object Instantiation**: Integration with grimoire-model for game object creation
- **Multi-platform Support**: Windows, macOS, and Linux compatibility

## Requirements

- Python 3.9 or higher
- PyQt6
- GRIMOIRE libraries (grimoire-logging, grimoire-model, grimoire-context)
- Wyrdbound libraries (wyrdbound-dice, wyrdbound-rng)

## Installation

### From Source

1. Clone the repository:

```bash
git clone https://github.com/wyrdbound/grimoire-design-studio.git
cd grimoire-design-studio
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install the package in development mode:

```bash
pip install -e .[dev]
```

### From PyPI (when available)

```bash
pip install grimoire-design-studio
```

## Usage

### Starting the Application

```bash
grimoire-studio
```

Or with debug logging:

```bash
grimoire-studio --debug
```

### Creating a New Project

1. Launch GRIMOIRE Design Studio
2. Go to **File > New Project**
3. Enter project details (name, system ID, path)
4. Click **Create Project**

### Editing GRIMOIRE Components

- **Models**: Define game object structures with attributes and validation
- **Flows**: Create step-by-step procedures for game logic
- **Compendiums**: Manage collections of game content
- **Prompts**: Design AI prompts for content generation
- **Tables**: Create lookup tables for random generation

### Testing Flows

1. Open a flow file in the editor
2. Use **Flow > Test Flow** to execute with test inputs
3. View results in the output console
4. Debug using the flow debugger tools

## Development

### Setting Up Development Environment

1. Clone and install as described above
2. Install pre-commit hooks (optional):

```bash
pre-commit install
```

### Code Quality

The project uses several tools to maintain code quality:

```bash
# Format code
ruff format src/ tests/

# Lint code
ruff check src/ tests/ --fix

# Type checking
mypy src/
```

### Testing

Run the test suite:

```bash
pytest
```

With coverage:

```bash
pytest --cov=grimoire_studio --cov-report=html
```

### Building

Build the package:

```bash
python -m build
```

## Architecture

GRIMOIRE Design Studio is built using a modular architecture:

- **Core**: Project management, configuration, validation
- **Models**: Data models for GRIMOIRE components
- **Services**: Business logic for object instantiation and flow execution
- **UI**: PyQt6-based user interface components
- **Views**: Specialized editors for different GRIMOIRE component types

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and quality checks
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [Project Wiki](https://github.com/wyrdbound/grimoire-design-studio/wiki)
- **Bug Reports**: [GitHub Issues](https://github.com/wyrdbound/grimoire-design-studio/issues)
- **Discussions**: [GitHub Discussions](https://github.com/wyrdbound/grimoire-design-studio/discussions)

## Acknowledgments

- Built on the GRIMOIRE specification
- Uses PyQt6 for the user interface
- Integrates with the broader GRIMOIRE ecosystem
