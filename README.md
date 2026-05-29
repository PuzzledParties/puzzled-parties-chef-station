# Puzzled Parties Chef Station

Chef Station is the hardware/software project for interactive kitchen-game features. The current build includes the first feature, a Simon-style ingredient button module, plus the wiring foundation for audio output.

GitHub is the source of truth for the project: tasks live in Issues, work happens on branches, reviews happen through Pull Requests, and build decisions live in `docs/decisions`.

## Current Build

- ESP32 dev board controller.
- Four illuminated arcade buttons labeled Ingredient 1 through Ingredient 4.
- One MOSFET low-side lamp driver per button.
- One 1k gate resistor and one 10k gate pulldown per MOSFET.
- Shared lamp positive rail for the button LEDs.
- Common ground rail with local ground buses for each button channel.
- PAM8403 5V mini amplifier board.
- One 4 ohm / 3W speaker connected across PAM8403 `L+` and `L-`.

## Repo Layout

```text
hardware/
  fritzing/              Editable Fritzing sketches, exports, downloaded parts
  wiring-checklists/     Wiring checklists and legacy notes

firmware/
  esp32-chef-station/    ESP32 firmware home

docs/
  build-notes/           Running notes from assembly/testing
  decisions/             Decision records for hardware/software choices
  collaborator-setup.md  How collaborators get started
  project-management.md  How we use GitHub/Codex to manage work

tools/
  diagram-generators/    Scripts that generate/edit diagram assets
```

## Main Files

- `hardware/fritzing/library-art/chef_station_simon_4btn_audio_editable.fzz` - current editable Fritzing sketch.
- `hardware/fritzing/library-art/chef_station_simon_4btn_audio_editable.png` - current PNG preview.
- `hardware/fritzing/library-art/fritzing_svg_export/chef_station_simon_4btn_audio_editable_breadboard.svg` - current Fritzing SVG export.
- `hardware/fritzing/library-art/wiring_checklist_4btn_audio.md` - current wiring checklist.
- `tools/diagram-generators/generate_orthogonal_fritzing_diagram.py` - generator for the latest native Fritzing sketch.

## Important Electrical Notes

- All grounds must be common: ESP32, lamp supply negative, PAM8403 GND, button switch grounds, MOSFET sources, and pulldown grounds.
- The linked illuminated arcade buttons are treated as 12V LED buttons.
- PAM8403 must be powered from 5V only. Do not power the PAM8403 from the 12V lamp rail.
- PAM8403 speaker outputs are bridge-tied outputs. Connect the speaker across `L+` and `L-`; do not connect either speaker lead to ground.
- Button inputs use ESP32 internal pullups: unpressed = HIGH, pressed = LOW.
- IRFB11N50APBF is overkill and not logic-level; replace with a logic-level MOSFET if the button LEDs do not fully turn on.

## Daily Workflow

1. Pick or create a GitHub Issue.
2. Create a branch named for the work, such as `firmware/simon-game` or `hardware/audio-test`.
3. Make the change locally.
4. Push the branch and open a Pull Request.
5. Merge into `main` after review or test notes are captured.

## Regenerating The Current Wiring Diagram

Run from the repo root:

```powershell
python .\tools\diagram-generators\generate_orthogonal_fritzing_diagram.py
```

The script writes the editable `.fzz` and asks Fritzing to export SVGs through:

```powershell
& 'C:\Program Files\Fritzing\Fritzing.exe' -svg .\hardware\fritzing\library-art\fritzing_svg_export
```
