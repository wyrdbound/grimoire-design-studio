"""
Project Manager for GRIMOIRE Design Studio.

This module provides the ProjectManager class for creating, loading, and managing
GRIMOIRE projects and systems.
"""

import shutil
from pathlib import Path
from typing import Optional, Union

import yaml

from ..models.grimoire_definitions import (
    CompendiumDefinition,
    CompleteSystem,
    FlowDefinition,
    ModelDefinition,
    PromptDefinition,
    SourceDefinition,
    SystemDefinition,
    TableDefinition,
)
from ..models.project import GrimoireProject


class ProjectManager:
    """
    Manages GRIMOIRE projects and system loading.

    This class handles the creation of new projects, loading existing systems,
    and providing access to all components of a GRIMOIRE system.
    """

    def __init__(self) -> None:
        """Initialize the ProjectManager."""
        self.current_project: Optional[GrimoireProject] = None
        self.current_system: Optional[CompleteSystem] = None

    def create_project(
        self,
        project_name: str,
        project_path: Union[str, Path],
        system_id: Optional[str] = None,
    ) -> "GrimoireProject":
        """
        Create a new GRIMOIRE project with the standard directory structure.

        Args:
            project_name: Name of the project
            project_path: Path where the project should be created
            system_id: Optional system ID (defaults to project_name)

        Returns:
            GrimoireProject: The newly created project

        Raises:
            FileExistsError: If project directory already exists
            OSError: If unable to create directories
        """
        project_path = Path(project_path)

        if system_id is None:
            system_id = project_name.lower().replace(" ", "_")

        # Create main project directory
        if project_path.exists():
            raise FileExistsError(f"Project directory already exists: {project_path}")

        try:
            # Create directory structure
            project_path.mkdir(parents=True, exist_ok=False)

            # Create subdirectories
            (project_path / "models").mkdir()
            (project_path / "flows").mkdir()
            (project_path / "compendiums").mkdir()
            (project_path / "tables").mkdir()
            (project_path / "sources").mkdir()
            (project_path / "prompts").mkdir()

            # Create basic system.yaml
            system_config = {
                "id": system_id,
                "kind": "system",
                "name": project_name,
                "version": "1.0.0",
                "description": f"GRIMOIRE system for {project_name}",
                "currency": {
                    "base_unit": "gold",
                    "denominations": {
                        "cp": {"name": "Copper", "symbol": "cp", "value": 1},
                        "sp": {"name": "Silver", "symbol": "sp", "value": 10},
                        "gp": {"name": "Gold", "symbol": "gp", "value": 100},
                    },
                },
                "credits": {"author": project_name},
            }

            with open(project_path / "system.yaml", "w") as f:
                yaml.dump(system_config, f, default_flow_style=False, indent=2)

            # Create basic README
            readme_content = f"""# {project_name}

A GRIMOIRE system created with GRIMOIRE Design Studio.

## Project Structure

- `models/` - Character models, item definitions, etc.
- `flows/` - Workflow definitions for generation and automation
- `compendiums/` - Collections of game content (spells, items, etc.)
- `tables/` - Random generation tables
- `sources/` - Source material references
- `prompts/` - AI prompt templates
- `system.yaml` - System configuration and metadata

## Getting Started

1. Define your models in the `models/` directory
2. Create flows for content generation in `flows/`
3. Add content to compendiums for your system
4. Use the GRIMOIRE Design Studio to test and validate your system
"""

            with open(project_path / "README.md", "w") as f:
                f.write(readme_content)

            # Create and return project
            project = GrimoireProject(project_path, project_name, system_id)
            self.current_project = project

            return project

        except Exception as e:
            # Clean up on failure
            if project_path.exists():
                shutil.rmtree(project_path)
            raise OSError(f"Failed to create project: {e}") from e

    def load_system(self, system_path: Union[str, Path]) -> CompleteSystem:
        """
        Load a complete GRIMOIRE system from a directory.

        Args:
            system_path: Path to the system directory

        Returns:
            CompleteSystem: The loaded system with all components

        Raises:
            FileNotFoundError: If system.yaml not found
            yaml.YAMLError: If YAML parsing fails
            ValueError: If system definition is invalid
        """
        system_path = Path(system_path)

        if not system_path.exists():
            raise FileNotFoundError(f"System path does not exist: {system_path}")

        system_file = system_path / "system.yaml"
        if not system_file.exists():
            raise FileNotFoundError(f"system.yaml not found in: {system_path}")

        try:
            # Load system definition
            with open(system_file) as f:
                system_data = yaml.safe_load(f)

            if not system_data:
                raise ValueError("system.yaml is empty or invalid")

            system_def = SystemDefinition.from_dict(system_data)

            # Load all components
            models = self._load_models(system_path / "models")
            flows = self._load_flows(system_path / "flows")
            compendiums = self._load_compendiums(system_path / "compendiums")
            tables = self._load_tables(system_path / "tables")
            sources = self._load_sources(system_path / "sources")
            prompts = self._load_prompts(system_path / "prompts")

            # Create complete system
            complete_system = CompleteSystem(
                system=system_def,
                models=models,
                flows=flows,
                compendiums=compendiums,
                tables=tables,
                sources=sources,
                prompts=prompts,
            )

            self.current_system = complete_system

            return complete_system

        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse YAML in {system_file}: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load system from {system_path}: {e}") from e

    def _load_models(self, models_path: Path) -> dict[str, ModelDefinition]:
        """Load all model definitions from the models directory."""
        models: dict[str, ModelDefinition] = {}

        if not models_path.exists():
            return models

        for yaml_file in models_path.glob("**/*.yaml"):
            try:
                with open(yaml_file) as f:
                    model_data = yaml.safe_load(f)

                if model_data and isinstance(model_data, dict):
                    model = ModelDefinition.model_validate(model_data)
                    models[model.id] = model

            except Exception as e:
                # Log error but continue loading other models
                print(f"Warning: Failed to load model from {yaml_file}: {e}")

        return models

    def _load_flows(self, flows_path: Path) -> dict[str, FlowDefinition]:
        """Load all flow definitions from the flows directory."""
        flows: dict[str, FlowDefinition] = {}

        if not flows_path.exists():
            return flows

        for yaml_file in flows_path.glob("**/*.yaml"):
            try:
                with open(yaml_file) as f:
                    flow_data = yaml.safe_load(f)

                if flow_data and isinstance(flow_data, dict):
                    flow = FlowDefinition.from_dict(flow_data)
                    flows[flow.id] = flow

            except Exception as e:
                print(f"Warning: Failed to load flow from {yaml_file}: {e}")

        return flows

    def _load_compendiums(
        self, compendiums_path: Path
    ) -> dict[str, CompendiumDefinition]:
        """Load all compendium definitions from the compendiums directory."""
        compendiums: dict[str, CompendiumDefinition] = {}

        if not compendiums_path.exists():
            return compendiums

        for yaml_file in compendiums_path.glob("**/*.yaml"):
            try:
                with open(yaml_file) as f:
                    compendium_data = yaml.safe_load(f)

                if compendium_data and isinstance(compendium_data, dict):
                    compendium = CompendiumDefinition.from_dict(compendium_data)
                    compendiums[compendium.id] = compendium

            except Exception as e:
                print(f"Warning: Failed to load compendium from {yaml_file}: {e}")

        return compendiums

    def _load_tables(self, tables_path: Path) -> dict[str, TableDefinition]:
        """Load all table definitions from the tables directory."""
        tables: dict[str, TableDefinition] = {}

        if not tables_path.exists():
            return tables

        for yaml_file in tables_path.glob("**/*.yaml"):
            try:
                with open(yaml_file) as f:
                    table_data = yaml.safe_load(f)

                if table_data and isinstance(table_data, dict):
                    table = TableDefinition.from_dict(table_data)
                    tables[table.id] = table

            except Exception as e:
                print(f"Warning: Failed to load table from {yaml_file}: {e}")

        return tables

    def _load_sources(self, sources_path: Path) -> dict[str, SourceDefinition]:
        """Load all source definitions from the sources directory."""
        sources: dict[str, SourceDefinition] = {}

        if not sources_path.exists():
            return sources

        for yaml_file in sources_path.glob("**/*.yaml"):
            try:
                with open(yaml_file) as f:
                    source_data = yaml.safe_load(f)

                if source_data and isinstance(source_data, dict):
                    source = SourceDefinition.from_dict(source_data)
                    sources[source.id] = source

            except Exception as e:
                print(f"Warning: Failed to load source from {yaml_file}: {e}")

        return sources

    def _load_prompts(self, prompts_path: Path) -> dict[str, PromptDefinition]:
        """Load all prompt definitions from the prompts directory."""
        prompts: dict[str, PromptDefinition] = {}

        if not prompts_path.exists():
            return prompts

        for yaml_file in prompts_path.glob("**/*.yaml"):
            try:
                with open(yaml_file) as f:
                    prompt_data = yaml.safe_load(f)

                if prompt_data and isinstance(prompt_data, dict):
                    prompt = PromptDefinition.from_dict(prompt_data)
                    prompts[prompt.id] = prompt

            except Exception as e:
                print(f"Warning: Failed to load prompt from {yaml_file}: {e}")

        return prompts
