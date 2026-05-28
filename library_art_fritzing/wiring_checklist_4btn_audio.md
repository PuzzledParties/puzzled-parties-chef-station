# Chef Station Simon 4-Button + Audio Wiring Checklist

This revision uses four illuminated arcade buttons, individual MOSFET low-side lamp control, and a PAM8403 5V mini amplifier driving one 4 ohm / 3W speaker.

## Pin Map

| Function | ESP32 pin |
| --- | --- |
| BTN1 / Ingredient 1 switch input | GPIO 16 |
| BTN2 / Ingredient 2 switch input | GPIO 17 |
| BTN3 / Ingredient 3 switch input | GPIO 18 |
| BTN4 / Ingredient 4 switch input | GPIO 19 |
| BTN1 lamp gate | GPIO 21 |
| BTN2 lamp gate | GPIO 22 |
| BTN3 lamp gate | GPIO 23 |
| BTN4 lamp gate | GPIO 25 |
| Audio signal to PAM8403 L IN | GPIO 26 DAC/PWM |

## Button And Lamp Wiring

- Configure each button input as `INPUT_PULLUP`: unpressed = HIGH, pressed = LOW.
- Wire each switch with one terminal to common GND and the other terminal to its ESP32 GPIO input.
- Feed each button LED + from the shared lamp supply rail.
- Run each button LED - separately to its own MOSFET drain.
- Connect each MOSFET source to local GND, then to the common GND rail.
- Connect each ESP32 lamp GPIO to its MOSFET gate through a 1k resistor.
- Add a 10k pulldown from each MOSFET gate to GND.
- Do not connect LED/lamp negatives together if individual flashing is required.

## Audio Wiring

- Power the PAM8403 from the +5V amp rail only.
- Connect PAM8403 power GND and input GND to the common GND rail.
- Connect ESP32 GPIO26 DAC/PWM audio output to PAM8403 `L IN`.
- Connect the 4 ohm / 3W speaker across PAM8403 `L+` and `L-`.
- Leave the right channel unused unless adding a second speaker.
- Do not connect either PAM8403 speaker output lead to GND; PAM8403 speaker outputs are bridge-tied outputs.

## Layout Validation

- Fritzing export validation passed.
- Wire audit found 188 editable wire segments.
- Wire audit found 0 diagonal segments.
- Wire audit found 0 zero-length wire segments.
- Wire audit found 0 exact duplicate/overlapping wire segments.
- Ground routing is bus-oriented: button channel grounds branch into local GND buses, then each local bus has one trunk to the common GND rail.

## Part Notes

- ESP32: downloaded DOIT ESP32 DevKit V1 Fritzing part.
- Resistors: value-specific Fritzing 1k and 10k resistor artwork, plus visible labels.
- MOSFET: stock Fritzing TO-220 N-channel MOSFET artwork, titled as IRFB11N50APBF.
- Arcade buttons: stock Fritzing arcade button visuals plus labeled 4-position terminal blocks showing LED +, LED -, SW SIG, and SW GND.
- Speaker: stock Fritzing speaker artwork, titled as 4 ohm / 3W.
- PAM8403: custom generic mini amplifier board part because this Fritzing install did not include a PAM8403 module part and no exact board SKU was specified.
