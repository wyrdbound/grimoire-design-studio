"""
Project wrapper class for GRIMOIRE Design Studio.

This module provides the GrimoireProject class that represents a complete
GRIMOIRE project with metadata and file management capabilities.
"""

from pathlib import Path


class GrimoireProject:
    """
    Represents a GRIMOIRE project with metadata and file management.

    This class provides a high-level interface for working with GRIMOIRE
    projects, including file management, project metadata, and integration
    with the ProjectManager.
    """

    def __init__(self, project_path: Path, project_name: str, system_id: str):
        """
        Initialize a GRIMOIRE project.

        Args:
            project_path: Path to the project directory
            project_name: Display name of the project
            system_id: Unique system identifier
        """
        self.project_path = project_path
        self.project_name = project_name
        self.system_id = system_id
        self._system = None

    @property
    def system_file(self) -> Path:
        """Path to the system.yaml file."""
        return self.project_path / "system.yaml"

    @property
    def models_dir(self) -> Path:
        """Path to the models directory."""
        return self.project_path / "models"

    @property
    def flows_dir(self) -> Path:
        """Path to the flows directory."""
        return self.project_path / "flows"

    @property
    def compendiums_dir(self) -> Path:
        """Path to the compendiums directory."""
        return self.project_path / "compendiums"

    @property
    def tables_dir(self) -> Path:
        """Path to the tables directory."""
        return self.project_path / "tables"

    @property
    def sources_dir(self) -> Path:
        """Path to the sources directory."""
        return self.project_path / "sources"

    @property
    def prompts_dir(self) -> Path:
        """Path to the prompts directory."""
        return self.project_path / "prompts"

    @property
    def readme_file(self) -> Path:
        """Path to the README.md file."""
        return self.project_path / "README.md"

    def exists(self) -> bool:
        """Check if the project directory and system file exist."""
        return self.project_path.exists() and self.system_file.exists()

    def get_all_yaml_files(self) -> list[Path]:
        """
        Get a list of all YAML files in the project.

        Returns:
            List of Path objects for all .yaml files in the project
        """
        yaml_files = []

        # Add system.yaml if it exists
        if self.system_file.exists():
            yaml_files.append(self.system_file)

        # Search all subdirectories for YAML files
        for directory in [
            self.models_dir,
            self.flows_dir,
            self.compendiums_dir,
            self.tables_dir,
            self.sources_dir,
            self.prompts_dir,
        ]:
            if directory.exists():
                yaml_files.extend(directory.glob("**/*.yaml"))

        return sorted(yaml_files)

    def get_yaml_files_by_type(self, file_type: str) -> list[Path]:
        """
        Get YAML files of a specific type.

        Args:
            file_type: Type of files to get ('models', 'flows', 'compendiums',
                      'tables', 'sources', 'prompts')

        Returns:
            List of Path objects for YAML files of the specified type
        """
        type_mapping = {
            "models": self.models_dir,
            "flows": self.flows_dir,
            "compendiums": self.compendiums_dir,
            "tables": self.tables_dir,
            "sources": self.sources_dir,
            "prompts": self.prompts_dir,
        }

        directory = type_mapping.get(file_type)
        if directory and directory.exists():
            return sorted(directory.glob("**/*.yaml"))

        return []

    def create_file_path(self, file_type: str, filename: str) -> Path:
        """
        Create a path for a new file of the specified type.

        Args:
            file_type: Type of file ('models', 'flows', etc.)
            filename: Name of the file (with or without .yaml extension)

        Returns:
            Path object for the new file
        """
        if not filename.endswith(".yaml"):
            filename += ".yaml"

        type_mapping = {
            "models": self.models_dir,
            "flows": self.flows_dir,
            "compendiums": self.compendiums_dir,
            "tables": self.tables_dir,
            "sources": self.sources_dir,
            "prompts": self.prompts_dir,
        }

        directory = type_mapping.get(file_type)
        if directory:
            directory.mkdir(parents=True, exist_ok=True)
            return directory / filename

        raise ValueError(f"Unknown file type: {file_type}")

    def __str__(self) -> str:
        """String representation of the project."""
        return (
            f"GrimoireProject(name='{self.project_name}', path='{self.project_path}')"
        )

    def __repr__(self) -> str:
        """Detailed string representation of the project."""
        return (
            f"GrimoireProject(project_name='{self.project_name}', "
            f"system_id='{self.system_id}', "
            f"project_path='{self.project_path}')"
        )
