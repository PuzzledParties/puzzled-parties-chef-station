# Chef Station Simon Lane-Routed Wiring Checklist

This revision uses editable Fritzing wire segments routed into separated lanes. Long runs are horizontal/vertical, and parallel wires do not share the same line segment. Each button channel now has a visible local GND bus: MOSFET source, switch ground, and pulldown ground branch into that bus, then a single trunk runs to the common GND rail.

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
- Connect ESP32 GND to the common GND rail.
- Configure each button input as INPUT_PULLUP: unpressed = HIGH, pressed = LOW.
- Do not connect the LED/lamp negatives together if individual flashing is required.

## Layout Validation

- Fritzing export validation passed.
- Wire audit found 204 editable wire segments.
- Wire audit found 0 diagonal segments.
- Wire audit found 0 zero-length wire segments.
- Wire audit found 0 exact duplicate/overlapping wire segments.
- Separate lanes are used for LED +, LED -, switch signal, switch ground, gate drive, pulldown ground, and MOSFET source ground.
- Ground routing is bus-oriented: each channel uses short local branches plus one trunk to the common GND rail, avoiding split/rejoin ground paths.

## Part Notes

- ESP32: downloaded DOIT ESP32 DevKit V1 Fritzing part.
- Resistors: value-specific Fritzing 1k and 10k resistor artwork, plus visible labels.
- MOSFET: stock Fritzing TO-220 N-channel MOSFET artwork, titled as IRFB11N50APBF.
- Arcade buttons: stock Fritzing arcade button visuals plus labeled 4-position terminal blocks showing LED +, LED -, SW SIG, and SW GND.
- Ground buses: custom annotation/rail helper parts used to make the shared ground topology visually explicit while remaining editable in Fritzing.
