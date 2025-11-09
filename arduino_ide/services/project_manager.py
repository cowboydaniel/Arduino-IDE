"""
Project Manager Service

Handles arduino-project.json configuration and project-level dependency management.
"""

from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import QObject, Signal
from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.version import Version, InvalidVersion

from ..models import ProjectConfig, InstallPlan, ProjectDependency


class ProjectManager(QObject):
    """Manages Arduino project configuration"""

    # Signals
    project_loaded = Signal(str)  # project name
    project_saved = Signal(str)  # project name
    dependencies_changed = Signal()
    status_message = Signal(str)

    PROJECT_FILE_NAME = "arduino-project.json"

    def __init__(self, library_manager=None, board_manager=None, parent=None):
        super().__init__(parent)

        self.library_manager = library_manager
        self.board_manager = board_manager

        self.current_project: Optional[ProjectConfig] = None
        self.project_path: Optional[Path] = None

    def has_project_file(self, directory: Path) -> bool:
        """Check if directory has an arduino-project.json file"""
        return (directory / self.PROJECT_FILE_NAME).exists()

    def load_project(self, directory: Path) -> bool:
        """Load project configuration from directory"""
        project_file = directory / self.PROJECT_FILE_NAME

        if not project_file.exists():
            self.status_message.emit(f"No {self.PROJECT_FILE_NAME} found in {directory}")
            return False

        try:
            self.current_project = ProjectConfig.load(project_file)
            self.project_path = directory
            self.status_message.emit(f"Loaded project: {self.current_project.name}")
            self.project_loaded.emit(self.current_project.name)
            return True

        except Exception as e:
            self.status_message.emit(f"Error loading project: {str(e)}")
            return False

    def save_project(self) -> bool:
        """Save current project configuration"""
        if not self.current_project or not self.project_path:
            self.status_message.emit("No project loaded")
            return False

        try:
            project_file = self.project_path / self.PROJECT_FILE_NAME
            self.current_project.save(project_file)
            self.status_message.emit(f"Saved project: {self.current_project.name}")
            self.project_saved.emit(self.current_project.name)
            return True

        except Exception as e:
            self.status_message.emit(f"Error saving project: {str(e)}")
            return False

    def create_project(self, directory: Path, name: str, board_fqbn: Optional[str] = None) -> bool:
        """Create a new project configuration"""
        try:
            self.current_project = ProjectConfig.create_default(name, board_fqbn)
            self.project_path = directory

            # Save immediately
            project_file = directory / self.PROJECT_FILE_NAME
            self.current_project.save(project_file)

            self.status_message.emit(f"Created project: {name}")
            self.project_loaded.emit(name)
            return True

        except Exception as e:
            self.status_message.emit(f"Error creating project: {str(e)}")
            return False

    def add_dependency(self, library_name: str, version: str = "*", dev: bool = False) -> bool:
        """Add a dependency to current project"""
        if not self.current_project:
            self.status_message.emit("No project loaded")
            return False

        self.current_project.add_dependency(library_name, version, dev=dev)
        self.dependencies_changed.emit()
        self.status_message.emit(f"Added dependency: {library_name} ({version})")
        return True

    def remove_dependency(self, library_name: str) -> bool:
        """Remove a dependency from current project"""
        if not self.current_project:
            self.status_message.emit("No project loaded")
            return False

        self.current_project.remove_dependency(library_name)
        self.dependencies_changed.emit()
        self.status_message.emit(f"Removed dependency: {library_name}")
        return True

    def install_dependencies(self, include_dev: bool = False) -> InstallPlan:
        """Install all project dependencies"""
        return self.create_install_plan(include_dev=include_dev)

    def create_install_plan(self, include_dev: bool = False) -> InstallPlan:
        """Create an installation plan for project dependencies"""
        if not self.current_project:
            plan = InstallPlan()
            plan.conflicts.append("No project loaded")
            return plan

        if not self.library_manager:
            plan = InstallPlan()
            plan.conflicts.append("Library manager not available")
            return plan

        plan = InstallPlan()

        # Get all dependencies
        dependencies = self.current_project.get_all_dependencies(include_dev=include_dev)

        for dep_name, dep in dependencies.items():
            library = self.library_manager.get_library(dep_name)

            if not library:
                plan.conflicts.append(f"Library '{dep_name}' not found")
                continue

            version_to_install = self._resolve_dependency_version(library, dep)

            if not version_to_install:
                plan.conflicts.append(
                    f"No available versions of '{dep_name}' satisfy constraint '{dep.version}'"
                )
                continue

            if library.installed_version:
                if library.installed_version == version_to_install:
                    plan.already_installed.append((dep_name, version_to_install))
                else:
                    plan.to_update.append((dep_name, library.installed_version, version_to_install))
            else:
                plan.to_install.append((dep_name, version_to_install))

        return plan

    def _resolve_dependency_version(self, library, dependency: ProjectDependency) -> Optional[str]:
        """Resolve the best matching version for a dependency"""
        available_versions = getattr(library, "available_versions", None)
        if not available_versions:
            # Fall back to latest_version if available
            return library.latest_version

        constraint = (dependency.version or "*").strip()

        # Wildcard or default constraint selects the highest available version
        if constraint in ("", "*"):
            return available_versions[0]
        normalized_constraint = self._normalize_constraint(constraint)

        try:
            spec = SpecifierSet(normalized_constraint)
        except InvalidSpecifier:
            try:
                target_version = Version(normalized_constraint)
            except InvalidVersion:
                return normalized_constraint if normalized_constraint in available_versions else None

            for version_str in available_versions:
                try:
                    if Version(version_str) == target_version:
                        return version_str
                except InvalidVersion:
                    continue
            return None

        for version_str in available_versions:
            if spec.contains(version_str, prereleases=True):
                return version_str

        return None

    def _normalize_constraint(self, constraint: str) -> str:
        """Normalize constraint strings (handle caret and spacing)."""
        if constraint.startswith("^"):
            caret_target = constraint[1:]
            try:
                version = Version(caret_target)
            except InvalidVersion:
                return constraint

            if version.major > 0:
                upper = Version(f"{version.major + 1}.0.0")
            elif version.minor > 0:
                upper = Version(f"0.{version.minor + 1}.0")
            else:
                upper = Version(f"0.0.{version.micro + 1}")

            return f">={version},<{upper}"

        parts = [part.strip() for part in constraint.replace(",", " ").split() if part.strip()]
        if len(parts) > 1:
            return ",".join(parts)

        return parts[0] if parts else constraint

    def execute_install_plan(self, plan: InstallPlan) -> bool:
        """Execute an installation plan"""
        if not self.library_manager:
            return False

        if plan.has_conflicts():
            self.status_message.emit("Cannot install: plan has conflicts")
            return False

        success = True

        # Install new libraries
        for lib_name, version in plan.to_install:
            if not self.library_manager.install_library(lib_name, version):
                success = False

        # Update existing libraries
        for lib_name, old_version, new_version in plan.to_update:
            if not self.library_manager.update_library(lib_name, new_version):
                success = False

        return success

    def sync_dependencies_from_code(self, code: str) -> List[str]:
        """Detect and suggest dependencies from code includes"""
        if not self.current_project:
            return []

        # Parse #include statements
        includes = []
        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('#include'):
                # Extract library name
                if '<' in line and '>' in line:
                    lib_file = line.split('<')[1].split('>')[0]
                    lib_name = lib_file.split('.')[0]
                    if lib_name and lib_name not in ['Arduino', 'avr']:
                        includes.append(lib_name)
                elif '"' in line:
                    lib_file = line.split('"')[1]
                    lib_name = lib_file.split('.')[0]
                    if lib_name:
                        includes.append(lib_name)

        # Check which libraries are not in project dependencies
        missing_deps = []
        for lib_name in includes:
            if not self.current_project.has_dependency(lib_name):
                missing_deps.append(lib_name)

        return missing_deps

    def auto_add_dependencies_from_code(self, code: str) -> int:
        """Automatically add missing dependencies detected from code"""
        missing = self.sync_dependencies_from_code(code)
        added_count = 0

        for lib_name in missing:
            # Try to find exact library name
            if self.library_manager:
                library = self.library_manager.get_library(lib_name)
                if library:
                    self.add_dependency(library.name)
                    added_count += 1

        if added_count > 0:
            self.save_project()

        return added_count

    def set_board(self, fqbn: str, port: Optional[str] = None) -> bool:
        """Set project board configuration"""
        if not self.current_project:
            self.status_message.emit("No project loaded")
            return False

        from ..models import ProjectBoard
        self.current_project.board = ProjectBoard(fqbn=fqbn, port=port)
        self.status_message.emit(f"Set board: {fqbn}")
        return True

    def get_board_name(self) -> Optional[str]:
        """Get current project board name"""
        if not self.current_project or not self.current_project.board:
            return None

        if self.board_manager:
            board = self.board_manager.get_board(self.current_project.board.fqbn)
            if board:
                return board.name

        return self.current_project.board.fqbn

    def export_dependencies(self, path: Path):
        """Export project dependencies to a file"""
        if not self.current_project:
            return

        import json
        data = {
            "project": self.current_project.name,
            "dependencies": {
                name: dep.version
                for name, dep in self.current_project.dependencies.items()
            }
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def validate_project(self) -> List[str]:
        """Validate project configuration and return list of issues"""
        issues = []

        if not self.current_project:
            issues.append("No project loaded")
            return issues

        # Check board
        if not self.current_project.board:
            issues.append("No board configured")
        elif self.board_manager:
            board = self.board_manager.get_board(self.current_project.board.fqbn)
            if not board:
                issues.append(f"Board '{self.current_project.board.fqbn}' not found")

        # Check dependencies
        if self.library_manager:
            for dep_name, dep in self.current_project.dependencies.items():
                library = self.library_manager.get_library(dep_name)
                if not library:
                    issues.append(f"Dependency '{dep_name}' not found in library index")
                elif not library.installed_version:
                    issues.append(f"Dependency '{dep_name}' not installed")

        return issues
