"""Utilities for generating example sketch templates."""

from textwrap import dedent


def build_missing_example_template(example_name: str, board_name: str) -> str:
    """Return a minimal sketch to use when an example is unavailable."""

    documentation_url = "https://docs.arduino.cc/built-in-examples/"
    native_usb_boards = {
        "Arduino Leonardo",
        "Arduino Due",
    }

    safe_board_name = board_name or "Unknown board"

    header = dedent(
        f"""/*
  Missing Example: {example_name}

  The {example_name} sketch is not bundled with this preview of the IDE.
  You can browse the official documentation for guidance:
  {documentation_url}

  Selected board: {safe_board_name}
*/\n\n"""
    )

    setup_lines = [
        "void setup() {",
        "  Serial.begin(9600);",
    ]

    if safe_board_name in native_usb_boards:
        setup_lines.extend(
            [
                "  while (!Serial) {",
                f"    ; // Wait for the USB serial connection on {safe_board_name}",
                "  }",
            ]
        )
    else:
        setup_lines.append(
            "  // Open the Serial Monitor at 9600 baud if your board provides one."
        )

    setup_lines.append(
        "  Serial.println(\"Placeholder setup complete. Replace with example logic.\");"
    )
    setup_lines.append("}")

    loop_section = dedent(
        """

void loop() {
  // Replace this block with the behaviour from the original example.
  Serial.println("Loop placeholder - update with example code.");
  delay(1000);
}
"""
    )

    return header + "\n".join(setup_lines) + loop_section
