# Chef Station Pot Temperature / Heat Balance Wiring Checklist

## Pin Assignment Table

| ESP32 pin | Function |
|---|---|
| GPIO32 | Rotary encoder A / CLK |
| GPIO33 | Rotary encoder B / DT |
| GPIO27 | Rotary encoder pushbutton / SW |
| GPIO23 | Cooktop coil RGB strip data through 330-470 ohm resistor |
| GPIO18 | Pot temperature indicator RGB strip/ring data through 330-470 ohm resistor |

## Wiring Checklist

- ESP32 is powered and networked by PoE from the TP-Link LS108GP switch.
- PoE powers the ESP32 controller only. Do not power cooktop LEDs or indicator LEDs from the ESP32 PoE board.
- `5V_LED` positive from the master power distribution goes to the local `5V_LED` rail for the temperature indicator and any 5V cooktop LED strip.
- `5V_LED` return connects to `COMMON_GND`.
- ESP32 GND connects to the `COMMON_GND` rail wherever LED data or encoder signals share external references.
- Cooktop coil strip +5V connects to `5V_LED` if it is a 5V strip. If it is a true 12V strip, connect it to `12V_SHOW` instead and keep only its data/control reference common.
- Cooktop coil strip GND connects to `COMMON_GND`.
- ESP32 GPIO23 connects through a 330-470 ohm resistor to the cooktop coil strip DIN.
- Pot temperature indicator +5V connects to `5V_LED`.
- Pot temperature indicator GND connects to `COMMON_GND`.
- ESP32 GPIO18 connects through a 330-470 ohm resistor to the temperature indicator DIN.
- Place a 1000uF electrolytic capacitor across LED strip +5V and GND near the strip power input.
- Observe electrolytic capacitor polarity.
- Rotary encoder A / CLK connects to GPIO32.
- Rotary encoder B / DT connects to GPIO33.
- Rotary encoder SW connects to GPIO27.
- Rotary encoder common / GND connects to `COMMON_GND`.
- If using a KY-040 style encoder module, connect module VCC to ESP32 3.3V, not `5V_LED` or `12V_SHOW`.
- Use ESP32 `INPUT_PULLUP` for encoder A / CLK, B / DT, and SW.
- Do not feed external +5V into the ESP32 `3V3` pin.
- All grounds must be common where signals cross rails: ESP32, `5V_LED` return, cooktop coil strip, temperature indicator, and encoder.

## Callout Notes

- Common ground: the `5V_LED` return and ESP32 ground must be tied together where LED data crosses power domains.
- External LED power: LED strips use `5V_LED` or `12V_SHOW` by device rating; the ESP32 only provides data signals.
- Encoder INPUT_PULLUP wiring: A / CLK, B / DT, and SW should read HIGH idle and LOW when pulled to COMMON_GND.
- Cooktop coil brightness represents heat setting, not measured temperature.
- Temperature indicator represents simulated pot temperature, not a real sensor reading.
- Score is the percentage of total game time spent in the white/correct zone.

## Firmware Behavior Notes

- Use a fixed game duration, such as 30 or 60 seconds.
- Rotary encoder controls `heatSetting` from 0.0 to 1.0.
- Clockwise rotation increases heat; counterclockwise rotation decreases heat.
- Clamp heat setting from 0-100 percent.
- Cooktop coil color should remain red/orange and vary brightness from `heatSetting`.
- `potTemperature` is simulated, not directly measured.
- Model temperature with velocity/acceleration and damping so it feels physical.
- Higher `heatSetting` increases upward temperature acceleration.
- Lower `heatSetting` allows temperature to fall.
- Add random drift as a slow random walk so the balance point moves over time.
- Random drift should be slow and fair, not sudden or punitive.
- Suggested model: `acceleration = (heatSetting - balancePoint + drift) * tuningFactor`.
- Update `tempVelocity += acceleration * dt`, damp velocity, then update `potTemp += tempVelocity * dt`.
- Constrain `potTemp` to 0.0-1.0.
- `potTemp < 0.42` is TOO COLD / BLUE.
- `0.42 <= potTemp <= 0.58` is CORRECT / WHITE.
- `potTemp > 0.58` is TOO HOT / RED.
- Track milliseconds in the correct zone and total round milliseconds.
- At end of round, report `scorePercent = correctZoneMs / totalGameMs * 100`.
- Example Serial event: `{"station":"chef","module":"pot_temp","event":"score","percent":73}`.

## Game-State Notes

- IDLE: coil dim/off and temperature indicator idle glow.
- ACTIVE: encoder is live and temperature simulation runs.
- SCORING: freeze indicator and report score.
- RESET: clear score, recenter temperature, and recalibrate drift.
- The player should instantly understand that turning the knob changes heat.
- The pot temperature should not stay stable without input.
- The correct/white zone should be forgiving enough for public event use.
- Monitor graphics may show polish and score, but local LEDs should communicate the core gameplay.

## Assumptions And Part Notes

- Controller: diagram uses a custom Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH PoE helper part.
- The requested ESP32 GPIO function map is preserved on that PoE board helper. Verify exact pin availability before final harness fabrication.
- Accessory rail assumption: temperature LEDs use `5V_LED`; any actual 12V cooktop strip must move to `12V_SHOW`.
- LED strips/rings are represented as custom WS2812B-style helper parts so the +5V, DIN, and GND pins are explicit.
- Rotary encoder is represented as a custom KY-040/bare-encoder helper part so VCC, GND, A/CLK, B/DT, and SW are labeled clearly.
- 1000uF electrolytic capacitor uses the installed Fritzing stock part.
- Resistors, rails, supply, breadboard backplane, LED visuals, encoder, and callout notes are custom editable Fritzing helper parts for readability.
