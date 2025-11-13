"""Adapter that converts KiCAD `.kicad_sym` libraries into component definitions."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from arduino_ide.models.circuit_domain import (
    ComponentDefinition,
    ComponentType,
    Pin,
    PinType,
)

logger = logging.getLogger(__name__)

_COORD_KEYS = {"xy", "start", "end", "center", "at"}
_PIN_FUNCTION_MAP = {
    "passive": PinType.ANALOG,
    "input": PinType.DIGITAL,
    "output": PinType.DIGITAL,
    "bidirectional": PinType.DIGITAL,
    "tri_state": PinType.DIGITAL,
    "open_collector": PinType.DIGITAL,
    "open_emitter": PinType.DIGITAL,
    "unspecified": PinType.DIGITAL,
    "power_in": PinType.POWER,
    "power_out": PinType.POWER,
    "power": PinType.POWER,
    "ground": PinType.GROUND,
}
_CACHE_VERSION = 2  # Incremented for graphics support


class KiCADSymbolAdapter:
    """Parse KiCAD symbol libraries and emit `ComponentDefinition` objects."""

    def __init__(self, search_paths: Sequence[Path], cache_dir: Path):
        self.search_paths = [Path(path).expanduser() for path in (search_paths or [])]
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_components(self) -> List[ComponentDefinition]:
        """Discover all KiCAD libraries and return their component definitions."""

        libraries = self._discover_symbol_libraries()
        if not libraries:
            logger.warning("No KiCAD symbol libraries discovered in %s", self.search_paths)
            return []

        components: List[ComponentDefinition] = []
        for library_name in sorted(libraries.keys()):
            lib_path = libraries[library_name]
            try:
                components.extend(self._load_library(library_name, lib_path))
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.error("Failed to load KiCAD library %s: %s", lib_path, exc)
        return components

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------
    def _discover_symbol_libraries(self) -> Dict[str, Path]:
        """Return a mapping of KiCAD library names to their paths."""

        libraries: Dict[str, Path] = {}
        for base_path in self.search_paths:
            if not base_path.exists():
                logger.debug("Skipping missing KiCAD path: %s", base_path)
                continue

            if base_path.is_file() and base_path.suffix == ".kicad_sym":
                libraries[base_path.stem] = base_path
                continue

            if not base_path.is_dir():
                continue

            for lib_path in base_path.glob("*.kicad_sym"):
                libraries[lib_path.stem] = lib_path
        return libraries

    # ------------------------------------------------------------------
    # Library parsing and caching
    # ------------------------------------------------------------------
    def _load_library(self, library_name: str, library_path: Path) -> List[ComponentDefinition]:
        cache_path = self.cache_dir / f"{library_name}.json"
        stat = library_path.stat()
        source_signature = {
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size,
        }

        cached = self._read_cache(cache_path)
        if (
            cached
            and cached.get("source_signature") == source_signature
            and cached.get("version") == _CACHE_VERSION
        ):
            return [self._component_from_cache(entry) for entry in cached.get("components", [])]

        definitions = self._parse_symbol_file(library_name, library_path)
        payload = {
            "version": _CACHE_VERSION,
            "source_signature": source_signature,
            "components": [self._component_to_cache(entry) for entry in definitions],
        }
        cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return definitions

    def _read_cache(self, cache_path: Path) -> Optional[Dict[str, object]]:
        if not cache_path.exists():
            return None
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Discarding corrupt KiCAD symbol cache: %s", cache_path)
            return None

    # ------------------------------------------------------------------
    # Component serialization helpers
    # ------------------------------------------------------------------
    def _component_to_cache(self, component: ComponentDefinition) -> Dict[str, object]:
        return {
            "id": component.id,
            "name": component.name,
            "component_type": component.component_type.value,
            "width": component.width,
            "height": component.height,
            "description": component.description,
            "datasheet_url": component.datasheet_url,
            "image_path": component.image_path,
            "metadata": component.metadata,
            "pins": [
                {
                    "id": pin.id,
                    "label": pin.label,
                    "pin_type": pin.pin_type.value,
                    "position": [pin.position[0], pin.position[1]],
                }
                for pin in component.pins
            ],
            "graphics": component.graphics,
        }

    def _component_from_cache(self, data: Dict[str, object]) -> ComponentDefinition:
        pins = [
            Pin(
                id=pin_data["id"],
                label=pin_data["label"],
                pin_type=PinType(pin_data["pin_type"]),
                position=(float(pin_data["position"][0]), float(pin_data["position"][1])),
            )
            for pin_data in data.get("pins", [])
        ]
        component_type = ComponentType(data["component_type"])
        return ComponentDefinition(
            id=data["id"],
            name=data["name"],
            component_type=component_type,
            width=float(data["width"]),
            height=float(data["height"]),
            pins=pins,
            graphics=data.get("graphics", []),
            image_path=data.get("image_path"),
            description=data.get("description", ""),
            datasheet_url=data.get("datasheet_url"),
            metadata=data.get("metadata", {}),
        )

    # ------------------------------------------------------------------
    # KiCAD parser helpers
    # ------------------------------------------------------------------
    def _parse_symbol_file(self, library_name: str, library_path: Path) -> List[ComponentDefinition]:
        raw_text = library_path.read_text(encoding="utf-8")
        sexpr = self._parse_sexpr(raw_text)
        if not sexpr:
            return []

        definitions: List[ComponentDefinition] = []
        for node in sexpr:
            if not isinstance(node, list) or not node:
                continue
            if node[0] != "kicad_symbol_lib":
                continue
            for child in node[1:]:
                if isinstance(child, list) and child and child[0] == "symbol":
                    definition = self._symbol_to_component(library_name, library_path, child)
                    if definition:
                        definitions.append(definition)
        return definitions

    def _symbol_to_component(
        self,
        library_name: str,
        library_path: Path,
        symbol_node: List[object],
    ) -> Optional[ComponentDefinition]:
        if len(symbol_node) < 2:
            return None

        qualified_name = str(symbol_node[1])
        symbol_name = qualified_name.split(":", 1)[1] if ":" in qualified_name else qualified_name
        properties = self._extract_properties(symbol_node)
        keywords = self._split_keywords(properties.get("Keywords", ""))
        description = properties.get("Description", "")
        datasheet = properties.get("Datasheet") or None
        value_name = properties.get("Value", symbol_name)
        reference = properties.get("Reference", "")
        units = [
            (unit[1].split(":", 1)[1] if isinstance(unit[1], str) and ":" in unit[1] else unit[1])
            for unit in symbol_node[2:]
            if isinstance(unit, list) and unit and unit[0] == "symbol" and len(unit) > 1
        ]

        pin_records = self._collect_pins(symbol_node)
        bounds = self._calculate_bounds(symbol_node)
        offset_x, offset_y, width, height = bounds

        pins = [
            Pin(
                id=record["id"],
                label=record["label"],
                pin_type=record["pin_type"],
                position=(record["x"] - offset_x, record["y"] - offset_y),
            )
            for record in pin_records
        ]

        # Extract graphics elements from the symbol
        graphics = self._collect_graphics(symbol_node, offset_x, offset_y)

        metadata = {
            "library": library_name,
            "library_path": str(library_path),
            "symbol_name": symbol_name,
            "symbol_qualified_name": qualified_name,
            "keywords": keywords,
            "reference": reference,
            "units": units,
            "source_mtime": library_path.stat().st_mtime,
        }
        if datasheet:
            metadata["datasheet"] = datasheet

        component = ComponentDefinition(
            id=f"{library_name}:{symbol_name}",
            name=value_name,
            component_type=self._guess_component_type(reference, keywords, symbol_name),
            width=width,
            height=height,
            pins=pins,
            graphics=graphics,
            image_path=None,
            description=description,
            datasheet_url=datasheet,
            metadata=metadata,
        )
        return component

    def _extract_properties(self, symbol_node: List[object]) -> Dict[str, str]:
        properties: Dict[str, str] = {}
        for child in symbol_node[1:]:
            if isinstance(child, list) and child and child[0] == "property" and len(child) >= 3:
                properties[str(child[1])] = str(child[2])
        return properties

    def _split_keywords(self, keywords_raw: str) -> List[str]:
        return [token for token in keywords_raw.split() if token]

    def _collect_pins(self, symbol_node: List[object]) -> List[Dict[str, object]]:
        pin_nodes: List[List[object]] = []
        for child in symbol_node[2:]:
            if isinstance(child, list) and child and child[0] == "symbol":
                pin_nodes.extend(self._collect_pin_nodes(child))
        if not pin_nodes:
            pin_nodes = self._collect_pin_nodes(symbol_node)

        pins: List[Dict[str, object]] = []
        for index, pin_node in enumerate(pin_nodes, start=1):
            pin_type = self._map_pin_type(pin_node)
            position = self._extract_position(pin_node)
            name = self._extract_text(pin_node, "name")
            number = self._extract_text(pin_node, "number")
            label = name or number or f"Pin {index}"
            pin_id = number or label
            pins.append(
                {
                    "id": pin_id,
                    "label": label,
                    "pin_type": pin_type,
                    "x": position[0],
                    "y": position[1],
                }
            )
        return pins

    def _collect_pin_nodes(self, node: List[object]) -> List[List[object]]:
        nodes: List[List[object]] = []
        for child in node[1:]:
            if isinstance(child, list) and child and child[0] == "pin":
                nodes.append(child)
        return nodes

    def _collect_graphics(self, symbol_node: List[object], offset_x: float, offset_y: float) -> List[Dict[str, object]]:
        """Extract all graphics primitives from the symbol, with position offsets applied."""
        graphics: List[Dict[str, object]] = []

        # Graphics are in the unit sub-symbols (e.g., "Reference:R_Generic_0")
        for child in symbol_node[2:]:
            if isinstance(child, list) and child and child[0] == "symbol":
                graphics.extend(self._extract_graphics_from_unit(child, offset_x, offset_y))

        # If no graphics found in units, try the main symbol node
        if not graphics:
            graphics.extend(self._extract_graphics_from_unit(symbol_node, offset_x, offset_y))

        return graphics

    def _extract_graphics_from_unit(self, unit_node: List[object], offset_x: float, offset_y: float) -> List[Dict[str, object]]:
        """Extract graphics primitives from a symbol unit node."""
        graphics: List[Dict[str, object]] = []

        for child in unit_node[1:]:
            if not isinstance(child, list) or not child:
                continue

            element_type = str(child[0])

            if element_type == "polyline":
                graphic = self._parse_polyline(child, offset_x, offset_y)
                if graphic:
                    graphics.append(graphic)
            elif element_type == "rectangle":
                graphic = self._parse_rectangle(child, offset_x, offset_y)
                if graphic:
                    graphics.append(graphic)
            elif element_type == "circle":
                graphic = self._parse_circle(child, offset_x, offset_y)
                if graphic:
                    graphics.append(graphic)
            elif element_type == "arc":
                graphic = self._parse_arc(child, offset_x, offset_y)
                if graphic:
                    graphics.append(graphic)

        return graphics

    def _parse_polyline(self, node: List[object], offset_x: float, offset_y: float) -> Optional[Dict[str, object]]:
        """Parse a polyline graphic element."""
        points: List[Tuple[float, float]] = []
        stroke_width = 0.254  # Default KiCad stroke width
        fill_type = "none"

        for child in node[1:]:
            if not isinstance(child, list) or not child:
                continue

            if child[0] == "pts":
                # Extract points from (xy x y) tuples
                for pt_child in child[1:]:
                    if isinstance(pt_child, list) and pt_child and pt_child[0] == "xy" and len(pt_child) >= 3:
                        x = self._to_float(pt_child[1]) - offset_x
                        y = self._to_float(pt_child[2]) - offset_y
                        points.append((x, y))
            elif child[0] == "stroke":
                stroke_width = self._extract_stroke_width(child) or stroke_width
            elif child[0] == "fill":
                fill_type = self._extract_fill_type(child)

        if not points:
            return None

        # Convert to renderer format
        result = {
            "type": "polygon",
            "points": points,
            "width": max(stroke_width, 0.254),  # Ensure minimum visible width
            "pen": "#000000",  # Black stroke like KiCad
        }

        # Only add fill if it's not "none"
        if fill_type and fill_type != "none":
            result["fill"] = "#FAFAFA"  # Light gray fill like KiCad

        return result

    def _parse_rectangle(self, node: List[object], offset_x: float, offset_y: float) -> Optional[Dict[str, object]]:
        """Parse a rectangle graphic element."""
        start_x, start_y = 0.0, 0.0
        end_x, end_y = 0.0, 0.0
        stroke_width = 0.254  # Default KiCad stroke width
        fill_type = "none"

        for child in node[1:]:
            if not isinstance(child, list) or not child:
                continue

            if child[0] == "start" and len(child) >= 3:
                start_x = self._to_float(child[1]) - offset_x
                start_y = self._to_float(child[2]) - offset_y
            elif child[0] == "end" and len(child) >= 3:
                end_x = self._to_float(child[1]) - offset_x
                end_y = self._to_float(child[2]) - offset_y
            elif child[0] == "stroke":
                stroke_width = self._extract_stroke_width(child) or stroke_width
            elif child[0] == "fill":
                fill_type = self._extract_fill_type(child)

        # Convert to renderer format (x, y, width, height)
        x = min(start_x, end_x)
        y = min(start_y, end_y)
        width = abs(end_x - start_x)
        height = abs(end_y - start_y)

        result = {
            "type": "rect",
            "rect": [x, y, width, height],
            "width": max(stroke_width, 0.254),  # Ensure minimum visible width
            "pen": "#000000",  # Black stroke like KiCad
        }

        # Only add fill if it's not "none"
        if fill_type and fill_type != "none":
            result["fill"] = "#FAFAFA"  # Light gray fill like KiCad

        return result

    def _parse_circle(self, node: List[object], offset_x: float, offset_y: float) -> Optional[Dict[str, object]]:
        """Parse a circle graphic element."""
        center_x, center_y = 0.0, 0.0
        radius = 0.0
        stroke_width = 0.254  # Default KiCad stroke width
        fill_type = "none"

        for child in node[1:]:
            if not isinstance(child, list) or not child:
                continue

            if child[0] == "center" and len(child) >= 3:
                center_x = self._to_float(child[1]) - offset_x
                center_y = self._to_float(child[2]) - offset_y
            elif child[0] == "radius" and len(child) >= 2:
                radius = self._to_float(child[1])
            elif child[0] == "stroke":
                stroke_width = self._extract_stroke_width(child) or stroke_width
            elif child[0] == "fill":
                fill_type = self._extract_fill_type(child)

        result = {
            "type": "circle",
            "center": [center_x, center_y],
            "radius": radius,
            "width": max(stroke_width, 0.254),  # Ensure minimum visible width
            "pen": "#000000",  # Black stroke like KiCad
        }

        # Only add fill if it's not "none"
        if fill_type and fill_type != "none":
            result["fill"] = "#FAFAFA"  # Light gray fill like KiCad

        return result

    def _parse_arc(self, node: List[object], offset_x: float, offset_y: float) -> Optional[Dict[str, object]]:
        """Parse an arc graphic element.

        KiCad uses 3-point arcs (start, mid, end). For simplicity, we approximate
        with a polyline for now. A full implementation would calculate the center
        and angles from the 3 points.
        """
        start_x, start_y = 0.0, 0.0
        mid_x, mid_y = 0.0, 0.0
        end_x, end_y = 0.0, 0.0
        stroke_width = 0.254  # Default KiCad stroke width
        fill_type = "none"

        for child in node[1:]:
            if not isinstance(child, list) or not child:
                continue

            if child[0] == "start" and len(child) >= 3:
                start_x = self._to_float(child[1]) - offset_x
                start_y = self._to_float(child[2]) - offset_y
            elif child[0] == "mid" and len(child) >= 3:
                mid_x = self._to_float(child[1]) - offset_x
                mid_y = self._to_float(child[2]) - offset_y
            elif child[0] == "end" and len(child) >= 3:
                end_x = self._to_float(child[1]) - offset_x
                end_y = self._to_float(child[2]) - offset_y
            elif child[0] == "stroke":
                stroke_width = self._extract_stroke_width(child) or stroke_width
            elif child[0] == "fill":
                fill_type = self._extract_fill_type(child)

        # Approximate arc with a simple 3-point polyline
        # TODO: Calculate proper arc center and angles for accurate rendering
        result = {
            "type": "polygon",
            "points": [(start_x, start_y), (mid_x, mid_y), (end_x, end_y)],
            "width": max(stroke_width, 0.254),
            "pen": "#000000",
        }

        if fill_type and fill_type != "none":
            result["fill"] = "#FAFAFA"

        return result

    def _extract_stroke_width(self, stroke_node: List[object]) -> float:
        """Extract stroke width from a stroke node."""
        for child in stroke_node[1:]:
            if isinstance(child, list) and child and child[0] == "width" and len(child) >= 2:
                return self._to_float(child[1])
        return 0.0

    def _extract_fill_type(self, fill_node: List[object]) -> str:
        """Extract fill type from a fill node."""
        for child in fill_node[1:]:
            if isinstance(child, list) and child and child[0] == "type" and len(child) >= 2:
                return str(child[1])
        return "none"

    def _map_pin_type(self, pin_node: List[object]) -> PinType:
        function_name = pin_node[1] if len(pin_node) > 1 else ""
        return _PIN_FUNCTION_MAP.get(str(function_name), PinType.DIGITAL)

    def _extract_text(self, node: List[object], key: str) -> str:
        for child in node[1:]:
            if isinstance(child, list) and child and child[0] == key and len(child) > 1:
                return str(child[1])
        return ""

    def _extract_position(self, node: List[object]) -> Tuple[float, float]:
        for child in node[1:]:
            if isinstance(child, list) and child and child[0] == "at" and len(child) >= 3:
                return (self._to_float(child[1]), self._to_float(child[2]))
        return (0.0, 0.0)

    def _calculate_bounds(self, node: List[object]) -> Tuple[float, float, float, float]:
        coords: List[Tuple[float, float]] = []
        self._gather_coordinates(node, coords)
        if not coords:
            margin = 20.0
            return (-margin / 2, -margin / 2, margin, margin)

        xs = [coord[0] for coord in coords]
        ys = [coord[1] for coord in coords]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        margin = 5.0
        width = max((max_x - min_x) + 2 * margin, 20.0)
        height = max((max_y - min_y) + 2 * margin, 20.0)
        return (min_x - margin, min_y - margin, width, height)

    def _gather_coordinates(self, node: List[object], coords: List[Tuple[float, float]]):
        if not isinstance(node, list):
            return
        if node and node[0] in _COORD_KEYS and len(node) >= 3:
            coords.append((self._to_float(node[1]), self._to_float(node[2])))
        for child in node[1:]:
            self._gather_coordinates(child, coords)

    def _guess_component_type(self, reference: str, keywords: List[str], symbol_name: str) -> ComponentType:
        reference = reference.upper()
        mapping = {
            "R": ComponentType.RESISTOR,
            "C": ComponentType.CAPACITOR,
            "Q": ComponentType.TRANSISTOR,
            "U": ComponentType.IC,
            "IC": ComponentType.IC,
            "SW": ComponentType.BUTTON,
            "S": ComponentType.SENSOR,
            "D": ComponentType.LED,
            "LED": ComponentType.LED,
        }
        for prefix, component_type in mapping.items():
            if reference.startswith(prefix):
                return component_type
        for keyword in keywords:
            kw = keyword.lower()
            if "sensor" in kw:
                return ComponentType.SENSOR
            if "led" in kw:
                return ComponentType.LED
            if "res" in kw:
                return ComponentType.RESISTOR
            if "cap" in kw:
                return ComponentType.CAPACITOR
        if symbol_name.upper().startswith("BAT"):
            return ComponentType.BATTERY
        return ComponentType.IC

    def _parse_sexpr(self, raw_text: str) -> List[object]:
        tokens = self._tokenize(raw_text)
        stack: List[List[object]] = [[]]
        current = stack[0]
        for token in tokens:
            if token == "(":
                new_list: List[object] = []
                current.append(new_list)
                stack.append(current)
                current = new_list
            elif token == ")":
                if len(stack) == 1:
                    continue
                current = stack.pop()
            else:
                current.append(token)
        return stack[0]

    def _tokenize(self, raw_text: str) -> List[str]:
        tokens: List[str] = []
        index = 0
        length = len(raw_text)
        while index < length:
            char = raw_text[index]
            if char in "()":
                tokens.append(char)
                index += 1
            elif char.isspace():
                index += 1
            elif char == '"':
                end_index = index + 1
                buffer: List[str] = []
                escape = False
                while end_index < length:
                    current_char = raw_text[end_index]
                    if escape:
                        buffer.append(current_char)
                        escape = False
                    elif current_char == "\\":
                        escape = True
                    elif current_char == '"':
                        break
                    else:
                        buffer.append(current_char)
                    end_index += 1
                tokens.append("".join(buffer))
                index = end_index + 1
            else:
                end_index = index + 1
                while end_index < length and not raw_text[end_index].isspace() and raw_text[end_index] not in "()":
                    end_index += 1
                tokens.append(raw_text[index:end_index])
                index = end_index
        return tokens

    def _to_float(self, value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):  # pragma: no cover - defensive conversion
            return 0.0

