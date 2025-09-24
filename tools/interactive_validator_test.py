#!/usr/bin/env python3
"""
Interactive Validator CLI for testing.

This script provides a simple command-line interface to test the Validator
functionality interactively on real GRIMOIRE systems.
"""

import sys
from pathlib import Path

from src.grimoire_studio.core.project_manager import ProjectManager
from src.grimoire_studio.core.validator import ValidationSeverity, YamlValidator


def main():
    """Main interactive CLI."""
    print("🔍 GRIMOIRE Validator Interactive CLI")
    print("=" * 50)

    validator = YamlValidator()
    pm = ProjectManager()

    while True:
        print("\n📋 Available Commands:")
        print("1. Validate single YAML file")
        print("2. Validate entire system")
        print("3. Validate system with cross-references")
        print("4. Exit")

        choice = input("\n❓ Enter your choice (1-4): ").strip()

        if choice == "1":
            validate_single_file(validator)
        elif choice == "2":
            validate_system_files(validator)
        elif choice == "3":
            validate_system_complete(validator, pm)
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")


def validate_single_file(validator: YamlValidator):
    """Interactive single file validation."""
    print("\n📄 Validate Single YAML File")
    print("-" * 30)

    file_path = input("📁 File path: ").strip()
    if not file_path:
        print("❌ File path cannot be empty.")
        return

    file_path = Path(file_path)

    if not file_path.exists():
        print(f"❌ File does not exist: {file_path}")
        return

    if not file_path.is_file():
        print(f"❌ Path is not a file: {file_path}")
        return

    try:
        print("⏳ Validating file...")
        results = validator.validate_file(file_path)

        print(f"\n✅ Validation completed for: {file_path.name}")
        display_validation_results(results)

    except Exception as e:
        print(f"❌ Failed to validate file: {e}")


def validate_system_files(validator: YamlValidator):
    """Interactive system files validation (without cross-references)."""
    print("\n📁 Validate System Files")
    print("-" * 25)

    system_path = input("📁 System directory path: ").strip()
    if not system_path:
        print("❌ System path cannot be empty.")
        return

    system_path = Path(system_path)

    if not system_path.exists():
        print(f"❌ Directory does not exist: {system_path}")
        return

    if not system_path.is_dir():
        print(f"❌ Path is not a directory: {system_path}")
        return

    try:
        print("⏳ Scanning for YAML files...")

        # Only scan official GRIMOIRE directories (not fixtures or other non-spec directories)
        official_dirs = [
            "models",
            "flows",
            "compendiums",
            "tables",
            "sources",
            "prompts",
        ]
        yaml_files = []

        # Add system.yaml
        if (system_path / "system.yaml").exists():
            yaml_files.append(system_path / "system.yaml")

        # Add files from official directories only
        for dir_name in official_dirs:
            dir_path = system_path / dir_name
            if dir_path.exists():
                yaml_files.extend(dir_path.rglob("*.yaml"))
                yaml_files.extend(dir_path.rglob("*.yml"))

        if not yaml_files:
            print(
                f"❌ No YAML files found in official GRIMOIRE directories: {system_path}"
            )
            return

        print(f"📋 Found {len(yaml_files)} YAML files in official directories")

        all_results = []
        for yaml_file in yaml_files:
            print(f"🔍 Validating: {yaml_file.relative_to(system_path)}")
            results = validator.validate_file(yaml_file)
            all_results.extend(results)

        print(f"\n✅ Validation completed for {len(yaml_files)} files")
        display_validation_results(all_results, group_by_file=True)

    except Exception as e:
        print(f"❌ Failed to validate system files: {e}")


def validate_system_complete(validator: YamlValidator, pm: ProjectManager):
    """Interactive complete system validation with cross-references."""
    print("\n🎯 Validate Complete System")
    print("-" * 30)

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
        print("⏳ Loading and validating complete system...")

        # First, load the system
        complete_system = pm.load_system(system_path)

        # Then validate with cross-references
        results = validator.validate_system(system_path, complete_system)

        print(f"\n✅ Complete system validation finished")
        print(f"🎲 System: {complete_system.system.name}")

        # Show component counts
        components = [
            ("Models", complete_system.models),
            ("Flows", complete_system.flows),
            ("Compendiums", complete_system.compendiums),
            ("Tables", complete_system.tables),
            ("Sources", complete_system.sources),
            ("Prompts", complete_system.prompts),
        ]

        print("\n📊 System Components:")
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

        display_validation_results(results, group_by_file=True)

    except Exception as e:
        print(f"❌ Failed to validate complete system: {e}")


def display_validation_results(results, group_by_file=False):
    """Display validation results in a formatted way."""
    if not results:
        print("\n🎉 No validation issues found! System looks good.")
        return

    # Count results by severity
    severity_counts = {
        ValidationSeverity.INFO: 0,
        ValidationSeverity.WARNING: 0,
        ValidationSeverity.ERROR: 0,
        ValidationSeverity.CRITICAL: 0,
    }

    for result in results:
        severity_counts[result.severity] += 1

    # Display summary
    print(f"\n📈 Validation Summary:")
    print(f"   🚨 Critical: {severity_counts[ValidationSeverity.CRITICAL]}")
    print(f"   ❌ Errors:   {severity_counts[ValidationSeverity.ERROR]}")
    print(f"   ⚠️  Warnings: {severity_counts[ValidationSeverity.WARNING]}")
    print(f"   ℹ️  Info:     {severity_counts[ValidationSeverity.INFO]}")

    # Show details if requested
    if input("\n❓ Show detailed validation results? (y/N): ").lower().startswith("y"):
        print("\n" + "=" * 60)

        if group_by_file:
            # Group results by file
            file_results = {}
            for result in results:
                file_key = str(result.file_path) if result.file_path else "Unknown"
                if file_key not in file_results:
                    file_results[file_key] = []
                file_results[file_key].append(result)

            for file_path, file_results_list in file_results.items():
                print(f"\n📄 {Path(file_path).name}:")
                print("-" * 40)
                for result in file_results_list:
                    print(f"  {result}")
        else:
            # Show all results sequentially
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result}")

    # Show actionable summary
    critical_and_errors = (
        severity_counts[ValidationSeverity.CRITICAL]
        + severity_counts[ValidationSeverity.ERROR]
    )
    if critical_and_errors > 0:
        print(f"\n⚠️  Found {critical_and_errors} issues that need attention!")
        print("   Please review and fix errors before proceeding.")
    elif severity_counts[ValidationSeverity.WARNING] > 0:
        print(f"\n⚠️  Found {severity_counts[ValidationSeverity.WARNING]} warnings.")
        print("   System should work but consider addressing warnings.")
    else:
        print("\n✨ System validation passed with only informational messages!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
