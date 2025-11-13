"""
Schematic I/O Base - Base class for schematic file I/O
Based on KiCad's sch_io plugin structure
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SchematicIOBase(ABC):
    """
    Abstract base class for schematic file I/O plugins.
    Corresponds to KiCad's SCH_IO base class.
    """

    def __init__(self):
        self.name = "Base I/O Plugin"
        self.description = "Abstract base class"
        self.file_extension = ".sch"

    @abstractmethod
    def can_read(self, file_path: Path) -> bool:
        """Check if this plugin can read the given file"""
        pass

    @abstractmethod
    def load(self, file_path: Path) -> Dict:
        """Load schematic from file"""
        pass

    @abstractmethod
    def save(self, file_path: Path, schematic_data: Dict):
        """Save schematic to file"""
        pass

    def get_file_extension(self) -> str:
        """Get the file extension for this format"""
        return self.file_extension

    def get_description(self) -> str:
        """Get description of this I/O plugin"""
        return self.description
