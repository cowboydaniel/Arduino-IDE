# EESchema - KiCad-Style Schematic Editor

This module implements a schematic editor architecture modeled after KiCad's `eeschema` module.

## Architecture

The module follows KiCad's proven modular architecture with clear separation of concerns:

```
arduino_ide/eeschema/
├── schematic.py              # Core schematic data model (like KiCad's schematic.cpp)
├── sch_painter.py            # Rendering engine (like KiCad's sch_painter.cpp)
├── connection_graph.py       # Electrical connectivity analysis
│
├── tools/                    # Editor tools (select, wire, bus, etc.)
│   └── __init__.py
│
├── dialogs/                  # UI dialogs
│   └── __init__.py
│
├── erc/                      # Electrical Rules Checking
│   ├── __init__.py
│   └── erc_engine.py
│
├── sch_io/                   # File I/O plugins
│   ├── __init__.py
│   ├── sch_io_base.py       # Abstract base class
│   ├── kicad/               # KiCad format (.kicad_sch)
│   │   ├── __init__.py
│   │   └── sch_kicad_plugin.py
│   └── json/                # JSON format (legacy)
│       ├── __init__.py
│       └── sch_json_plugin.py
│
├── widgets/                  # Custom Qt widgets and graphics items
│   ├── __init__.py
│   └── sch_graphics_items.py
│
├── symbol_editor/           # Symbol editing (separate from schematic)
│   └── __init__.py
│
└── sim/                     # Circuit simulation integration
    └── __init__.py
```

## Core Components

### schematic.py - Core Data Model

The `Schematic` class manages:
- Component definitions and instances
- Electrical connections
- Hierarchical sheets
- Nets and buses
- Component annotations

Corresponds to KiCad's `SCHEMATIC` class.

### sch_painter.py - Rendering Engine

The `SchematicPainter` class provides:
- Component body rendering
- Pin rendering with decorations (clock, dot, triangle)
- Wire and bus drawing
- Orthogonal routing
- KiCad-compatible color scheme

Corresponds to KiCad's `SCH_PAINTER` class.

### connection_graph.py - Connectivity Analysis

The `ConnectionGraph` class handles:
- Building electrical connectivity graph
- Net identification and merging
- Netlist generation
- Unconnected pin detection

Corresponds to KiCad's `CONNECTION_GRAPH` class.

### erc/ - Electrical Rules Checking

The `ERCEngine` checks for:
- Unconnected power/ground pins
- Floating inputs
- Conflicting drivers
- Custom ERC rules

Follows KiCad's ERC architecture.

### sch_io/ - File Format Plugins

Pluggable I/O system supporting:
- **KiCad format** (`.kicad_sch`) - Native KiCad s-expression format
- **JSON format** (`.json`) - Legacy format for backward compatibility
- Extensible to support Eagle, Altium, LTSpice, etc.

Follows KiCad's `SCH_IO` plugin architecture.

### widgets/ - Graphics Items

Qt graphics items for rendering:
- `PinGraphicsItem` - Interactive pin representation
- `ComponentGraphicsItem` - Component symbol rendering
- `ConnectionGraphicsItem` - Wire/bus rendering

## Comparison with KiCad's eeschema

| KiCad eeschema | Arduino IDE eeschema | Description |
|----------------|---------------------|-------------|
| `schematic.cpp/h` | `schematic.py` | Core schematic data model |
| `sch_edit_frame.cpp/h` | (in `ui/circuit_editor.py`) | Main editor window |
| `sch_painter.cpp/h` | `sch_painter.py` | Rendering engine |
| `connection_graph.cpp/h` | `connection_graph.py` | Connectivity analysis |
| `tools/` | `tools/` | Editor tools |
| `dialogs/` | `dialogs/` | UI dialogs |
| `erc/` | `erc/` | Electrical rules checking |
| `sch_io/` | `sch_io/` | File I/O plugins |
| `widgets/` | `widgets/` | Custom widgets |
| `symbol_editor/` | `symbol_editor/` | Symbol editing |

## Key Design Principles

1. **Separation of Concerns**: Data model, rendering, and UI are clearly separated
2. **Modularity**: Each subsystem is independent and replaceable
3. **Extensibility**: Plugin-based I/O, tool system, and ERC rules
4. **KiCad Compatibility**: File format and workflow compatibility with KiCad
5. **Qt Integration**: Native PySide6 widgets and graphics framework

## Usage Example

```python
from arduino_ide.eeschema.schematic import Schematic
from arduino_ide.eeschema.sch_painter import SchematicPainter
from arduino_ide.eeschema.erc.erc_engine import ERCEngine
from arduino_ide.eeschema.connection_graph import ConnectionGraph

# Create schematic
schematic = Schematic()

# Add components
comp_id = schematic.add_component("resistor_symbol", x=100, y=100)

# Add connections
conn_id = schematic.add_connection(comp1_id, "pin1", comp2_id, "pin2")

# Run ERC
erc = ERCEngine()
is_valid, errors = erc.run_erc(
    schematic._components,
    schematic._connections,
    schematic._component_definitions
)

# Build connection graph
graph = ConnectionGraph()
graph.build_graph(
    schematic._components,
    schematic._connections,
    schematic._component_definitions
)
netlist = graph.generate_netlist()
```

## Future Enhancements

### Tools System
- [ ] Implement individual tool modules (sch_select_tool, sch_wire_tool, etc.)
- [ ] Tool state management and switching
- [ ] Keyboard shortcuts per tool

### File I/O
- [ ] Complete KiCad s-expression parser/writer
- [ ] Eagle XML import
- [ ] Altium import
- [ ] LTSpice import

### Simulation
- [ ] SPICE netlist export
- [ ] ngspice integration
- [ ] Waveform viewer

### Symbol Editor
- [ ] Dedicated symbol editing window
- [ ] Symbol library management
- [ ] Custom symbol creation

## Migration from Old Architecture

The previous monolithic structure:
- `ui/circuit_editor.py` (1,356 lines) - Everything in one file
- `services/circuit_service.py` (1,532 lines) - All business logic

Has been refactored into:
- Modular components with single responsibilities
- Clear API boundaries
- Easier testing and maintenance
- Better code organization

The old files remain for backward compatibility but should be updated to use the new modules.

## Visual Appearance - KiCad-Style UI

The schematic editor visually matches KiCad's eeschema interface:

### SCH_EDIT_FRAME - Main Editor Window

The main editor window (`sch_edit_frame.py`) replicates KiCad's layout:

**Canvas (Center):**
- White background (light theme) or dark gray (dark theme)
- Grid with dots (default), lines, or crosses
- Default grid size: 50 mil (1.27mm)
- Grid color: Light gray (#848484) on light theme, dark gray (#505050) on dark theme
- Pan with middle mouse button
- Zoom with mouse wheel
- Full-screen crosshair cursor (optional)

**Top Toolbar:**
- File operations (New, Open, Save)
- Edit operations (Undo, Redo)
- Zoom controls (Zoom In, Out, Fit)
- Find tool

**Left Toolbar:**
- Grid visibility toggle
- Units toggle (inch/mm)
- Cursor display toggle
- Properties panel toggle

**Right Toolbar:**
- Selection tool (Esc)
- Symbol placement (A)
- Power symbol (P)
- Wire drawing (W)
- Bus drawing (B)
- No-connect flag
- Junction (J)
- Net label (L)
- Global label
- Hierarchical sheet (S)
- Sheet pins
- Graphics (lines, text, images)
- Delete tool

**Status Bar:**
- Cursor position (X, Y) in mils or mm
- Relative position (dx, dy, dist)
- Zoom level (Z)
- Grid size
- Units (inches/mm)

**Menus:**
- File: New, Open, Save, Import, Export
- Edit: Undo, Redo, Cut, Copy, Paste
- View: Zoom, Grid options
- Place: Symbols, Wires, Buses, Labels, Power
- Inspect: ERC, Netlist generation
- Tools: Annotate, BOM generation
- Preferences: Settings, Color themes

### Launching the KiCad-Style UI

To see the KiCad-lookalike interface:

```bash
python test_kicad_ui.py
```

This launches the standalone schematic editor with KiCad's visual appearance and layout.

### Color Schemes

Two themes are supported:

**Light Theme (Default):**
- Background: White (#FFFFFF)
- Grid: Light gray (#848484)
- Wires: Dark gray (#2A2A2A)
- Components: Black outlines (#000000)

**Dark Theme:**
- Background: Dark gray (#191919)
- Grid: Medium gray (#505050)
- Wires: Green/Blue
- Components: Light colored outlines

Switch themes via `canvas.set_dark_theme()` or `canvas.set_light_theme()`.

## References

- [KiCad Source Code](https://gitlab.com/kicad/code/kicad/-/tree/master/eeschema)
- [KiCad File Formats](https://dev-docs.kicad.org/en/file-formats/)
- [KiCad Developer Documentation](https://dev-docs.kicad.org/)
- [KiCad 8.0 Schematic Editor Docs](https://docs.kicad.org/8.0/en/eeschema/eeschema.html)
