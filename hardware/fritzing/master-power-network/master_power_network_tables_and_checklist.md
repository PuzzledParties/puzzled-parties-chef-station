# Chef Station Master Power And Network Tables / Checklist

## Power Rail Table

| Rail | Source | Voltage | Use | Hard rule |
|---|---|---:|---|---|
| PoE | LS108GP switch ports | PoE | ESP32 controller boards only | Do not power LED strips, servos, lamps, or amplifiers from ESP32 PoE boards. |
| 12V_SHOW | 12V Adapter A | 12V DC | Actual 12V LED strips, 12V amplifier, fans, monitor accessory if rated 12V | Only connect devices explicitly rated for 12V. Do not tie to other adapter positives. |
| 5V_LED | 12V Adapter B -> Buck #2 | 5.0V-5.1V DC | WS2812/NeoPixel strips, cooktop coil LEDs, overhead strip, 5V Simon button lamps | Do not parallel with another buck output. |
| 5V_AUDIO_SERVO | 12V Adapter C -> Buck #3 | 5.0V-5.1V DC | DFPlayer modules, small amplifiers, small speakers, servo timer, optional LCD backlights | Do not feed from ESP32 5V/PoE board power. |
| 5V_AUX | 12V Adapter D -> Buck #1 | 5.0V-5.1V DC | Optional LCD backlights, small non-PoE accessories, low-current status LEDs, small relay boards | Keep low-current and isolated from other 5V positives. |
| COMMON_GND | Ground terminal block / bus | 0V reference | Shared reference where GPIO/data/control crosses rails | Do not route load return current through ESP32 ground pins. |

## Network Port Table

| LS108GP port | Device | Cable behavior | Power behavior |
|---|---|---|---|
| 1 | Simon ESP32 PoE board | Ethernet network | PoE powers ESP32 controller only. |
| 2 | Chopping ESP32 PoE board | Ethernet network | PoE powers ESP32 controller only. |
| 3 | Pan Motion ESP32 PoE board | Ethernet network | PoE powers ESP32 controller only. |
| 4 | Pot Temperature ESP32 PoE board | Ethernet network | PoE powers ESP32 controller only. |
| 5 | Garnish Placement ESP32 PoE board | Ethernet network | PoE powers ESP32 controller only. |
| 6 | Master Controller ESP32 PoE board | Ethernet network | PoE powers ESP32 controller only. |
| 7 | Epson TM-T20IV / TM-T20V-family printer | Ethernet network | Separate Epson manufacturer power supply. Not PoE. |
| 8 | Optional router/DHCP source or spare | DHCP/network management if needed | Router uses its own power if used. |

## Per-Module Accessory Power Table

| Module | ESP32 power/network | Accessory power | Control/ground notes |
|---|---|---|---|
| Simon | PoE over Ethernet | Button lamps from 5V_LED or 12V_SHOW by lamp rating; audio if present from 5V_AUDIO_SERVO | Button switches to ESP32 GPIO/GND. Lamp MOSFET sources to COMMON_GND. ESP32 GPIOs drive MOSFET gates only. |
| Chopping | PoE over Ethernet | Piezo from ESP32 3.3V if suitable; I2C LCD backlight from 5V_AUX or 5V_LED | Use optional I2C level shifter for 5V I2C LCD. LCD/piezo ground common with ESP32. |
| Pan Motion | PoE over Ethernet | Hall sensors from ESP32 3.3V; cooktop LED from 5V_LED or 12V_SHOW by strip type; DFPlayer/audio from 5V_AUDIO_SERVO | ESP32 sends LED data and serial to DFPlayer. All grounds common. |
| Pot Temperature | PoE over Ethernet | Encoder on ESP32 GPIO; cooktop LED from 5V_LED or 12V_SHOW; temp strip/ring from 5V_LED | Encoder uses INPUT_PULLUP. ESP32 and LED rail grounds common. |
| Garnish Placement | PoE over Ethernet | Touch electrodes only to ESP32 touch pins through 1k resistors; RGB strip from 5V_LED; servo from 5V_AUDIO_SERVO | DONE button to ESP32 GPIO/GND. ESP32, servo, and LED grounds common. |

## Grounding Notes

- All grounds must be common where GPIO/data/control signals cross between PoE ESP32 boards and external 5V/12V accessories.
- Connect Adapter A/B/C/D negatives, Buck #1/#2/#3 grounds, LED strip ground, DFPlayer/audio ground, servo ground, Simon lamp ground, and any relevant ESP32 GND pins to COMMON_GND.
- Module commands travel over Ethernet, so no separate GPIO sync harness is required for module start/reset.
- Do not route high-current LED, servo, or audio return current through ESP32 ground pins. Use a ground terminal block or bus.
- Grounds may be common; separate 12V positives and separate buck 5V positives must not be tied together.

## Setup Checklist

- Verify every adapter output with a multimeter before connecting electronics.
- Tape or lock adjustable adapter selector dials at 12V.
- Adjust buck converters to 5.0V-5.1V before connecting 5V electronics.
- Label both ends of every power cable.
- Confirm 12V_SHOW never touches 5V devices.
- Confirm 5V rails never touch ESP32 3.3V pins.
- Keep each 12V adapter as its own limited-current branch.
- Do not parallel separate wall adapter outputs.
- Do not parallel separate buck converter outputs.
- Use proper wire gauge for LED, servo, and audio currents.
- Avoid breadboard rails for multi-amp loads.
- Add 1000uF across LED strip 5V/GND near strip input.
- Add 470uF-1000uF near servo power.
- Add 470uF-1000uF near DFPlayer/audio modules.
- Add 0.1uF near Hall, piezo, and small sensor modules.
- Add a 330-470 ohm resistor on each WS2812 data line.
- If no fuses are available, avoid the 5V/60A open-frame supply in this temporary build.

## Warning Callouts

- PoE budget: keep total ESP32 PoE load under the LS108GP 62W budget and 30W per-port max.
- Common ground: required wherever GPIO/data/control signals cross between ESP32 boards and external accessory power rails.
- 12V vs 5V separation: only 12V-rated devices connect to 12V_SHOW; 5V devices connect only to named buck-derived 5V rails.
- No high-current loads from ESP32 PoE boards: ESP32 GPIOs send signals only.
- No unfused 60A supply in the temporary build: add fused distribution before using any large open-frame supply.
- Do not parallel buck outputs.
- Verify adjustable adapters with a multimeter.

## Network Behavior Notes

- ESP32 modules can receive IP addresses from a router/DHCP source or use static IPs.
- If there is no router, create and label a static IP plan before the event.
- The Master Controller ESP32 communicates with modules over Ethernet.
- The Epson printer is addressed by IP.
- The LS108GP may be unmanaged; use an optional router/DHCP source if network management is needed.
- Do not rely on internet access during the event.

## Assumptions And Substitutions

- The master controller in this build is a Waveshare ESP32-P4-POE-ETH / NH board.
- Hardware START_SYNC / RESET_SYNC wiring is intentionally omitted. Module start/reset/score traffic is planned over Ethernet.
- Exact LS108GP and Waveshare ESP32-P4-POE-ETH/NH Fritzing parts were not available in the installed library, so the sketch embeds custom editable helper parts with labeled connectors.
- No third-party parts were downloaded.
- The diagram is a master power/network layout, not a PCB fabrication footprint.
