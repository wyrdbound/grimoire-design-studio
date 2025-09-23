#!/usr/bin/env python3
"""
Interactive Project Manager CLI for testing.

This script provides a simple command-line interface to test the Project Manager
functionality interactively.
"""

import sys
from pathlib import Path

from src.grimoire_studio.core.project_manager import ProjectManager


def main():
    """Main interactive CLI."""
    print("🎲 GRIMOIRE Project Manager Interactive CLI")
    print("=" * 50)

    pm = ProjectManager()

    while True:
        print("\n📋 Available Commands:")
        print("1. Create new project")
        print("2. Load existing system")
        print("3. Exit")

        choice = input("\n❓ Enter your choice (1-3): ").strip()

        if choice == "1":
            create_project_interactive(pm)
        elif choice == "2":
            load_system_interactive(pm)
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")


def create_project_interactive(pm: ProjectManager):
    """Interactive project creation."""
    print("\n🆕 Create New Project")
    print("-" * 20)

    # Get project details
    project_name = input("📝 Project name: ").strip()
    if not project_name:
        print("❌ Project name cannot be empty.")
        return

    system_id = input("🆔 System ID (e.g., 'my_rpg'): ").strip()
    if not system_id:
        system_id = project_name.lower().replace(" ", "_")
        print(f"🔧 Using auto-generated system ID: {system_id}")

    project_path = input(
        "📁 Project directory path (or press Enter for current dir): "
    ).strip()
    if not project_path:
        project_path = Path.cwd() / system_id
    else:
        project_path = Path(project_path)

    try:
        # Create the project
        project = pm.create_project(
            project_path=project_path, project_name=project_name, system_id=system_id
        )

        print("✅ Successfully created project!")
        print(f"📁 Location: {project.project_path}")
        print(f"📄 System file: {project.system_file}")

        # List created directories
        directories = ["models", "flows", "compendiums", "tables", "sources", "prompts"]
        print("📂 Created directories:")
        for dir_name in directories:
            print(f"   • {dir_name}/")

    except Exception as e:
        print(f"❌ Failed to create project: {e}")


def load_system_interactive(pm: ProjectManager):
    """Interactive system loading."""
    print("\n📖 Load Existing System")
    print("-" * 20)

    system_path = input("📁 System directory path: ").strip()
    if not system_path:
        print("❌ System path cannot be empty.")
        return

    system_path = Path(system_path)

    if not system_path.exists():
        print(f"❌ Directory does not exist: {system_path}")
        return

    if not (system_path / "system.yaml").exists():
        print(f"❌ No system.yaml found in: {system_path}")
        return

    try:
        # Load the system
        print("⏳ Loading system...")
        complete_system = pm.load_system(system_path)

        print("✅ Successfully loaded system!")
        print(f"🎲 System: {complete_system.system.name}")
        print(f"📖 Description: {complete_system.system.description}")

        # Show component summary
        components = [
            ("Models", complete_system.models),
            ("Flows", complete_system.flows),
            ("Compendiums", complete_system.compendiums),
            ("Tables", complete_system.tables),
            ("Sources", complete_system.sources),
            ("Prompts", complete_system.prompts),
        ]

        print("\n📊 Component Summary:")
        for name, component_dict in components:
            count = len(component_dict)
            icon = (
                "📋"
                if name == "Models"
                else "🔄"
                if name == "Flows"
                else "📚"
                if name == "Compendiums"
                else "🎯"
                if name == "Tables"
                else "📄"
                if name == "Sources"
                else "💭"
            )
            print(f"   {icon} {name}: {count}")

        # Optionally show details
        if input("\n❓ Show detailed component list? (y/N): ").lower().startswith("y"):
            show_component_details(complete_system)

    except Exception as e:
        print(f"❌ Failed to load system: {e}")


def show_component_details(complete_system):
    """Show detailed component information."""
    components = [
        ("📋 Models", complete_system.models),
        ("🔄 Flows", complete_system.flows),
        ("📚 Compendiums", complete_system.compendiums),
        ("🎯 Tables", complete_system.tables),
        ("📄 Sources", complete_system.sources),
        ("💭 Prompts", complete_system.prompts),
    ]

    for icon_name, component_dict in components:
        if component_dict:
            print(f"\n{icon_name}:")
            for comp_id, comp in component_dict.items():
                print(f"   • {comp.name} ({comp_id})")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
