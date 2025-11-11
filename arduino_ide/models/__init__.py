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
    KnownIssue,
    DownloadMirror,
    CommunityRating,
    BoardCompatibility,
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
    "KnownIssue",
    "DownloadMirror",
    "CommunityRating",
    "BoardCompatibility",
    # Board models
    "Board",
    "BoardSpecs",
    "BoardPackage",
    "BoardPackageVersion",
    "BoardPackageURL",
    "BoardStatus",
    "BoardCategory",
    "BoardIndex",
    # Package models
    "ProjectConfig",
    "ProjectBoard",
    "ProjectDependency",
    "DependencyTree",
    "InstallPlan",
]
