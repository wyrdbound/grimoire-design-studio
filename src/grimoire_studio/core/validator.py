"""
Validation framework for GRIMOIRE Design Studio.

This module provides comprehensive validation for GRIMOIRE system files,
including YAML syntax validation, required field validation, and cross-reference
validation between different components.
"""

import logging
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml

from ..models.grimoire_definitions import (
    CompendiumDefinition,
    FlowDefinition,
    ModelDefinition,
    PromptDefinition,
    SourceDefinition,
    SystemDefinition,
    TableDefinition,
)


class ValidationSeverity(Enum):
    """Severity levels for validation results."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """
    Represents the result of a validation operation.

    This class encapsulates validation feedback including severity level,
    error messages, file locations, and line numbers for precise error reporting.
    """

    severity: ValidationSeverity
    message: str
    file_path: Optional[Path] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    error_code: Optional[str] = None
    component_id: Optional[str] = None

    @property
    def is_error(self) -> bool:
        """Check if this result represents an error or critical issue."""
        return self.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)

    @property
    def is_warning(self) -> bool:
        """Check if this result represents a warning."""
        return self.severity == ValidationSeverity.WARNING

    @property
    def location_info(self) -> str:
        """
        Get formatted location information for the validation result.

        Returns:
            Formatted string with file path and line/column info
        """
        if not self.file_path:
            return "Unknown location"

        location = str(self.file_path)
        if self.line_number is not None:
            location += f":{self.line_number}"
            if self.column_number is not None:
                location += f":{self.column_number}"

        return location

    def __str__(self) -> str:
        """String representation of the validation result."""
        severity_icon = {
            ValidationSeverity.INFO: "ℹ️",
            ValidationSeverity.WARNING: "⚠️",
            ValidationSeverity.ERROR: "❌",
            ValidationSeverity.CRITICAL: "🚨",
        }

        icon = severity_icon.get(self.severity, "?")
        result = f"{icon} [{self.severity.value.upper()}] {self.message}"

        if self.file_path:
            result += f" ({self.location_info})"

        if self.error_code:
            result += f" [{self.error_code}]"

        return result


class YamlValidator:
    """
    Thread-safe YAML validator for GRIMOIRE system files.

    This validator performs comprehensive validation including:
    - YAML syntax validation
    - Required field validation
    - Data type validation
    - Cross-reference validation between components
    """

    # Official GRIMOIRE directories from specification
    GRIMOIRE_DIRECTORIES = [
        "flows",
        "models",
        "compendiums",
        "tables",
        "sources",
        "prompts",
    ]

    # Required fields for each component type
    REQUIRED_FIELDS = {
        "system": {"id", "kind", "name"},
        "model": {"id", "kind", "name", "attributes"},
        "flow": {"id", "kind", "name", "steps"},
        "compendium": {"id", "kind", "name"},
        "table": {"id", "kind", "name", "roll"},
        "source": {"id", "kind", "name"},
        "prompt": {"id", "kind", "name", "prompt_template"},
    }

    # Valid 'kind' values for each component type
    VALID_KINDS = {
        "system": {"system"},
        "model": {"model"},
        "flow": {"flow"},
        "compendium": {"compendium"},
        "table": {"table"},
        "source": {"source"},
        "prompt": {"prompt"},
    }

    def __init__(self) -> None:
        """Initialize the validator with thread safety."""
        self._lock = threading.RLock()
        self.logger = logging.getLogger(__name__)

    def validate_yaml_syntax(
        self, content: str, file_path: Optional[Path] = None
    ) -> list[ValidationResult]:
        """
        Validate YAML syntax.

        Args:
            content: YAML content as string
            file_path: Optional path to the file being validated

        Returns:
            List of validation results (empty if syntax is valid)
        """
        with self._lock:
            results = []

            try:
                # Try to parse the YAML
                yaml.safe_load(content)
                self.logger.debug(f"YAML syntax valid for {file_path}")

            except yaml.YAMLError as e:
                # Extract line and column information if available
                line_number = None
                column_number = None

                # Type ignore for PyYAML dynamic attributes
                if hasattr(e, "problem_mark") and getattr(e, "problem_mark", None):
                    problem_mark = e.problem_mark
                    line_number = problem_mark.line + 1  # Convert to 1-based
                    column_number = problem_mark.column + 1

                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        message=f"YAML syntax error: {str(e)}",
                        file_path=file_path,
                        line_number=line_number,
                        column_number=column_number,
                        error_code="YAML_SYNTAX_ERROR",
                    )
                )

            except Exception as e:
                # Catch any other parsing errors
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Unexpected error parsing YAML: {str(e)}",
                        file_path=file_path,
                        error_code="YAML_PARSE_ERROR",
                    )
                )

            return results

    def validate_required_fields(
        self, data: Any, file_path: Optional[Path] = None
    ) -> list[ValidationResult]:
        """
        Validate required fields for GRIMOIRE components.

        Args:
            data: Parsed YAML data as dictionary
            file_path: Optional path to the file being validated

        Returns:
            List of validation results
        """
        with self._lock:
            results = []

            if not isinstance(data, Mapping):
                error_result = ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    message="Root element must be an object/mapping",
                    file_path=file_path,
                    error_code="INVALID_ROOT_TYPE",
                )
                results.append(error_result)
                return results

            # Check if 'kind' field exists first
            kind = data.get("kind")
            if not kind:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        message="Missing required field: 'kind'",
                        file_path=file_path,
                        error_code="MISSING_KIND_FIELD",
                    )
                )
                return results

            # Validate 'kind' value
            component_type = self._determine_component_type(kind)
            if not component_type:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid kind value: '{kind}'. Must be one of: "
                        f"{', '.join(self.VALID_KINDS.keys())}",
                        file_path=file_path,
                        error_code="INVALID_KIND_VALUE",
                    )
                )
                return results

            # Check required fields for this component type
            required_fields = self.REQUIRED_FIELDS.get(component_type, set())
            missing_fields = []

            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)

            if missing_fields:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        message=f"Missing required fields for {component_type}: "
                        f"{', '.join(missing_fields)}",
                        file_path=file_path,
                        component_id=data.get("id"),
                        error_code="MISSING_REQUIRED_FIELDS",
                    )
                )

            # Validate 'id' field format if present
            component_id = data.get("id")
            if component_id and not self._is_valid_id(component_id):
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid ID format: '{component_id}'. "
                        "IDs must be alphanumeric with underscores/hyphens only",
                        file_path=file_path,
                        component_id=component_id,
                        error_code="INVALID_ID_FORMAT",
                    )
                )

            return results

    def validate_component_structure(
        self, data: dict[str, Any], file_path: Optional[Path] = None
    ) -> list[ValidationResult]:
        """
        Validate component-specific structure using dataclass models.

        Args:
            data: Parsed YAML data as dictionary
            file_path: Optional path to the file being validated

        Returns:
            List of validation results
        """
        with self._lock:
            results: list[ValidationResult] = []

            try:
                kind = data.get("kind")
                if not isinstance(kind, str):
                    return results

                component_type = self._determine_component_type(kind)

                if not component_type:
                    # Already handled in required_fields validation
                    return results

                # Try to create the appropriate dataclass
                model_class = {
                    "system": SystemDefinition,
                    "model": ModelDefinition,
                    "flow": FlowDefinition,
                    "compendium": CompendiumDefinition,
                    "table": TableDefinition,
                    "source": SourceDefinition,
                    "prompt": PromptDefinition,
                }.get(component_type)

                if model_class:
                    try:
                        # Additional type checking for specific fields
                        if component_type == "model" and "attributes" in data:
                            if not isinstance(data["attributes"], (dict, list)):
                                raise ValueError("attributes must be a dict or list")

                        # This will raise exceptions for invalid data
                        model_class(**data)
                        self.logger.debug(
                            f"Component structure valid for {component_type} "
                            f"in {file_path}"
                        )

                    except (TypeError, ValueError, KeyError, AttributeError) as e:
                        results.append(
                            ValidationResult(
                                severity=ValidationSeverity.ERROR,
                                message=f"Invalid {component_type} structure: {str(e)}",
                                file_path=file_path,
                                component_id=data.get("id"),
                                error_code="INVALID_STRUCTURE",
                            )
                        )

            except Exception as e:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Unexpected error validating structure: {str(e)}",
                        file_path=file_path,
                        error_code="VALIDATION_ERROR",
                    )
                )

            return results

    def validate_file(self, file_path: Path) -> list[ValidationResult]:
        """
        Validate a single GRIMOIRE YAML file.

        Args:
            file_path: Path to the YAML file to validate

        Returns:
            List of validation results
        """
        with self._lock:
            results = []

            try:
                # Check file exists and is readable
                if not file_path.exists():
                    results.append(
                        ValidationResult(
                            severity=ValidationSeverity.ERROR,
                            message=f"File does not exist: {file_path}",
                            file_path=file_path,
                            error_code="FILE_NOT_FOUND",
                        )
                    )
                    return results

                if not file_path.is_file():
                    results.append(
                        ValidationResult(
                            severity=ValidationSeverity.ERROR,
                            message=f"Path is not a file: {file_path}",
                            file_path=file_path,
                            error_code="NOT_A_FILE",
                        )
                    )
                    return results

                # Read file content
                try:
                    content = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError as e:
                    results.append(
                        ValidationResult(
                            severity=ValidationSeverity.ERROR,
                            message=f"File encoding error: {str(e)}",
                            file_path=file_path,
                            error_code="ENCODING_ERROR",
                        )
                    )
                    return results

                # Validate YAML syntax
                syntax_results = self.validate_yaml_syntax(content, file_path)
                results.extend(syntax_results)

                # If syntax is valid, continue with structure validation
                if not any(r.is_error for r in syntax_results):
                    try:
                        data = yaml.safe_load(content)

                        # Validate required fields
                        field_results = self.validate_required_fields(data, file_path)
                        results.extend(field_results)

                        # If required fields are valid, validate structure
                        if not any(r.is_error for r in field_results):
                            structure_results = self.validate_component_structure(
                                data, file_path
                            )
                            results.extend(structure_results)

                    except Exception as e:
                        results.append(
                            ValidationResult(
                                severity=ValidationSeverity.CRITICAL,
                                message=f"Unexpected error during validation: {str(e)}",
                                file_path=file_path,
                                error_code="VALIDATION_ERROR",
                            )
                        )

            except Exception as e:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Failed to validate file: {str(e)}",
                        file_path=file_path,
                        error_code="FILE_VALIDATION_ERROR",
                    )
                )

            return results

    def _determine_component_type(self, kind: str) -> Optional[str]:
        """
        Determine component type from 'kind' field.

        Args:
            kind: The 'kind' value from YAML

        Returns:
            Component type or None if invalid
        """
        for component_type, valid_kinds in self.VALID_KINDS.items():
            if kind in valid_kinds:
                return component_type
        return None

    def _is_valid_id(self, component_id: str) -> bool:
        """
        Validate ID format.

        Args:
            component_id: ID to validate

        Returns:
            True if ID format is valid
        """
        if not isinstance(component_id, str) or not component_id:
            return False

        # Allow alphanumeric characters, underscores, and hyphens
        # Must start with a letter or underscore
        import re

        return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", component_id))

    def validate_system(
        self, system_path: Path, complete_system: Optional[Any] = None
    ) -> list[ValidationResult]:
        """
        Validate cross-references within a complete GRIMOIRE system.

        Args:
            system_path: Path to the system directory
            complete_system: Optional CompleteSystem object (will load if not provided)

        Returns:
            List of validation results for cross-reference issues
        """
        with self._lock:
            results = []

            try:
                # If complete_system not provided, try to load it
                if complete_system is None:
                    try:
                        from .project_manager import ProjectManager

                        pm = ProjectManager()
                        complete_system = pm.load_system(system_path)
                    except Exception as e:
                        results.append(
                            ValidationResult(
                                severity=ValidationSeverity.CRITICAL,
                                message=f"Failed to load system for validation: {str(e)}",
                                file_path=system_path,
                                error_code="SYSTEM_LOAD_ERROR",
                            )
                        )
                        return results

                # Validate model references in flows
                self._validate_flow_model_references(complete_system, results)

                # Validate compendium references in flows
                self._validate_flow_compendium_references(complete_system, results)

                # Validate table references in flows
                self._validate_flow_table_references(complete_system, results)

                # Validate prompt references in flows
                self._validate_flow_prompt_references(complete_system, results)

                # Validate model inheritance
                self._validate_model_inheritance(complete_system, results)

            except Exception as e:
                results.append(
                    ValidationResult(
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Unexpected error during system validation: {str(e)}",
                        file_path=system_path,
                        error_code="SYSTEM_VALIDATION_ERROR",
                    )
                )

            return results

    def _validate_flow_model_references(
        self, complete_system: Any, results: list[ValidationResult]
    ) -> None:
        """Validate that flows reference existing models."""
        available_models = set(complete_system.models.keys())

        for flow_id, flow in complete_system.flows.items():
            # Check input model references
            for input_def in flow.inputs:
                if hasattr(input_def, "model") and input_def.model:
                    if input_def.model not in available_models:
                        results.append(
                            ValidationResult(
                                severity=ValidationSeverity.ERROR,
                                message=f"Flow '{flow_id}' input references "
                                f"unknown model: '{input_def.model}'",
                                component_id=flow_id,
                                error_code="UNKNOWN_MODEL_REFERENCE",
                            )
                        )

            # Check output model references
            for output_def in flow.outputs:
                if hasattr(output_def, "model") and output_def.model:
                    if output_def.model not in available_models:
                        results.append(
                            ValidationResult(
                                severity=ValidationSeverity.ERROR,
                                message=f"Flow '{flow_id}' output references "
                                f"unknown model: '{output_def.model}'",
                                component_id=flow_id,
                                error_code="UNKNOWN_MODEL_REFERENCE",
                            )
                        )

            # Check step model references
            for step in flow.steps:
                if hasattr(step, "model") and step.model:
                    if step.model not in available_models:
                        results.append(
                            ValidationResult(
                                severity=ValidationSeverity.ERROR,
                                message=f"Flow '{flow_id}' step '{step.id}' "
                                f"references unknown model: '{step.model}'",
                                component_id=flow_id,
                                error_code="UNKNOWN_MODEL_REFERENCE",
                            )
                        )

    def _validate_flow_compendium_references(
        self, complete_system: Any, results: list[ValidationResult]
    ) -> None:
        """Validate that flows reference existing compendiums."""
        available_compendiums = set(complete_system.compendiums.keys())

        for flow_id, flow in complete_system.flows.items():
            for step in flow.steps:
                # Check for compendium references in step parameters
                if hasattr(step, "compendium") and step.compendium:
                    if step.compendium not in available_compendiums:
                        results.append(
                            ValidationResult(
                                severity=ValidationSeverity.ERROR,
                                message=f"Flow '{flow_id}' step '{step.id}' "
                                f"references unknown compendium: '{step.compendium}'",
                                component_id=flow_id,
                                error_code="UNKNOWN_COMPENDIUM_REFERENCE",
                            )
                        )

    def _validate_flow_table_references(
        self, complete_system: Any, results: list[ValidationResult]
    ) -> None:
        """Validate that flows reference existing tables."""
        available_tables = set(complete_system.tables.keys())

        for flow_id, flow in complete_system.flows.items():
            for step in flow.steps:
                # Check for table references in step parameters
                if hasattr(step, "table") and step.table:
                    if step.table not in available_tables:
                        results.append(
                            ValidationResult(
                                severity=ValidationSeverity.ERROR,
                                message=f"Flow '{flow_id}' step '{step.id}' "
                                f"references unknown table: '{step.table}'",
                                component_id=flow_id,
                                error_code="UNKNOWN_TABLE_REFERENCE",
                            )
                        )

    def _validate_flow_prompt_references(
        self, complete_system: Any, results: list[ValidationResult]
    ) -> None:
        """Validate that flows reference existing prompts in prompt_id fields."""
        available_prompts = set(complete_system.prompts.keys())

        for flow_id, flow in complete_system.flows.items():
            for step in flow.steps:
                # Check for prompt_id references in step parameters (not the prompt field)
                # The 'prompt' field is display text, not a reference
                if hasattr(step, "prompt_id") and step.prompt_id:
                    if step.prompt_id not in available_prompts:
                        results.append(
                            ValidationResult(
                                severity=ValidationSeverity.ERROR,
                                message=f"Flow '{flow_id}' step '{step.id}' "
                                f"references unknown prompt: '{step.prompt_id}'",
                                component_id=flow_id,
                                error_code="UNKNOWN_PROMPT_REFERENCE",
                            )
                        )

                # Also check step_config for prompt_id references
                if hasattr(step, "step_config") and isinstance(step.step_config, dict):
                    prompt_id = step.step_config.get("prompt_id")
                    if prompt_id and prompt_id not in available_prompts:
                        results.append(
                            ValidationResult(
                                severity=ValidationSeverity.ERROR,
                                message=f"Flow '{flow_id}' step '{step.id}' "
                                f"references unknown prompt: '{prompt_id}'",
                                component_id=flow_id,
                                error_code="UNKNOWN_PROMPT_REFERENCE",
                            )
                        )

    def _validate_model_inheritance(
        self, complete_system: Any, results: list[ValidationResult]
    ) -> None:
        """Validate model inheritance chains."""
        available_models = set(complete_system.models.keys())

        for model_id, model in complete_system.models.items():
            if hasattr(model, "inherits") and model.inherits:
                # Check that parent models exist
                for parent_id in model.inherits:
                    if parent_id not in available_models:
                        results.append(
                            ValidationResult(
                                severity=ValidationSeverity.ERROR,
                                message=f"Model '{model_id}' inherits from "
                                f"unknown model: '{parent_id}'",
                                component_id=model_id,
                                error_code="UNKNOWN_PARENT_MODEL",
                            )
                        )

                # Check for circular inheritance (basic check)
                if model_id in model.inherits:
                    results.append(
                        ValidationResult(
                            severity=ValidationSeverity.ERROR,
                            message=f"Model '{model_id}' has circular "
                            "inheritance (inherits from itself)",
                            component_id=model_id,
                            error_code="CIRCULAR_INHERITANCE",
                        )
                    )

    def __repr__(self) -> str:
        """String representation of the validator."""
        return "YamlValidator(thread_safe=True)"
