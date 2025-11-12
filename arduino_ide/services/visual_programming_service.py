"""
Visual Programming Service
Provides block-based programming capabilities similar to Scratch/Blockly
"""

import json
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class BlockType(Enum):
    """Types of programming blocks"""
    STATEMENT = "statement"
    VALUE = "value"
    BOOLEAN = "boolean"
    HAT = "hat"  # Entry point blocks (e.g., setup, loop)
    CAP = "cap"  # End blocks


class BlockCategory(Enum):
    """Block categories for organization"""
    CONTROL = "Control"
    LOGIC = "Logic"
    MATH = "Math"
    TEXT = "Text"
    VARIABLES = "Variables"
    FUNCTIONS = "Functions"
    INPUT_OUTPUT = "Input/Output"
    MOTION = "Motion"
    SENSING = "Sensing"
    OPERATORS = "Operators"
    ARDUINO = "Arduino"


@dataclass
class BlockParameter:
    """Parameter for a block"""
    name: str
    param_type: str  # "number", "string", "boolean", "dropdown", "color"
    default: Any = None
    options: Optional[List[str]] = None  # For dropdown type
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass
class BlockDefinition:
    """Definition of a programming block"""
    id: str
    label: str
    block_type: BlockType
    category: BlockCategory
    color: str  # Hex color
    parameters: List[BlockParameter] = field(default_factory=list)
    code_template: str = ""  # Template for code generation
    icon: Optional[str] = None
    tooltip: str = ""
    returns_value: bool = False
    accepts_statements: bool = False


@dataclass
class BlockInstance:
    """Instance of a block in the workspace"""
    instance_id: str
    definition_id: str
    x: float
    y: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    children: List['BlockInstance'] = field(default_factory=list)
    next_block: Optional['BlockInstance'] = None
    parent: Optional['BlockInstance'] = None


class VisualProgrammingService(QObject):
    """
    Service for managing block-based visual programming
    Handles block definitions, workspace management, and code generation
    """

    # Signals
    workspace_changed = Signal()
    block_added = Signal(str)  # block instance id
    block_removed = Signal(str)
    block_moved = Signal(str, float, float)  # id, x, y
    code_generated = Signal(str)  # Generated Arduino code

    def __init__(self, parent=None):
        super().__init__(parent)

        self._block_definitions: Dict[str, BlockDefinition] = {}
        self._workspace_blocks: Dict[str, BlockInstance] = {}
        self._next_instance_id = 1
        self._variables: Set[str] = set()
        self._functions: Dict[str, List[str]] = {}  # function_name -> parameter_list

        # Initialize built-in blocks
        self._init_arduino_blocks()

        logger.info("Visual programming service initialized")


    def _init_arduino_blocks(self):
        """Initialize Arduino-specific block definitions"""

        # ===== HAT BLOCKS (Entry Points) =====

        self.register_block(BlockDefinition(
            id="arduino_setup",
            label="Setup",
            block_type=BlockType.HAT,
            category=BlockCategory.ARDUINO,
            color="#FF6680",
            accepts_statements=True,
            tooltip="Runs once when the program starts",
            code_template="void setup() {\n{statements}\n}"
        ))

        self.register_block(BlockDefinition(
            id="arduino_loop",
            label="Loop",
            block_type=BlockType.HAT,
            category=BlockCategory.ARDUINO,
            color="#FF6680",
            accepts_statements=True,
            tooltip="Runs repeatedly forever",
            code_template="void loop() {\n{statements}\n}"
        ))

        # ===== INPUT/OUTPUT BLOCKS =====

        self.register_block(BlockDefinition(
            id="pin_mode",
            label="Set pin {pin} mode to {mode}",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.INPUT_OUTPUT,
            color="#4C97FF",
            parameters=[
                BlockParameter("pin", "number", 13, min_value=0, max_value=53),
                BlockParameter("mode", "dropdown", "OUTPUT", ["INPUT", "OUTPUT", "INPUT_PULLUP"])
            ],
            code_template="pinMode({pin}, {mode});"
        ))

        self.register_block(BlockDefinition(
            id="digital_write",
            label="Digital write pin {pin} to {value}",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.INPUT_OUTPUT,
            color="#4C97FF",
            parameters=[
                BlockParameter("pin", "number", 13, min_value=0, max_value=53),
                BlockParameter("value", "dropdown", "HIGH", ["HIGH", "LOW"])
            ],
            code_template="digitalWrite({pin}, {value});"
        ))

        self.register_block(BlockDefinition(
            id="digital_read",
            label="Digital read pin {pin}",
            block_type=BlockType.VALUE,
            category=BlockCategory.INPUT_OUTPUT,
            color="#4C97FF",
            parameters=[
                BlockParameter("pin", "number", 2, min_value=0, max_value=53)
            ],
            returns_value=True,
            code_template="digitalRead({pin})"
        ))

        self.register_block(BlockDefinition(
            id="analog_write",
            label="Analog write pin {pin} to {value}",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.INPUT_OUTPUT,
            color="#4C97FF",
            parameters=[
                BlockParameter("pin", "number", 9, min_value=0, max_value=53),
                BlockParameter("value", "number", 128, min_value=0, max_value=255)
            ],
            code_template="analogWrite({pin}, {value});"
        ))

        self.register_block(BlockDefinition(
            id="analog_read",
            label="Analog read pin {pin}",
            block_type=BlockType.VALUE,
            category=BlockCategory.INPUT_OUTPUT,
            color="#4C97FF",
            parameters=[
                BlockParameter("pin", "number", 0, min_value=0, max_value=15)
            ],
            returns_value=True,
            code_template="analogRead({pin})"
        ))

        self.register_block(BlockDefinition(
            id="serial_begin",
            label="Serial begin at {baud}",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.INPUT_OUTPUT,
            color="#4C97FF",
            parameters=[
                BlockParameter("baud", "dropdown", "9600", ["300", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])
            ],
            code_template="Serial.begin({baud});"
        ))

        self.register_block(BlockDefinition(
            id="serial_print",
            label="Serial print {text}",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.INPUT_OUTPUT,
            color="#4C97FF",
            parameters=[
                BlockParameter("text", "string", "Hello")
            ],
            code_template='Serial.print("{text}");'
        ))

        self.register_block(BlockDefinition(
            id="serial_println",
            label="Serial println {text}",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.INPUT_OUTPUT,
            color="#4C97FF",
            parameters=[
                BlockParameter("text", "string", "Hello")
            ],
            code_template='Serial.println("{text}");'
        ))

        # ===== CONTROL BLOCKS =====

        self.register_block(BlockDefinition(
            id="delay",
            label="Delay {ms} milliseconds",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.CONTROL,
            color="#FFAB19",
            parameters=[
                BlockParameter("ms", "number", 1000, min_value=0)
            ],
            code_template="delay({ms});"
        ))

        self.register_block(BlockDefinition(
            id="delay_microseconds",
            label="Delay {us} microseconds",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.CONTROL,
            color="#FFAB19",
            parameters=[
                BlockParameter("us", "number", 1000, min_value=0)
            ],
            code_template="delayMicroseconds({us});"
        ))

        self.register_block(BlockDefinition(
            id="if_then",
            label="If {condition} then",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.CONTROL,
            color="#FFAB19",
            parameters=[
                BlockParameter("condition", "boolean", True)
            ],
            accepts_statements=True,
            code_template="if ({condition}) {\n{statements}\n}"
        ))

        self.register_block(BlockDefinition(
            id="if_then_else",
            label="If {condition} then ... else ...",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.CONTROL,
            color="#FFAB19",
            parameters=[
                BlockParameter("condition", "boolean", True)
            ],
            accepts_statements=True,
            code_template="if ({condition}) {\n{statements}\n} else {\n{else_statements}\n}"
        ))

        self.register_block(BlockDefinition(
            id="while_loop",
            label="While {condition}",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.CONTROL,
            color="#FFAB19",
            parameters=[
                BlockParameter("condition", "boolean", True)
            ],
            accepts_statements=True,
            code_template="while ({condition}) {\n{statements}\n}"
        ))

        self.register_block(BlockDefinition(
            id="for_loop",
            label="For {var} from {start} to {end}",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.CONTROL,
            color="#FFAB19",
            parameters=[
                BlockParameter("var", "string", "i"),
                BlockParameter("start", "number", 0),
                BlockParameter("end", "number", 10)
            ],
            accepts_statements=True,
            code_template="for (int {var} = {start}; {var} < {end}; {var}++) {\n{statements}\n}"
        ))

        self.register_block(BlockDefinition(
            id="repeat_times",
            label="Repeat {times} times",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.CONTROL,
            color="#FFAB19",
            parameters=[
                BlockParameter("times", "number", 10, min_value=1)
            ],
            accepts_statements=True,
            code_template="for (int i = 0; i < {times}; i++) {\n{statements}\n}"
        ))

        # ===== LOGIC BLOCKS =====

        self.register_block(BlockDefinition(
            id="compare_equal",
            label="{a} == {b}",
            block_type=BlockType.BOOLEAN,
            category=BlockCategory.LOGIC,
            color="#59C059",
            parameters=[
                BlockParameter("a", "number", 0),
                BlockParameter("b", "number", 0)
            ],
            returns_value=True,
            code_template="({a} == {b})"
        ))

        self.register_block(BlockDefinition(
            id="compare_not_equal",
            label="{a} != {b}",
            block_type=BlockType.BOOLEAN,
            category=BlockCategory.LOGIC,
            color="#59C059",
            parameters=[
                BlockParameter("a", "number", 0),
                BlockParameter("b", "number", 0)
            ],
            returns_value=True,
            code_template="({a} != {b})"
        ))

        self.register_block(BlockDefinition(
            id="compare_less",
            label="{a} < {b}",
            block_type=BlockType.BOOLEAN,
            category=BlockCategory.LOGIC,
            color="#59C059",
            parameters=[
                BlockParameter("a", "number", 0),
                BlockParameter("b", "number", 0)
            ],
            returns_value=True,
            code_template="({a} < {b})"
        ))

        self.register_block(BlockDefinition(
            id="compare_greater",
            label="{a} > {b}",
            block_type=BlockType.BOOLEAN,
            category=BlockCategory.LOGIC,
            color="#59C059",
            parameters=[
                BlockParameter("a", "number", 0),
                BlockParameter("b", "number", 0)
            ],
            returns_value=True,
            code_template="({a} > {b})"
        ))

        self.register_block(BlockDefinition(
            id="logic_and",
            label="{a} AND {b}",
            block_type=BlockType.BOOLEAN,
            category=BlockCategory.LOGIC,
            color="#59C059",
            parameters=[
                BlockParameter("a", "boolean", True),
                BlockParameter("b", "boolean", True)
            ],
            returns_value=True,
            code_template="({a} && {b})"
        ))

        self.register_block(BlockDefinition(
            id="logic_or",
            label="{a} OR {b}",
            block_type=BlockType.BOOLEAN,
            category=BlockCategory.LOGIC,
            color="#59C059",
            parameters=[
                BlockParameter("a", "boolean", True),
                BlockParameter("b", "boolean", True)
            ],
            returns_value=True,
            code_template="({a} || {b})"
        ))

        self.register_block(BlockDefinition(
            id="logic_not",
            label="NOT {value}",
            block_type=BlockType.BOOLEAN,
            category=BlockCategory.LOGIC,
            color="#59C059",
            parameters=[
                BlockParameter("value", "boolean", True)
            ],
            returns_value=True,
            code_template="(!{value})"
        ))

        self.register_block(BlockDefinition(
            id="boolean_value",
            label="{value}",
            block_type=BlockType.BOOLEAN,
            category=BlockCategory.LOGIC,
            color="#59C059",
            parameters=[
                BlockParameter("value", "dropdown", "true", ["true", "false"])
            ],
            returns_value=True,
            code_template="{value}"
        ))

        # ===== MATH BLOCKS =====

        self.register_block(BlockDefinition(
            id="math_number",
            label="{value}",
            block_type=BlockType.VALUE,
            category=BlockCategory.MATH,
            color="#59C059",
            parameters=[
                BlockParameter("value", "number", 0)
            ],
            returns_value=True,
            code_template="{value}"
        ))

        self.register_block(BlockDefinition(
            id="math_add",
            label="{a} + {b}",
            block_type=BlockType.VALUE,
            category=BlockCategory.MATH,
            color="#59C059",
            parameters=[
                BlockParameter("a", "number", 0),
                BlockParameter("b", "number", 0)
            ],
            returns_value=True,
            code_template="({a} + {b})"
        ))

        self.register_block(BlockDefinition(
            id="math_subtract",
            label="{a} - {b}",
            block_type=BlockType.VALUE,
            category=BlockCategory.MATH,
            color="#59C059",
            parameters=[
                BlockParameter("a", "number", 0),
                BlockParameter("b", "number", 0)
            ],
            returns_value=True,
            code_template="({a} - {b})"
        ))

        self.register_block(BlockDefinition(
            id="math_multiply",
            label="{a} * {b}",
            block_type=BlockType.VALUE,
            category=BlockCategory.MATH,
            color="#59C059",
            parameters=[
                BlockParameter("a", "number", 0),
                BlockParameter("b", "number", 0)
            ],
            returns_value=True,
            code_template="({a} * {b})"
        ))

        self.register_block(BlockDefinition(
            id="math_divide",
            label="{a} / {b}",
            block_type=BlockType.VALUE,
            category=BlockCategory.MATH,
            color="#59C059",
            parameters=[
                BlockParameter("a", "number", 0),
                BlockParameter("b", "number", 1)
            ],
            returns_value=True,
            code_template="({a} / {b})"
        ))

        self.register_block(BlockDefinition(
            id="math_modulo",
            label="{a} % {b}",
            block_type=BlockType.VALUE,
            category=BlockCategory.MATH,
            color="#59C059",
            parameters=[
                BlockParameter("a", "number", 0),
                BlockParameter("b", "number", 1)
            ],
            returns_value=True,
            code_template="({a} % {b})"
        ))

        self.register_block(BlockDefinition(
            id="math_random",
            label="Random from {min} to {max}",
            block_type=BlockType.VALUE,
            category=BlockCategory.MATH,
            color="#59C059",
            parameters=[
                BlockParameter("min", "number", 0),
                BlockParameter("max", "number", 100)
            ],
            returns_value=True,
            code_template="random({min}, {max})"
        ))

        self.register_block(BlockDefinition(
            id="math_map",
            label="Map {value} from [{in_min}, {in_max}] to [{out_min}, {out_max}]",
            block_type=BlockType.VALUE,
            category=BlockCategory.MATH,
            color="#59C059",
            parameters=[
                BlockParameter("value", "number", 0),
                BlockParameter("in_min", "number", 0),
                BlockParameter("in_max", "number", 1023),
                BlockParameter("out_min", "number", 0),
                BlockParameter("out_max", "number", 255)
            ],
            returns_value=True,
            code_template="map({value}, {in_min}, {in_max}, {out_min}, {out_max})"
        ))

        # ===== VARIABLES BLOCKS =====

        self.register_block(BlockDefinition(
            id="set_variable",
            label="Set {var} to {value}",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.VARIABLES,
            color="#FF8C1A",
            parameters=[
                BlockParameter("var", "string", "myVariable"),
                BlockParameter("value", "number", 0)
            ],
            code_template="{var} = {value};"
        ))

        self.register_block(BlockDefinition(
            id="change_variable",
            label="Change {var} by {value}",
            block_type=BlockType.STATEMENT,
            category=BlockCategory.VARIABLES,
            color="#FF8C1A",
            parameters=[
                BlockParameter("var", "string", "myVariable"),
                BlockParameter("value", "number", 1)
            ],
            code_template="{var} += {value};"
        ))

        self.register_block(BlockDefinition(
            id="get_variable",
            label="{var}",
            block_type=BlockType.VALUE,
            category=BlockCategory.VARIABLES,
            color="#FF8C1A",
            parameters=[
                BlockParameter("var", "string", "myVariable")
            ],
            returns_value=True,
            code_template="{var}"
        ))


    def register_block(self, block_def: BlockDefinition):
        """Register a new block definition"""
        self._block_definitions[block_def.id] = block_def
        logger.debug(f"Registered block: {block_def.id}")


    def get_block_definition(self, block_id: str) -> Optional[BlockDefinition]:
        """Get block definition by ID"""
        return self._block_definitions.get(block_id)


    def get_blocks_by_category(self, category: BlockCategory) -> List[BlockDefinition]:
        """Get all blocks in a category"""
        return [b for b in self._block_definitions.values() if b.category == category]


    def get_all_categories(self) -> List[BlockCategory]:
        """Get list of all categories with blocks"""
        categories = set(b.category for b in self._block_definitions.values())
        return sorted(categories, key=lambda c: c.value)


    def create_block_instance(self, block_id: str, x: float = 0, y: float = 0) -> Optional[BlockInstance]:
        """Create a new block instance in the workspace"""
        block_def = self.get_block_definition(block_id)
        if not block_def:
            logger.error(f"Block definition not found: {block_id}")
            return None

        instance_id = f"block_{self._next_instance_id}"
        self._next_instance_id += 1

        # Initialize parameters with defaults
        parameters = {p.name: p.default for p in block_def.parameters}

        instance = BlockInstance(
            instance_id=instance_id,
            definition_id=block_id,
            x=x,
            y=y,
            parameters=parameters
        )

        self._workspace_blocks[instance_id] = instance
        self.block_added.emit(instance_id)
        self.workspace_changed.emit()

        logger.debug(f"Created block instance: {instance_id} ({block_id})")
        return instance


    def remove_block_instance(self, instance_id: str) -> bool:
        """Remove a block instance from workspace"""
        if instance_id not in self._workspace_blocks:
            return False

        del self._workspace_blocks[instance_id]
        self.block_removed.emit(instance_id)
        self.workspace_changed.emit()

        logger.debug(f"Removed block instance: {instance_id}")
        return True


    def move_block(self, instance_id: str, x: float, y: float) -> bool:
        """Move a block to new position"""
        if instance_id not in self._workspace_blocks:
            return False

        block = self._workspace_blocks[instance_id]
        block.x = x
        block.y = y

        self.block_moved.emit(instance_id, x, y)
        self.workspace_changed.emit()

        return True


    def connect_blocks(self, parent_id: str, child_id: str) -> bool:
        """Connect two blocks (parent -> child)"""
        if parent_id not in self._workspace_blocks or child_id not in self._workspace_blocks:
            return False

        parent = self._workspace_blocks[parent_id]
        child = self._workspace_blocks[child_id]

        parent.next_block = child
        child.parent = parent

        self.workspace_changed.emit()
        return True


    def get_workspace_blocks(self) -> List[BlockInstance]:
        """Get all blocks in workspace"""
        return list(self._workspace_blocks.values())


    def clear_workspace(self):
        """Clear all blocks from workspace"""
        self._workspace_blocks.clear()
        self.workspace_changed.emit()
        logger.info("Workspace cleared")


    def generate_code(self) -> str:
        """Generate Arduino code from blocks in workspace"""
        code_parts = []

        # Find entry point blocks (setup and loop)
        setup_blocks = [b for b in self._workspace_blocks.values()
                       if b.definition_id == "arduino_setup"]
        loop_blocks = [b for b in self._workspace_blocks.values()
                      if b.definition_id == "arduino_loop"]

        # Generate setup
        if setup_blocks:
            setup_code = self._generate_block_code(setup_blocks[0])
            code_parts.append(setup_code)

        # Generate loop
        if loop_blocks:
            loop_code = self._generate_block_code(loop_blocks[0])
            code_parts.append(loop_code)

        generated_code = "\n\n".join(code_parts)
        self.code_generated.emit(generated_code)

        return generated_code


    def _generate_block_code(self, block: BlockInstance, indent: int = 0) -> str:
        """Generate code for a block and its children"""
        block_def = self.get_block_definition(block.definition_id)
        if not block_def:
            return ""

        # Start with template
        code = block_def.code_template

        # Replace parameters
        for param_name, param_value in block.parameters.items():
            placeholder = f"{{{param_name}}}"
            code = code.replace(placeholder, str(param_value))

        # Handle child statements
        if block_def.accepts_statements and block.children:
            statements_code = ""
            for child in block.children:
                child_code = self._generate_block_code(child, indent + 2)
                statements_code += "  " + child_code + "\n"

            code = code.replace("{statements}", statements_code.rstrip())

        # Handle next block
        if block.next_block:
            next_code = self._generate_block_code(block.next_block, indent)
            code += "\n" + next_code

        return code


    def save_workspace(self, file_path: str) -> bool:
        """Save workspace to JSON file"""
        try:
            data = {
                "blocks": [
                    {
                        "instance_id": b.instance_id,
                        "definition_id": b.definition_id,
                        "x": b.x,
                        "y": b.y,
                        "parameters": b.parameters
                    }
                    for b in self._workspace_blocks.values()
                ],
                "variables": list(self._variables),
                "functions": self._functions
            }

            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Workspace saved to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save workspace: {e}")
            return False


    def load_workspace(self, file_path: str) -> bool:
        """Load workspace from JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            self.clear_workspace()

            for block_data in data.get("blocks", []):
                instance = BlockInstance(
                    instance_id=block_data["instance_id"],
                    definition_id=block_data["definition_id"],
                    x=block_data["x"],
                    y=block_data["y"],
                    parameters=block_data.get("parameters", {})
                )
                self._workspace_blocks[instance.instance_id] = instance

            self._variables = set(data.get("variables", []))
            self._functions = data.get("functions", {})

            self.workspace_changed.emit()
            logger.info(f"Workspace loaded from {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load workspace: {e}")
            return False
