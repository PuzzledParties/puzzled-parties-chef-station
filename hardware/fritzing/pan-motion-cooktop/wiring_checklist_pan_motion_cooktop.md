# Chef Station Pan Motion / Cooktop Wiring Checklist

## Pin Assignment Table

| ESP32 pin | Function |
|---|---|
| GPIO20 / ADC1_CH4 | HALL 1 analog output through optional 1k series resistor |
| GPIO21 / ADC1_CH5 | HALL 2 analog output through optional 1k series resistor |
| GPIO23 | Cooktop RGB LED strip data through 330-470 ohm resistor |
| GPIO26 / UART2 TX | ESP32 TX to DFPlayer RX through 1k resistor |
| GPIO27 / UART2 RX | ESP32 RX from DFPlayer TX |

## Wiring Checklist

- ESP32 is powered and networked by PoE from the TP-Link LS108GP switch.
- PoE powers the ESP32 controller only. Do not power LED strips, DFPlayer/audio, or speakers from the ESP32 PoE board.
- `5V_LED` positive from the master power distribution goes to the local `5V_LED` rail for the cooktop RGB strip only.
- `5V_AUDIO_SERVO` positive from the master power distribution goes to the local audio rail for DFPlayer/audio only.
- Both 5V rail returns connect to `COMMON_GND`; do not tie the two 5V positives together.
- ESP32 GND connects to the `COMMON_GND` rail wherever LED data, serial, or Hall signals cross power domains.
- Hall sensor VCC pins connect to ESP32 3.3V only, not external +5V.
- Do not feed external +5V into the ESP32 `3V3` pin.
- HALL 1 `AO` connects through an optional 1k series resistor to GPIO20 / ADC1_CH4.
- HALL 2 `AO` connects through an optional 1k series resistor to GPIO21 / ADC1_CH5.
- Use analog Hall sensors such as SS49E, OH49E, or 49E. KY-024 modules are acceptable only when using `AO`.
- Do not use digital-only A3144 / KY-003 sensors for motion scoring.
- Add a 0.1uF capacitor between VCC and GND near each Hall sensor.
- RGB strip `+5V` connects to the `5V_LED` rail.
- RGB strip `GND` connects to `COMMON_GND`.
- ESP32 GPIO23 connects through a 330-470 ohm resistor to RGB strip `DIN`.
- Place a 1000uF electrolytic capacitor across RGB strip +5V and GND near the strip.
- DFPlayer `VCC` connects to the `5V_AUDIO_SERVO` rail.
- DFPlayer `GND` connects to `COMMON_GND`.
- ESP32 GPIO26 / UART2 TX connects through a 1k resistor to DFPlayer `RX`.
- ESP32 GPIO27 / UART2 RX connects directly to DFPlayer `TX`.
- Optional 470uF-1000uF capacitor goes across DFPlayer +5V and GND near the module.
- Speaker connects only to DFPlayer `SPK1` and `SPK2`.
- Do not connect either speaker terminal to GND.
- All grounds must be common where signals cross rails: ESP32, 5V_LED return, 5V_AUDIO_SERVO return, RGB strip, DFPlayer, and Hall sensors.

## Physical Cooktop Checklist

- Mount HALL 1 slightly left of burner center.
- Mount HALL 2 slightly right of burner center.
- Space HALL 1 and HALL 2 about 2.5-3.5 inches apart.
- Keep both Hall sensors under the fake cooktop within the 8-inch pan/burner area.
- Magnet should be hidden in the underside of the pan and offset about 1.5-2.5 inches from pan center.
- Target normal magnet-to-sensor gap is 1/4-1/2 inch.
- Use a thin non-metallic cooktop surface.
- Do not place Hall sensors under a stainless table or thick metal sheet.
- Optional expansion: add HALL 3-5 only if testing shows unreliable motion or dead zones; V1 uses two sensors.

## Firmware Behavior Notes

- At boot or round start, sample a no-pan baseline for both Hall sensors.
- Determine pan present by comparing current readings to the no-pan baseline.
- Sample Hall sensors repeatedly around 30-100 Hz.
- Calculate `motionScore = abs(H1_now - H1_last) + abs(H2_now - H2_last)`.
- Repeated changes above threshold count as pan moving.
- Pan present with motionScore below threshold counts as stationary.
- Accumulate pan active motion time for recipe scoring.
- RGB coil should react immediately to pan presence and movement.
- If pan is present and moving, play sizzle at low/medium volume.
- If pan is present but not moving, gradually increase volume and/or switch to burning track.
- If pan is absent, stop or reduce audio.
- Use forgiving thresholds; this is not precision gesture tracking.

## Assumptions And Part Notes

- Controller assumption: Waveshare ESP32-P4-POE-ETH / ESP32-P4-POE-ETH-NH module powered from the LS108GP over Ethernet.
- ESP32 part: custom editable ESP32-P4 PoE helper part with the module's functional GPIO labels. The Hall pins match the firmware's ESP32-P4 ADC1 map.
- Accessory rail assumption: cooktop LEDs use `5V_LED`; DFPlayer/audio uses `5V_AUDIO_SERVO`; these positives are not tied together.
- DFPlayer Mini, speaker, and electrolytic capacitors use stock Fritzing parts.
- Hall sensors, RGB cooktop coil, rails, supply, 0.1uF capacitors, resistors, physical cooktop layout, and callouts are custom editable Fritzing helper parts for readability.
