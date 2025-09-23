"""
Unit tests for the GRIMOIRE validation framework.

Tests cover YAML syntax validation, required field validation,
component structure validation, and cross-reference validation.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.grimoire_studio.core.validator import (
    ValidationResult,
    ValidationSeverity,
    YamlValidator,
)


class TestValidationResult(unittest.TestCase):
    """Test cases for ValidationResult class."""

    def test_validation_result_initialization(self):
        """Test basic ValidationResult initialization."""
        result = ValidationResult(
            severity=ValidationSeverity.ERROR,
            message="Test error message",
        )

        assert result.severity == ValidationSeverity.ERROR
        assert result.message == "Test error message"
        assert result.file_path is None
        assert result.line_number is None

    def test_validation_result_with_location(self):
        """Test ValidationResult with file location information."""
        file_path = Path("/test/path.yaml")
        result = ValidationResult(
            severity=ValidationSeverity.WARNING,
            message="Test warning",
            file_path=file_path,
            line_number=42,
            column_number=10,
            error_code="TEST_WARNING",
        )

        assert result.file_path == file_path
        assert result.line_number == 42
        assert result.column_number == 10
        assert result.error_code == "TEST_WARNING"

    def test_is_error_property(self):
        """Test is_error property for different severity levels."""
        error_result = ValidationResult(ValidationSeverity.ERROR, "Error message")
        critical_result = ValidationResult(
            ValidationSeverity.CRITICAL, "Critical message"
        )
        warning_result = ValidationResult(ValidationSeverity.WARNING, "Warning message")
        info_result = ValidationResult(ValidationSeverity.INFO, "Info message")

        assert error_result.is_error is True
        assert critical_result.is_error is True
        assert warning_result.is_error is False
        assert info_result.is_error is False

    def test_is_warning_property(self):
        """Test is_warning property."""
        warning_result = ValidationResult(ValidationSeverity.WARNING, "Warning message")
        error_result = ValidationResult(ValidationSeverity.ERROR, "Error message")

        assert warning_result.is_warning is True
        assert error_result.is_warning is False

    def test_location_info_formatting(self):
        """Test location info formatting."""
        # No location info
        result1 = ValidationResult(ValidationSeverity.INFO, "Test")
        assert result1.location_info == "Unknown location"

        # File path only
        result2 = ValidationResult(
            ValidationSeverity.INFO, "Test", file_path=Path("/test.yaml")
        )
        assert result2.location_info == str(Path("/test.yaml"))

        # File path with line number
        result3 = ValidationResult(
            ValidationSeverity.INFO,
            "Test",
            file_path=Path("/test.yaml"),
            line_number=10,
        )
        assert result3.location_info == f"{Path('/test.yaml')}:10"

        # File path with line and column
        result4 = ValidationResult(
            ValidationSeverity.INFO,
            "Test",
            file_path=Path("/test.yaml"),
            line_number=10,
            column_number=5,
        )
        assert result4.location_info == f"{Path('/test.yaml')}:10:5"

    def test_string_representation(self):
        """Test string representation of ValidationResult."""
        result = ValidationResult(
            severity=ValidationSeverity.ERROR,
            message="Test error",
            file_path=Path("/test.yaml"),
            line_number=10,
            error_code="TEST_ERROR",
        )

        str_repr = str(result)
        assert "❌" in str_repr  # Error icon
        assert "[ERROR]" in str_repr
        assert "Test error" in str_repr
        assert str(Path("/test.yaml")) in str_repr
        assert "[TEST_ERROR]" in str_repr


class TestYamlValidator(unittest.TestCase):
    """Test cases for YamlValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = YamlValidator()

    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = YamlValidator()
        assert hasattr(validator, "_lock")
        assert hasattr(validator, "logger")

    def test_valid_yaml_syntax(self):
        """Test validation of valid YAML syntax."""
        valid_yaml = """
id: test_model
kind: model
name: Test Model
attributes:
  - id: test_attr
    name: Test Attribute
    type: string
"""

        results = self.validator.validate_yaml_syntax(valid_yaml)
        assert len(results) == 0

    def test_invalid_yaml_syntax(self):
        """Test validation of invalid YAML syntax."""
        invalid_yaml = """
id: test_model
kind: model
name: [invalid
  unclosed bracket
"""

        results = self.validator.validate_yaml_syntax(invalid_yaml)
        assert len(results) > 0
        assert any(r.severity == ValidationSeverity.ERROR for r in results)
        assert any("YAML syntax error" in r.message for r in results)

    def test_yaml_syntax_with_line_info(self):
        """Test that YAML syntax errors include line information."""
        invalid_yaml = "invalid: [\n  unclosed list"

        results = self.validator.validate_yaml_syntax(invalid_yaml, Path("test.yaml"))
        assert len(results) > 0

        error_result = results[0]
        assert error_result.severity == ValidationSeverity.ERROR
        assert error_result.file_path == Path("test.yaml")
        # Line number should be present for YAML errors
        # Note: exact line number depends on PyYAML version

    def test_required_fields_validation_valid(self):
        """Test required fields validation with valid data."""
        valid_data = {
            "id": "test_model",
            "kind": "model",
            "name": "Test Model",
            "attributes": {},
        }

        results = self.validator.validate_required_fields(valid_data)
        assert len(results) == 0

    def test_required_fields_validation_missing_kind(self):
        """Test required fields validation with missing 'kind' field."""
        invalid_data = {
            "id": "test_model",
            "name": "Test Model",
        }

        results = self.validator.validate_required_fields(invalid_data)
        assert len(results) > 0
        assert any(r.error_code == "MISSING_KIND_FIELD" for r in results)

    def test_required_fields_validation_invalid_kind(self):
        """Test required fields validation with invalid 'kind' value."""
        invalid_data = {
            "id": "test_model",
            "kind": "invalid_kind",
            "name": "Test Model",
        }

        results = self.validator.validate_required_fields(invalid_data)
        assert len(results) > 0
        assert any(r.error_code == "INVALID_KIND_VALUE" for r in results)

    def test_required_fields_validation_missing_fields(self):
        """Test required fields validation with missing required fields."""
        invalid_data = {
            "id": "test_model",
            "kind": "model",
            # Missing 'name' and 'attributes' fields
        }

        results = self.validator.validate_required_fields(invalid_data)
        assert len(results) > 0
        assert any(r.error_code == "MISSING_REQUIRED_FIELDS" for r in results)
        assert any("name" in r.message for r in results)
        assert any("attributes" in r.message for r in results)

    def test_required_fields_validation_invalid_id_format(self):
        """Test ID format validation."""
        test_cases = [
            {"id": "123invalid", "expected": True},  # Cannot start with number
            {"id": "invalid@id", "expected": True},  # Invalid character
            {"id": "invalid id", "expected": True},  # Space not allowed
            {"id": "valid_id", "expected": False},  # Valid
            {"id": "valid-id", "expected": False},  # Valid with hyphen
            {"id": "_valid_id", "expected": False},  # Valid starting with underscore
        ]

        for test_case in test_cases:
            invalid_data = {
                "id": test_case["id"],
                "kind": "model",
                "name": "Test Model",
                "attributes": [],
            }

            results = self.validator.validate_required_fields(invalid_data)
            has_id_error = any(r.error_code == "INVALID_ID_FORMAT" for r in results)
            assert has_id_error == test_case["expected"], (
                f"ID '{test_case['id']}' validation failed. "
                f"Expected error: {test_case['expected']}, Got error: {has_id_error}"
            )

    def test_component_structure_validation_valid(self):
        """Test component structure validation with valid data."""
        valid_model_data = {
            "id": "test_model",
            "kind": "model",
            "name": "Test Model",
            "description": "A test model",
            "attributes": {
                "test_attr": {
                    "type": "string",
                    "required": True,
                }
            },
        }

        results = self.validator.validate_component_structure(valid_model_data)
        assert len(results) == 0

    def test_component_structure_validation_invalid(self):
        """Test component structure validation with invalid data."""
        # Invalid data type that will cause from_dict to fail
        invalid_model_data = {
            "id": "test_model",
            "kind": "model",
            "name": "Test Model",
            "attributes": "should_be_dict_not_string",  # Invalid type
        }

        results = self.validator.validate_component_structure(invalid_model_data)
        assert len(results) > 0
        assert any(r.error_code == "INVALID_STRUCTURE" for r in results)

    def test_validate_file_nonexistent(self):
        """Test validation of non-existent file."""
        nonexistent_file = Path("/nonexistent/file.yaml")
        results = self.validator.validate_file(nonexistent_file)

        assert len(results) > 0
        assert any(r.error_code == "FILE_NOT_FOUND" for r in results)

    def test_validate_file_not_a_file(self):
        """Test validation when path is not a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dir_path = Path(temp_dir)
            results = self.validator.validate_file(dir_path)

            assert len(results) > 0
            assert any(r.error_code == "NOT_A_FILE" for r in results)

    def test_validate_file_valid(self):
        """Test validation of a valid YAML file."""
        valid_yaml_content = """
id: test_model
kind: model
name: Test Model
description: A valid test model
attributes:
  test_attr:
    type: string
    required: true
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as temp_file:
            temp_file.write(valid_yaml_content)
            temp_file.flush()
            temp_file_path = Path(temp_file.name)

        try:
            results = self.validator.validate_file(temp_file_path)
            # Should have no errors for valid file
            error_results = [r for r in results if r.is_error]
            assert len(error_results) == 0, f"Unexpected errors: {error_results}"

        finally:
            try:
                temp_file_path.unlink()
            except (OSError, PermissionError):
                # On Windows, sometimes the file is still locked
                pass

    def test_validate_file_invalid_syntax(self):
        """Test validation of file with invalid YAML syntax."""
        invalid_yaml_content = """
id: test_model
kind: model
name: Test Model
attributes: [
  invalid_yaml: unclosed_bracket
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as temp_file:
            temp_file.write(invalid_yaml_content)
            temp_file.flush()
            temp_file_path = Path(temp_file.name)

        try:
            results = self.validator.validate_file(temp_file_path)
            assert len(results) > 0
            assert any(r.error_code == "YAML_SYNTAX_ERROR" for r in results)

        finally:
            try:
                temp_file_path.unlink()
            except (OSError, PermissionError):
                # On Windows, sometimes the file is still locked
                pass

    def test_validate_file_missing_fields(self):
        """Test validation of file with missing required fields."""
        incomplete_yaml_content = """
id: test_model
kind: model
# Missing 'name' and 'attributes' fields
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as temp_file:
            temp_file.write(incomplete_yaml_content)
            temp_file.flush()
            temp_file_path = Path(temp_file.name)

        try:
            results = self.validator.validate_file(temp_file_path)
            assert len(results) > 0
            assert any(r.error_code == "MISSING_REQUIRED_FIELDS" for r in results)

        finally:
            try:
                temp_file_path.unlink()
            except (OSError, PermissionError):
                # On Windows, sometimes the file is still locked
                pass

    def test_determine_component_type(self):
        """Test component type determination from 'kind' field."""
        test_cases = [
            ("system", "system"),
            ("model", "model"),
            ("flow", "flow"),
            ("compendium", "compendium"),
            ("table", "table"),
            ("source", "source"),
            ("prompt", "prompt"),
            ("invalid", None),
        ]

        for kind, expected in test_cases:
            result = self.validator._determine_component_type(kind)
            assert result == expected, f"Kind '{kind}' should map to '{expected}'"

    def test_is_valid_id(self):
        """Test ID validation logic."""
        valid_ids = [
            "valid_id",
            "validId",
            "valid-id",
            "_valid_id",
            "valid123",
            "a",
            "_",
        ]

        invalid_ids = [
            "",
            "123invalid",
            "invalid@id",
            "invalid id",
            "invalid.id",
            "invalid/id",
            None,
            123,
        ]

        for valid_id in valid_ids:
            assert self.validator._is_valid_id(valid_id), (
                f"'{valid_id}' should be valid"
            )

        for invalid_id in invalid_ids:
            assert not self.validator._is_valid_id(invalid_id), (
                f"'{invalid_id}' should be invalid"
            )

    @patch("src.grimoire_studio.core.project_manager.ProjectManager")
    def test_validate_system_success(self, mock_pm_class):
        """Test successful system validation."""
        # Mock the complete system with proper iterables
        mock_model = Mock()
        mock_model.inherits = []  # Empty list for no inheritance

        mock_system = Mock()
        mock_system.models = {"test_model": mock_model}
        mock_system.flows = {}
        mock_system.compendiums = {}
        mock_system.tables = {}
        mock_system.prompts = {}

        # Mock ProjectManager
        mock_pm = Mock()
        mock_pm.load_system.return_value = mock_system
        mock_pm_class.return_value = mock_pm

        results = self.validator.validate_system(Path("/test/system"))
        assert len(results) == 0

    @patch("src.grimoire_studio.core.project_manager.ProjectManager")
    def test_validate_system_load_error(self, mock_pm_class):
        """Test system validation when system loading fails."""
        # Mock ProjectManager to raise exception
        mock_pm = Mock()
        mock_pm.load_system.side_effect = Exception("Load failed")
        mock_pm_class.return_value = mock_pm

        results = self.validator.validate_system(Path("/test/system"))
        assert len(results) > 0
        assert any(r.error_code == "SYSTEM_LOAD_ERROR" for r in results)

    def test_validate_flow_model_references(self):
        """Test flow model reference validation."""
        # Create mock system with models and flows
        mock_system = Mock()
        mock_system.models = {"existing_model": Mock()}

        # Mock flow with valid and invalid model references
        mock_input = Mock()
        mock_input.model = "existing_model"

        mock_invalid_input = Mock()
        mock_invalid_input.model = "nonexistent_model"

        mock_flow = Mock()
        mock_flow.inputs = [mock_input, mock_invalid_input]
        mock_flow.outputs = []
        mock_flow.steps = []

        mock_system.flows = {"test_flow": mock_flow}
        mock_system.compendiums = {}
        mock_system.tables = {}
        mock_system.prompts = {}

        results = []
        self.validator._validate_flow_model_references(mock_system, results)

        assert len(results) > 0
        assert any("nonexistent_model" in r.message for r in results)
        assert any(r.error_code == "UNKNOWN_MODEL_REFERENCE" for r in results)

    def test_thread_safety(self):
        """Test that validator operations are thread-safe."""
        import threading
        import time

        results_list = []
        exception_list = []

        def validate_worker():
            try:
                validator = YamlValidator()
                for _ in range(10):
                    results = validator.validate_yaml_syntax("id: test\nkind: model\n")
                    results_list.append(len(results))
                    time.sleep(0.001)  # Small delay to encourage race conditions
            except Exception as e:
                exception_list.append(e)

        # Run multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=validate_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should not have any exceptions
        assert len(exception_list) == 0, f"Thread safety failed: {exception_list}"
        assert len(results_list) == 50  # 5 threads × 10 operations each


if __name__ == "__main__":
    unittest.main()
