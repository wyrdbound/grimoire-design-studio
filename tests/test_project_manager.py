"""
Tests for the ProjectManager and GrimoireProject classes.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from grimoire_studio.core.project_manager import ProjectManager
from grimoire_studio.models.grimoire_definitions import (
    CompendiumDefinition,
    CompleteSystem,
    FlowDefinition,
    ModelDefinition,
    SystemDefinition,
)
from grimoire_studio.models.project import GrimoireProject


class TestGrimoireProject:
    """Test the GrimoireProject class."""

    def test_project_initialization(self):
        """Test basic project initialization."""
        project_path = Path("/tmp/test_project")
        project = GrimoireProject(project_path, "Test Project", "test_system")

        assert project.project_path == project_path
        assert project.project_name == "Test Project"
        assert project.system_id == "test_system"
        assert project.system_file == project_path / "system.yaml"
        assert project.models_dir == project_path / "models"
        assert project.flows_dir == project_path / "flows"
        assert project.compendiums_dir == project_path / "compendiums"

    def test_project_exists_false(self):
        """Test project exists returns False for non-existent project."""
        project_path = Path("/tmp/nonexistent_project")
        project = GrimoireProject(project_path, "Test", "test")

        assert not project.exists()

    def test_create_file_path(self):
        """Test creating file paths for different types."""
        project_path = Path("/tmp/test_project")
        project = GrimoireProject(project_path, "Test", "test")

        # Test with .yaml extension
        model_path = project.create_file_path("models", "character.yaml")
        assert model_path == project_path / "models" / "character.yaml"

        # Test without .yaml extension
        flow_path = project.create_file_path("flows", "generation")
        assert flow_path == project_path / "flows" / "generation.yaml"

        # Test invalid type
        with pytest.raises(ValueError, match="Unknown file type"):
            project.create_file_path("invalid", "test")

    def test_string_representation(self):
        """Test string representation of project."""
        project_path = Path("/tmp/test_project")
        project = GrimoireProject(project_path, "Test Project", "test_system")

        str_repr = str(project)
        assert "Test Project" in str_repr
        assert str(project_path) in str_repr

        repr_str = repr(project)
        assert "test_system" in repr_str
        assert "Test Project" in repr_str


class TestProjectManager:
    """Test the ProjectManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = None
        self.project_manager = ProjectManager()

    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up and tear down for each test."""
        self.setUp()
        yield
        self.tearDown()

    def test_project_manager_initialization(self):
        """Test ProjectManager initialization."""
        pm = ProjectManager()
        assert pm.current_project is None
        assert pm.current_system is None

    def test_create_project_success(self):
        """Test successful project creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"

            project = self.project_manager.create_project(
                "Test Project", project_path, "test_system"
            )

            # Check project object
            assert isinstance(project, GrimoireProject)
            assert project.project_name == "Test Project"
            assert project.system_id == "test_system"
            assert self.project_manager.current_project == project

            # Check directory structure
            assert project_path.exists()
            assert (project_path / "models").exists()
            assert (project_path / "flows").exists()
            assert (project_path / "compendiums").exists()
            assert (project_path / "tables").exists()
            assert (project_path / "sources").exists()
            assert (project_path / "prompts").exists()

            # Check system.yaml
            assert (project_path / "system.yaml").exists()
            with open(project_path / "system.yaml") as f:
                system_data = yaml.safe_load(f)

            assert system_data["id"] == "test_system"
            assert system_data["name"] == "Test Project"
            assert system_data["kind"] == "system"

            # Check README
            assert (project_path / "README.md").exists()
            readme_content = (project_path / "README.md").read_text()
            assert "Test Project" in readme_content

    def test_create_project_default_system_id(self):
        """Test project creation with default system ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"

            project = self.project_manager.create_project(
                "My Cool System", project_path
            )

            assert project.system_id == "my_cool_system"

            with open(project_path / "system.yaml") as f:
                system_data = yaml.safe_load(f)
            assert system_data["id"] == "my_cool_system"

    def test_create_project_existing_directory(self):
        """Test project creation fails when directory exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "existing"
            project_path.mkdir()

            with pytest.raises(FileExistsError):
                self.project_manager.create_project("Test", project_path)

    def test_load_system_knave_success(self):
        """Test loading the actual Knave system."""
        # Use the real Knave system in the repo
        knave_path = Path("systems/knave_1e")

        if knave_path.exists():
            system = self.project_manager.load_system(knave_path)

            assert isinstance(system, CompleteSystem)
            assert isinstance(system.system, SystemDefinition)
            assert system.system.id == "knave_1e"

            # Check that models were loaded
            assert len(system.models) > 0

            # Check that compendiums were loaded
            assert len(system.compendiums) > 0

            # Verify current_system is set
            assert self.project_manager.current_system == system

    def test_load_system_missing_directory(self):
        """Test loading system from non-existent directory."""
        with pytest.raises(FileNotFoundError):
            self.project_manager.load_system("/nonexistent/path")

    def test_load_system_missing_system_yaml(self):
        """Test loading system without system.yaml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(FileNotFoundError):
                self.project_manager.load_system(temp_dir)

    def test_load_system_invalid_yaml(self):
        """Test loading system with invalid YAML."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_file = Path(temp_dir) / "system.yaml"
            system_file.write_text("invalid: yaml: content: [")

            with pytest.raises(yaml.YAMLError):
                self.project_manager.load_system(temp_dir)

    def test_load_system_empty_yaml(self):
        """Test loading system with empty YAML."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_file = Path(temp_dir) / "system.yaml"
            system_file.write_text("")

            with pytest.raises(ValueError):
                self.project_manager.load_system(temp_dir)

    def test_load_models_success(self):
        """Test loading model definitions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir) / "models"
            models_dir.mkdir()

            # Create a test model
            model_data = {
                "id": "test_model",
                "kind": "model",
                "name": "Test Model",
                "attributes": {
                    "name": {"type": "string", "required": True},
                    "level": {"type": "integer", "default": 1},
                },
            }

            model_file = models_dir / "test_model.yaml"
            with open(model_file, "w") as f:
                yaml.dump(model_data, f)

            models = self.project_manager._load_models(models_dir)

            assert "test_model" in models
            assert isinstance(models["test_model"], ModelDefinition)
            assert models["test_model"].name == "Test Model"

    def test_load_models_invalid_file(self):
        """Test loading models with invalid file (should skip and continue)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir) / "models"
            models_dir.mkdir()

            # Create invalid YAML file
            invalid_file = models_dir / "invalid.yaml"
            invalid_file.write_text("invalid: yaml: [")

            # Create valid model
            model_data = {
                "id": "valid_model",
                "kind": "model",
                "name": "Valid Model",
                "attributes": {},
            }
            valid_file = models_dir / "valid.yaml"
            with open(valid_file, "w") as f:
                yaml.dump(model_data, f)

            # Should load the valid model and skip the invalid one
            models = self.project_manager._load_models(models_dir)

            assert len(models) == 1
            assert "valid_model" in models

    def test_load_models_nonexistent_directory(self):
        """Test loading models from non-existent directory."""
        models = self.project_manager._load_models(Path("/nonexistent"))
        assert models == {}

    def test_load_compendiums_success(self):
        """Test loading compendium definitions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            compendiums_dir = Path(temp_dir) / "compendiums"
            compendiums_dir.mkdir()

            # Create test compendium
            compendium_data = {
                "id": "test_compendium",
                "kind": "compendium",
                "name": "Test Compendium",
                "description": "A test compendium",
                "entries": [
                    {"id": "item1", "name": "Test Item", "description": "A test item"}
                ],
            }

            compendium_file = compendiums_dir / "test_compendium.yaml"
            with open(compendium_file, "w") as f:
                yaml.dump(compendium_data, f)

            compendiums = self.project_manager._load_compendiums(compendiums_dir)

            assert "test_compendium" in compendiums
            assert isinstance(compendiums["test_compendium"], CompendiumDefinition)
            assert compendiums["test_compendium"].name == "Test Compendium"

    def test_load_flows_success(self):
        """Test loading flow definitions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            flows_dir = Path(temp_dir) / "flows"
            flows_dir.mkdir()

            # Create test flow
            flow_data = {
                "id": "test_flow",
                "kind": "flow",
                "name": "Test Flow",
                "description": "A test flow",
                "inputs": [],
                "outputs": [],
                "variables": [],
                "steps": [],
            }

            flow_file = flows_dir / "test_flow.yaml"
            with open(flow_file, "w") as f:
                yaml.dump(flow_data, f)

            flows = self.project_manager._load_flows(flows_dir)

            assert "test_flow" in flows
            assert isinstance(flows["test_flow"], FlowDefinition)
            assert flows["test_flow"].name == "Test Flow"


class TestProjectManagerIntegration:
    """Integration tests for ProjectManager with real data."""

    def test_create_and_load_project_roundtrip(self):
        """Test creating a project and then loading it back."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "roundtrip_project"

            pm = ProjectManager()

            # Create project
            project = pm.create_project("Roundtrip Test", project_path)
            assert project.exists()

            # Load the created project as a system
            system = pm.load_system(project_path)

            assert isinstance(system, CompleteSystem)
            assert system.system.name == "Roundtrip Test"
            assert system.system.id == "roundtrip_test"

    def test_load_system_with_all_components(self):
        """Test loading a system with all component types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = Path(temp_dir)

            # Create system.yaml
            system_data = {
                "id": "full_system",
                "kind": "system",
                "name": "Full System Test",
                "version": "1.0.0",
                "description": "A system with all components",
                "currency": {
                    "base_unit": "gold",
                    "denominations": {
                        "gp": {"name": "Gold", "symbol": "gp", "value": 1}
                    },
                },
                "credits": {"author": "Test Author"},
            }

            with open(system_path / "system.yaml", "w") as f:
                yaml.dump(system_data, f)

            # Create directories and sample files
            for dir_name, sample_data in [
                (
                    "models",
                    {
                        "id": "character",
                        "kind": "model",
                        "name": "Character",
                        "attributes": {"name": {"type": "string"}},
                    },
                ),
                (
                    "flows",
                    {
                        "id": "gen_character",
                        "kind": "flow",
                        "name": "Generate Character",
                        "description": "Generate a character",
                        "inputs": [],
                        "outputs": [],
                        "variables": [],
                        "steps": [],
                    },
                ),
                (
                    "compendiums",
                    {
                        "id": "items",
                        "kind": "compendium",
                        "name": "Items",
                        "description": "Item compendium",
                        "entries": [],
                    },
                ),
                (
                    "tables",
                    {
                        "id": "random_table",
                        "kind": "table",
                        "name": "Random Table",
                        "description": "A random table",
                        "entries": [{"min": 1, "max": 1, "result": "Result 1"}],
                    },
                ),
                (
                    "sources",
                    {
                        "id": "rulebook",
                        "kind": "source",
                        "name": "Rulebook",
                        "description": "Main rulebook",
                        "type": "book",
                        "content": "",
                    },
                ),
                (
                    "prompts",
                    {
                        "id": "char_gen",
                        "kind": "prompt",
                        "name": "Character Generator",
                        "description": "Generate character",
                        "template": "Generate a character",
                        "variables": {},
                    },
                ),
            ]:
                dir_path = system_path / dir_name
                dir_path.mkdir()
                file_path = dir_path / f"{sample_data['id']}.yaml"
                with open(file_path, "w") as f:
                    yaml.dump(sample_data, f)

            # Load the system
            pm = ProjectManager()
            system = pm.load_system(system_path)

            # Verify all components loaded
            assert len(system.models) == 1
            assert len(system.flows) == 1
            assert len(system.compendiums) == 1
            assert len(system.tables) == 1
            assert len(system.sources) == 1
            assert len(system.prompts) == 1

            assert "character" in system.models
            assert "gen_character" in system.flows
            assert "items" in system.compendiums
            assert "random_table" in system.tables
            assert "rulebook" in system.sources
            assert "char_gen" in system.prompts
