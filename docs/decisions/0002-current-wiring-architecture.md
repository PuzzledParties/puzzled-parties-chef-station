# 0002 Current Wiring Architecture

## Status

Accepted

## Context

The Chef Station button module needs individually flashing illuminated buttons, button input sensing, and sound output.

## Decision

- Use four illuminated arcade buttons.
- Use ESP32 internal pullups for button switch inputs.
- Use one low-side MOSFET driver per button lamp.
- Use a shared lamp positive rail and individual lamp negative switching.
- Use local ground buses for each button channel, tied to one common ground rail.
- Use a PAM8403 5V mini amplifier for speaker output.
- Use one 4 ohm / 3W speaker connected across PAM8403 `L+` and `L-`.

## Consequences

- Button lamps can flash independently.
- Switch wiring remains simple: pressed = LOW, unpressed = HIGH.
- All grounds must be common.
- PAM8403 must not be powered from the lamp rail if the lamp rail is 12V.
- Neither speaker lead should be tied to ground because the PAM8403 output is bridge-tied.
