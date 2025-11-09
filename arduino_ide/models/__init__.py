"""
Data models for Arduino IDE
"""

from .library import (
    Library,
    LibraryDependency,
    LibraryVersion,
    LibraryExample,
    LibraryStats,
    LibraryStatus,
    LibraryType,
    LibraryIndex,
)

from .board import (
    Board,
    BoardSpecs,
    BoardPackage,
    BoardPackageVersion,
    BoardPackageURL,
    BoardStatus,
    BoardCategory,
    BoardIndex,
    DEFAULT_BOARDS,
)

from .package import (
    ProjectConfig,
    ProjectBoard,
    ProjectDependency,
    DependencyTree,
    InstallPlan,
)

__all__ = [
    # Library models
    "Library",
    "LibraryDependency",
    "LibraryVersion",
    "LibraryExample",
    "LibraryStats",
    "LibraryStatus",
    "LibraryType",
    "LibraryIndex",
    # Board models
    "Board",
    "BoardSpecs",
    "BoardPackage",
    "BoardPackageVersion",
    "BoardPackageURL",
    "BoardStatus",
    "BoardCategory",
    "BoardIndex",
    "DEFAULT_BOARDS",
    # Package models
    "ProjectConfig",
    "ProjectBoard",
    "ProjectDependency",
    "DependencyTree",
    "InstallPlan",
]
