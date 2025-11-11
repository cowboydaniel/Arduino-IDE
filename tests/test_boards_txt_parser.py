"""Tests for the boards.txt parser."""

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arduino_ide.services.boards_txt_parser import BoardsTxtParser


def test_parse_boards_txt_extracts_pin_counts(tmp_path):
    """The parser should enrich board specs with data from the variant."""

    platform_root = tmp_path / "avr-1.8.6"
    platform_root.mkdir()

    boards_txt = platform_root / "boards.txt"
    boards_txt.write_text(
        textwrap.dedent(
            """
            uno.name=Arduino Uno
            uno.build.mcu=atmega328p
            uno.build.f_cpu=16000000L
            uno.upload.maximum_size=32256
            uno.upload.maximum_data_size=2048
            uno.build.variant=standard
            """
        ).strip()
    )

    variant_dir = platform_root / "variants" / "standard"
    variant_dir.mkdir(parents=True)
    (variant_dir / "pins_arduino.h").write_text(
        textwrap.dedent(
            """
            #define NUM_DIGITAL_PINS            20
            #define NUM_ANALOG_INPUTS           6
            #define digitalPinHasPWM(p)         ((p) == 3 || (p) == 5 || (p) == 6 || (p) == 9 || (p) == 10 || (p) == 11)
            """
        ).strip()
    )

    boards = BoardsTxtParser.parse_boards_txt(
        boards_txt, package_name="arduino", architecture="avr", platform_root=platform_root
    )

    assert len(boards) == 1
    board = boards[0]

    assert board.specs.cpu == "ATMEGA328P"
    assert board.specs.clock == "16MHz"
    assert board.specs.flash == "31KB"
    assert board.specs.ram == "2KB"

    assert board.specs.digital_pins == 20
    assert board.specs.analog_pins == 6
    assert board.specs.pwm_pins == 6
