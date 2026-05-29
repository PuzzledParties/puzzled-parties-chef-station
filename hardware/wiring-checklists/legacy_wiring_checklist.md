# Chef Station Simon Wiring Checklist

Assumption: the prompt requested five buttons but only listed suggested pins for four, so BTN5 uses GPIO 26 for the switch input and GPIO 27 for the lamp output.

Button reference used for this revision: uxcell 60mm 12V LED illuminated arcade pushbuttons with a normally-open microswitch and screw terminals. Use a 12V lamp supply for these specific LED modules.

## Pin Map

| Button | Switch input | Lamp gate output |
| --- | --- | --- |
| BTN1 / Ingredient 1 | GPIO 16 | GPIO 21 |
| BTN2 / Ingredient 2 | GPIO 17 | GPIO 22 |
| BTN3 / Ingredient 3 | GPIO 18 | GPIO 23 |
| BTN4 / Ingredient 4 | GPIO 19 | GPIO 25 |
| BTN5 / Ingredient 5 | GPIO 26 | GPIO 27 |

## Wiring

- Tie ESP32 GND, external lamp supply negative, all switch ground terminals, MOSFET sources, and all 10k pulldown ground ends to the common ground rail.
- Feed every LED/lamp positive from the shared +12V lamp rail for the linked uxcell buttons. If you substitute 5V illuminated buttons, use the matching 5V lamp rail instead.
- Run each lamp negative separately to its own MOSFET drain. Do not tie lamp negatives together.
- Connect each MOSFET source to common ground.
- Connect each ESP32 lamp GPIO to its MOSFET gate through a 100 ohm resistor.
- Add a 10k resistor from each MOSFET gate to common ground.
- Wire each button switch with one side to GND and the other side to its ESP32 input GPIO.
- Configure each button input as INPUT_PULLUP in firmware: unpressed = HIGH, pressed = LOW.
- Observe LED polarity on the arcade button lamp terminals; if an LED does not light, swap its LED + and LED - leads.
- IRFB11N50APBF can work for small lamp loads, but it is not a logic-level MOSFET. If lamps are dim or do not fully turn on, replace it with a logic-level N-channel MOSFET.
