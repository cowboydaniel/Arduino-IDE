"""
Example Plugin for Arduino IDE Modern
Demonstrates how to create a plugin using the Plugin API
"""

from arduino_ide.services.plugin_system import Plugin
import logging

logger = logging.getLogger(__name__)


class ExamplePlugin(Plugin):
    """
    Example plugin that adds custom functionality to the IDE
    """

    def activate(self):
        """
        Called when plugin is activated
        Register commands, menu items, and panels here
        """
        logger.info(f"Activating {self.metadata.name}...")

        # Register a command
        self.api.register_command("example.hello_world", self.hello_world)
        logger.info("Registered command: example.hello_world")

        # Register a menu item
        self.api.register_menu_item(
            "Tools/Example Plugin",
            "Say Hello",
            self.hello_world
        )
        logger.info("Registered menu item: Tools/Example Plugin")

        # Show activation message
        self.api.show_message(
            f"{self.metadata.name} v{self.metadata.version} activated!",
            "Plugin Activated"
        )


    def deactivate(self):
        """
        Called when plugin is deactivated
        Clean up resources here
        """
        logger.info(f"Deactivating {self.metadata.name}...")

        # Show deactivation message
        self.api.show_message(
            f"{self.metadata.name} deactivated",
            "Plugin Deactivated"
        )


    def hello_world(self):
        """
        Example command handler
        """
        logger.info("Hello World command executed")

        # Get current code
        current_code = self.api.get_current_code()

        if current_code:
            # Insert a comment at the beginning
            self.api.insert_code("// Hello from Example Plugin!\n", position=0)
            self.api.show_message("Added greeting comment to code!", "Success")
        else:
            self.api.show_message("No code editor active", "Info")


    def on_file_opened(self, file_path: str):
        """
        Called when a file is opened
        """
        logger.info(f"File opened: {file_path}")

        # You could add custom handling here
        # For example, check file type, load project settings, etc.


    def on_file_saved(self, file_path: str):
        """
        Called when a file is saved
        """
        logger.info(f"File saved: {file_path}")

        # You could add custom handling here
        # For example, auto-format, run linter, backup, etc.


    def on_compile_started(self):
        """
        Called when compilation starts
        """
        logger.info("Compilation started")

        # You could add custom handling here
        # For example, show status, start timer, etc.


    def on_compile_finished(self, success: bool):
        """
        Called when compilation finishes
        """
        logger.info(f"Compilation finished (success={success})")

        if success:
            self.api.show_message("Compilation successful!", "Compile Complete")
        else:
            self.api.show_message("Compilation failed!", "Compile Error")
