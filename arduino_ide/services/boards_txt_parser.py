"""
Parser for Arduino boards.txt files

Implements the Arduino platform specification:
https://arduino.github.io/arduino-cli/latest/platform-specification/
"""

from pathlib import Path
from typing import Dict, List, Optional
from ..models import Board, BoardSpecs


class BoardsTxtParser:
    """Parse Arduino boards.txt files to extract board definitions"""

    @staticmethod
    def parse_boards_txt(boards_txt_path: Path, package_name: str, architecture: str) -> List[Board]:
        """
        Parse a boards.txt file and return list of Board objects.

        Args:
            boards_txt_path: Path to boards.txt file
            package_name: Package name (e.g., "arduino", "esp32")
            architecture: Architecture name (e.g., "avr", "esp32")

        Returns:
            List of Board objects
        """
        if not boards_txt_path.exists():
            return []

        # Read and parse the properties file
        properties = BoardsTxtParser._read_properties_file(boards_txt_path)

        # Extract unique board IDs
        board_ids = BoardsTxtParser._extract_board_ids(properties)

        # Create Board objects
        boards = []
        for board_id in board_ids:
            board = BoardsTxtParser._create_board(
                board_id, properties, package_name, architecture
            )
            if board:
                boards.append(board)

        return boards

    @staticmethod
    def _read_properties_file(file_path: Path) -> Dict[str, str]:
        """Read Arduino properties file format"""
        properties = {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue

                    # Parse key=value
                    if '=' in line:
                        key, value = line.split('=', 1)
                        properties[key.strip()] = value.strip()

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

        return properties

    @staticmethod
    def _extract_board_ids(properties: Dict[str, str]) -> List[str]:
        """Extract unique board IDs from properties"""
        board_ids = set()

        for key in properties.keys():
            # Board properties start with boardid.property
            # e.g., uno.name, mega.upload.maximum_size
            if '.' in key:
                board_id = key.split('.')[0]
                # Skip menu entries
                if board_id != 'menu':
                    board_ids.add(board_id)

        return sorted(list(board_ids))

    @staticmethod
    def _create_board(
        board_id: str,
        properties: Dict[str, str],
        package_name: str,
        architecture: str
    ) -> Optional[Board]:
        """Create a Board object from properties"""

        # Get board name (required)
        name_key = f"{board_id}.name"
        if name_key not in properties:
            return None

        name = properties[name_key]

        # Build FQBN
        fqbn = f"{package_name}:{architecture}:{board_id}"

        # Extract specs
        specs = BoardsTxtParser._extract_specs(board_id, properties)

        # Create board
        board = Board(
            name=name,
            fqbn=fqbn,
            architecture=architecture,
            package_name=package_name,
            specs=specs,
            upload_speed=BoardsTxtParser._get_int_property(
                properties, f"{board_id}.upload.speed", 115200
            ),
        )

        return board

    @staticmethod
    def _extract_specs(board_id: str, properties: Dict[str, str]) -> BoardSpecs:
        """Extract board specifications from properties"""

        # Helper to get property value
        def get_prop(suffix: str, default: str = "Unknown") -> str:
            key = f"{board_id}.{suffix}"
            return properties.get(key, default)

        # Extract common properties
        cpu = get_prop("build.mcu", "Unknown").upper()
        clock_hz = get_prop("build.f_cpu", "0")

        # Convert clock frequency to readable format
        try:
            clock_val = int(clock_hz.replace("L", "").replace("UL", ""))
            if clock_val >= 1000000:
                clock = f"{clock_val // 1000000}MHz"
            elif clock_val >= 1000:
                clock = f"{clock_val // 1000}kHz"
            else:
                clock = f"{clock_val}Hz"
        except (ValueError, AttributeError):
            clock = "Unknown"

        # Extract memory sizes
        flash = BoardsTxtParser._format_memory_size(
            get_prop("upload.maximum_size", "0")
        )
        ram = BoardsTxtParser._format_memory_size(
            get_prop("upload.maximum_data_size", "0")
        )

        # Operating voltage
        voltage = get_prop("build.voltage", "5V")
        if voltage and not voltage.endswith("V"):
            voltage = f"{voltage}V"

        return BoardSpecs(
            cpu=cpu,
            clock=clock,
            flash=flash,
            ram=ram,
            voltage=voltage,
        )

    @staticmethod
    def _format_memory_size(size_str: str) -> str:
        """Format memory size in human-readable format"""
        try:
            size = int(size_str)
            if size >= 1024 * 1024:
                return f"{size // (1024 * 1024)}MB"
            elif size >= 1024:
                return f"{size // 1024}KB"
            elif size > 0:
                return f"{size}B"
            else:
                return "Unknown"
        except (ValueError, AttributeError):
            return "Unknown"

    @staticmethod
    def _get_int_property(properties: Dict[str, str], key: str, default: int) -> int:
        """Get integer property value"""
        try:
            return int(properties.get(key, str(default)))
        except (ValueError, AttributeError):
            return default
