"""
JSON Schematic I/O Plugin - Read/write JSON format (legacy)
"""

import json
import logging
from pathlib import Path
from typing import Dict

from arduino_ide.eeschema.sch_io.sch_io_base import SchematicIOBase

logger = logging.getLogger(__name__)


class JSONSchematicPlugin(SchematicIOBase):
    """
    I/O plugin for JSON schematic format (legacy).
    """

    def __init__(self):
        super().__init__()
        self.name = "JSON Schematic"
        self.description = "JSON schematic files (*.json)"
        self.file_extension = ".json"

    def can_read(self, file_path: Path) -> bool:
        """Check if this plugin can read the given file"""
        if not file_path.exists():
            return False
        if file_path.suffix.lower() != self.file_extension:
            return False

        try:
            data = json.loads(file_path.read_text())
            return isinstance(data, dict) and "components" in data
        except (json.JSONDecodeError, OSError):
            return False

    def load(self, file_path: Path) -> Dict:
        """Load JSON schematic from file"""
        logger.info(f"Loading JSON schematic from {file_path}")

        data = json.loads(file_path.read_text())
        return {
            "format": "json",
            "components": data.get("components", {}),
            "connections": data.get("connections", {}),
            "sheets": data.get("sheets", {}),
        }

    def save(self, file_path: Path, schematic_data: Dict):
        """Save schematic to JSON format"""
        logger.info(f"Saving JSON schematic to {file_path}")

        output = {
            "format": "json",
            "version": "1.0",
            "components": schematic_data.get("components", {}),
            "connections": schematic_data.get("connections", {}),
            "sheets": schematic_data.get("sheets", {}),
        }

        file_path.write_text(json.dumps(output, indent=2))
        logger.info(f"Saved schematic to {file_path}")
