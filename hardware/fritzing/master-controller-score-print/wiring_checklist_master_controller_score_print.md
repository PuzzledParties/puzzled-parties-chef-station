# Chef Station Master Controller / Score + Print Layer Wiring Checklist

## Brief Wiring Checklist

- Power the Raspberry Pi from its official USB-C or micro-USB power supply. Do not power the Pi from the breadboard +5V rail.
- Power the Epson TM-T20IV / TM-T20V-family printer from its manufacturer supply. The printer does not power the Raspberry Pi.
- Power the WS2812B / NeoPixel overhead cooktop LED strip from an external regulated +5V supply sized for the LED count.
- Tie all low-voltage logic grounds together for the local controller wiring: Raspberry Pi GND, ADS1115 GND, external LED supply GND, LED strip GND, button GND, and level-shifter GND.
- Do not route high-current LED return current through a delicate Raspberry Pi ground jumper; use proper power distribution for the LED strip.
- Connect Start Game button one side to Raspberry Pi GPIO5 and the other side to GND. Configure GPIO5 with an internal pullup: unpressed = HIGH, pressed = LOW.
- Optionally place a 0.1uF capacitor across the Start Game button terminals, and still use software debounce.
- Wire ADS1115 VDD to Pi 3.3V, GND to common GND, SDA to GPIO2, SCL to GPIO3, ADDR to GND for address 0x48, and A0 to the volume pot wiper.
- Wire the 10k master volume potentiometer outer lugs to 3.3V and GND, with the center wiper to ADS1115 A0.
- Connect Raspberry Pi GPIO18 to a 74AHCT125 or 74HCT245 input. Power the level shifter from +5V and common GND.
- Connect the level-shifter output through a 330-470 ohm resistor to LED strip DIN.
- Place a 1000uF electrolytic capacitor across LED strip +5V and GND near the strip input. Observe polarity.
- Connect Raspberry Pi USB to the Epson printer USB port, or use Ethernet if the Epson model is networked.
- Connect Raspberry Pi Ethernet to the same module Ethernet network/switch as the ESP32-P4 boards.
- Do not wire separate START_SYNC, RESET_SYNC, DONE_OUT, or serial A/B terminals for game commands.
- Configure the master software to send `START_GAME`, `RESET_GAME`, `FORCE_END`, `REQUEST_SCORE`, and `VOLUME_SET` over UDP port 42100.
- Connect a USB powered speaker or USB audio dongle to the Raspberry Pi for global countdown and victory audio.

## Pin Assignment Table

| Raspberry Pi pin | Signal | Destination | Notes |
|---|---|---|---|
| GPIO2 / SDA | I2C SDA | ADS1115 SDA | Volume ADC bus |
| GPIO3 / SCL | I2C SCL | ADS1115 SCL | Volume ADC bus |
| GPIO5 | START_BUTTON | Start Game button to GND | Internal pullup; active LOW |
| GPIO18 | LED_DATA_3V3 | 74AHCT125 input | Level shifted before LED strip |
| Ethernet | MODULE_NET | LS108GP / module network | UDP port 42100 command/status link |
| 3.3V | PI_3V3_LOGIC | ADS1115 VDD and pot outer lug | Do not use for LED strip |
| GND | COMMON_GND | Logic ground rail | Must be common with shared signals |
| USB | PRINTER_USB | Epson receipt printer | Preferred printer connection |
| USB/audio | CONTROLLER_AUDIO | USB speaker or audio dongle | Global beeps/jingle only |

## Module Network Connector Table

| Module connector terminal | Wire color | Connects to | Required? | Notes |
|---|---|---|---|---|
| Ethernet / UDP | Blue | LS108GP switch and ESP32-P4 Ethernet ports | Yes | UDP port 42100 carries commands and score/status messages |
| Local accessory GND | Black | Shown on each station diagram | As needed | Common ground is still required where GPIO/data crosses local accessory power domains |

Connected branches shown:

| Branch | Expected module behavior |
|---|---|
| Simon Module | Reports complete/score events over Ethernet UDP |
| Chopping Module | Reports completion time and normalized score |
| Pan Motion Module | Reports motion timing and normalized score |
| Pot Temperature Module | Reports percent-in-zone and score |
| Garnish Placement Module | Reports zone result and score |

## Receipt-Printing Architecture Notes

- Raspberry Pi is the master score/print host because Epson receipt printers are easiest to control from Linux over USB or Ethernet using ESC/POS.
- Do not wire a USB-only Epson printer directly to ESP32 GPIO.
- Preprocess the fictional `R + B Grill` logo as a monochrome bitmap, about 384 px wide or the printer-compatible width for the model.
- Print the logo with an ESC/POS raster image command, then print concise text fields so the receipt is fast and theatrical.
- Print player total score, itemized module scores, a result line, a thank-you line, and cut paper if the printer supports it.
- If a module fails to report before timeout, print `NO REPORT` for that module and either average only valid scores or assign 0, depending on operator preference.
- Keep a cached last receipt so the operator can reprint after a paper jam or dramatic flourish failure.

Example receipt:

```text
R + B GRILL
[graphic logo]

CHEF SCORE RECEIPT

TOTAL SCORE: 084 / 100

Simon:        092
Chop Speed:   085
Pan Motion:   078
Pot Temp:     073
Garnish:      080

Result:
LINE COOK LEGEND

Thank you for dining
at R + B Grill
```

## Module Data Behavior

Modules send score/status JSON lines or compact messages over Ethernet UDP port 42100:

```text
{"module":"simon","event":"complete","score":92}
{"module":"chop","event":"complete","seconds":18.42,"score":85}
{"module":"pan","event":"complete","motion_ms":4200,"score":78}
{"module":"pot_temp","event":"score","percent":73,"score":73}
{"module":"garnish","event":"score","zone":"GOOD","score":80}
```

Master sends commands:

```text
START_GAME
RESET_GAME
VOLUME_SET 0-30
REQUEST_SCORE
FORCE_END
```

## Controller Software Notes

- IDLE: LED strip off or dim warm glow; wait for Start Game button; optionally poll modules for READY.
- COUNTDOWN: play 3-2-1-GO beeps on controller speaker and pulse overhead LED strip.
- At GO: broadcast Ethernet UDP `START_GAME`.
- ACTIVE: record `masterStartTime`, keep overhead LED strip on, read master volume knob repeatedly, broadcast `VOLUME_SET` only when changed, collect score/progress events.
- SCORING: send `FORCE_END` or `REQUEST_SCORE`, wait with timeout, compute itemized breakdown and total score, play victory jingle, run LED victory flourish.
- PRINTING: send ESC/POS print job to Epson: logo, total score, module breakdown, result line, thank-you line, and cut command when supported.
- RESET: broadcast Ethernet UDP `RESET_GAME`, clear score state, return to IDLE.
- Operator override options should include force start, force end, reprint last receipt, mute all, and reset all.

## Callout Notes

- Common ground: all shared logic grounds must be common.
- USB/Ethernet Epson printer connection: use Pi USB by default, Ethernet only for networked models.
- Ethernet module communication: UDP port 42100 carries module commands and score/status events.
- No hardware sync terminals: START/RESET/DONE wires are intentionally omitted.
- Master volume: the knob is a software volume cap signal, not an analog audio bus.
- External 5V LED power: LED strip current comes from the external regulated supply.
- LED data level shifting: use 74AHCT/74HCT for reliable 5V WS2812B data.
- Local controller speaker: only global countdown and victory sounds play here.
- R + B Grill thermal-printer logo: use a preprocessed monochrome raster logo.

## Assumptions And Substitutions

- Diagram chooses Raspberry Pi as the required master score/print host and draws a Pi 4/5/Zero 2 W-compatible 40-pin host helper part.
- ADS1115 is chosen for the volume ADC path. MCP3008 would also work but would use SPI pins and different wiring.
- Printer connection is drawn as USB preferred, with Ethernet noted as an option for networked Epson models.
- All visual parts are custom editable Fritzing helper parts embedded in the `.fzz`; no third-party parts were downloaded.
- The helper art is not a mechanical footprint for fabrication. It is a clean Fritzing-style wiring layout for build communication.
