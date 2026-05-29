# Chef Station Garnish Placement Wiring Checklist

## Pin Assignment Table

| ESP32 pin | Function |
|---|---|
| GPIO2 / Touch CH1 | CENTER capacitive electrode |
| GPIO3 / Touch CH2 | INNER RING capacitive electrode |
| GPIO6 / Touch CH5 | OUTER RING capacitive electrode |
| GPIO23 | RGB LED strip data through 330-470 ohm resistor |
| GPIO32 | Servo signal |
| GPIO26 | DONE button input using `INPUT_PULLUP` |

## Wiring Checklist

- ESP32 is powered and networked by PoE from the TP-Link LS108GP switch.
- PoE powers the ESP32 controller only. Do not power RGB strips or servos from the ESP32 PoE board.
- `5V_LED` positive from the master power distribution goes to the local `5V_LED` rail for the RGB strip only.
- `5V_AUDIO_SERVO` positive from the master power distribution goes to the local servo rail.
- Both 5V rail returns connect to `COMMON_GND`; do not tie the two 5V positives together.
- ESP32 GND connects to the `COMMON_GND` rail wherever LED data, servo signal, DONE input, or touch references cross power domains.
- Do not feed +5V into the ESP32 `3V3` pin.
- LED strip `+5V` connects to the `5V_LED` rail.
- LED strip `GND` connects to `COMMON_GND`.
- ESP32 GPIO23 connects through a 330-470 ohm resistor to LED strip `DIN`.
- Place a 1000uF electrolytic capacitor across LED strip +5V and GND near the strip.
- Servo red wire connects to `5V_AUDIO_SERVO`, brown/black wire to `COMMON_GND`, and signal to GPIO32.
- Place a 470uF-1000uF electrolytic capacitor across servo +5V and GND near the servo.
- DONE button one side connects to GPIO26; the other side connects to `COMMON_GND`.
- Configure DONE as `INPUT_PULLUP`; logic is unpressed = HIGH, pressed = LOW, with software debounce.
- CENTER electrode connects only to GPIO2 / Touch CH1 through its own 1k series resistor.
- INNER RING electrode connects only to GPIO3 / Touch CH2 through its own 1k series resistor.
- OUTER RING electrode connects only to GPIO6 / Touch CH5 through its own 1k series resistor.
- Capacitive electrodes do not connect to +5V or GND.
- Keep electrode wires short and leave visible gaps between copper/foil zones.
- Score after hands and chopsticks are away; calibrate capacitive baselines before each round.

## Firmware Behavior Notes

- At round start, sample capacitive baselines with no garnish present.
- Player has 30 seconds to place the conductive garnish.
- Servo sweeps from start to end over the 30-second timer.
- RGB strip shows active/countdown state: white at start, yellow at 10 seconds, flashing red at 5 seconds.
- DONE button ends the garnish round early.
- At scoring time, wait 300-800 ms, sample all three touch electrodes, calculate deltas from baseline, and score by strongest zone.
- CENTER strongest = PERFECT; INNER strongest = GOOD; OUTER strongest = OK; weak/no signal = MISS / NO GARNISH.

## Assumptions And Substitutions

- Controller assumption: Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH module powered from the LS108GP over Ethernet.
- ESP32 part: custom editable ESP32-P4 PoE helper part. ESP32-P4 touch-capable GPIOs are GPIO2-GPIO15; this layout uses GPIO2, GPIO3, and GPIO6 while GPIO24/GPIO25 remain untouched.
- Accessory rail assumption: RGB strip uses `5V_LED`; servo uses `5V_AUDIO_SERVO`; these positives are not tied together.
- The LED strip is represented as a custom editable 3-contact WS2812B/NeoPixel-style strip connector.
- The fake steak target is represented as a custom editable bullseye electrode part because no stock Fritzing part matches that prop.
- The servo, target, rails, supply, DONE button, and callouts use custom diagram parts for readable labeled terminals.
