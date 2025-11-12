"""
Plugin System
Extensible plugin architecture for Arduino IDE Modern
"""

import os
import sys
import json
import importlib
import importlib.util
import logging
from typing import Dict, List, Optional, Callable, Any, Type
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from pathlib import Path
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Types of plugins"""
    TOOL = "tool"
    EDITOR = "editor"
    COMPILER = "compiler"
    LIBRARY = "library"
    THEME = "theme"
    EXPORT = "export"
    DEBUGGER = "debugger"
    LANGUAGE = "language"


class PluginStatus(Enum):
    """Plugin status"""
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginMetadata:
    """Metadata for a plugin"""
    id: str
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    entry_point: str  # Module path or class name
    dependencies: List[str] = field(default_factory=list)
    min_ide_version: str = "1.0.0"
    max_ide_version: Optional[str] = None
    homepage: Optional[str] = None
    license: str = "MIT"
    icon: Optional[str] = None


@dataclass
class PluginInfo:
    """Information about an installed plugin"""
    metadata: PluginMetadata
    path: str
    status: PluginStatus
    error_message: Optional[str] = None
    instance: Optional['Plugin'] = None


class PluginAPI:
    """
    API provided to plugins
    Plugins can use this to interact with the IDE
    """

    def __init__(self, ide_instance=None):
        self.ide = ide_instance
        self._registered_commands: Dict[str, Callable] = {}
        self._registered_panels: Dict[str, QObject] = {}
        self._registered_menu_items: Dict[str, Dict] = {}

    def get_version(self) -> str:
        """Get IDE version"""
        return "2.0.0"  # Phase 5 version

    def register_command(self, command_id: str, handler: Callable):
        """Register a command"""
        self._registered_commands[command_id] = handler
        logger.info(f"Command registered: {command_id}")

    def execute_command(self, command_id: str, *args, **kwargs) -> Any:
        """Execute a registered command"""
        if command_id in self._registered_commands:
            return self._registered_commands[command_id](*args, **kwargs)
        raise ValueError(f"Command not found: {command_id}")

    def register_panel(self, panel_id: str, panel_widget: QObject):
        """Register a UI panel"""
        self._registered_panels[panel_id] = panel_widget
        logger.info(f"Panel registered: {panel_id}")

    def get_panel(self, panel_id: str) -> Optional[QObject]:
        """Get a registered panel"""
        return self._registered_panels.get(panel_id)

    def register_menu_item(self, menu_path: str, label: str, handler: Callable):
        """Register a menu item"""
        self._registered_menu_items[menu_path] = {
            "label": label,
            "handler": handler
        }
        logger.info(f"Menu item registered: {menu_path}")

    def show_message(self, message: str, title: str = "Plugin Message"):
        """Show a message to the user"""
        # This would show a dialog in the actual IDE
        logger.info(f"Plugin message: {title} - {message}")

    def get_current_file_path(self) -> Optional[str]:
        """Get path of currently open file"""
        # Would get from IDE
        return None

    def get_current_code(self) -> Optional[str]:
        """Get code from current editor"""
        # Would get from IDE's editor
        return None

    def insert_code(self, code: str, position: Optional[int] = None):
        """Insert code into current editor"""
        # Would insert into IDE's editor
        logger.info(f"Plugin inserting code: {code[:50]}...")

    def get_project_path(self) -> Optional[str]:
        """Get current project path"""
        # Would get from IDE
        return None

    def compile_sketch(self, sketch_path: str) -> bool:
        """Trigger sketch compilation"""
        # Would trigger IDE's compiler
        logger.info(f"Plugin requested compilation: {sketch_path}")
        return True

    def upload_sketch(self, sketch_path: str, port: str) -> bool:
        """Trigger sketch upload"""
        # Would trigger IDE's uploader
        logger.info(f"Plugin requested upload: {sketch_path} to {port}")
        return True


class Plugin(ABC):
    """
    Base class for all plugins
    Plugins must inherit from this class
    """

    def __init__(self, api: PluginAPI):
        self.api = api
        self.metadata: Optional[PluginMetadata] = None

    @abstractmethod
    def activate(self):
        """
        Called when plugin is activated
        Override this to initialize your plugin
        """
        pass

    @abstractmethod
    def deactivate(self):
        """
        Called when plugin is deactivated
        Override this to cleanup your plugin
        """
        pass

    def on_file_opened(self, file_path: str):
        """Called when a file is opened"""
        pass

    def on_file_saved(self, file_path: str):
        """Called when a file is saved"""
        pass

    def on_compile_started(self):
        """Called when compilation starts"""
        pass

    def on_compile_finished(self, success: bool):
        """Called when compilation finishes"""
        pass


class PluginManager(QObject):
    """
    Manages plugin loading, activation, and lifecycle
    """

    # Signals
    plugin_loaded = Signal(str)  # plugin_id
    plugin_activated = Signal(str)
    plugin_deactivated = Signal(str)
    plugin_error = Signal(str, str)  # plugin_id, error_message

    def __init__(self, plugins_dir: Optional[str] = None, parent=None):
        super().__init__(parent)

        self.plugins_dir = plugins_dir or self._get_default_plugins_dir()
        self.api = PluginAPI()

        self._plugins: Dict[str, PluginInfo] = {}
        self._active_plugins: Dict[str, Plugin] = {}

        # Ensure plugins directory exists
        os.makedirs(self.plugins_dir, exist_ok=True)

        logger.info(f"Plugin manager initialized (plugins dir: {self.plugins_dir})")


    def _get_default_plugins_dir(self) -> str:
        """Get default plugins directory"""
        # Use user's home directory
        home = Path.home()
        plugins_dir = home / ".arduino-ide-modern" / "plugins"
        return str(plugins_dir)


    def discover_plugins(self) -> int:
        """
        Discover all plugins in the plugins directory
        Returns number of plugins found
        """
        count = 0

        if not os.path.exists(self.plugins_dir):
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return count

        # Scan subdirectories
        for item in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, item)

            if not os.path.isdir(plugin_path):
                continue

            # Look for plugin manifest
            manifest_path = os.path.join(plugin_path, "plugin.json")

            if not os.path.exists(manifest_path):
                logger.debug(f"No manifest found in {plugin_path}")
                continue

            try:
                # Load manifest
                with open(manifest_path, 'r') as f:
                    manifest_data = json.load(f)

                # Parse metadata
                metadata = self._parse_manifest(manifest_data)

                if not metadata:
                    logger.warning(f"Invalid manifest in {plugin_path}")
                    continue

                # Create plugin info
                plugin_info = PluginInfo(
                    metadata=metadata,
                    path=plugin_path,
                    status=PluginStatus.INACTIVE
                )

                self._plugins[metadata.id] = plugin_info
                count += 1

                logger.info(f"Discovered plugin: {metadata.name} v{metadata.version}")

            except Exception as e:
                logger.error(f"Error discovering plugin in {plugin_path}: {e}")

        logger.info(f"Discovered {count} plugin(s)")
        return count


    def _parse_manifest(self, data: Dict) -> Optional[PluginMetadata]:
        """Parse plugin manifest"""
        try:
            plugin_type_str = data.get("type", "tool")
            plugin_type = PluginType(plugin_type_str)

            metadata = PluginMetadata(
                id=data["id"],
                name=data["name"],
                version=data["version"],
                author=data["author"],
                description=data.get("description", ""),
                plugin_type=plugin_type,
                entry_point=data["entry_point"],
                dependencies=data.get("dependencies", []),
                min_ide_version=data.get("min_ide_version", "1.0.0"),
                max_ide_version=data.get("max_ide_version"),
                homepage=data.get("homepage"),
                license=data.get("license", "MIT"),
                icon=data.get("icon")
            )

            return metadata

        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing manifest: {e}")
            return None


    def load_plugin(self, plugin_id: str) -> bool:
        """Load a plugin"""
        if plugin_id not in self._plugins:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        plugin_info = self._plugins[plugin_id]

        if plugin_info.status == PluginStatus.LOADED:
            logger.warning(f"Plugin already loaded: {plugin_id}")
            return True

        try:
            # Add plugin path to Python path
            if plugin_info.path not in sys.path:
                sys.path.insert(0, plugin_info.path)

            # Import plugin module
            entry_point = plugin_info.metadata.entry_point

            # Load module
            module_name = entry_point.rsplit('.', 1)[0] if '.' in entry_point else entry_point
            spec = importlib.util.spec_from_file_location(
                module_name,
                os.path.join(plugin_info.path, f"{module_name}.py")
            )

            if not spec or not spec.loader:
                raise ImportError(f"Could not load module: {module_name}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get plugin class
            class_name = entry_point.rsplit('.', 1)[1] if '.' in entry_point else "MainPlugin"
            plugin_class = getattr(module, class_name)

            # Verify it's a Plugin subclass
            if not issubclass(plugin_class, Plugin):
                raise TypeError(f"{class_name} must inherit from Plugin")

            # Create instance
            plugin_instance = plugin_class(self.api)
            plugin_instance.metadata = plugin_info.metadata

            plugin_info.instance = plugin_instance
            plugin_info.status = PluginStatus.LOADED

            self.plugin_loaded.emit(plugin_id)
            logger.info(f"Plugin loaded: {plugin_id}")

            return True

        except Exception as e:
            logger.error(f"Error loading plugin {plugin_id}: {e}")
            plugin_info.status = PluginStatus.ERROR
            plugin_info.error_message = str(e)
            self.plugin_error.emit(plugin_id, str(e))
            return False


    def activate_plugin(self, plugin_id: str) -> bool:
        """Activate a plugin"""
        if plugin_id not in self._plugins:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        plugin_info = self._plugins[plugin_id]

        # Load if not loaded
        if plugin_info.status != PluginStatus.LOADED:
            if not self.load_plugin(plugin_id):
                return False

        if plugin_info.status == PluginStatus.ACTIVE:
            logger.warning(f"Plugin already active: {plugin_id}")
            return True

        try:
            # Activate plugin
            plugin_info.instance.activate()
            plugin_info.status = PluginStatus.ACTIVE
            self._active_plugins[plugin_id] = plugin_info.instance

            self.plugin_activated.emit(plugin_id)
            logger.info(f"Plugin activated: {plugin_id}")

            return True

        except Exception as e:
            logger.error(f"Error activating plugin {plugin_id}: {e}")
            plugin_info.status = PluginStatus.ERROR
            plugin_info.error_message = str(e)
            self.plugin_error.emit(plugin_id, str(e))
            return False


    def deactivate_plugin(self, plugin_id: str) -> bool:
        """Deactivate a plugin"""
        if plugin_id not in self._plugins:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        plugin_info = self._plugins[plugin_id]

        if plugin_info.status != PluginStatus.ACTIVE:
            logger.warning(f"Plugin not active: {plugin_id}")
            return True

        try:
            # Deactivate plugin
            plugin_info.instance.deactivate()
            plugin_info.status = PluginStatus.LOADED

            if plugin_id in self._active_plugins:
                del self._active_plugins[plugin_id]

            self.plugin_deactivated.emit(plugin_id)
            logger.info(f"Plugin deactivated: {plugin_id}")

            return True

        except Exception as e:
            logger.error(f"Error deactivating plugin {plugin_id}: {e}")
            plugin_info.error_message = str(e)
            self.plugin_error.emit(plugin_id, str(e))
            return False


    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """Get plugin information"""
        return self._plugins.get(plugin_id)


    def get_all_plugins(self) -> List[PluginInfo]:
        """Get list of all plugins"""
        return list(self._plugins.values())


    def get_active_plugins(self) -> List[Plugin]:
        """Get list of active plugins"""
        return list(self._active_plugins.values())


    def get_plugins_by_type(self, plugin_type: PluginType) -> List[PluginInfo]:
        """Get plugins of a specific type"""
        return [p for p in self._plugins.values()
                if p.metadata.plugin_type == plugin_type]


    def install_plugin(self, plugin_path: str) -> bool:
        """
        Install a plugin from a zip file or directory
        """
        try:
            import shutil

            # If it's a zip, extract it
            if plugin_path.endswith('.zip'):
                import zipfile

                with zipfile.ZipFile(plugin_path, 'r') as zip_ref:
                    # Extract to temporary location
                    import tempfile
                    temp_dir = tempfile.mkdtemp()
                    zip_ref.extractall(temp_dir)

                    # Read manifest to get plugin ID
                    manifest_path = os.path.join(temp_dir, "plugin.json")
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)

                    plugin_id = manifest["id"]

                    # Move to plugins directory
                    dest_path = os.path.join(self.plugins_dir, plugin_id)
                    if os.path.exists(dest_path):
                        shutil.rmtree(dest_path)

                    shutil.move(temp_dir, dest_path)

            else:
                # Copy directory
                with open(os.path.join(plugin_path, "plugin.json"), 'r') as f:
                    manifest = json.load(f)

                plugin_id = manifest["id"]
                dest_path = os.path.join(self.plugins_dir, plugin_id)

                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)

                shutil.copytree(plugin_path, dest_path)

            logger.info(f"Plugin installed: {plugin_id}")

            # Rediscover plugins
            self.discover_plugins()

            return True

        except Exception as e:
            logger.error(f"Error installing plugin: {e}")
            return False


    def uninstall_plugin(self, plugin_id: str) -> bool:
        """Uninstall a plugin"""
        if plugin_id not in self._plugins:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        try:
            # Deactivate if active
            if self._plugins[plugin_id].status == PluginStatus.ACTIVE:
                self.deactivate_plugin(plugin_id)

            # Remove plugin directory
            import shutil
            plugin_path = self._plugins[plugin_id].path
            shutil.rmtree(plugin_path)

            # Remove from registry
            del self._plugins[plugin_id]

            logger.info(f"Plugin uninstalled: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"Error uninstalling plugin: {e}")
            return False


    def notify_file_opened(self, file_path: str):
        """Notify all active plugins that a file was opened"""
        for plugin in self._active_plugins.values():
            try:
                plugin.on_file_opened(file_path)
            except Exception as e:
                logger.error(f"Error in plugin file_opened handler: {e}")


    def notify_file_saved(self, file_path: str):
        """Notify all active plugins that a file was saved"""
        for plugin in self._active_plugins.values():
            try:
                plugin.on_file_saved(file_path)
            except Exception as e:
                logger.error(f"Error in plugin file_saved handler: {e}")


    def notify_compile_started(self):
        """Notify all active plugins that compilation started"""
        for plugin in self._active_plugins.values():
            try:
                plugin.on_compile_started()
            except Exception as e:
                logger.error(f"Error in plugin compile_started handler: {e}")


    def notify_compile_finished(self, success: bool):
        """Notify all active plugins that compilation finished"""
        for plugin in self._active_plugins.values():
            try:
                plugin.on_compile_finished(success)
            except Exception as e:
                logger.error(f"Error in plugin compile_finished handler: {e}")
