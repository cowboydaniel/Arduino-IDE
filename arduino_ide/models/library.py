"""
Data models for Arduino libraries
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict

from packaging.version import Version, InvalidVersion


class LibraryStatus(Enum):
    """Library installation status"""
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    UPDATE_AVAILABLE = "update_available"
    OUTDATED = "outdated"
    CONFLICTED = "conflicted"


class LibraryType(Enum):
    """Library type"""
    OFFICIAL = "official"
    COMMUNITY = "community"
    LOCAL = "local"
    CONTRIBUTED = "contributed"


@dataclass
class LibraryDependency:
    """Represents a library dependency"""
    name: str
    version: str = "*"  # Supports version constraints like ">=1.0.0", "^1.2.0"
    optional: bool = False

    def __str__(self):
        return f"{self.name} ({self.version})"


@dataclass
class KnownIssue:
    """Represents a known issue in a library version"""
    severity: str  # "critical", "high", "medium", "low"
    description: str
    workaround: str = ""
    affected_versions: List[str] = field(default_factory=list)
    fixed_in: Optional[str] = None
    issue_url: Optional[str] = None


@dataclass
class DownloadMirror:
    """Represents a download mirror for a library"""
    url: str
    type: str  # "primary", "mirror", "cdn"
    priority: int = 0  # Higher priority = tried first


@dataclass
class LibraryVersion:
    """Represents a specific version of a library"""
    version: str
    url: str
    size: int  # Size in bytes
    checksum: str
    release_date: datetime
    changelog: str = ""
    breaking_changes: bool = False
    known_issues: List[KnownIssue] = field(default_factory=list)
    dependencies: List[LibraryDependency] = field(default_factory=list)
    architectures: List[str] = field(default_factory=list)  # ["avr", "esp32", "*"]
    mirrors: List[DownloadMirror] = field(default_factory=list)  # Download mirrors

    def size_human_readable(self) -> str:
        """Get human-readable size"""
        if self.size < 1024:
            return f"{self.size}B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f}KB"
        else:
            return f"{self.size / (1024 * 1024):.1f}MB"

    def get_download_urls(self) -> List[str]:
        """Get all download URLs sorted by priority"""
        urls = [(self.url, 1000)]  # Primary URL has highest priority
        for mirror in sorted(self.mirrors, key=lambda m: m.priority, reverse=True):
            urls.append((mirror.url, mirror.priority))
        return [url for url, _ in sorted(urls, key=lambda x: x[1], reverse=True)]


@dataclass
class LibraryExample:
    """Represents a library example sketch"""
    name: str
    path: str
    description: str = ""
    difficulty: str = "beginner"  # "beginner", "intermediate", "advanced"


@dataclass
class CommunityRating:
    """Community rating information"""
    average: float = 0.0
    count: int = 0
    five_star: int = 0
    four_star: int = 0
    three_star: int = 0
    two_star: int = 0
    one_star: int = 0


@dataclass
class BoardCompatibility:
    """Board compatibility information"""
    board_fqbn: str
    status: str  # "tested", "partial", "untested", "incompatible"
    notes: str = ""


@dataclass
class LibraryStats:
    """Library statistics and metadata"""
    downloads: int = 0
    stars: int = 0
    rating: float = 0.0
    open_issues: int = 0
    closed_issues: int = 0
    last_commit: Optional[datetime] = None
    actively_maintained: bool = True

    # Enhanced metadata
    downloads_last_month: int = 0
    forks: int = 0
    watchers: int = 0
    contributors: int = 0
    verified: bool = False  # Official Arduino verification
    compatibility_score: float = 0.98  # 0.0 to 1.0

    # Community ratings
    community_rating: Optional[CommunityRating] = None


@dataclass
class Library:
    """Represents an Arduino library"""
    name: str
    author: str
    description: str
    category: str
    lib_type: LibraryType

    # Version information
    versions: List[LibraryVersion] = field(default_factory=list)
    installed_version: Optional[str] = None
    latest_version: Optional[str] = None

    # Metadata
    url: str = ""
    repository: str = ""
    documentation: str = ""
    license: str = ""
    maintainer: str = ""
    sentence: str = ""  # Short description
    paragraph: str = ""  # Long description

    # Examples
    examples: List[LibraryExample] = field(default_factory=list)

    # Compatibility
    architectures: List[str] = field(default_factory=list)
    compatible_boards: List[str] = field(default_factory=list)
    incompatible_boards: List[str] = field(default_factory=list)
    board_compatibility: List[BoardCompatibility] = field(default_factory=list)

    # Stats
    stats: Optional[LibraryStats] = None

    # Issues and warnings
    known_issues: List[KnownIssue] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Installation info
    install_path: Optional[str] = None
    pinned_version: Optional[str] = None  # User can pin to specific version

    # Metadata
    last_updated: Optional[datetime] = None
    last_used: Optional[datetime] = None

    @property
    def status(self) -> LibraryStatus:
        """Get current library status"""
        if not self.installed_version:
            return LibraryStatus.NOT_INSTALLED

        if self.latest_version and self.installed_version != self.latest_version:
            return LibraryStatus.UPDATE_AVAILABLE

        return LibraryStatus.INSTALLED

    def get_version(self, version: str) -> Optional[LibraryVersion]:
        """Get specific version object"""
        for v in self.versions:
            if v.version == version:
                return v
        return None

    def get_latest_version_obj(self) -> Optional[LibraryVersion]:
        """Get latest version object"""
        if self.latest_version:
            return self.get_version(self.latest_version)
        return None

    def get_installed_version_obj(self) -> Optional[LibraryVersion]:
        """Get installed version object"""
        if self.installed_version:
            return self.get_version(self.installed_version)
        return None

    @property
    def available_versions(self) -> List[str]:
        """Return all available version strings sorted by semantic version"""
        valid_versions: List[tuple[Version, str]] = []
        invalid_versions: List[str] = []

        for version in self.versions:
            version_str = version.version
            try:
                parsed = Version(version_str)
            except InvalidVersion:
                invalid_versions.append(version_str)
            else:
                valid_versions.append((parsed, version_str))

        valid_versions.sort(key=lambda item: item[0], reverse=True)

        sorted_versions = [version_str for _, version_str in valid_versions]
        sorted_versions.extend(invalid_versions)
        return sorted_versions

    def is_compatible_with_board(self, board_architecture: str) -> bool:
        """Check if library is compatible with board architecture"""
        if not self.architectures or "*" in self.architectures:
            return True
        return board_architecture in self.architectures

    def has_update(self) -> bool:
        """Check if update is available"""
        return self.status == LibraryStatus.UPDATE_AVAILABLE

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "author": self.author,
            "description": self.description,
            "category": self.category,
            "type": self.lib_type.value,
            "installed_version": self.installed_version,
            "pinned_version": self.pinned_version,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    @classmethod
    def from_arduino_index(cls, data: dict) -> "Library":
        """Create Library from Arduino library index entry"""
        versions = []
        for v_data in data.get("versions", []):
            deps = [
                LibraryDependency(
                    name=d.get("name", ""),
                    version=d.get("version", "*")
                )
                for d in v_data.get("dependencies", [])
            ]

            version = LibraryVersion(
                version=v_data.get("version", ""),
                url=v_data.get("url", ""),
                size=v_data.get("size", 0),
                checksum=v_data.get("checksum", ""),
                release_date=datetime.fromisoformat(v_data.get("releaseDate", "2000-01-01")),
                dependencies=deps,
                architectures=v_data.get("architectures", ["*"]),
            )
            versions.append(version)

        # Sort versions (newest first)
        versions.sort(key=lambda v: v.release_date, reverse=True)

        return cls(
            name=data.get("name", ""),
            author=data.get("author", ""),
            description=data.get("sentence", ""),
            category=data.get("category", "Uncategorized"),
            lib_type=LibraryType.OFFICIAL if data.get("official", False) else LibraryType.COMMUNITY,
            versions=versions,
            latest_version=versions[0].version if versions else None,
            url=data.get("url", ""),
            repository=data.get("repository", ""),
            license=data.get("license", ""),
            maintainer=data.get("maintainer", ""),
            sentence=data.get("sentence", ""),
            paragraph=data.get("paragraph", ""),
            architectures=data.get("architectures", ["*"]),
        )


@dataclass
class LibraryIndex:
    """Represents the entire library index"""
    libraries: List[Library] = field(default_factory=list)
    last_updated: Optional[datetime] = None

    def get_library(self, name: str) -> Optional[Library]:
        """Get library by name"""
        for lib in self.libraries:
            if lib.name == name:
                return lib
        return None

    def search(self, query: str, category: Optional[str] = None,
               architecture: Optional[str] = None,
               installed_only: bool = False,
               updates_only: bool = False) -> List[Library]:
        """Search libraries with filters"""
        results = []
        query_lower = query.lower()

        for lib in self.libraries:
            # Filter by query
            if query and query_lower not in lib.name.lower() and \
               query_lower not in lib.description.lower() and \
               query_lower not in lib.author.lower():
                continue

            # Filter by category
            if category and lib.category != category:
                continue

            # Filter by architecture
            if architecture and not lib.is_compatible_with_board(architecture):
                continue

            # Filter installed only
            if installed_only and not lib.installed_version:
                continue

            # Filter updates only
            if updates_only and not lib.has_update():
                continue

            results.append(lib)

        return results

    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        categories = set()
        for lib in self.libraries:
            categories.add(lib.category)
        return sorted(list(categories))

    def get_installed_libraries(self) -> List[Library]:
        """Get all installed libraries"""
        return [lib for lib in self.libraries if lib.installed_version]

    def get_libraries_with_updates(self) -> List[Library]:
        """Get libraries with available updates"""
        return [lib for lib in self.libraries if lib.has_update()]
