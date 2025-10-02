#!/usr/bin/env python3
"""Demo of PropertyPanel component with real game objects.

This script demonstrates the PropertyPanel's dynamic widget creation
and validation features using the Knave 1e system.

Key Features Demonstrated:
- Dynamic widget creation based on model definitions
- Support for all data types (string, int, float, bool, list, dict, objects)
- Real-time validation with grimoire-model
- **Derived field computation**: Shows computed values like "defense (derived)"
  which automatically update when dependent fields change (e.g., bonus)
- Property change tracking and validation feedback
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from typing import Any, Optional

from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QTextEdit, QVBoxLayout, QWidget

from grimoire_studio.core.project_manager import CompleteSystem, ProjectManager
from grimoire_studio.ui.components.property_panel import PropertyPanel


class PropertyPanelDemo(QWidget):
    """Demo window for PropertyPanel component."""

    def __init__(self) -> None:
        """Initialize the demo window."""
        super().__init__()
        self.setWindowTitle("Property Panel Demo - Knave 1e")
        self.resize(1000, 700)

        # Load Knave system
        self.system: Optional[CompleteSystem] = self._load_knave_system()
        if not self.system:
            print("❌ Could not load Knave 1e system")
            sys.exit(1)

        self._setup_ui()
        self._load_test_objects()

    def _load_knave_system(self) -> Optional[CompleteSystem]:
        """Load the Knave 1e system."""
        print("📚 Loading Knave 1e system...")
        project_manager = ProjectManager()
        knave_path = Path(__file__).parent.parent / "systems" / "knave_1e"

        if not knave_path.exists():
            print(f"❌ Knave 1e system not found at: {knave_path}")
            return None

        try:
            system = project_manager.load_system(knave_path)
            print(f"✅ Loaded system: {system.system.name}")
            return system
        except Exception as e:
            print(f"❌ Failed to load system: {e}")
            return None

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)

        # Property panel on the left
        self.property_panel = PropertyPanel(system=self.system)
        self.property_panel.setMinimumWidth(400)

        # Output area on the right
        right_layout = QVBoxLayout()

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        right_layout.addWidget(self.output)

        layout.addWidget(self.property_panel, stretch=1)
        layout.addLayout(right_layout, stretch=1)

        # Connect signals
        self.property_panel.property_changed.connect(self._on_property_changed)
        self.property_panel.validation_error.connect(self._on_validation_error)

    def _load_test_objects(self) -> None:
        """Load test objects to demonstrate different features."""
        self.test_objects: dict[str, dict[str, Any]] = {
            "Character Ability": {
                "model": "character_ability",
                "bonus": 5,
            },
            "Simple Item": {
                "model": "item",
                "name": "Longsword",
                "slot_cost": 1,
            },
            "Weapon": {
                "model": "weapon",
                "name": "Greatsword",
                "slot_cost": 2,
                "damage": "2d6",
                "hands": 2,
                "properties": ["two-handed", "heavy"],
            },
            "Armor": {
                "model": "armor",
                "name": "Chainmail",
                "bonus": 4,
                "slot_cost": 2,
            },
            "Breakable Item": {
                "model": "breakable",
                "name": "Glass Vial",
                "slot_cost": 1,
                "usage_die": "d6",
            },
            "Character Abilities": {
                "model": "character_abilities",
                "strength": {"model": "character_ability", "bonus": 5},
                "dexterity": {"model": "character_ability", "bonus": 4},
                "constitution": {"model": "character_ability", "bonus": 6},
                "intelligence": {"model": "character_ability", "bonus": 3},
                "wisdom": {"model": "character_ability", "bonus": 4},
                "charisma": {"model": "character_ability", "bonus": 3},
            },
        }

        self._show_menu()

    def _show_menu(self) -> None:
        """Show the menu of available test objects."""
        self.output.clear()
        self.output.append("🎮 Property Panel Demo - Knave 1e\n")
        self.output.append("=" * 50 + "\n")
        self.output.append("Available test objects:\n")

        for i, name in enumerate(self.test_objects.keys(), 1):
            self.output.append(f"  {i}. {name}")

        self.output.append("\n" + "=" * 50 + "\n")
        self.output.append("Instructions:")
        self.output.append(
            f"  • Type a number (1-{len(self.test_objects)}) and press Enter to load an object"
        )
        self.output.append("  • Edit the properties in the left panel")
        self.output.append("  • Watch for validation feedback below")
        self.output.append("  • Property changes are logged in this panel\n")

        # Auto-load first object for demonstration
        self._load_object_by_index(0)

    def _load_object_by_index(self, index: int) -> None:
        """Load an object by its index."""
        obj_list = list(self.test_objects.items())
        if 0 <= index < len(obj_list):
            name, data = obj_list[index]
            self.output.append(f"\n📦 Loading: {name}\n")
            self.output.append(f"Model type: {data['model']}\n")
            self.output.append(f"Data: {data}\n")
            self.property_panel.load_object(data)
            self.output.append("✅ Object loaded successfully!\n")
            self.output.append("You can now edit the properties in the left panel.\n")

    def _on_property_changed(self, property_path: str, new_value: Any) -> None:
        """Handle property change events."""
        self.output.append(f"🔧 Property changed: {property_path} = {new_value}")

        # Show current object state (raw data)
        current_obj = self.property_panel.get_object_data()
        if current_obj and self.system:
            self.output.append(f"Current state: {current_obj}")

            # Try to instantiate the object to show computed/derived fields
            try:
                from grimoire_studio.services.object_service import (
                    ObjectInstantiationService,
                )

                service = ObjectInstantiationService(self.system)
                game_obj = service.create_object(current_obj)

                # Convert object to dict to show all fields including derived
                if hasattr(game_obj, "model_dump"):
                    obj_dict = game_obj.model_dump()
                    self.output.append(
                        f"Instantiated object (with derived fields): {obj_dict}"
                    )
                else:
                    self.output.append(f"Instantiated object: {game_obj}")
            except Exception as e:
                self.output.append(f"⚠️  Could not instantiate object: {e}")

            self.output.append("")  # Empty line for readability

    def _on_validation_error(self, error_message: str) -> None:
        """Handle validation error events."""
        self.output.append(f"⚠️  Validation error:\n{error_message}\n")

    def keyPressEvent(self, a0: Optional[QKeyEvent]) -> None:
        """Handle key press events for quick object loading."""
        if not a0:
            return
        key = a0.text()
        if key.isdigit():
            index = int(key) - 1
            if 0 <= index < len(self.test_objects):
                self._load_object_by_index(index)


def main() -> None:
    """Run the property panel demo."""
    app = QApplication(sys.argv)
    app.setApplicationName("Property Panel Demo")

    demo = PropertyPanelDemo()
    demo.show()

    print("\n✨ Property Panel Demo Started!")
    print("\nTest Scenarios:")
    print(
        "1. Character Ability - Simple model with DERIVED FIELD (defense = 10 + bonus)"
    )
    print(
        "   → Try changing the 'bonus' value and watch 'defense' update automatically!"
    )
    print("2. Simple Item - Basic string and int fields")
    print("3. Weapon - Complex item with list properties")
    print("4. Armor - Model with bonus and slot cost")
    print("5. Breakable Item - Model with usage die")
    print("6. Character Abilities - Composite model with nested objects")
    print("\nFeatures demonstrated:")
    print("• Dynamic widget creation based on model definitions")
    print("• Support for string, int, float, bool, list, and object types")
    print("• Real-time validation with grimoire-model")
    print("• **DERIVED FIELDS** - Computed values that update automatically")
    print("• Property change tracking")
    print("• Validation error reporting")
    print("\n👉 Press numbers 1-6 to switch between test objects")
    print("👉 Edit properties in the left panel (e.g., change 'bonus' from 5 to 8)")
    print("👉 Watch derived fields update in real-time!")
    print("👉 Check the right panel for instantiated object state\n")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
