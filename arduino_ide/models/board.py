"""
Data models for Arduino boards and board packages
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class BoardStatus(Enum):
    """Board package installation status"""
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    UPDATE_AVAILABLE = "update_available"


class BoardCategory(Enum):
    """Board categories"""
    OFFICIAL = "official"
    COMMUNITY = "community"
    PARTNER = "partner"


@dataclass
class BoardSpecs:
    """Technical specifications for a board"""
    cpu: str
    clock: str
    flash: str
    ram: str
    eeprom: str = "N/A"
    voltage: str = "5V"
    digital_pins: int = 0
    analog_pins: int = 0
    pwm_pins: int = 0
    uart: int = 1
    spi: int = 1
    i2c: int = 1

    # Advanced specs
    adc_resolution: str = "10-bit"
    dac: bool = False
    touch_pins: int = 0
    rtc: bool = False
    wifi: bool = False
    bluetooth: bool = False
    ethernet: bool = False
    usb: bool = True
    can: bool = False

    # Power consumption
    power_typical: str = "N/A"
    power_max: str = "N/A"
    sleep_mode: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "CPU": self.cpu,
            "Clock": self.clock,
            "Flash": self.flash,
            "RAM": self.ram,
            "EEPROM": self.eeprom,
            "Voltage": self.voltage,
            "Digital I/O": str(self.digital_pins),
            "Analog In": str(self.analog_pins),
            "PWM": str(self.pwm_pins),
        }


@dataclass
class Board:
    """Represents an Arduino board"""
    name: str
    fqbn: str  # Fully Qualified Board Name (e.g., "arduino:avr:uno")
    architecture: str  # e.g., "avr", "esp32", "samd"
    package_name: str  # e.g., "arduino", "esp32"

    # Specs
    specs: BoardSpecs

    # Metadata
    description: str = ""
    url: str = ""
    price: str = "N/A"
    popularity: int = 0  # Based on usage/downloads

    # Features
    features: List[str] = field(default_factory=list)
    best_for: List[str] = field(default_factory=list)  # ["IoT", "Beginner", "Low Power"]

    # Compatibility
    supported_libraries: List[str] = field(default_factory=list)
    known_issues: List[str] = field(default_factory=list)

    # Programming
    programmer: str = "arduino"
    bootloader: str = ""
    upload_speed: int = 115200

    def is_wireless(self) -> bool:
        """Check if board has wireless capability"""
        return self.specs.wifi or self.specs.bluetooth

    def is_low_power(self) -> bool:
        """Check if board supports low power modes"""
        return self.specs.sleep_mode

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "fqbn": self.fqbn,
            "architecture": self.architecture,
            "specs": self.specs.to_dict(),
            "price": self.price,
        }


@dataclass
class BoardPackageVersion:
    """Represents a specific version of a board package"""
    version: str
    url: str
    size: int
    checksum: str
    release_date: datetime
    changelog: str = ""
    boards_count: int = 0
    boards: List[str] = field(default_factory=list)  # List of board names

    def size_human_readable(self) -> str:
        """Get human-readable size"""
        if self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f}KB"
        elif self.size < 1024 * 1024 * 1024:
            return f"{self.size / (1024 * 1024):.1f}MB"
        else:
            return f"{self.size / (1024 * 1024 * 1024):.1f}GB"


@dataclass
class BoardPackage:
    """Represents a board package (collection of boards)"""
    name: str
    maintainer: str
    category: BoardCategory
    url: str

    # Versions
    versions: List[BoardPackageVersion] = field(default_factory=list)
    installed_version: Optional[str] = None
    latest_version: Optional[str] = None

    # Boards in this package
    boards: List[Board] = field(default_factory=list)

    # Metadata
    description: str = ""
    website: str = ""
    email: str = ""
    help_url: str = ""

    # Stats
    downloads: int = 0
    rating: float = 0.0

    @property
    def status(self) -> BoardStatus:
        """Get current package status"""
        if not self.installed_version:
            return BoardStatus.NOT_INSTALLED

        if self.latest_version and self.installed_version != self.latest_version:
            return BoardStatus.UPDATE_AVAILABLE

        return BoardStatus.INSTALLED

    def get_version(self, version: str) -> Optional[BoardPackageVersion]:
        """Get specific version object"""
        for v in self.versions:
            if v.version == version:
                return v
        return None

    def get_latest_version_obj(self) -> Optional[BoardPackageVersion]:
        """Get latest version object"""
        if self.latest_version:
            return self.get_version(self.latest_version)
        return None

    def has_update(self) -> bool:
        """Check if update is available"""
        return self.status == BoardStatus.UPDATE_AVAILABLE

    @classmethod
    def from_arduino_index(cls, data: dict) -> "BoardPackage":
        """Create BoardPackage from Arduino package index entry"""
        versions = []
        for v_data in data.get("platforms", []):
            version = BoardPackageVersion(
                version=v_data.get("version", ""),
                url=v_data.get("url", ""),
                size=v_data.get("size", 0),
                checksum=v_data.get("checksum", ""),
                release_date=datetime.fromisoformat(v_data.get("releaseDate", "2000-01-01")),
                boards_count=len(v_data.get("boards", [])),
                boards=v_data.get("boards", []),
            )
            versions.append(version)

        # Sort versions (newest first)
        versions.sort(key=lambda v: v.release_date, reverse=True)

        category = BoardCategory.OFFICIAL if data.get("official", False) else BoardCategory.COMMUNITY

        return cls(
            name=data.get("name", ""),
            maintainer=data.get("maintainer", ""),
            category=category,
            url=data.get("websiteURL", ""),
            versions=versions,
            latest_version=versions[0].version if versions else None,
            website=data.get("websiteURL", ""),
            email=data.get("email", ""),
            help_url=data.get("help", {}).get("online", ""),
        )


@dataclass
class BoardPackageURL:
    """Represents a board package URL"""
    name: str
    url: str
    enabled: bool = True


@dataclass
class BoardIndex:
    """Represents the entire board package index"""
    packages: List[BoardPackage] = field(default_factory=list)
    package_urls: List[BoardPackageURL] = field(default_factory=list)
    last_updated: Optional[datetime] = None

    # Predefined popular package URLs
    POPULAR_URLS = [
        BoardPackageURL(
            name="ESP32 (Espressif)",
            url="https://espressif.github.io/arduino-esp32/package_esp32_index.json",
            enabled=False
        ),
        BoardPackageURL(
            name="ESP8266 (Community)",
            url="http://arduino.esp8266.com/stable/package_esp8266com_index.json",
            enabled=False
        ),
        BoardPackageURL(
            name="STM32 (STMicroelectronics)",
            url="https://github.com/stm32duino/BoardManagerFiles/raw/main/package_stmicroelectronics_index.json",
            enabled=False
        ),
        BoardPackageURL(
            name="Adafruit SAMD",
            url="https://adafruit.github.io/arduino-board-index/package_adafruit_index.json",
            enabled=False
        ),
        BoardPackageURL(
            name="Raspberry Pi Pico",
            url="https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json",
            enabled=False
        ),
    ]

    def get_package(self, name: str) -> Optional[BoardPackage]:
        """Get package by name"""
        for pkg in self.packages:
            if pkg.name == name:
                return pkg
        return None

    def get_board(self, fqbn: str) -> Optional[Board]:
        """Get board by FQBN"""
        for pkg in self.packages:
            for board in pkg.boards:
                if board.fqbn == fqbn:
                    return board
        return None

    def search_boards(self, query: str, features: Optional[List[str]] = None,
                     architecture: Optional[str] = None,
                     installed_only: bool = False) -> List[Board]:
        """Search boards with filters"""
        results = []
        query_lower = query.lower()

        for pkg in self.packages:
            # Filter installed packages only
            if installed_only and not pkg.installed_version:
                continue

            for board in pkg.boards:
                # Filter by query
                if query and query_lower not in board.name.lower() and \
                   query_lower not in board.description.lower():
                    continue

                # Filter by architecture
                if architecture and board.architecture != architecture:
                    continue

                # Filter by features
                if features:
                    has_all_features = True
                    for feature in features:
                        feature_lower = feature.lower()
                        if feature_lower == "wifi" and not board.specs.wifi:
                            has_all_features = False
                        elif feature_lower == "bluetooth" and not board.specs.bluetooth:
                            has_all_features = False
                        elif feature_lower == "ethernet" and not board.specs.ethernet:
                            has_all_features = False
                        elif feature_lower == "sleep" and not board.specs.sleep_mode:
                            has_all_features = False

                    if not has_all_features:
                        continue

                results.append(board)

        return results

    def get_installed_packages(self) -> List[BoardPackage]:
        """Get all installed packages"""
        return [pkg for pkg in self.packages if pkg.installed_version]

    def get_packages_with_updates(self) -> List[BoardPackage]:
        """Get packages with available updates"""
        return [pkg for pkg in self.packages if pkg.has_update()]


# Predefined board specifications (for initial data)
# No default boards - all boards come from installed cores via package index
