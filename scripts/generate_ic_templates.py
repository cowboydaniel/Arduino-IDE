"""Generate integrated circuit templates for the component library."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "arduino_ide" / "component_library" / "ics"


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def write_component(filename: str, data: Dict[str, object]) -> None:
    ensure_output_dir()
    (OUTPUT_DIR / filename).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def linear_package_positions(pin_count: int, width: int, spacing: int) -> Dict[int, Sequence[int]]:
    per_side = pin_count // 2
    positions: Dict[int, Sequence[int]] = {}
    for index in range(per_side):
        y = index * spacing
        positions[index + 1] = [0, y]
        positions[pin_count - index] = [width, y]
    return positions


def quad_package_positions(pin_count: int, body: int, pitch: int) -> Dict[int, Sequence[int]]:
    pins_per_side = pin_count // 4
    positions: Dict[int, Sequence[int]] = {}
    for idx in range(pin_count):
        pin = idx + 1
        side = idx // pins_per_side
        offset = idx % pins_per_side
        if side == 0:
            positions[pin] = [offset * pitch, 0]
        elif side == 1:
            positions[pin] = [body, offset * pitch]
        elif side == 2:
            positions[pin] = [body - offset * pitch, body]
        else:
            positions[pin] = [0, body - offset * pitch]
    return positions


def package_geometry(name: str) -> Tuple[int, int, Dict[int, Sequence[int]]]:
    mapping = {
        "dip8": (200, 280, linear_package_positions(8, 200, 40)),
        "dip14": (220, 320, linear_package_positions(14, 220, 32)),
        "dip16": (240, 360, linear_package_positions(16, 240, 30)),
        "dip20": (260, 420, linear_package_positions(20, 260, 26)),
        "dip28": (280, 480, linear_package_positions(28, 280, 20)),
        "dip32": (300, 520, linear_package_positions(32, 300, 18)),
        "dip40": (320, 560, linear_package_positions(40, 320, 18)),
        "soic8": (180, 240, linear_package_positions(8, 180, 32)),
        "soic14": (200, 280, linear_package_positions(14, 200, 28)),
        "soic16": (220, 320, linear_package_positions(16, 220, 26)),
        "soic20": (240, 360, linear_package_positions(20, 240, 24)),
        "soic28": (280, 440, linear_package_positions(28, 280, 20)),
        "tssop8": (160, 220, linear_package_positions(8, 160, 28)),
        "tssop14": (180, 260, linear_package_positions(14, 180, 24)),
        "tssop16": (200, 300, linear_package_positions(16, 200, 22)),
        "tssop20": (220, 340, linear_package_positions(20, 220, 20)),
        "tssop28": (260, 400, linear_package_positions(28, 260, 18)),
        "qfn20": (220, 220, quad_package_positions(20, 200, 24)),
        "qfn32": (240, 240, quad_package_positions(32, 220, 22)),
        "qfn48": (260, 260, quad_package_positions(48, 240, 18)),
        "tqfp32": (260, 260, quad_package_positions(32, 240, 24)),
        "tqfp44": (280, 280, quad_package_positions(44, 260, 20)),
        "tqfp64": (320, 320, quad_package_positions(64, 300, 18)),
    }
    if name not in mapping:
        raise KeyError(f"Unknown package {name}")
    return mapping[name]


def map_pins(pin_table: Iterable[Tuple[int, str, str, str]], positions: Dict[int, Sequence[int]]) -> List[Dict[str, object]]:
    pins: List[Dict[str, object]] = []
    for number, identifier, label, pin_type in pin_table:
        pins.append(
            {
                "id": identifier,
                "label": label,
                "pin_type": pin_type,
                "position": list(positions[number]),
            }
        )
    return pins


def generate_logic_gates() -> None:
    families = {
        "sn74hc": {
            "name": "SN74HC",
            "manufacturer": "Texas Instruments",
            "voltage": "2V to 6V",
            "temperature": "-40°C to 125°C",
            "datasheet_pattern": "https://www.ti.com/lit/ds/symlink/sn74hc{code}.pdf",
            "part_pattern": "SN74HC{code}N",
        },
        "sn74hct": {
            "name": "SN74HCT",
            "manufacturer": "Texas Instruments",
            "voltage": "4.5V to 5.5V",
            "temperature": "-40°C to 125°C",
            "datasheet_pattern": "https://www.ti.com/lit/ds/symlink/sn74hct{code}.pdf",
            "part_pattern": "SN74HCT{code}N",
        },
        "sn74ac": {
            "name": "SN74AC",
            "manufacturer": "Texas Instruments",
            "voltage": "2V to 6V",
            "temperature": "-40°C to 125°C",
            "datasheet_pattern": "https://www.ti.com/lit/ds/symlink/sn74ac{code}.pdf",
            "part_pattern": "SN74AC{code}N",
        },
        "sn74lvc": {
            "name": "SN74LVC",
            "manufacturer": "Texas Instruments",
            "voltage": "1.65V to 5.5V",
            "temperature": "-40°C to 125°C",
            "datasheet_pattern": "https://www.ti.com/lit/ds/symlink/sn74lvc{code}.pdf",
            "part_pattern": "SN74LVC{code}PW",
        },
        "mc74hc": {
            "name": "MC74HC",
            "manufacturer": "onsemi",
            "voltage": "2V to 6V",
            "temperature": "-55°C to 125°C",
            "datasheet_pattern": "https://www.onsemi.com/pdf/datasheet/mc74hc{code}.pdf",
            "part_pattern": "MC74HC{code}NG",
        },
    }

    functions = [
        ("00", "Quad 2-Input NAND Gate"),
        ("01", "Quad 2-Input NAND Gate (Open Collector)"),
        ("02", "Quad 2-Input NOR Gate"),
        ("03", "Quad 2-Input NAND Gate (Open Drain)"),
        ("04", "Hex Inverter"),
        ("05", "Hex Inverter (Open Collector)"),
        ("06", "Hex Inverter (High Voltage)"),
        ("07", "Hex Buffer (Open Drain)"),
        ("08", "Quad 2-Input AND Gate"),
        ("09", "Quad 2-Input AND Gate (Open Collector)"),
        ("10", "Triple 3-Input NAND Gate"),
        ("11", "Triple 3-Input AND Gate"),
        ("12", "Triple 3-Input NAND Gate (Open Collector)"),
        ("13", "Triple 3-Input AND Gate (Open Collector)"),
        ("14", "Hex Schmitt-Trigger Inverter"),
        ("17", "Hex Schmitt-Trigger Buffer"),
        ("20", "Dual 4-Input NAND Gate"),
        ("21", "Dual 4-Input AND Gate"),
        ("22", "Dual 4-Input NAND Gate (Open Collector)"),
        ("23", "Dual 4-Input AND Gate (Open Collector)"),
        ("24", "Dual 4-Input NOR Gate"),
        ("25", "Dual 4-Input NOR Gate (Open Collector)"),
        ("26", "Dual 4-Input OR Gate"),
        ("27", "Triple 3-Input NOR Gate"),
        ("30", "Eight-Input NAND Gate"),
        ("32", "Quad 2-Input OR Gate"),
        ("37", "Quad Buffer with Enable"),
        ("38", "Quad Buffer with Enable (Open Collector)"),
        ("86", "Quad 2-Input XOR Gate"),
    ]

    quad_layout = [
        (1, "1A", "1A", "digital"),
        (2, "1B", "1B", "digital"),
        (3, "1Y", "1Y", "digital"),
        (4, "2A", "2A", "digital"),
        (5, "2B", "2B", "digital"),
        (6, "2Y", "2Y", "digital"),
        (7, "GND", "GND", "ground"),
        (8, "3Y", "3Y", "digital"),
        (9, "3A", "3A", "digital"),
        (10, "3B", "3B", "digital"),
        (11, "4Y", "4Y", "digital"),
        (12, "4A", "4A", "digital"),
        (13, "4B", "4B", "digital"),
        (14, "VCC", "VCC", "power"),
    ]

    quad_variant_layout = [
        (1, "1Y", "1Y", "digital"),
        (2, "1A", "1A", "digital"),
        (3, "1B", "1B", "digital"),
        (4, "2Y", "2Y", "digital"),
        (5, "2A", "2A", "digital"),
        (6, "2B", "2B", "digital"),
        (7, "GND", "GND", "ground"),
        (8, "3A", "3A", "digital"),
        (9, "3B", "3B", "digital"),
        (10, "3Y", "3Y", "digital"),
        (11, "4A", "4A", "digital"),
        (12, "4B", "4B", "digital"),
        (13, "4Y", "4Y", "digital"),
        (14, "VCC", "VCC", "power"),
    ]

    triple_layout = [
        (1, "1A", "1A", "digital"),
        (2, "1B", "1B", "digital"),
        (3, "1C", "1C", "digital"),
        (4, "1Y", "1Y", "digital"),
        (5, "2A", "2A", "digital"),
        (6, "2B", "2B", "digital"),
        (7, "GND", "GND", "ground"),
        (8, "2Y", "2Y", "digital"),
        (9, "2C", "2C", "digital"),
        (10, "3A", "3A", "digital"),
        (11, "3B", "3B", "digital"),
        (12, "3C", "3C", "digital"),
        (13, "3Y", "3Y", "digital"),
        (14, "VCC", "VCC", "power"),
    ]

    hex_layout = [
        (1, "1A", "1A", "digital"),
        (2, "1Y", "1Y", "digital"),
        (3, "2A", "2A", "digital"),
        (4, "2Y", "2Y", "digital"),
        (5, "3A", "3A", "digital"),
        (6, "3Y", "3Y", "digital"),
        (7, "GND", "GND", "ground"),
        (8, "4Y", "4Y", "digital"),
        (9, "4A", "4A", "digital"),
        (10, "5Y", "5Y", "digital"),
        (11, "5A", "5A", "digital"),
        (12, "6Y", "6Y", "digital"),
        (13, "6A", "6A", "digital"),
        (14, "VCC", "VCC", "power"),
    ]

    eight_layout = [
        (1, "A", "A", "digital"),
        (2, "B", "B", "digital"),
        (3, "C", "C", "digital"),
        (4, "D", "D", "digital"),
        (5, "E", "E", "digital"),
        (6, "F", "F", "digital"),
        (7, "GND", "GND", "ground"),
        (8, "Y", "Y", "digital"),
        (9, "H", "H", "digital"),
        (10, "G", "G", "digital"),
        (11, "J", "J", "digital"),
        (12, "I", "I", "digital"),
        (13, "Z", "Z", "digital"),
        (14, "VCC", "VCC", "power"),
    ]

    layout_map = {
        "00": quad_layout,
        "01": quad_layout,
        "02": quad_variant_layout,
        "03": quad_layout,
        "04": hex_layout,
        "05": hex_layout,
        "06": hex_layout,
        "07": hex_layout,
        "08": quad_layout,
        "09": quad_layout,
        "10": triple_layout,
        "11": triple_layout,
        "12": triple_layout,
        "13": triple_layout,
        "14": hex_layout,
        "17": hex_layout,
        "20": triple_layout,
        "21": triple_layout,
        "22": triple_layout,
        "23": triple_layout,
        "24": triple_layout,
        "25": triple_layout,
        "26": triple_layout,
        "27": triple_layout,
        "30": eight_layout,
        "32": quad_layout,
        "37": quad_layout,
        "38": quad_layout,
        "86": quad_layout,
    }

    width, height, positions = package_geometry("dip14")

    for family_key, family in families.items():
        for code, label in functions:
            layout = layout_map[code]
            pins = map_pins(layout, positions)

            component = {
                "id": f"ic_logic_{family_key}_{code.lower()}",
                "name": f"{family['name']} {label}",
                "component_type": "ic",
                "description": f"Template for {label} in the {family['name']} logic family",
                "width": width,
                "height": height,
                "pins": pins,
                "metadata": {
                    "manufacturer": family["manufacturer"],
                    "part_number": family["part_pattern"].format(code=code),
                    "package": "PDIP-14",
                    "operating_limits": {
                        "supply_voltage": family["voltage"],
                        "temperature": family["temperature"],
                    },
                    "datasheet_url": family["datasheet_pattern"].format(code=code.lower()),
                    "logic_function": label,
                    "logic_family": family["name"],
                },
            }

            write_component(f"ic_logic_{family_key}_{code.lower()}.json", component)


def generate_op_amps() -> None:
    models = [
        ("model01", "Atlas 741 Precision Op Amp", "Atlas Analog"),
        ("model02", "Atlas 742 Precision Op Amp", "Atlas Analog"),
        ("model03", "Atlas 743 Precision Op Amp", "Atlas Analog"),
        ("model04", "Atlas 744 Precision Op Amp", "Atlas Analog"),
        ("model05", "Atlas 745 Precision Op Amp", "Atlas Analog"),
        ("model06", "Atlas 746 Precision Op Amp", "Atlas Analog"),
        ("model07", "Atlas 747 Precision Op Amp", "Atlas Analog"),
        ("model08", "Atlas 748 Precision Op Amp", "Atlas Analog"),
        ("model09", "Atlas 749 Precision Op Amp", "Atlas Analog"),
        ("model10", "Atlas 750 Precision Op Amp", "Atlas Analog"),
        ("model11", "Atlas 760 Dual Op Amp", "Atlas Analog"),
        ("model12", "Atlas 761 Dual Op Amp", "Atlas Analog"),
        ("model13", "Atlas 762 Dual Op Amp", "Atlas Analog"),
        ("model14", "Atlas 763 Dual Op Amp", "Atlas Analog"),
        ("model15", "Atlas 764 Dual Op Amp", "Atlas Analog"),
        ("model16", "Atlas 765 Dual Op Amp", "Atlas Analog"),
        ("model17", "Atlas 770 Quad Op Amp", "Atlas Analog"),
        ("model18", "Atlas 771 Quad Op Amp", "Atlas Analog"),
        ("model19", "Atlas 772 Quad Op Amp", "Atlas Analog"),
        ("model20", "Atlas 773 Quad Op Amp", "Atlas Analog"),
    ]

    single_pins = [
        (1, "OFFSET1", "Offset", "analog"),
        (2, "IN-", "-", "analog"),
        (3, "IN+", "+", "analog"),
        (4, "V-", "V-", "power"),
        (5, "OFFSET2", "Offset", "analog"),
        (6, "OUT", "OUT", "analog"),
        (7, "V+", "V+", "power"),
        (8, "NC", "NC", "digital"),
    ]

    dual_pins = [
        (1, "OUTA", "OUTA", "analog"),
        (2, "INA-", "A-", "analog"),
        (3, "INA+", "A+", "analog"),
        (4, "V-", "V-", "power"),
        (5, "INB+", "B+", "analog"),
        (6, "INB-", "B-", "analog"),
        (7, "OUTB", "OUTB", "analog"),
        (8, "V+", "V+", "power"),
    ]

    quad_pins = [
        (1, "OUTA", "OUTA", "analog"),
        (2, "INA-", "A-", "analog"),
        (3, "INA+", "A+", "analog"),
        (4, "VSS", "VSS", "ground"),
        (5, "INB+", "B+", "analog"),
        (6, "INB-", "B-", "analog"),
        (7, "OUTB", "OUTB", "analog"),
        (8, "OUTC", "OUTC", "analog"),
        (9, "INC-", "C-", "analog"),
        (10, "INC+", "C+", "analog"),
        (11, "VDD", "VDD", "power"),
        (12, "IND+", "D+", "analog"),
        (13, "IND-", "D-", "analog"),
        (14, "OUTD", "OUTD", "analog"),
    ]

    package_variants = {
        "single": {
            "packages": {
                "dip8": ("PDIP-8", "±5V to ±18V", "-40°C to 85°C"),
                "soic8": ("SOIC-8", "±5V to ±18V", "-40°C to 85°C"),
                "tssop8": ("TSSOP-8", "±5V to ±18V", "-40°C to 85°C"),
            },
            "pins": single_pins,
        },
        "dual": {
            "packages": {
                "dip8": ("PDIP-8", "3V to 36V", "-40°C to 125°C"),
                "soic8": ("SOIC-8", "3V to 36V", "-40°C to 125°C"),
                "tssop8": ("TSSOP-8", "3V to 36V", "-40°C to 125°C"),
            },
            "pins": dual_pins,
        },
        "quad": {
            "packages": {
                "dip14": ("PDIP-14", "3V to 36V", "-40°C to 125°C"),
                "soic14": ("SOIC-14", "3V to 36V", "-40°C to 125°C"),
                "tssop14": ("TSSOP-14", "3V to 36V", "-40°C to 125°C"),
            },
            "pins": quad_pins,
        },
    }

    channel_layout = {
        "model01": "single",
        "model02": "single",
        "model03": "single",
        "model04": "single",
        "model05": "single",
        "model06": "single",
        "model07": "single",
        "model08": "single",
        "model09": "single",
        "model10": "single",
        "model11": "dual",
        "model12": "dual",
        "model13": "dual",
        "model14": "dual",
        "model15": "dual",
        "model16": "dual",
        "model17": "quad",
        "model18": "quad",
        "model19": "quad",
        "model20": "quad",
    }

    for model_id, model_name, manufacturer in models:
        layout_key = channel_layout[model_id]
        variant = package_variants[layout_key]
        pins = variant["pins"]

        for package_key, (package_name, supply, temperature) in variant["packages"].items():
            width, height, positions = package_geometry(package_key)
            pin_defs = map_pins(pins, positions)

            metadata = {
                "manufacturer": manufacturer,
                "part_number": f"{model_name.split()[0]}-{model_id.upper()}-{package_key.upper()}",
                "package": package_name,
                "operating_limits": {
                    "supply_voltage": supply,
                    "temperature": temperature,
                },
                "datasheet_url": f"https://example.com/datasheets/{model_id}.pdf",
                "channels": {
                    "single": 1,
                    "dual": 2,
                    "quad": 4,
                }[layout_key],
            }

            component = {
                "id": f"ic_op_amp_{model_id}_{package_key}",
                "name": f"{model_name} ({package_name})",
                "component_type": "ic",
                "description": f"Template for {model_name} in {package_name}",
                "width": width,
                "height": height,
                "pins": pin_defs,
                "metadata": metadata,
            }

            write_component(f"ic_op_amp_{model_id}_{package_key}.json", component)


def generate_timers() -> None:
    timers = [
        ("timer01", "Astra 555 Classic Timer", "Nova Circuits"),
        ("timer02", "Astra 556 Dual Timer", "Nova Circuits"),
        ("timer03", "Astra 557 CMOS Timer", "Nova Circuits"),
        ("timer04", "Astra 558 Precision Timer", "Nova Circuits"),
        ("timer05", "Astra 559 Nanopower Timer", "Nova Circuits"),
        ("timer06", "Astra 560 Programmable Timer", "Nova Circuits"),
        ("timer07", "Astra 561 Oscillator", "Nova Circuits"),
    ]

    single_layout = [
        (1, "GND", "GND", "ground"),
        (2, "TRIG", "TRIG", "analog"),
        (3, "OUT", "OUT", "digital"),
        (4, "RESET", "RESET", "digital"),
        (5, "CTRL", "CTRL", "analog"),
        (6, "THRES", "TH", "analog"),
        (7, "DISCH", "DIS", "digital"),
        (8, "VCC", "VCC", "power"),
    ]

    dual_layout = [
        (1, "DIS1", "DIS1", "digital"),
        (2, "TRIG1", "TR1", "analog"),
        (3, "OUT1", "OUT1", "digital"),
        (4, "RESET1", "RST1", "digital"),
        (5, "CTRL1", "CTRL1", "analog"),
        (6, "TH1", "TH1", "analog"),
        (7, "GND", "GND", "ground"),
        (8, "TH2", "TH2", "analog"),
        (9, "CTRL2", "CTRL2", "analog"),
        (10, "RESET2", "RST2", "digital"),
        (11, "OUT2", "OUT2", "digital"),
        (12, "TRIG2", "TR2", "analog"),
        (13, "DIS2", "DIS2", "digital"),
        (14, "VCC", "VCC", "power"),
    ]

    architecture = {
        "timer01": ("single", "4.5V to 18V", "-40°C to 105°C"),
        "timer02": ("dual", "4.5V to 18V", "-40°C to 105°C"),
        "timer03": ("single", "2V to 15V", "-40°C to 125°C"),
        "timer04": ("single", "3V to 18V", "-55°C to 125°C"),
        "timer05": ("single", "1.5V to 6V", "-40°C to 85°C"),
        "timer06": ("single", "2.7V to 18V", "-40°C to 105°C"),
        "timer07": ("dual", "4.5V to 16V", "-40°C to 105°C"),
    }

    for timer_id, timer_name, manufacturer in timers:
        topology, voltage, temperature = architecture[timer_id]
        if topology == "single":
            packages = {
                "dip8": "PDIP-8",
                "soic8": "SOIC-8",
                "tssop8": "TSSOP-8",
            }
            pinset = single_layout
        else:
            packages = {
                "dip14": "PDIP-14",
                "soic14": "SOIC-14",
                "tssop14": "TSSOP-14",
            }
            pinset = dual_layout

        for package_key, package_name in packages.items():
            width, height, positions = package_geometry(package_key)
            pins = map_pins(pinset, positions)

            metadata = {
                "manufacturer": manufacturer,
                "part_number": f"{timer_name.split()[0]}-{timer_id.upper()}-{package_key.upper()}",
                "package": package_name,
                "operating_limits": {
                    "supply_voltage": voltage,
                    "temperature": temperature,
                },
                "datasheet_url": f"https://example.com/datasheets/{timer_id}.pdf",
                "channels": 2 if topology == "dual" else 1,
            }

            component = {
                "id": f"ic_timer_{timer_id}_{package_key}",
                "name": f"{timer_name} ({package_name})",
                "component_type": "ic",
                "description": f"Template for {timer_name} packaged as {package_name}",
                "width": width,
                "height": height,
                "pins": pins,
                "metadata": metadata,
            }

            write_component(f"ic_timer_{timer_id}_{package_key}.json", component)


def build_pin_table(labels: Sequence[Tuple[str, str]]) -> List[Tuple[int, str, str, str]]:
    return [(index + 1, label.replace("/", "_"), label, pin_type) for index, (label, pin_type) in enumerate(labels)]


def generate_microcontrollers() -> None:
    microcontrollers = [
        {
            "id": "mcu01",
            "name": "Orion Tiny8 MCU",
            "manufacturer": "Celestial Microsystems",
            "voltage": "1.8V to 5.5V",
            "temperature": "-40°C to 125°C",
            "datasheet": "https://example.com/mcus/mcu01.pdf",
            "pins": build_pin_table(
                [
                    ("PB5/RESET", "digital"),
                    ("PB3", "digital"),
                    ("PB4", "digital"),
                    ("GND", "ground"),
                    ("PB0/MOSI", "digital"),
                    ("PB1/MISO", "digital"),
                    ("PB2/SCK", "digital"),
                    ("VCC", "power"),
                ]
            ),
            "packages": [
                ("dip8", "PDIP-8"),
                ("soic8", "SOIC-8"),
                ("tssop8", "TSSOP-8"),
            ],
        },
        {
            "id": "mcu02",
            "name": "Orion Tiny14 MCU",
            "manufacturer": "Celestial Microsystems",
            "voltage": "1.8V to 5.5V",
            "temperature": "-40°C to 125°C",
            "datasheet": "https://example.com/mcus/mcu02.pdf",
            "pins": build_pin_table(
                [
                    ("PA0/ADC0", "analog"),
                    ("PA1/ADC1", "analog"),
                    ("PA2/ADC2", "analog"),
                    ("PA3/ADC3", "analog"),
                    ("PA4/SCK", "digital"),
                    ("PA5/MISO", "digital"),
                    ("GND", "ground"),
                    ("VCC", "power"),
                    ("PB0/MOSI", "digital"),
                    ("PB1/OC0A", "digital"),
                    ("PB2/OC0B", "digital"),
                    ("PB3/RESET", "digital"),
                    ("PB4/XTAL1", "digital"),
                    ("PB5/XTAL2", "digital"),
                ]
            ),
            "packages": [
                ("dip14", "PDIP-14"),
                ("soic14", "SOIC-14"),
                ("tssop14", "TSSOP-14"),
            ],
        },
        {
            "id": "mcu03",
            "name": "Orion Tiny16 MCU",
            "manufacturer": "Celestial Microsystems",
            "voltage": "1.8V to 5.5V",
            "temperature": "-40°C to 125°C",
            "datasheet": "https://example.com/mcus/mcu03.pdf",
            "pins": build_pin_table(
                [
                    ("PA0", "digital"),
                    ("PA1", "digital"),
                    ("PA2", "digital"),
                    ("PA3", "digital"),
                    ("PA4", "digital"),
                    ("PA5", "digital"),
                    ("PA6", "digital"),
                    ("PA7", "digital"),
                    ("PB0", "digital"),
                    ("PB1", "digital"),
                    ("PB2", "digital"),
                    ("PB3", "digital"),
                    ("GND", "ground"),
                    ("VCC", "power"),
                    ("RESET", "digital"),
                    ("XTAL", "digital"),
                ]
            ),
            "packages": [
                ("dip16", "PDIP-16"),
                ("soic16", "SOIC-16"),
                ("tssop16", "TSSOP-16"),
            ],
        },
        {
            "id": "mcu04",
            "name": "Orion Control20 MCU",
            "manufacturer": "Celestial Microsystems",
            "voltage": "2.0V to 5.5V",
            "temperature": "-40°C to 105°C",
            "datasheet": "https://example.com/mcus/mcu04.pdf",
            "pins": build_pin_table(
                [
                    ("PA0", "digital"),
                    ("PA1", "digital"),
                    ("PA2", "digital"),
                    ("PA3", "digital"),
                    ("PA4", "digital"),
                    ("PA5", "digital"),
                    ("PA6", "digital"),
                    ("PA7", "digital"),
                    ("PB0", "digital"),
                    ("PB1", "digital"),
                    ("PB2", "digital"),
                    ("PB3", "digital"),
                    ("PB4", "digital"),
                    ("PB5", "digital"),
                    ("GND", "ground"),
                    ("VCC", "power"),
                    ("PC0", "digital"),
                    ("PC1", "digital"),
                    ("PC2", "digital"),
                    ("PC3", "digital"),
                ]
            ),
            "packages": [
                ("dip20", "PDIP-20"),
                ("soic20", "SOIC-20"),
                ("tssop20", "TSSOP-20"),
            ],
        },
        {
            "id": "mcu05",
            "name": "Orion Control20X MCU",
            "manufacturer": "Celestial Microsystems",
            "voltage": "2.0V to 5.5V",
            "temperature": "-40°C to 105°C",
            "datasheet": "https://example.com/mcus/mcu05.pdf",
            "pins": build_pin_table(
                [
                    ("PA0", "digital"),
                    ("PA1", "digital"),
                    ("PA2", "digital"),
                    ("PA3", "digital"),
                    ("PA4", "digital"),
                    ("PA5", "digital"),
                    ("PA6", "digital"),
                    ("PA7", "digital"),
                    ("PB0", "digital"),
                    ("PB1", "digital"),
                    ("PB2", "digital"),
                    ("PB3", "digital"),
                    ("PB4", "digital"),
                    ("PB5", "digital"),
                    ("GND", "ground"),
                    ("VCC", "power"),
                    ("PC0", "digital"),
                    ("PC1", "digital"),
                    ("PC2", "digital"),
                    ("PC3", "digital"),
                ]
            ),
            "packages": [
                ("dip20", "PDIP-20"),
                ("qfn20", "QFN-20"),
                ("tssop20", "TSSOP-20"),
            ],
        },
        {
            "id": "mcu06",
            "name": "Orion Gateway28 MCU",
            "manufacturer": "Celestial Microsystems",
            "voltage": "2.7V to 5.5V",
            "temperature": "-40°C to 105°C",
            "datasheet": "https://example.com/mcus/mcu06.pdf",
            "pins": build_pin_table(
                [
                    ("PA0", "digital"),
                    ("PA1", "digital"),
                    ("PA2", "digital"),
                    ("PA3", "digital"),
                    ("PA4", "digital"),
                    ("PA5", "digital"),
                    ("PA6", "digital"),
                    ("PA7", "digital"),
                    ("PB0", "digital"),
                    ("PB1", "digital"),
                    ("PB2", "digital"),
                    ("PB3", "digital"),
                    ("PB4", "digital"),
                    ("PB5", "digital"),
                    ("PB6", "digital"),
                    ("PB7", "digital"),
                    ("PC0", "digital"),
                    ("PC1", "digital"),
                    ("PC2", "digital"),
                    ("PC3", "digital"),
                    ("PC4", "digital"),
                    ("GND", "ground"),
                    ("VCC", "power"),
                    ("AVCC", "power"),
                    ("AREF", "analog"),
                    ("RESET", "digital"),
                    ("XTAL1", "digital"),
                    ("XTAL2", "digital"),
                ]
            ),
            "packages": [
                ("dip28", "PDIP-28"),
                ("soic28", "SOIC-28"),
                ("tssop28", "TSSOP-28"),
            ],
        },
        {
            "id": "mcu07",
            "name": "Orion Gateway28X MCU",
            "manufacturer": "Celestial Microsystems",
            "voltage": "2.7V to 5.5V",
            "temperature": "-40°C to 105°C",
            "datasheet": "https://example.com/mcus/mcu07.pdf",
            "pins": build_pin_table(
                [
                    ("PA0", "digital"),
                    ("PA1", "digital"),
                    ("PA2", "digital"),
                    ("PA3", "digital"),
                    ("PA4", "digital"),
                    ("PA5", "digital"),
                    ("PA6", "digital"),
                    ("PA7", "digital"),
                    ("PB0", "digital"),
                    ("PB1", "digital"),
                    ("PB2", "digital"),
                    ("PB3", "digital"),
                    ("PB4", "digital"),
                    ("PB5", "digital"),
                    ("PB6", "digital"),
                    ("PB7", "digital"),
                    ("PC0", "digital"),
                    ("PC1", "digital"),
                    ("PC2", "digital"),
                    ("PC3", "digital"),
                    ("PC4", "digital"),
                    ("PC5", "digital"),
                    ("PC6", "digital"),
                    ("PC7", "digital"),
                    ("GND", "ground"),
                    ("VCC", "power"),
                    ("AVCC", "power"),
                    ("AREF", "analog"),
                    ("PD0", "digital"),
                    ("PD1", "digital"),
                    ("PD2", "digital"),
                    ("PD3", "digital"),
                ]
            ),
            "packages": [
                ("dip32", "PDIP-32"),
                ("tqfp32", "TQFP-32"),
                ("qfn32", "QFN-32"),
            ],
        },
        {
            "id": "mcu08",
            "name": "Orion Vector32 MCU",
            "manufacturer": "Celestial Microsystems",
            "voltage": "1.8V to 3.6V",
            "temperature": "-40°C to 105°C",
            "datasheet": "https://example.com/mcus/mcu08.pdf",
            "pins": build_pin_table(
                [
                    ("PA0", "digital"),
                    ("PA1", "digital"),
                    ("PA2", "digital"),
                    ("PA3", "digital"),
                    ("PA4", "digital"),
                    ("PA5", "digital"),
                    ("PA6", "digital"),
                    ("PA7", "digital"),
                    ("PB0", "digital"),
                    ("PB1", "digital"),
                    ("PB2", "digital"),
                    ("PB3", "digital"),
                    ("PB4", "digital"),
                    ("PB5", "digital"),
                    ("PB6", "digital"),
                    ("PB7", "digital"),
                    ("PC0", "digital"),
                    ("PC1", "digital"),
                    ("PC2", "digital"),
                    ("PC3", "digital"),
                    ("PC4", "digital"),
                    ("PC5", "digital"),
                    ("PC6", "digital"),
                    ("PC7", "digital"),
                    ("GND", "ground"),
                    ("VCC", "power"),
                    ("VBAT", "power"),
                    ("RESET", "digital"),
                    ("SWDIO", "digital"),
                    ("SWCLK", "digital"),
                    ("PA8", "digital"),
                    ("PA9", "digital"),
                ]
            ),
            "packages": [
                ("dip32", "PDIP-32"),
                ("tqfp32", "TQFP-32"),
                ("qfn32", "QFN-32"),
            ],
        },
        {
            "id": "mcu09",
            "name": "Orion Vector32X MCU",
            "manufacturer": "Celestial Microsystems",
            "voltage": "1.8V to 3.6V",
            "temperature": "-40°C to 105°C",
            "datasheet": "https://example.com/mcus/mcu09.pdf",
            "pins": build_pin_table(
                [
                    ("PA0", "digital"),
                    ("PA1", "digital"),
                    ("PA2", "digital"),
                    ("PA3", "digital"),
                    ("PA4", "digital"),
                    ("PA5", "digital"),
                    ("PA6", "digital"),
                    ("PA7", "digital"),
                    ("PB0", "digital"),
                    ("PB1", "digital"),
                    ("PB2", "digital"),
                    ("PB3", "digital"),
                    ("PB4", "digital"),
                    ("PB5", "digital"),
                    ("PB6", "digital"),
                    ("PB7", "digital"),
                    ("PC0", "digital"),
                    ("PC1", "digital"),
                    ("PC2", "digital"),
                    ("PC3", "digital"),
                    ("PC4", "digital"),
                    ("PC5", "digital"),
                    ("PC6", "digital"),
                    ("PC7", "digital"),
                    ("GND", "ground"),
                    ("VCC", "power"),
                    ("VBUS", "power"),
                    ("RESET", "digital"),
                    ("USB_DM", "digital"),
                    ("USB_DP", "digital"),
                    ("PA8", "digital"),
                    ("PA9", "digital"),
                ]
            ),
            "packages": [
                ("dip32", "PDIP-32"),
                ("tqfp32", "TQFP-32"),
                ("qfn32", "QFN-32"),
            ],
        },
        {
            "id": "mcu10",
            "name": "Orion Fusion32 MCU",
            "manufacturer": "Celestial Microsystems",
            "voltage": "1.8V to 3.6V",
            "temperature": "-40°C to 125°C",
            "datasheet": "https://example.com/mcus/mcu10.pdf",
            "pins": build_pin_table(
                [
                    ("PA0", "digital"),
                    ("PA1", "digital"),
                    ("PA2", "digital"),
                    ("PA3", "digital"),
                    ("PA4", "digital"),
                    ("PA5", "digital"),
                    ("PA6", "digital"),
                    ("PA7", "digital"),
                    ("PB0", "digital"),
                    ("PB1", "digital"),
                    ("PB2", "digital"),
                    ("PB3", "digital"),
                    ("PB4", "digital"),
                    ("PB5", "digital"),
                    ("PB6", "digital"),
                    ("PB7", "digital"),
                    ("PC0", "digital"),
                    ("PC1", "digital"),
                    ("PC2", "digital"),
                    ("PC3", "digital"),
                    ("PC4", "digital"),
                    ("PC5", "digital"),
                    ("PC6", "digital"),
                    ("PC7", "digital"),
                    ("GND", "ground"),
                    ("VCC", "power"),
                    ("VBAT", "power"),
                    ("RESET", "digital"),
                    ("SWDIO", "digital"),
                    ("SWCLK", "digital"),
                    ("PA8", "digital"),
                    ("PA9", "digital"),
                ]
            ),
            "packages": [
                ("dip32", "PDIP-32"),
                ("tqfp32", "TQFP-32"),
                ("qfn32", "QFN-32"),
            ],
        },
        {
            "id": "mcu11",
            "name": "Orion Fusion32X MCU",
            "manufacturer": "Celestial Microsystems",
            "voltage": "1.8V to 3.6V",
            "temperature": "-40°C to 125°C",
            "datasheet": "https://example.com/mcus/mcu11.pdf",
            "pins": build_pin_table(
                [
                    ("PA0", "digital"),
                    ("PA1", "digital"),
                    ("PA2", "digital"),
                    ("PA3", "digital"),
                    ("PA4", "digital"),
                    ("PA5", "digital"),
                    ("PA6", "digital"),
                    ("PA7", "digital"),
                    ("PB0", "digital"),
                    ("PB1", "digital"),
                    ("PB2", "digital"),
                    ("PB3", "digital"),
                    ("PB4", "digital"),
                    ("PB5", "digital"),
                    ("PB6", "digital"),
                    ("PB7", "digital"),
                    ("PC0", "digital"),
                    ("PC1", "digital"),
                    ("PC2", "digital"),
                    ("PC3", "digital"),
                    ("PC4", "digital"),
                    ("PC5", "digital"),
                    ("PC6", "digital"),
                    ("PC7", "digital"),
                    ("GND", "ground"),
                    ("VCC", "power"),
                    ("VIO", "power"),
                    ("RESET", "digital"),
                    ("SWDIO", "digital"),
                    ("SWCLK", "digital"),
                    ("PA8", "digital"),
                    ("PA9", "digital"),
                ]
            ),
            "packages": [
                ("dip32", "PDIP-32"),
                ("tqfp32", "TQFP-32"),
                ("qfn32", "QFN-32"),
            ],
        },
    ]

    for mcu in microcontrollers:
        for package_key, package_name in mcu["packages"]:
            width, height, positions = package_geometry(package_key)
            pins = map_pins(mcu["pins"], positions)

            metadata = {
                "manufacturer": mcu["manufacturer"],
                "part_number": f"{mcu['name'].split()[0]}-{mcu['id'].upper()}-{package_key.upper()}",
                "package": package_name,
                "operating_limits": {
                    "supply_voltage": mcu["voltage"],
                    "temperature": mcu["temperature"],
                },
                "datasheet_url": mcu["datasheet"],
                "flash_size_kb": 64,
            }

            component = {
                "id": f"ic_mcu_{mcu['id']}_{package_key}",
                "name": f"{mcu['name']} ({package_name})",
                "component_type": "ic",
                "description": f"Template for {mcu['name']} with {package_name} footprint",
                "width": width,
                "height": height,
                "pins": pins,
                "metadata": metadata,
            }

            write_component(f"ic_mcu_{mcu['id']}_{package_key}.json", component)


def main() -> None:
    generate_logic_gates()
    generate_op_amps()
    generate_timers()
    generate_microcontrollers()


if __name__ == "__main__":
    main()

