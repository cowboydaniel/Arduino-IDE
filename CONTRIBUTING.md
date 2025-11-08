# Contributing to Arduino IDE Modern

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect differing viewpoints and experiences

## How to Contribute

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates.

**Bug Report Should Include**:
- Clear, descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Screenshots (if applicable)
- Environment details:
  - OS version
  - Python version
  - PySide6 version
  - Arduino board type

### Suggesting Features

Feature requests are welcome! Please:
- Use a clear, descriptive title
- Explain the problem your feature would solve
- Describe the desired behavior
- Include mockups or examples if possible

### Pull Requests

1. **Fork the repository**
2. **Create a branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Test thoroughly**
5. **Commit with clear messages**: `git commit -m "Add feature X"`
6. **Push to your fork**: `git push origin feature/your-feature-name`
7. **Open a Pull Request**

## Development Setup

### Prerequisites
- Python 3.9+
- Git
- Virtual environment (recommended)

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Arduino-IDE.git
cd Arduino-IDE

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest black pylint mypy

# Run the application
python -m arduino_ide.main
```

## Code Style

### Python Style Guide
- Follow **PEP 8**
- Use **type hints** for function parameters and return values
- Maximum line length: **88 characters** (Black default)
- Use **docstrings** for all public modules, classes, and functions

### Example:

```python
def calculate_checksum(data: bytes) -> int:
    """
    Calculate checksum for given data.

    Args:
        data: Byte array to calculate checksum for

    Returns:
        Integer checksum value
    """
    return sum(data) % 256
```

### Formatting

Use **Black** for code formatting:
```bash
black arduino_ide/
```

### Linting

Use **Pylint** for code quality:
```bash
pylint arduino_ide/
```

### Type Checking

Use **mypy** for type checking:
```bash
mypy arduino_ide/
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=arduino_ide

# Run specific test file
pytest tests/test_code_editor.py
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use descriptive test names

Example:
```python
def test_syntax_highlighter_recognizes_arduino_keywords():
    """Test that Arduino keywords are properly highlighted"""
    # Test implementation
    pass
```

## Commit Messages

### Format

```
<type>: <subject>

<body>

<footer>
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

### Examples

```
feat: Add code folding support to editor

Implement code folding functionality that allows users to
collapse/expand code blocks for better navigation in large files.

Closes #123
```

```
fix: Resolve serial monitor connection timeout

Fixed issue where serial monitor would timeout on slower systems
by increasing the connection timeout from 1s to 5s.

Fixes #456
```

## Project Structure

```
arduino_ide/
├── ui/              # User interface components
├── services/        # Business logic and services
├── models/          # Data models
├── utils/           # Utility functions
└── resources/       # Icons, themes, templates
```

### Adding New UI Components

1. Create file in `arduino_ide/ui/`
2. Inherit from appropriate QWidget
3. Implement `init_ui()` method
4. Document public methods
5. Add to `__init__.py` if needed

### Adding New Services

1. Create file in `arduino_ide/services/`
2. Define clear interface
3. Handle errors gracefully
4. Add comprehensive docstrings
5. Write unit tests

## Documentation

### Inline Documentation

- Use docstrings for all public classes and methods
- Include parameter and return type descriptions
- Provide usage examples for complex functions

### Wiki Documentation

For larger features, update the Wiki with:
- User guide
- Technical specifications
- API documentation
- Troubleshooting tips

## Review Process

Pull requests will be reviewed for:
1. **Code Quality**
   - Follows style guide
   - No obvious bugs
   - Proper error handling

2. **Testing**
   - Adequate test coverage
   - All tests passing
   - Manual testing completed

3. **Documentation**
   - Code is well-documented
   - README updated if needed
   - Changelog updated

4. **Functionality**
   - Solves the intended problem
   - Doesn't break existing features
   - Performs efficiently

## Questions?

- Open a discussion on GitHub Discussions
- Ask in pull request comments
- Contact maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Arduino IDE Modern!** 🎉
