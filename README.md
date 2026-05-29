# Puzzled Parties Chef Station

Chef Station is the hardware/software project for interactive kitchen-game
features. The current build includes the shared power/network layout, the
Master Controller ESP32, and the Simon, chopping, pan motion, pot temperature,
and garnish placement modules.

GitHub is the source of truth for the project: tasks live in Issues, work happens on branches, reviews happen through Pull Requests, and build decisions live in `docs/decisions`.

## Current Build

- Waveshare ESP32-P4-POE-ETH controller board. This is the default board for
  Chef Station unless a future note explicitly says otherwise.
- Four illuminated arcade buttons labeled Ingredient 1 through Ingredient 4.
- One MOSFET low-side lamp driver per button.
- One 1k gate resistor and one 10k gate pulldown per MOSFET.
- Shared lamp positive rail for the button LEDs.
- Common ground rail with local ground buses for each button channel.
- Onboard ES8311 codec and NS4150B speaker amplifier on the Waveshare board.
- One 8 ohm / 2W speaker connected to the Waveshare MX1.25 2-pin speaker header.

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

- `docs/build-wiring-diagrams.md` - iPad-friendly index of the build wiring diagrams, checklists, and editable Fritzing files.
- `hardware/fritzing/master-power-network/` - master power and network layout.
- `hardware/fritzing/library-art/chef_station_simon_4btn_audio_editable.fzz` - current editable Fritzing sketch.
- `hardware/fritzing/library-art/chef_station_simon_4btn_audio_editable.png` - current PNG preview.
- `hardware/fritzing/library-art/fritzing_svg_export/chef_station_simon_4btn_audio_editable_breadboard.svg` - current Fritzing SVG export.
- `hardware/fritzing/library-art/wiring_checklist_4btn_audio.md` - current wiring checklist.
- `hardware/fritzing/chopping-module/` - chopping module wiring.
- `hardware/fritzing/pan-motion-cooktop/` - pan motion cooktop wiring.
- `hardware/fritzing/pot-temperature-heat-balance/` - pot temperature / heat balance wiring.
- `hardware/fritzing/garnish-placement/` - garnish placement wiring.
- `tools/diagram-generators/generate_orthogonal_fritzing_diagram.py` - generator for the latest native Fritzing sketch.

## Important Electrical Notes

- All grounds must be common: ESP32-P4 GND, lamp supply negative, button switch grounds, MOSFET sources, and pulldown grounds.
- The linked illuminated arcade buttons are treated as 12V LED buttons.
- Button inputs use ESP32-P4 internal pullups: unpressed = HIGH, pressed = LOW.
- Lamp gates use GPIO20, GPIO21, GPIO22, and GPIO23. Avoid GPIO24/GPIO25 for lamps because the Waveshare header labels them as USB `D-`/`D+`.
- Audio uses the onboard ES8311 codec and NS4150B amplifier. Connect the speaker only to the board speaker header; do not tie either speaker lead to ground.
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
