"""
Data models for Arduino project package management (arduino-project.json)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json
from pathlib import Path


@dataclass
class ProjectBoard:
    """Board configuration for a project"""
    fqbn: str  # Fully Qualified Board Name
    port: Optional[str] = None


@dataclass
class ProjectDependency:
    """Project dependency specification"""
    name: str
    version: str  # Supports "^1.2.0", ">=1.0.0", "1.4.4", "*"
    optional: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "version": self.version,
            "optional": self.optional,
        }

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "ProjectDependency":
        """Create from dictionary"""
        if isinstance(data, str):
            # Simple version string
            return cls(name=name, version=data)
        else:
            # Complex object
            return cls(
                name=name,
                version=data.get("version", "*"),
                optional=data.get("optional", False),
            )


@dataclass
class ProjectConfig:
    """Arduino project configuration (arduino-project.json)"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    license: str = ""

    # Board configuration
    board: Optional[ProjectBoard] = None

    # Dependencies
    dependencies: Dict[str, ProjectDependency] = field(default_factory=dict)
    dev_dependencies: Dict[str, ProjectDependency] = field(default_factory=dict)

    # Build settings
    build_settings: Dict[str, any] = field(default_factory=dict)

    # Scripts
    scripts: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = {
            "name": self.name,
            "version": self.version,
        }

        if self.description:
            data["description"] = self.description

        if self.author:
            data["author"] = self.author

        if self.license:
            data["license"] = self.license

        if self.board:
            data["board"] = {
                "fqbn": self.board.fqbn,
            }
            if self.board.port:
                data["board"]["port"] = self.board.port

        if self.dependencies:
            data["dependencies"] = {
                name: dep.version if not dep.optional else dep.to_dict()
                for name, dep in self.dependencies.items()
            }

        if self.dev_dependencies:
            data["devDependencies"] = {
                name: dep.version if not dep.optional else dep.to_dict()
                for name, dep in self.dev_dependencies.items()
            }

        if self.build_settings:
            data["buildSettings"] = self.build_settings

        if self.scripts:
            data["scripts"] = self.scripts

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectConfig":
        """Create from dictionary"""
        # Parse board
        board = None
        if "board" in data:
            board_data = data["board"]
            board = ProjectBoard(
                fqbn=board_data.get("fqbn", ""),
                port=board_data.get("port"),
            )

        # Parse dependencies
        dependencies = {}
        for name, dep_data in data.get("dependencies", {}).items():
            dependencies[name] = ProjectDependency.from_dict(name, dep_data)

        # Parse dev dependencies
        dev_dependencies = {}
        for name, dep_data in data.get("devDependencies", {}).items():
            dev_dependencies[name] = ProjectDependency.from_dict(name, dep_data)

        return cls(
            name=data.get("name", "Untitled"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            license=data.get("license", ""),
            board=board,
            dependencies=dependencies,
            dev_dependencies=dev_dependencies,
            build_settings=data.get("buildSettings", {}),
            scripts=data.get("scripts", {}),
        )

    def save(self, path: Path) -> None:
        """Save project configuration to JSON file"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "ProjectConfig":
        """Load project configuration from JSON file"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def create_default(cls, name: str, board_fqbn: Optional[str] = None) -> "ProjectConfig":
        """Create a default project configuration"""
        board = None
        if board_fqbn:
            board = ProjectBoard(fqbn=board_fqbn)

        return cls(
            name=name,
            version="1.0.0",
            description="",
            author="",
            license="MIT",
            board=board,
        )

    def add_dependency(self, name: str, version: str, dev: bool = False, optional: bool = False) -> None:
        """Add a dependency to the project"""
        dep = ProjectDependency(name=name, version=version, optional=optional)

        if dev:
            self.dev_dependencies[name] = dep
        else:
            self.dependencies[name] = dep

    def remove_dependency(self, name: str) -> None:
        """Remove a dependency from the project"""
        if name in self.dependencies:
            del self.dependencies[name]
        if name in self.dev_dependencies:
            del self.dev_dependencies[name]

    def has_dependency(self, name: str) -> bool:
        """Check if project has a dependency"""
        return name in self.dependencies or name in self.dev_dependencies

    def get_all_dependencies(self, include_dev: bool = False) -> Dict[str, ProjectDependency]:
        """Get all dependencies"""
        deps = dict(self.dependencies)
        if include_dev:
            deps.update(self.dev_dependencies)
        return deps


@dataclass
class DependencyTree:
    """Represents a dependency tree for resolution"""
    library: str
    version: str
    dependencies: List["DependencyTree"] = field(default_factory=list)
    optional: bool = False
    installed: bool = False
    conflicts: List[str] = field(default_factory=list)

    def flatten(self) -> List[tuple[str, str]]:
        """Flatten dependency tree to list of (name, version) tuples"""
        result = [(self.library, self.version)]
        for dep in self.dependencies:
            result.extend(dep.flatten())
        return list(set(result))  # Remove duplicates

    def get_total_size(self) -> int:
        """Get total size of all dependencies"""
        # This would need to be calculated with actual library data
        return 0

    def has_conflicts(self) -> bool:
        """Check if tree has any conflicts"""
        if self.conflicts:
            return True
        for dep in self.dependencies:
            if dep.has_conflicts():
                return True
        return False


@dataclass
class InstallPlan:
    """Installation plan for dependencies"""
    to_install: List[tuple[str, str]] = field(default_factory=list)  # (name, version)
    to_update: List[tuple[str, str, str]] = field(default_factory=list)  # (name, old_version, new_version)
    already_installed: List[tuple[str, str]] = field(default_factory=list)  # (name, version)
    conflicts: List[str] = field(default_factory=list)
    total_download_size: int = 0

    def has_changes(self) -> bool:
        """Check if plan has any changes"""
        return len(self.to_install) > 0 or len(self.to_update) > 0

    def has_conflicts(self) -> bool:
        """Check if plan has conflicts"""
        return len(self.conflicts) > 0

    def get_summary(self) -> str:
        """Get human-readable summary"""
        parts = []

        if self.to_install:
            parts.append(f"Install {len(self.to_install)} libraries")

        if self.to_update:
            parts.append(f"Update {len(self.to_update)} libraries")

        if self.already_installed:
            parts.append(f"{len(self.already_installed)} already installed")

        if not parts:
            return "No changes needed"

        return ", ".join(parts)
