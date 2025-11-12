# Motor Component Data Tables

This document enumerates the parameter tables used to generate the DC motor, servo motor, and stepper motor component definitions in the component library.

## DC Motor Parameters (6 × 6 × 3)

### Supply Voltages
| ID   | Nominal Voltage | No-Load Current | Rated Current | Stall Current |
|------|-----------------|-----------------|---------------|---------------|
| 3v   | 3 V             | 0.08 A          | 0.25 A        | 0.60 A        |
| 5v   | 5 V             | 0.09 A          | 0.30 A        | 0.90 A        |
| 6v   | 6 V             | 0.10 A          | 0.35 A        | 1.10 A        |
| 9v   | 9 V             | 0.12 A          | 0.45 A        | 1.60 A        |
| 12v  | 12 V            | 0.14 A          | 0.60 A        | 2.40 A        |
| 24v  | 24 V            | 0.18 A          | 0.85 A        | 3.20 A        |

### Nominal Speeds
| ID      | Nominal RPM | Use Case                                |
|---------|-------------|-----------------------------------------|
| 60rpm   | 60 RPM      | High torque gearmotor for robotics      |
| 120rpm  | 120 RPM     | Precision drive for pan-tilt systems    |
| 300rpm  | 300 RPM     | General purpose robotics gearmotor      |
| 600rpm  | 600 RPM     | Conveyor and drive wheel applications   |
| 1200rpm | 1,200 RPM   | Lightweight drive platforms             |
| 2400rpm | 2,400 RPM   | High speed fans and blowers             |

### Torque Classes
| ID     | Rated Torque    | Current Factor | Mechanical Envelope                                      |
|--------|-----------------|----------------|-----------------------------------------------------------|
| light  | 0.25 kg·cm      | 0.8×           | Ø24 mm can, 30 mm length, 2 mm D-shaft                   |
| medium | 1.20 kg·cm      | 1.0×           | Ø27 mm can, 35 mm length, 3 mm D-shaft                   |
| heavy  | 2.80 kg·cm      | 1.4×           | Ø37 mm can, 50 mm length, 4 mm keyed shaft               |

## Servo Motor Parameters (6 × 5)

### Servo Models
| ID     | Name                     | Form Factor  | Dimensions (mm) | Voltage Range | Nominal Speed |
|--------|--------------------------|--------------|-----------------|---------------|---------------|
| sg90   | SG90 Micro Servo         | Micro        | 22.8 × 12.2 × 28.5 | 4.8–6.0 V   | 0.12 s/60° @ 4.8 V |
| mg90s  | MG90S Metal Gear Micro   | Micro        | 22.5 × 12.0 × 28.5 | 4.8–6.0 V   | 0.10 s/60° @ 6.0 V |
| mg996r | MG996R High-Torque Servo | Standard     | 40.7 × 19.7 × 42.9 | 4.8–7.2 V   | 0.14 s/60° @ 6.0 V |
| ds3218 | DS3218 Digital Servo     | Large Torque | 40.5 × 20.0 × 40.5 | 4.8–6.8 V   | 0.16 s/60° @ 6.8 V |
| hs422  | HS-422 Analog Servo      | Standard     | 40.6 × 19.8 × 36.6 | 4.8–6.0 V   | 0.21 s/60° @ 6.0 V |
| fs5106r| FS5106R Continuous Servo | Continuous   | 40.8 × 20.1 × 39.5 | 4.8–6.0 V   | 0.12 s/60° @ 6.0 V |

### Torque Ratings
| ID       | Torque Output | Stall Current | Notes                              |
|----------|---------------|---------------|------------------------------------|
| 2kg_cm   | 2.0 kg·cm     | 0.65 A        | Entry-level duty for micro servos  |
| 3kg_cm   | 3.0 kg·cm     | 0.80 A        | Medium torque for lightweight linkages |
| 5kg_cm   | 5.0 kg·cm     | 1.20 A        | Standard robotics articulation     |
| 8kg_cm   | 8.0 kg·cm     | 1.80 A        | Metal gear drivetrain upgrade      |
| 12kg_cm  | 12.0 kg·cm    | 2.50 A        | High-torque or large control surfaces |

## Stepper Motor Parameters (3 × 4 × 3)

### Stepper Families
| ID     | Name                   | Frame Size | Body Length | Holding Torque | Shaft Style |
|--------|------------------------|------------|-------------|----------------|-------------|
| nema11 | NEMA 11 Bipolar        | 28 mm      | 28 mm       | 0.18 N·m       | 5 mm round  |
| nema17 | NEMA 17 Bipolar        | 42 mm      | 40 mm       | 0.45 N·m       | 5 mm round  |
| nema23 | NEMA 23 Bipolar        | 57 mm      | 56 mm       | 1.25 N·m       | 6.35 mm round |

### Step Counts per Revolution
| ID    | Steps/Rev | Step Angle |
|-------|-----------|------------|
| 200   | 200       | 1.8°       |
| 400   | 400       | 0.9°       |
| 1000  | 1,000     | 0.36°      |
| 2000  | 2,000     | 0.18°      |

### Operating Voltages
| ID  | Nominal Voltage | Current/Phase |
|-----|-----------------|---------------|
| 5v  | 5 V             | 0.70 A        |
| 12v | 12 V            | 1.20 A        |
| 24v | 24 V            | 1.80 A        |

Each table combines to produce the 108 brushed DC motor, 30 servo motor, and 36 stepper motor component definitions that populate the component library.
