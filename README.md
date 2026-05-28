# Chef Station Simon Wiring

Native Fritzing wiring assets for the Chef Station Simon button module.

## Current Build

- ESP32 dev board controller.
- Four illuminated arcade buttons labeled Ingredient 1 through Ingredient 4.
- One MOSFET low-side lamp driver per button.
- One 1k gate resistor and one 10k gate pulldown per MOSFET.
- Shared lamp positive rail for the button LEDs.
- Common ground rail with local ground buses for each button channel.
- PAM8403 5V mini amplifier board.
- One 4 ohm / 3W speaker connected across PAM8403 `L+` and `L-`.

## Main Files

- `library_art_fritzing/chef_station_simon_4btn_audio_editable.fzz` - current editable Fritzing sketch.
- `library_art_fritzing/chef_station_simon_4btn_audio_editable.png` - current PNG preview.
- `library_art_fritzing/fritzing_svg_export/chef_station_simon_4btn_audio_editable_breadboard.svg` - current Fritzing SVG export.
- `library_art_fritzing/wiring_checklist_4btn_audio.md` - current wiring checklist.
- `generate_orthogonal_fritzing_diagram.py` - generator for the latest native Fritzing sketch.

Older diagram iterations are kept in the repo for reference.

## Important Electrical Notes

- All grounds must be common: ESP32, lamp supply negative, PAM8403 GND, button switch grounds, MOSFET sources, and pulldown grounds.
- The linked illuminated arcade buttons are treated as 12V LED buttons.
- PAM8403 must be powered from 5V only. Do not power the PAM8403 from the 12V lamp rail.
- PAM8403 speaker outputs are bridge-tied outputs. Connect the speaker across `L+` and `L-`; do not connect either speaker lead to ground.
- Button inputs use ESP32 internal pullups: unpressed = HIGH, pressed = LOW.
- IRFB11N50APBF is overkill and not logic-level; replace with a logic-level MOSFET if the button LEDs do not fully turn on.

## Regenerating

Run from this folder:

```powershell
python .\generate_orthogonal_fritzing_diagram.py
```

The script writes the editable `.fzz` and asks Fritzing to export SVGs through:

```powershell
& 'C:\Program Files\Fritzing\Fritzing.exe' -svg .\library_art_fritzing\fritzing_svg_export
```
