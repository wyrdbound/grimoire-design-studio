# Testing Strategy for GRIMOIRE Design Studio

This document outlines the testing strategy for the GRIMOIRE Design Studio, particularly regarding cross-platform compatibility and UI testing challenges.

## Test Categories

### 1. Unit Tests (`tests/test_*.py`)

- Test individual components and functions
- Business logic validation
- Data model testing
- Configuration system testing
- **Platform**: All platforms (Windows, macOS, Linux)
- **Marker**: `@pytest.mark.unit` (optional)

### 2. Integration Tests (`tests/test_integration.py`)

- Test component interactions
- System-level functionality
- File loading and validation workflows
- **Platform**: All platforms
- **Marker**: `@pytest.mark.integration`

### 3. UI Tests (`tests/ui/test_*.py`)

- PyQt6 widget and window testing
- User interface component testing
- Main window functionality
- **Platform**: Linux (CI) and local development
- **Marker**: `@pytest.mark.ui` (required)

## Platform Considerations

### Windows CI Issues

PyQt6 has known issues running in headless mode on Windows CI environments:

- Windows lacks proper headless X server support
- Qt applications may fail to initialize without a display
- Memory and resource management differs from Unix systems

**Solution**: UI tests are marked with `@pytest.mark.ui` and skipped on Windows CI.

### Linux CI (Ubuntu)

- Full PyQt6 support with `xvfb` (X Virtual Framebuffer)
- All tests run including UI tests
- Uses `xvfb-run -a pytest` for headless execution

### macOS CI

- Limited PyQt6 support in headless mode
- UI tests are excluded to prevent failures
- Only integration and unit tests run

## Running Tests Locally

### Run All Tests (including UI)

```bash
# Local development with display
pytest -v

# With coverage
pytest --cov=grimoire_studio --cov-report=term-missing -v
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m "unit" -v

# Integration tests only
pytest -m "integration" -v

# UI tests only
pytest -m "ui" -v

# Exclude UI tests (for CI-like behavior)
pytest -m "not ui" -v
```

### Headless Testing (Linux/macOS)

```bash
# With xvfb (Linux)
xvfb-run -a pytest -v

# With Qt platform override
QT_QPA_PLATFORM=minimal pytest -v
```

## CI/CD Configuration

### GitHub Actions Workflow

1. **Ubuntu**: Runs all tests including UI tests with `xvfb`
2. **Windows**: Runs tests excluding UI tests (`-m "not ui"`)
3. **macOS**: Runs integration tests only

### Test Markers

All UI tests must be marked with `@pytest.mark.ui`:

```python
import pytest

@pytest.mark.ui
def test_main_window_creation():
    # UI test code here
    pass
```

### Platform Skipping

UI tests automatically skip on Windows CI:

```python
import os
import platform
import pytest

SKIP_UI_ON_WINDOWS_CI = (
    platform.system() == "Windows"
    and (bool(os.environ.get("CI")) or bool(os.environ.get("GITHUB_ACTIONS")))
)

@pytest.mark.skipif(SKIP_UI_ON_WINDOWS_CI, reason="UI tests don't work in Windows CI")
@pytest.mark.ui
def test_ui_component():
    # UI test code
    pass
```

## Best Practices

### For UI Tests

1. Always mark with `@pytest.mark.ui`
2. Include Windows CI skip decorator when needed
3. Keep UI tests minimal and focused
4. Test only critical UI functionality
5. Prefer testing business logic separately from UI

### For Business Logic Tests

1. Separate business logic from UI components
2. Use dependency injection for testability
3. Mock UI components when testing controllers
4. Focus on algorithms, validation, and data processing

### Cross-Platform Compatibility

1. Use `pathlib.Path` for file operations
2. Handle platform-specific behavior explicitly
3. Test file operations on all platforms
4. Use proper encoding (`utf-8`) for text files

## Adding New Tests

### New Business Logic Test

```python
# tests/test_new_feature.py
import pytest

def test_new_business_logic():
    # No special markers needed
    # Will run on all platforms
    pass
```

### New UI Test

```python
# tests/ui/test_new_ui_component.py
import os
import platform
import pytest
from PyQt6.QtWidgets import QApplication

SKIP_UI_ON_WINDOWS_CI = (
    platform.system() == "Windows"
    and (bool(os.environ.get("CI")) or bool(os.environ.get("GITHUB_ACTIONS")))
)

@pytest.mark.ui
@pytest.mark.skipif(SKIP_UI_ON_WINDOWS_CI, reason="UI tests don't work in Windows CI")
def test_new_ui_component(qapp: QApplication):
    # UI test code here
    pass
```

This strategy ensures maximum compatibility across platforms while maintaining comprehensive test coverage where it matters most.
