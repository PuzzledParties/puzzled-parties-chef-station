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
- Use the Waveshare ESP32-P4-POE-ETH as the controller board for this and
  future Chef Station builds unless another board is explicitly specified.
- Use GPIO16-GPIO19 for the four switch inputs.
- Use GPIO20-GPIO23 for the four lamp gate outputs.
- Avoid GPIO24/GPIO25 for lamp outputs because they are exposed as USB OTG
  `D-`/`D+` on the Waveshare header.
- Use the board's onboard ES8311 codec and NS4150B amplifier for speaker output.
- Use one 8 ohm / 2W speaker connected to the board's MX1.25 2-pin speaker header.

## Consequences

- Button lamps can flash independently.
- Switch wiring remains simple: pressed = LOW, unpressed = HIGH.
- All grounds must be common.
- A separate PAM8403 module is no longer part of the default build.
- Neither speaker lead should be tied to ground; use the board speaker header only.
