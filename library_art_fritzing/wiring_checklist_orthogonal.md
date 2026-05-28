# Chef Station Simon Orthogonal Wiring Checklist

This revision uses editable Fritzing wire segments routed as horizontal/vertical paths. Long diagonal wires have been replaced with routed segments joined by small editable waypoint nodes.

## Pin Map

| Button | Switch input | Lamp gate output |
| --- | --- | --- |
| BTN1 / Ingredient 1 | GPIO 16 | GPIO 21 |
| BTN2 / Ingredient 2 | GPIO 17 | GPIO 22 |
| BTN3 / Ingredient 3 | GPIO 18 | GPIO 23 |
| BTN4 / Ingredient 4 | GPIO 19 | GPIO 25 |
| BTN5 / Ingredient 5 | GPIO 26 | GPIO 27 |

## Wiring

- Use the linked uxcell 12V LED illuminated arcade buttons with a 12V lamp/LED rail.
- Tie ESP32 GND, external 12V supply negative, switch ground terminals, MOSFET sources, and pulldown grounds to common ground.
- Feed each arcade button LED + from the shared +12V lamp rail.
- Run each arcade button LED - separately to its own MOSFET drain.
- Connect each MOSFET source to common ground.
- Connect each ESP32 lamp GPIO to its MOSFET gate through a 1k resistor.
- Add a 10k resistor from each MOSFET gate to common ground.
- Wire each button switch with one terminal to GND and the other terminal to its ESP32 input GPIO.
- Configure each button input as INPUT_PULLUP: unpressed = HIGH, pressed = LOW.
- Do not connect the LED/lamp negatives together if individual flashing is required.

## Layout Notes

- Wires are split into editable straight Fritzing segments with waypoint nodes.
- Long wire runs are horizontal/vertical; package audit found zero diagonal wire segments.
- Value-specific Fritzing resistor artwork is used for 1k and 10k resistors, with visible value labels.
- ESP32 uses the downloaded DOIT ESP32 DevKit V1 Fritzing part.
- MOSFETs use stock Fritzing TO-220 N-channel MOSFET artwork, titled as IRFB11N50APBF.
- Arcade button visuals use stock Fritzing arcade button artwork plus labeled 4-position terminal blocks for LED +, LED -, SW SIG, and SW GND.
