# Chef Station Simon 4-Button Wiring Checklist

This revision uses a Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH controller powered and networked by the LS108GP PoE switch. PoE powers the ESP32 controller and the board's onboard ES8311 codec / NS4150B speaker amplifier. Button lamps and other external loads use named accessory rails.

## Pin Map

| Function | ESP32 pin |
| --- | --- |
| BTN1 / Ingredient 1 switch input | GPIO 16 |
| BTN2 / Ingredient 2 switch input | GPIO 17 |
| BTN3 / Ingredient 3 switch input | GPIO 18 |
| BTN4 / Ingredient 4 switch input | GPIO 19 |
| BTN1 lamp MOSFET gate | GPIO 20 |
| BTN2 lamp MOSFET gate | GPIO 21 |
| BTN3 lamp MOSFET gate | GPIO 22 |
| BTN4 lamp MOSFET gate | GPIO 23 |

## Power Rails

| Rail | Use |
| --- | --- |
| PoE from LS108GP | ESP32 controller, Ethernet, and onboard ES8311/NS4150B audio only |
| 12V_SHOW | 12V-rated Simon button lamps or show loads only |
| 5V_LED | Use instead of 12V_SHOW if the button lamps are 5V-rated |
| 5V_AUDIO_SERVO | Reserved for optional external audio accessories; not used by the default Simon speaker path |
| COMMON_GND | Signal reference and accessory return bus |

## Button And Lamp Wiring

- Configure each button input as `INPUT_PULLUP`: unpressed = HIGH, pressed = LOW.
- Wire each switch with one terminal to COMMON_GND and the other terminal to its ESP32 GPIO input.
- Feed each button lamp positive from the rail matching the lamp voltage: `12V_SHOW` for 12V lamps or `5V_LED` for 5V lamps.
- Run each button lamp negative separately to its own MOSFET drain.
- Connect each MOSFET source to the local ground bus, then to COMMON_GND.
- Connect each ESP32 lamp GPIO to its MOSFET gate through a 1k resistor.
- Add a 10k pulldown from each MOSFET gate to COMMON_GND.
- Do not connect lamp negatives together if individual flashing is required.

## Audio Wiring

- The default Simon sound path uses the Waveshare board's onboard ES8311 codec and NS4150B amplifier.
- Connect one 8 ohm / 2W speaker to the board's MX1.25 2-pin speaker header only.
- Do not tie either speaker lead to COMMON_GND or to any accessory rail.
- A separate PAM8403 or DFPlayer module is not part of the default Simon build.

## Grounding Notes

- Tie the Simon ESP32 GND reference to COMMON_GND anywhere GPIO controls externally powered lamps or audio.
- Do not route high-current lamp/audio return current through ESP32 ground pins.
- Use a ground terminal block or bus for lamp and audio returns.

## Setup Checklist

- Verify each adjustable adapter output with a multimeter before connecting the module.
- Confirm lamp voltage before connecting to `12V_SHOW` or `5V_LED`.
- Do not connect 12V to 5V lamps or 5V to ESP32 3.3V pins.
- Do not parallel separate buck converter outputs.
- Do not parallel separate wall adapter positive outputs.
- Label both ends of every lamp, signal, and rail cable.

## Part Notes

- ESP32 controller: custom editable Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH helper art with functional GPIO labels. Verify exact board pinout before final harness fabrication.
- Resistors: value-specific Fritzing 1k and 10k resistor artwork, plus visible labels.
- MOSFET: stock Fritzing TO-220 N-channel MOSFET artwork, titled as IRFB11N50APBF.
- Arcade buttons: stock Fritzing arcade button visuals plus labeled 4-position terminal blocks showing lamp +, lamp -, SW SIG, and SW GND.
- Rails, buses, and callouts are custom editable Fritzing helper parts for readability.
