# Breadboard Variant Matrix

This directory defines solderless breadboard components that combine four physical size tiers, six enclosure colors, and two material quality grades. Every combination is available as an individual JSON definition so the circuit designer can surface precise options while reusing common metadata.

## Size tiers and mechanical metadata

| Size tier | Component prefix | Tie points | Power rails | Rail configuration | Approx. dimensions (mm) | Canvas size (px) | Mounting options |
|-----------|-----------------|------------|-------------|--------------------|-------------------------|------------------|------------------|
| Mini | `breadboard_mini_*` | 170 | 0 | Terminal strips only (no dedicated power rails) | 45.5 × 35.0 × 9.0 | 180 × 90 | Adhesive foam backing; modular dovetail alignment slots |
| Half-Size | `breadboard_half_*` | 400 | 2 | Dual power rails on one side | 82.5 × 54.0 × 9.0 | 300 × 120 | Adhesive foam backing; M2 mounting holes via adapter plate |
| Full-Size | `breadboard_full_*` | 830 | 4 | Dual power rails on both sides | 165.0 × 55.0 × 10.0 | 460 × 160 | Adhesive foam backing; countersunk M3 holes; snap-fit alignment keys |
| Large Project | `breadboard_large_*` | 1660 | 4 | Quad length with dual rails on both sides | 220.0 × 70.0 × 10.5 | 620 × 200 | Adhesive foam backing; countersunk M3 holes; DIN rail clip adapters |

All JSON files expose this information through the `metadata.tie_point_layout`, `metadata.power_rails`, `metadata.rail_configuration`, and `metadata.dimensions_mm` fields so downstream tooling can reason about tie-point counts, rail usage, and physical footprints without additional lookups.

## Color palette

All sizes are available in the following body colors:

- White (`white`, hex `#F8F9FA`)
- Black (`black`, hex `#1F1F1F`)
- Blue (`blue`, hex `#2D7DD2`)
- Green (`green`, hex `#2B9348`)
- Red (`red`, hex `#D62828`)
- Clear (`clear`, hex `#EAEAEA`)

Each component stores the human-readable color as well as the associated hex value in `metadata.color` and `metadata.color_hex`.

## Quality grades

Two quality levels differentiate contact plating, electrical ratings, and certification coverage:

- **Standard** — ABS enclosure with nickel-plated phosphor bronze contacts, rated for 300 V AC / 2 A per contact. Suitable for educational and general-purpose prototyping. (`quality`: `Standard`)
- **Premium** — High-impact ABS enclosure with gold-plated contacts, rated for 500 V AC / 3 A per contact. Provides improved contact resistance, higher insulation resistance, and extended temperature support. (`quality`: `Premium`)

Electrical information is captured through `metadata.material_quality`, `metadata.electrical_ratings`, `metadata.contact_resistance`, `metadata.insulation_resistance`, and `metadata.operating_temperature`.

## Generated combinations

Each variant follows the naming pattern `breadboard_<size>_<color>_<quality>.json`. The table below enumerates all 48 generated IDs so that editors and tests can reference them explicitly.

| Size tier | Color | Standard ID | Premium ID |
|-----------|-------|-------------|------------|
| Mini | White | `breadboard_mini_white_standard` | `breadboard_mini_white_premium` |
| Mini | Black | `breadboard_mini_black_standard` | `breadboard_mini_black_premium` |
| Mini | Blue | `breadboard_mini_blue_standard` | `breadboard_mini_blue_premium` |
| Mini | Green | `breadboard_mini_green_standard` | `breadboard_mini_green_premium` |
| Mini | Red | `breadboard_mini_red_standard` | `breadboard_mini_red_premium` |
| Mini | Clear | `breadboard_mini_clear_standard` | `breadboard_mini_clear_premium` |
| Half-Size | White | `breadboard_half_white_standard` | `breadboard_half_white_premium` |
| Half-Size | Black | `breadboard_half_black_standard` | `breadboard_half_black_premium` |
| Half-Size | Blue | `breadboard_half_blue_standard` | `breadboard_half_blue_premium` |
| Half-Size | Green | `breadboard_half_green_standard` | `breadboard_half_green_premium` |
| Half-Size | Red | `breadboard_half_red_standard` | `breadboard_half_red_premium` |
| Half-Size | Clear | `breadboard_half_clear_standard` | `breadboard_half_clear_premium` |
| Full-Size | White | `breadboard_full_white_standard` | `breadboard_full_white_premium` |
| Full-Size | Black | `breadboard_full_black_standard` | `breadboard_full_black_premium` |
| Full-Size | Blue | `breadboard_full_blue_standard` | `breadboard_full_blue_premium` |
| Full-Size | Green | `breadboard_full_green_standard` | `breadboard_full_green_premium` |
| Full-Size | Red | `breadboard_full_red_standard` | `breadboard_full_red_premium` |
| Full-Size | Clear | `breadboard_full_clear_standard` | `breadboard_full_clear_premium` |
| Large Project | White | `breadboard_large_white_standard` | `breadboard_large_white_premium` |
| Large Project | Black | `breadboard_large_black_standard` | `breadboard_large_black_premium` |
| Large Project | Blue | `breadboard_large_blue_standard` | `breadboard_large_blue_premium` |
| Large Project | Green | `breadboard_large_green_standard` | `breadboard_large_green_premium` |
| Large Project | Red | `breadboard_large_red_standard` | `breadboard_large_red_premium` |
| Large Project | Clear | `breadboard_large_clear_standard` | `breadboard_large_clear_premium` |

The consistent structure allows automated tooling (such as `count_components.py`) and human reviewers to validate availability across every size tier, color, and quality grade.
