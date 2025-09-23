"""GRIMOIRE system definition dataclasses.

This module contains all the dataclass definitions needed to represent
GRIMOIRE system components based on the official GRIMOIRE specification.
These models match the actual YAML format used by GRIMOIRE systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union


@dataclass
class CurrencyDenomination:
    """Definition of a currency denomination.

    Attributes:
        name: Full name of the currency (e.g., "copper", "gold")
        symbol: Abbreviated symbol (e.g., "cp", "gp")
        value: Exchange rate relative to base unit
        weight: Physical weight per coin (optional)
    """

    name: str
    symbol: str
    value: int
    weight: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CurrencyDenomination:
        """Create CurrencyDenomination from dictionary data."""
        return cls(
            name=data["name"],
            symbol=data["symbol"],
            value=data["value"],
            weight=data.get("weight"),
        )


@dataclass
class Currency:
    """Definition of a currency system.

    Attributes:
        base_unit: The fundamental unit for internal calculations
        denominations: Map of currency types by ID
    """

    base_unit: str
    denominations: dict[str, CurrencyDenomination] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Currency:
        """Create Currency from dictionary data."""
        denominations = {
            denom_id: CurrencyDenomination.from_dict(denom_data)
            for denom_id, denom_data in data.get("denominations", {}).items()
        }

        return cls(
            base_unit=data["base_unit"],
            denominations=denominations,
        )


@dataclass
class Credits:
    """Attribution information for the original system.

    Attributes:
        author: Original creator(s) of the system
        license: License under which system is distributed
        publisher: Publishing company or entity
        source_url: Official website or purchase link
    """

    author: str | None = None
    license: str | None = None
    publisher: str | None = None
    source_url: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Credits:
        """Create Credits from dictionary data."""
        return cls(
            author=data.get("author"),
            license=data.get("license"),
            publisher=data.get("publisher"),
            source_url=data.get("source_url"),
        )


@dataclass
class SystemDefinition:
    """Definition of a GRIMOIRE system with metadata and configuration.

    Attributes:
        id: Unique identifier for the system
        kind: Always "system" for system definitions
        name: Human-readable name for the system
        description: Detailed description of the system
        version: Version number for the system definition
        default_source: ID of default source book/ruleset
        currency: Currency system definition (optional)
        credits: Attribution information (optional)
    """

    id: str
    kind: str
    name: str
    description: str | None = None
    version: int = 1
    default_source: str | None = None
    currency: Currency | None = None
    credits: Credits | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SystemDefinition:
        """Create SystemDefinition from dictionary data."""
        currency = None
        if "currency" in data:
            currency = Currency.from_dict(data["currency"])

        credits = None
        if "credits" in data:
            credits = Credits.from_dict(data["credits"])

        return cls(
            id=data["id"],
            kind=data["kind"],
            name=data["name"],
            description=data.get("description"),
            version=data.get("version", 1),
            default_source=data.get("default_source"),
            currency=currency,
            credits=credits,
        )


@dataclass
class AttributeDefinition:
    """Definition of a model attribute with type and constraints.

    Attributes:
        type: Data type (str, int, float, bool, roll, list, dict, or model name)
        default: Default value if not provided
        range: Valid range for numeric types (e.g., "1..20", "0..")
        enum: List of allowed values for string types
        derived: Formula for calculated attributes
        of: Element type for list attributes
        optional: Whether the attribute can be null/undefined
    """

    type: str
    default: Any | None = None
    range: str | None = None
    enum: list[str] | None = None
    derived: str | None = None
    of: str | None = None
    optional: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttributeDefinition:
        """Create AttributeDefinition from dictionary data."""
        return cls(
            type=data["type"],
            default=data.get("default"),
            range=data.get("range"),
            enum=data.get("enum"),
            derived=data.get("derived"),
            of=data.get("of"),
            optional=data.get("optional"),
        )


@dataclass
class ValidationRule:
    """A validation rule for model instances.

    Attributes:
        expression: Boolean expression that must evaluate to true
        message: Human-readable error message when validation fails
    """

    expression: str
    message: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationRule:
        """Create ValidationRule from dictionary data."""
        return cls(
            expression=data["expression"],
            message=data["message"],
        )


@dataclass
class ModelDefinition:
    """Definition of a GRIMOIRE model with attributes and validation.

    Attributes:
        id: Unique identifier for the model
        kind: Always "model" for model definitions
        name: Human-readable name for the model
        description: Detailed description of what the model represents
        version: Version number for the model definition
        extends: Array of model IDs that this model inherits from
        attributes: Map of attribute definitions by name
        validations: Array of validation rules
    """

    id: str
    kind: str
    name: str
    description: str | None = None
    version: int = 1
    extends: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    validations: list[ValidationRule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelDefinition:
        """Create ModelDefinition from dictionary data."""
        # Parse nested attribute definitions recursively
        attributes = cls._parse_attributes(data.get("attributes", {}))

        validations = [
            ValidationRule.from_dict(val_data)
            for val_data in data.get("validations", [])
        ]

        return cls(
            id=data["id"],
            kind=data["kind"],
            name=data["name"],
            description=data.get("description"),
            version=data.get("version", 1),
            extends=data.get("extends", []),
            attributes=attributes,
            validations=validations,
        )

    @classmethod
    def _parse_attributes(cls, attrs: dict[str, Any]) -> dict[str, Any]:
        """Recursively parse attribute definitions."""
        parsed_attrs: dict[str, Any] = {}

        for attr_name, attr_data in attrs.items():
            if isinstance(attr_data, dict):
                # Check if this looks like an attribute definition
                if "type" in attr_data:
                    parsed_attrs[attr_name] = AttributeDefinition.from_dict(attr_data)
                else:
                    # Nested structure - recurse
                    parsed_attrs[attr_name] = cls._parse_attributes(attr_data)
            else:
                # Direct value
                parsed_attrs[attr_name] = attr_data

        return parsed_attrs


@dataclass
class FlowInputOutput:
    """Definition of flow input or output parameter.

    Attributes:
        type: Data type of the parameter
        id: Identifier used within the flow
        required: Whether input is mandatory (inputs only)
        validate: Whether to run validation (outputs only)
    """

    type: str
    id: str
    required: bool | None = None
    validate: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FlowInputOutput:
        """Create FlowInputOutput from dictionary data."""
        return cls(
            type=data["type"],
            id=data["id"],
            required=data.get("required"),
            validate=data.get("validate"),
        )


@dataclass
class FlowVariable:
    """Definition of flow local variable.

    Attributes:
        type: Data type of the variable
        id: Identifier used within the flow
        description: Optional description
        validate: Whether to validate the variable
    """

    type: str
    id: str
    description: str | None = None
    validate: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FlowVariable:
        """Create FlowVariable from dictionary data."""
        return cls(
            type=data["type"],
            id=data["id"],
            description=data.get("description"),
            validate=data.get("validate"),
        )


@dataclass
class FlowStep:
    """Definition of a flow step with actions and configuration.

    Attributes:
        id: Unique identifier for the step
        name: Human-readable name for the step (optional)
        type: Step type (dice_roll, player_choice, llm_generation, etc.)
        prompt: Text displayed to the user (optional)
        condition: Optional condition for step execution
        parallel: Whether step executes in parallel (optional)
        pre_actions: Actions to run before step execution (optional)
        actions: Actions to run during/after step execution
        next_step: ID of next step (optional)

        # Step-specific fields (depending on type)
        roll: Dice expression (for dice_roll)
        sequence: Sequence definition (for dice_sequence)
    """

    id: str
    name: str
    type: str
    prompt: str | None = None
    condition: str | None = None
    parallel: bool | None = None
    pre_actions: list[dict[str, Any]] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)
    next_step: str | None = None

    # Step-specific fields (stored as generic dict)
    step_config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FlowStep:
        """Create FlowStep from dictionary data."""
        # Extract standard fields
        standard_fields = {
            "id",
            "name",
            "type",
            "prompt",
            "condition",
            "parallel",
            "pre_actions",
            "actions",
            "next_step",
        }

        # Store step-specific config separately
        step_config = {k: v for k, v in data.items() if k not in standard_fields}

        return cls(
            id=data["id"],
            name=data["name"],
            type=data["type"],
            prompt=data.get("prompt"),
            condition=data.get("condition"),
            parallel=data.get("parallel"),
            pre_actions=data.get("pre_actions", []),
            actions=data.get("actions", []),
            next_step=data.get("next_step"),
            step_config=step_config,
        )


@dataclass
class FlowDefinition:
    """Definition of a GRIMOIRE flow with steps and metadata.

    Attributes:
        id: Unique identifier for the flow
        kind: Always "flow" for flow definitions
        name: Human-readable name for the flow
        description: Detailed description of the flow's purpose
        version: Version number for the flow definition
        inputs: Array of input parameter definitions
        outputs: Array of output parameter definitions
        variables: Array of local variable definitions
        steps: Array of step definitions that define the flow logic
        resume_points: Array of step IDs where execution can be resumed
    """

    id: str
    kind: str
    name: str
    description: str | None = None
    version: int = 1
    inputs: list[FlowInputOutput] = field(default_factory=list)
    outputs: list[FlowInputOutput] = field(default_factory=list)
    variables: list[FlowVariable] = field(default_factory=list)
    steps: list[FlowStep] = field(default_factory=list)
    resume_points: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FlowDefinition:
        """Create FlowDefinition from dictionary data."""
        inputs = [
            FlowInputOutput.from_dict(input_data)
            for input_data in data.get("inputs", [])
        ]

        outputs = [
            FlowInputOutput.from_dict(output_data)
            for output_data in data.get("outputs", [])
        ]

        variables = [
            FlowVariable.from_dict(var_data) for var_data in data.get("variables", [])
        ]

        steps = [FlowStep.from_dict(step_data) for step_data in data.get("steps", [])]

        return cls(
            id=data["id"],
            kind=data["kind"],
            name=data["name"],
            description=data.get("description"),
            version=data.get("version", 1),
            inputs=inputs,
            outputs=outputs,
            variables=variables,
            steps=steps,
            resume_points=data.get("resume_points", []),
        )


@dataclass
class CompendiumDefinition:
    """Definition of a GRIMOIRE compendium with entries and metadata.

    Attributes:
        id: Unique identifier for the compendium
        kind: Always "compendium" for compendium definitions
        name: Human-readable name for the compendium
        description: Detailed description of the compendium
        version: Version number for the compendium definition
        model: Model ID for compendium items (optional)
        entries: Dictionary of compendium entry items
    """

    id: str
    kind: str
    name: str
    description: str | None = None
    version: int = 1
    model: str | None = None
    entries: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompendiumDefinition:
        """Create CompendiumDefinition from dictionary data."""
        return cls(
            id=data["id"],
            kind=data["kind"],
            name=data["name"],
            description=data.get("description"),
            version=data.get("version", 1),
            model=data.get("model"),
            entries=data.get("entries", {}),
        )


@dataclass
class TableDefinition:
    """Definition of a GRIMOIRE table with rows and metadata.

    Attributes:
        id: Unique identifier for the table
        kind: Always "table" for table definitions
        name: Human-readable name for the table
        description: Detailed description of the table
        version: Version number for the table definition
        dice: Dice expression for rolling on the table
        entries: List of table entries with ranges and values
    """

    id: str
    kind: str
    name: str
    description: str | None = None
    version: int = 1
    dice: str | None = None
    entries: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TableDefinition:
        """Create TableDefinition from dictionary data."""
        return cls(
            id=data["id"],
            kind=data["kind"],
            name=data["name"],
            description=data.get("description"),
            version=data.get("version", 1),
            dice=data.get("dice"),
            entries=data.get("entries", []),
        )


@dataclass
class SourceDefinition:
    """Definition of a GRIMOIRE source with reference information.

    Attributes:
        id: Unique identifier for the source
        kind: Always "source" for source definitions
        name: Human-readable name for the source
        description: Detailed description of the source
        version: Version number for the source definition
        type: Source type (book, website, manual, etc.)
        author: Author information (optional)
        publisher: Publisher information (optional)
        year: Publication year (optional)
        url: URL reference (optional)
        isbn: ISBN number (optional)
    """

    id: str
    kind: str
    name: str
    description: str | None = None
    version: int = 1
    type: str | None = None
    author: str | None = None
    publisher: str | None = None
    year: int | None = None
    url: str | None = None
    isbn: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceDefinition:
        """Create SourceDefinition from dictionary data."""
        return cls(
            id=data["id"],
            kind=data["kind"],
            name=data["name"],
            description=data.get("description"),
            version=data.get("version", 1),
            type=data.get("type"),
            author=data.get("author"),
            publisher=data.get("publisher"),
            year=data.get("year"),
            url=data.get("url"),
            isbn=data.get("isbn"),
        )


@dataclass
class PromptDefinition:
    """Definition of a GRIMOIRE prompt for LLM generation.

    Attributes:
        id: Unique identifier for the prompt
        kind: Always "prompt" for prompt definitions
        name: Human-readable name for the prompt
        description: Detailed description of the prompt
        version: Version number for the prompt definition
        template: Prompt template with variable substitution
        variables: Variable definitions for the template
        llm_settings: Default LLM configuration (optional)
    """

    id: str
    kind: str
    name: str
    description: str | None = None
    version: int = 1
    template: str = ""
    variables: dict[str, Any] = field(default_factory=dict)
    llm_settings: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptDefinition:
        """Create PromptDefinition from dictionary data."""
        return cls(
            id=data["id"],
            kind=data["kind"],
            name=data["name"],
            description=data.get("description"),
            version=data.get("version", 1),
            template=data.get("template", ""),
            variables=data.get("variables", {}),
            llm_settings=data.get("llm_settings", {}),
        )


@dataclass
class CompleteSystem:
    """Complete GRIMOIRE system with all components.

    This class represents a fully loaded GRIMOIRE system containing
    all models, flows, compendiums, tables, sources, and prompts.

    Attributes:
        system: The system definition
        models: Dictionary of model definitions by ID
        flows: Dictionary of flow definitions by ID
        compendiums: Dictionary of compendium definitions by ID
        tables: Dictionary of table definitions by ID
        sources: Dictionary of source definitions by ID
        prompts: Dictionary of prompt definitions by ID
    """

    system: SystemDefinition
    models: dict[str, ModelDefinition] = field(default_factory=dict)
    flows: dict[str, FlowDefinition] = field(default_factory=dict)
    compendiums: dict[str, CompendiumDefinition] = field(default_factory=dict)
    tables: dict[str, TableDefinition] = field(default_factory=dict)
    sources: dict[str, SourceDefinition] = field(default_factory=dict)
    prompts: dict[str, PromptDefinition] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompleteSystem:
        """Create CompleteSystem from dictionary data.

        Args:
            data: Dictionary containing system data with nested components

        Returns:
            CompleteSystem instance with all components loaded
        """
        # Load system definition
        system = SystemDefinition.from_dict(data.get("system", {}))

        # Load all component types
        models = {
            model_id: ModelDefinition.from_dict(model_data)
            for model_id, model_data in data.get("models", {}).items()
        }

        flows = {
            flow_id: FlowDefinition.from_dict(flow_data)
            for flow_id, flow_data in data.get("flows", {}).items()
        }

        compendiums = {
            comp_id: CompendiumDefinition.from_dict(comp_data)
            for comp_id, comp_data in data.get("compendiums", {}).items()
        }

        tables = {
            table_id: TableDefinition.from_dict(table_data)
            for table_id, table_data in data.get("tables", {}).items()
        }

        sources = {
            source_id: SourceDefinition.from_dict(source_data)
            for source_id, source_data in data.get("sources", {}).items()
        }

        prompts = {
            prompt_id: PromptDefinition.from_dict(prompt_data)
            for prompt_id, prompt_data in data.get("prompts", {}).items()
        }

        return cls(
            system=system,
            models=models,
            flows=flows,
            compendiums=compendiums,
            tables=tables,
            sources=sources,
            prompts=prompts,
        )


# Type aliases for convenience
GrimoireDefinition = Union[
    SystemDefinition,
    ModelDefinition,
    FlowDefinition,
    CompendiumDefinition,
    TableDefinition,
    SourceDefinition,
    PromptDefinition,
]
