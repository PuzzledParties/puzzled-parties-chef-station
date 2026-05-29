# Chef Station Chopping Module Wiring Checklist

## Pin Assignment Table

| ESP32 pin | Function |
|---|---|
| GPIO16 / ADC1_CH0 | Piezo AO analog input through 1k-10k series resistor |
| SDA / GPIO7 | I2C SDA to LCD through level shifter LV1/HV1 if LCD is powered at 5V |
| SCL / GPIO8 | I2C SCL to LCD through level shifter LV2/HV2 if LCD is powered at 5V |
| Ethernet UDP 42100 | START_GAME, FORCE_END, REQUEST_SCORE, RESET_GAME, and score JSON |

## Wiring Checklist

- ESP32 is powered and networked by PoE from the TP-Link LS108GP switch.
- PoE powers the ESP32 controller only. Do not power LCD backlights or other accessories from the ESP32 PoE board.
- ESP32 `GND` connects to the `COMMON_GND` rail wherever LCD or piezo signals cross to externally powered accessories.
- `5V_AUX` positive from the master power distribution connects to the local `5V_AUX` rail for the LCD/backlight and optional I2C level shifter HV side.
- `5V_AUX` ground/return connects to `COMMON_GND`.
- Do not feed +5V into the ESP32 `3V3` pin.
- Piezo module `VCC` connects to ESP32 3.3V, not +5V.
- Piezo module `GND` connects to `COMMON_GND`.
- Piezo module `AO` connects through a 1k-10k series resistor to GPIO16 / ADC1_CH0.
- Piezo module `DO` is left disconnected unless used as an optional debug input.
- Use `AO` analog output for scoring. Do not use `DO` as the main chop input.
- LCD `GND` connects to `COMMON_GND`.
- LCD `VCC` connects to `5V_AUX`, or to 3.3V only if the LCD/backpack works reliably at 3.3V.
- ESP32 SDA / GPIO7 connects to level shifter `LV1`; matching `HV1` connects to LCD `SDA`.
- ESP32 SCL / GPIO8 connects to level shifter `LV2`; matching `HV2` connects to LCD `SCL`.
- If the LCD backpack is powered at +5V, use the bidirectional I2C level shifter shown.
- Level shifter LV connects to ESP32 3.3V, HV connects to `5V_AUX`, and GND connects to `COMMON_GND`.
- Master game commands arrive over Ethernet; do not wire separate START_SYNC, RESET_SYNC, or DONE_OUT terminals.

## Piezo And Cutting Board Notes

- Piezo detects impacts, not static pressure.
- Mechanically couple the piezo disc or module to the underside of the cutting board.
- Protect the piezo from direct knife strikes.
- Put the cutting board on damped/rubber feet to reduce table vibration.
- Tune the analog threshold only after the piezo is mounted in the final board.
- Start with debounce/refractory period around 100-150 ms.
- If fast chopping is required, allow shorter debounce such as 60-100 ms after testing.
- Use threshold above vibration/noise baseline.
- Do not count multiple ringing peaks from one chop.
- Use forgiving thresholds because public users will chop inconsistently.

## Raw Piezo Disc Alternative

- Use the raw piezo circuit instead of the piezo module, not in parallel with it.
- One piezo lead goes to GPIO16 / ADC through a 10k-100k series resistor.
- The other piezo lead goes to GND.
- Add a 1M resistor across the piezo leads as bleed/reference.
- Add an optional 3.3V clamp diode or Schottky protection to protect the ESP32 ADC.
- Do not connect a raw piezo directly to the ESP32 ADC without input protection.

## LCD Behavior Notes

- LCD line 1: `CHOP FASTER`
- LCD line 2: `KEEP GOING`
- LCD line 3: progress bar fills as `chopCount / 100`
- LCD line 4: `Chops: 037/100` or `Time: 12.4s`
- Common I2C LCD addresses are `0x27` and `0x3F`.
- Adjust the LCD contrast potentiometer if characters are invisible.
- Mount the LCD above or behind the board so players do not need to look straight down.

## Firmware Behavior Notes

- IDLE: LCD may show `READY TO CHOP` with an empty progress bar.
- START: on Ethernet `START_GAME phase=main`, set `chopCount = 0` and `startTimeMs = millis()`.
- ACTIVE: sample GPIO16 frequently and count one valid chop when the analog value exceeds threshold.
- ACTIVE: update the LCD progress bar immediately after every valid chop.
- ACTIVE: reject ringing using the debounce/refractory period.
- COMPLETE: when `chopCount` reaches 100, set `finishTimeMs = millis()`.
- COMPLETE: compute `elapsedSeconds = (finishTimeMs - startTimeMs) / 1000.0`.
- COMPLETE: show completion time locally on the LCD and send score JSON.
- RESET: on Ethernet `RESET_GAME`, clear count and return to IDLE.
- Ethernet complete event: `{"station":"chef","module":"chop","event":"complete","chops":100,"seconds":18.42}`
- If the game ends before 100 chops, report partial score: `{"station":"chef","module":"chop","event":"incomplete","chops":72,"seconds":30.00}`

## Scoring

- Primary score is elapsed time from Ethernet `START_GAME` to the 100th valid chop.
- Lower time is better.
- The master clock may decide final ranking later.
- The chopping module measures local elapsed time and chop count.
- The monitor or central controller can add polish, but core gameplay should work locally.

## Assumptions And Part Notes

- Controller assumption: Waveshare ESP32-P4-ETH / ESP32-P4-POE-ETH module powered from the LS108GP over Ethernet.
- ESP32-P4 pinout basis: Waveshare exposes SDA/GPIO7 and SCL/GPIO8 on the 40-pin header; ESP32-P4 ADC pins are different from classic ESP32 DevKit GPIO34-style ADC pins.
- ESP32 part: custom editable ESP32-P4 helper part with the module's functional GPIO labels; verify exact board pinout before final harness fabrication.
- Accessory rail assumption: LCD/backlight power comes from `5V_AUX`, not from the ESP32 PoE board.
- Piezo module, LCD, level shifter, rails, physical board layout, raw piezo alternative, and callouts are custom editable Fritzing helper parts for readability.
- LCD is shown powered from +5V, so the diagram includes the optional level shifter in the active I2C path.
