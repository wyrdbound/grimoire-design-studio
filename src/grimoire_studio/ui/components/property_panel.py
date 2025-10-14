"""Property panel for editing game object properties dynamically.

This module provides the PropertyPanel widget which creates dynamic editing
interfaces based on object structure and model definitions.
"""

from __future__ import annotations

from typing import Any

from grimoire_logging import get_logger
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...models.grimoire_definitions import CompleteSystem
from ...services.object_service import ObjectInstantiationService

logger = get_logger(__name__)


class PropertyPanel(QWidget):
    """Dynamic property editing panel for game objects.

    This widget creates editing interfaces dynamically based on the structure
    of game objects and their model definitions. It supports various data types
    including primitives, lists, dicts, and nested objects.

    Signals:
        property_changed: Emitted when a property value changes (property_path, new_value)
        validation_error: Emitted when validation fails (error_message)
    """

    property_changed = pyqtSignal(str, object)
    validation_error = pyqtSignal(str)

    def __init__(
        self,
        system: CompleteSystem | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the property panel.

        Args:
            system: GRIMOIRE system for validation (optional)
            parent: Parent widget
        """
        super().__init__(parent)

        self.system = system
        self.object_service: ObjectInstantiationService | None = None
        self.current_object: dict[str, Any] | None = None
        self.widgets: dict[str, QWidget] = {}

        if system:
            self.object_service = ObjectInstantiationService(system)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the property panel user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title_label = QLabel("Properties")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        main_layout.addWidget(title_label)

        # Scroll area for properties
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Container widget for the form
        self.form_container = QWidget()
        self.form_layout = QFormLayout(self.form_container)
        self.form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        scroll_area.setWidget(self.form_container)
        main_layout.addWidget(scroll_area)

        # Empty state label
        self.empty_label = QLabel("No object selected")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: gray; font-style: italic;")
        self.form_layout.addRow(self.empty_label)

    def load_object(self, obj_data: dict[str, Any]) -> None:
        """Load an object for editing.

        Args:
            obj_data: Object data dictionary with 'model' field
        """
        logger.info(f"Loading object into property panel: {obj_data.get('model')}")

        # Clear existing widgets
        self._clear_form()

        # Store current object
        self.current_object = obj_data.copy()

        # Verify model exists
        model_type = obj_data.get("model")
        if not model_type:
            self._show_error("Object missing 'model' field")
            return

        if not self.system or model_type not in self.system.models:
            self._show_error(f"Unknown model type: {model_type}")
            return

        # Get model definition
        model_def = self.system.models[model_type]

        # Instantiate object to get computed/derived fields
        instantiated_obj = None
        if self.object_service:
            try:
                instantiated_obj = self.object_service.create_object(obj_data)
                logger.debug(
                    f"Instantiated object for derived fields: {type(instantiated_obj)}"
                )
            except Exception as e:
                logger.warning(f"Could not instantiate object for derived fields: {e}")

        # Hide empty label
        self.empty_label.hide()

        # Create widgets for each attribute
        for attr_name, attr_def in model_def.attributes.items():
            # Try to get value from instantiated object first (includes derived fields)
            current_value = obj_data.get(attr_name)

            if instantiated_obj:
                # GrimoireModel is dict-like, access via get()
                instantiated_value = instantiated_obj.get(attr_name)
                if instantiated_value is not None:
                    current_value = instantiated_value

            self._create_attribute_widget(attr_name, attr_def, current_value)

        logger.info(f"Loaded {len(self.widgets)} property widgets for {model_type}")

    def _clear_form(self) -> None:
        """Clear all form widgets."""
        # Remove all rows (this will delete widgets, including empty_label)
        while self.form_layout.count() > 0:
            self.form_layout.removeRow(0)

        self.widgets.clear()
        self.current_object = None

        # Create new empty label since the old one was deleted
        self.empty_label = QLabel("No object selected")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: gray; font-style: italic;")
        self.form_layout.addRow(self.empty_label)
        self.empty_label.show()  # Explicitly show the label

    def _show_error(self, message: str) -> None:
        """Show an error message in the panel.

        Args:
            message: Error message to display
        """
        self._clear_form()
        self.empty_label.setText(message)
        self.empty_label.setStyleSheet("color: red; font-style: italic;")
        self.empty_label.show()
        self.validation_error.emit(message)

    def _create_attribute_widget(
        self, attr_name: str, attr_def: Any, current_value: Any
    ) -> None:
        """Create an editing widget for an attribute.

        Args:
            attr_name: Name of the attribute
            attr_def: Attribute definition from model
            current_value: Current value of the attribute
        """
        # Get attribute type
        attr_type = getattr(attr_def, "type", "str")

        # Create label with optional marker
        is_optional = getattr(attr_def, "optional", False)
        has_default = hasattr(attr_def, "default")
        is_derived = getattr(attr_def, "derived", None) is not None

        label_text = attr_name
        if is_derived:
            label_text += " (derived)"
        elif not (is_optional or has_default):
            label_text += " *"  # Required field marker

        label = QLabel(label_text)

        # Create appropriate widget based on type
        widget: QWidget | None = None

        if is_derived:
            # Derived fields are read-only
            widget = self._create_readonly_widget(current_value)
        elif attr_type == "str":
            widget = self._create_string_widget(attr_name, current_value)
        elif attr_type == "int":
            widget = self._create_int_widget(attr_name, current_value, attr_def)
        elif attr_type == "float":
            widget = self._create_float_widget(attr_name, current_value, attr_def)
        elif attr_type == "bool":
            widget = self._create_bool_widget(attr_name, current_value)
        elif attr_type == "list":
            widget = self._create_list_widget(attr_name, current_value, attr_def)
        elif attr_type == "dict":
            widget = self._create_dict_widget(attr_name, current_value, attr_def)
        else:
            # Assume it's a model reference or complex type
            widget = self._create_object_widget(attr_name, current_value, attr_type)

        if widget:
            self.form_layout.addRow(label, widget)
            self.widgets[attr_name] = widget

    def _create_readonly_widget(self, value: Any) -> QWidget:
        """Create a read-only widget for derived fields.

        Args:
            value: Current value

        Returns:
            Read-only label widget
        """
        label = QLabel(str(value) if value is not None else "N/A")
        label.setStyleSheet("color: gray; font-style: italic;")
        return label

    def _create_string_widget(self, attr_name: str, value: Any) -> QLineEdit:
        """Create a string editing widget.

        Args:
            attr_name: Name of the attribute
            value: Current value

        Returns:
            Line edit widget
        """
        widget = QLineEdit()
        widget.setText(str(value) if value is not None else "")
        widget.textChanged.connect(
            lambda text: self._on_property_changed(attr_name, text or None)
        )
        return widget

    def _create_int_widget(self, attr_name: str, value: Any, attr_def: Any) -> QSpinBox:
        """Create an integer editing widget.

        Args:
            attr_name: Name of the attribute
            value: Current value
            attr_def: Attribute definition with range info

        Returns:
            Spin box widget
        """
        widget = QSpinBox()

        # Set range if specified
        range_str = getattr(attr_def, "range", None)
        if range_str:
            # Parse range like "0..100" or "0.."
            try:
                parts = range_str.split("..")
                if len(parts) == 2:
                    min_val = int(parts[0]) if parts[0] else -2147483648
                    max_val = int(parts[1]) if parts[1] else 2147483647
                    widget.setRange(min_val, max_val)
            except (ValueError, AttributeError):
                # Default range if parsing fails
                widget.setRange(-2147483648, 2147483647)
        else:
            widget.setRange(-2147483648, 2147483647)

        widget.setValue(int(value) if value is not None else 0)
        widget.valueChanged.connect(
            lambda val: self._on_property_changed(attr_name, val)
        )
        return widget

    def _create_float_widget(
        self, attr_name: str, value: Any, attr_def: Any
    ) -> QDoubleSpinBox:
        """Create a float editing widget.

        Args:
            attr_name: Name of the attribute
            value: Current value
            attr_def: Attribute definition with range info

        Returns:
            Double spin box widget
        """
        widget = QDoubleSpinBox()
        widget.setDecimals(2)

        # Set range if specified
        range_str = getattr(attr_def, "range", None)
        if range_str:
            try:
                parts = range_str.split("..")
                if len(parts) == 2:
                    min_val = float(parts[0]) if parts[0] else -1e308
                    max_val = float(parts[1]) if parts[1] else 1e308
                    widget.setRange(min_val, max_val)
            except (ValueError, AttributeError):
                widget.setRange(-1e308, 1e308)
        else:
            widget.setRange(-1e308, 1e308)

        widget.setValue(float(value) if value is not None else 0.0)
        widget.valueChanged.connect(
            lambda val: self._on_property_changed(attr_name, val)
        )
        return widget

    def _create_bool_widget(self, attr_name: str, value: Any) -> QCheckBox:
        """Create a boolean editing widget.

        Args:
            attr_name: Name of the attribute
            value: Current value

        Returns:
            Checkbox widget
        """
        widget = QCheckBox()
        widget.setChecked(bool(value) if value is not None else False)
        widget.stateChanged.connect(
            lambda state: self._on_property_changed(
                attr_name, state == Qt.CheckState.Checked.value
            )
        )
        return widget

    def _create_list_widget(self, attr_name: str, value: Any, attr_def: Any) -> QWidget:
        """Create a list editing widget.

        Args:
            attr_name: Name of the attribute
            value: Current list value
            attr_def: Attribute definition with 'of' type

        Returns:
            Container widget with list and buttons
        """
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # List widget
        list_widget = QListWidget()
        if value:
            for item in value:
                list_widget.addItem(str(item))

        layout.addWidget(list_widget)

        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        remove_btn = QPushButton("Remove")

        add_btn.clicked.connect(lambda: self._on_list_add(attr_name, list_widget))
        remove_btn.clicked.connect(lambda: self._on_list_remove(attr_name, list_widget))

        button_layout.addWidget(add_btn)
        button_layout.addWidget(remove_btn)
        layout.addLayout(button_layout)

        return container

    def _create_dict_widget(self, attr_name: str, value: Any, attr_def: Any) -> QWidget:
        """Create a dict editing widget with nested properties.

        Args:
            attr_name: Name of the attribute
            value: Current dict value
            attr_def: Attribute definition

        Returns:
            Group box with nested properties
        """
        group = QGroupBox(f"{attr_name} (dict)")
        layout = QFormLayout(group)

        if isinstance(value, dict):
            for key, val in value.items():
                label = QLabel(key)
                value_widget = QLineEdit(str(val))
                value_widget.textChanged.connect(
                    lambda text, k=key: self._on_dict_property_changed(
                        attr_name, k, text
                    )
                )
                layout.addRow(label, value_widget)
        else:
            layout.addRow(QLabel("Empty dict or invalid type"))

        return group

    def _create_object_widget(
        self, attr_name: str, value: Any, attr_type: str
    ) -> QWidget:
        """Create a widget for object/model references.

        Args:
            attr_name: Name of the attribute
            value: Current object value
            attr_type: Type of the object (model name)

        Returns:
            Group box or label for object
        """
        from grimoire_model import GrimoireModel

        # Handle both dict and GrimoireModel objects as expandable widgets
        if isinstance(value, (dict, GrimoireModel)):
            group = QGroupBox(f"{attr_name} ({attr_type})")
            layout = QFormLayout(group)

            # Get items - use .items() for both dict and GrimoireModel
            items = value.items() if hasattr(value, "items") else []

            for key, val in items:
                if key != "model":  # Skip model field
                    label = QLabel(key)
                    value_widget = QLineEdit(str(val))
                    value_widget.textChanged.connect(
                        lambda text, k=key: self._on_nested_property_changed(
                            attr_name, k, text
                        )
                    )
                    layout.addRow(label, value_widget)

            return group

        # Simple display for non-dict values
        label = QLabel(str(value) if value is not None else "None")  # type: ignore[unreachable]
        label.setStyleSheet("color: gray;")
        return label

    def _on_property_changed(self, attr_name: str, new_value: Any) -> None:
        """Handle property value change.

        Args:
            attr_name: Name of the changed attribute
            new_value: New value
        """
        if self.current_object is not None:
            self.current_object[attr_name] = new_value
            self.property_changed.emit(attr_name, new_value)

            # Re-instantiate object to update derived fields
            self._update_derived_fields()

            # Validate if service available
            if self.object_service:
                self._validate_current_object()

    def _update_derived_fields(self) -> None:
        """Update derived field displays after property changes."""
        if not self.current_object or not self.object_service or not self.system:
            return

        model_type = self.current_object.get("model")
        if not model_type or model_type not in self.system.models:
            return

        model_def = self.system.models[model_type]

        try:
            # Re-instantiate object to get updated derived fields
            instantiated_obj = self.object_service.create_object(self.current_object)
            logger.debug("Re-instantiated object for derived field updates")

            # Update only derived field widgets
            for attr_name, attr_def in model_def.attributes.items():
                # Check if field is derived (has a formula)
                is_derived = getattr(attr_def, "derived", None) is not None

                if is_derived and attr_name in self.widgets:
                    widget = self.widgets[attr_name]

                    # Update the QLabel showing the derived value
                    if isinstance(widget, QLabel):
                        # GrimoireModel is dict-like, access via get()
                        derived_value = instantiated_obj.get(attr_name)
                        widget.setText(
                            str(derived_value) if derived_value is not None else "N/A"
                        )
                        logger.debug(
                            f"Updated derived field {attr_name} = {derived_value}"
                        )

        except Exception as e:
            logger.warning(f"Could not update derived fields: {e}")

    def _on_list_add(self, attr_name: str, list_widget: QListWidget) -> None:
        """Handle adding an item to a list.

        Args:
            attr_name: Name of the list attribute
            list_widget: List widget to add to
        """
        # For now, add empty string (could be enhanced with type-specific dialogs)
        list_widget.addItem("")
        self._update_list_value(attr_name, list_widget)

    def _on_list_remove(self, attr_name: str, list_widget: QListWidget) -> None:
        """Handle removing an item from a list.

        Args:
            attr_name: Name of the list attribute
            list_widget: List widget to remove from
        """
        current_row = list_widget.currentRow()
        if current_row >= 0:
            list_widget.takeItem(current_row)
            self._update_list_value(attr_name, list_widget)

    def _update_list_value(self, attr_name: str, list_widget: QListWidget) -> None:
        """Update the list value from the widget.

        Args:
            attr_name: Name of the list attribute
            list_widget: List widget
        """
        items = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item:
                items.append(item.text())
        self._on_property_changed(attr_name, items)

    def _on_dict_property_changed(
        self, attr_name: str, key: str, new_value: Any
    ) -> None:
        """Handle dict property change.

        Args:
            attr_name: Name of the dict attribute
            key: Key in the dict
            new_value: New value for the key
        """
        if self.current_object is not None:
            if attr_name not in self.current_object:
                self.current_object[attr_name] = {}
            self.current_object[attr_name][key] = new_value
            self.property_changed.emit(f"{attr_name}.{key}", new_value)

            if self.object_service:
                self._validate_current_object()

    def _on_nested_property_changed(
        self, attr_name: str, key: str, new_value: Any
    ) -> None:
        """Handle nested object property change.

        Args:
            attr_name: Name of the object attribute
            key: Key in the object
            new_value: New value for the key
        """
        self._on_dict_property_changed(attr_name, key, new_value)

    def _validate_current_object(self) -> None:
        """Validate the current object and emit results."""
        if not self.current_object or not self.object_service:
            return

        try:
            is_valid, errors = self.object_service.validate_object(self.current_object)
            if not is_valid:
                error_msg = "\n".join(errors[:3])  # Show first 3 errors
                if len(errors) > 3:
                    error_msg += f"\n... and {len(errors) - 3} more"
                self.validation_error.emit(error_msg)
                logger.debug(f"Validation failed: {error_msg}")
        except Exception as e:
            error_msg = f"Validation error: {e}"
            self.validation_error.emit(error_msg)
            logger.error(error_msg)

    def get_object_data(self) -> dict[str, Any] | None:
        """Get the current object data.

        Returns:
            Current object data dictionary, or None if no object loaded
        """
        return self.current_object.copy() if self.current_object else None

    def clear(self) -> None:
        """Clear the property panel."""
        self._clear_form()
