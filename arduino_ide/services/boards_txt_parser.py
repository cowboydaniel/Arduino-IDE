"""Parser utilities for ``boards.txt`` platform definitions.

The parser focuses on extracting enough information for the IDE widgets to
display meaningful technical specifications. Besides the standard metadata in
``boards.txt`` we also inspect the referenced variant's ``pins_arduino.h`` file
to recover pin counts so that the "Pin Usage" and "Board Information" widgets
can operate using real hardware data.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from ..models import Board, BoardSpecs


class BoardsTxtParser:
    """Parse Arduino boards.txt files to extract board definitions"""

    @staticmethod
    def parse_boards_txt(
        boards_txt_path: Path,
        package_name: str,
        architecture: str,
        platform_root: Optional[Path] = None,
    ) -> List[Board]:
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
        # If a platform root is not provided assume the boards.txt parent folder.
        if platform_root is None:
            platform_root = boards_txt_path.parent

        boards: List[Board] = []
        for board_id in board_ids:
            board = BoardsTxtParser._create_board(
                board_id,
                properties,
                package_name,
                architecture,
                platform_root,
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
        architecture: str,
        platform_root: Path,
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
        variant_info = BoardsTxtParser._extract_variant_pin_info(
            board_id, properties, platform_root
        )
        specs = BoardsTxtParser._extract_specs(board_id, properties, variant_info)

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
    def _extract_specs(
        board_id: str,
        properties: Dict[str, str],
        variant_info: Dict[str, int],
    ) -> BoardSpecs:
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
        flash = BoardsTxtParser._format_memory_size(get_prop("upload.maximum_size", "0"))
        ram = BoardsTxtParser._format_memory_size(get_prop("upload.maximum_data_size", "0"))

        # Operating voltage
        voltage = get_prop("build.voltage", "5V")
        if voltage and not voltage.endswith("V"):
            voltage = f"{voltage}V"

        specs = BoardSpecs(
            cpu=cpu,
            clock=clock,
            flash=flash,
            ram=ram,
            voltage=voltage,
        )

        # Enrich specs with variant information when available.
        if variant_info:
            if "digital_pins" in variant_info:
                specs.digital_pins = variant_info["digital_pins"]
            if "analog_pins" in variant_info:
                specs.analog_pins = variant_info["analog_pins"]
            if "pwm_pins" in variant_info:
                specs.pwm_pins = variant_info["pwm_pins"]

        return specs

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

    # ------------------------------------------------------------------
    # Variant helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_variant_pin_info(
        board_id: str, properties: Dict[str, str], platform_root: Path
    ) -> Dict[str, int]:
        """Inspect the board variant to extract pin counts.

        The Arduino platform definition specifies the ``build.variant`` property
        that points at a folder under ``variants/`` containing a
        ``pins_arduino.h`` file with hardware limits. Parsing that file allows
        the IDE to present accurate pin information without hard-coding boards.
        """

        variant_name = properties.get(f"{board_id}.build.variant")
        if not variant_name:
            return {}

        variant_dir = BoardsTxtParser._locate_variant_directory(platform_root, variant_name)
        if not variant_dir:
            return {}

        pins_header = BoardsTxtParser._locate_pins_header(variant_dir)
        if not pins_header or not pins_header.exists():
            return {}

        try:
            content = pins_header.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return {}

        content = BoardsTxtParser._normalise_header_content(content)

        digital_pins = BoardsTxtParser._extract_numeric_macro(
            content, ["NUM_DIGITAL_PINS", "NUM_PIN_DESCRIPTION_ENTRIES"]
        )
        analog_pins = BoardsTxtParser._extract_numeric_macro(
            content, ["NUM_ANALOG_INPUTS", "NUM_ANALOG_INPUTS_DEFAULT"]
        )
        pwm_pins = BoardsTxtParser._extract_numeric_macro(content, ["NUM_PWM_PINS"])

        if pwm_pins is None:
            pwm_pins = BoardsTxtParser._count_pwm_from_macro(content)

        pin_info: Dict[str, int] = {}
        if digital_pins is not None:
            pin_info["digital_pins"] = digital_pins
        if analog_pins is not None:
            pin_info["analog_pins"] = analog_pins
        if pwm_pins is not None:
            pin_info["pwm_pins"] = pwm_pins

        return pin_info

    @staticmethod
    def _locate_variant_directory(platform_root: Path, variant_name: str) -> Optional[Path]:
        """Locate the directory containing the variant definition."""

        candidates = [
            platform_root / "variants" / variant_name,
            platform_root / variant_name,
        ]

        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate

        # Some packages unpack an additional folder (e.g. ``avr-1.8.6``). Walk a
        # couple of levels looking for the requested variant to accommodate both
        # layouts without incurring a costly recursive search.
        for subdir in platform_root.glob("*/variants"):
            candidate = subdir / variant_name
            if candidate.exists() and candidate.is_dir():
                return candidate

        # Fall back to a limited recursive search within the platform root to
        # handle custom packages that may nest variants differently.
        for candidate in platform_root.rglob(variant_name):
            if candidate.is_dir() and candidate.name == variant_name:
                return candidate

        return None

    @staticmethod
    def _locate_pins_header(variant_dir: Path) -> Optional[Path]:
        """Return the canonical ``pins_arduino`` header for a variant."""

        for filename in ("pins_arduino.h", "pins_arduino.hpp", "pins_arduino.hh"):
            header = variant_dir / filename
            if header.exists():
                return header
        return None

    @staticmethod
    def _normalise_header_content(content: str) -> str:
        """Prepare header content for regex parsing."""

        # Remove line continuations to treat macro definitions as single lines
        # and strip block comments that could contain stray numbers.
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        content = content.replace("\\\n", "")
        return content

    @staticmethod
    def _extract_numeric_macro(content: str, macro_names: List[str]) -> Optional[int]:
        """Extract the first integer value defined for any macro in ``macro_names``."""

        for macro in macro_names:
            pattern = rf"#define\s+{re.escape(macro)}\s+([0-9]+)"
            match = re.search(pattern, content)
            if match:
                return int(match.group(1))

            pattern = rf"static\s+const\s+[^=]+\s+{re.escape(macro)}\s*=\s*([0-9]+)"
            match = re.search(pattern, content)
            if match:
                return int(match.group(1))

        return None

    @staticmethod
    def _count_pwm_from_macro(content: str) -> Optional[int]:
        """Infer the number of PWM capable pins from the helper macro."""

        match = re.search(r"#define\s+digitalPinHasPWM\s*\([^)]*\)\s*(.+)", content)
        if not match:
            return None

        expr = match.group(1)
        if not expr:
            return None

        numbers = set()

        # Range based expressions: (p) >= 2 && (p) <= 13
        for range_match in re.finditer(
            r"(?:p|P)[^&|]*>=\s*(\d+)\s*&&\s*(?:p|P)[^&|]*<=\s*(\d+)", expr
        ):
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            if start <= end:
                numbers.update(range(start, end + 1))

        # Equality based expressions: (p) == 3 || (p) == 5
        for value_match in re.finditer(r"==\s*(\d+)", expr):
            numbers.add(int(value_match.group(1)))

        if not numbers:
            return None

        return len(numbers)
