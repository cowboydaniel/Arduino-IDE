# Example Plugin for Arduino IDE Modern

This is an example plugin that demonstrates how to use the Plugin API.

## Features

- Adds a "Say Hello" menu item under Tools
- Registers a command that can be executed
- Responds to IDE events (file open/save, compile)
- Interacts with the code editor

## Installation

1. Copy this directory to your plugins folder:
   - Linux/Mac: `~/.arduino-ide-modern/plugins/example-plugin/`
   - Windows: `%USERPROFILE%\.arduino-ide-modern\plugins\example-plugin\`

2. Or install via Plugin Manager:
   - Tools → Plugin Manager
   - Click "Install"
   - Select the plugin zip file

## Usage

1. Open Plugin Manager (Tools → Plugin Manager)
2. Find "Example Plugin" in the list
3. Click "Activate"
4. Go to Tools → Example Plugin → Say Hello

The plugin will add a comment to your code!

## Plugin Structure

```
example-plugin/
├── plugin.json          # Plugin manifest
├── example_plugin.py    # Main plugin code
└── README.md            # This file
```

## Plugin Manifest

The `plugin.json` file contains:
- Plugin ID and name
- Version and author
- Entry point (Python class)
- Dependencies
- License information

## Plugin Code

The `example_plugin.py` file contains:
- `ExamplePlugin` class inheriting from `Plugin`
- `activate()` method - called when plugin loads
- `deactivate()` method - called when plugin unloads
- Event handlers for IDE events
- Command handlers

## Available API Methods

### Information
- `api.get_version()` - Get IDE version

### Commands
- `api.register_command(id, handler)` - Register command
- `api.execute_command(id, *args)` - Execute command

### UI
- `api.register_panel(id, widget)` - Register UI panel
- `api.register_menu_item(path, label, handler)` - Add menu item
- `api.show_message(message, title)` - Show dialog

### Editor
- `api.get_current_file_path()` - Get current file
- `api.get_current_code()` - Get editor content
- `api.insert_code(code, position)` - Insert code

### Build
- `api.compile_sketch(path)` - Trigger compilation
- `api.upload_sketch(path, port)` - Trigger upload

### Project
- `api.get_project_path()` - Get project directory

## Event Handlers

Override these methods to handle events:
- `on_file_opened(file_path)` - File opened
- `on_file_saved(file_path)` - File saved
- `on_compile_started()` - Compilation started
- `on_compile_finished(success)` - Compilation finished

## Creating Your Own Plugin

1. Copy this example
2. Modify `plugin.json` with your info
3. Rename the Python file and class
4. Implement your features in `activate()`
5. Clean up in `deactivate()`
6. Package as zip or install directory

## License

MIT License - see plugin.json for details
