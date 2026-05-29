# Collaborator Setup

## Clone The Repo

```powershell
git clone https://github.com/PuzzledParties/puzzled-parties-chef-station.git
cd puzzled-parties-chef-station
```

## Create A Branch

```powershell
git checkout -b firmware/simon-game
```

Use a branch name that describes the task.

## Open The Wiring Diagram

Install Fritzing, then open:

```text
hardware/fritzing/library-art/chef_station_simon_4btn_audio_editable.fzz
```

## Current Electrical Assumptions

- All Chef Station boards are Waveshare ESP32-P4-POE-ETH unless a task or
  decision record explicitly says otherwise.
- Arcade button LEDs use the lamp supply rail, currently documented as 12V.
- Button inputs use GPIO16, GPIO17, GPIO18, and GPIO19.
- Lamp gate outputs use GPIO20, GPIO21, GPIO22, and GPIO23.
- Avoid GPIO24/GPIO25 for lamps because the Waveshare header labels them as USB `D-`/`D+`.
- Audio uses the Waveshare board's onboard ES8311 codec and NS4150B amplifier.
- ESP32-P4 GND, lamp supply negative, MOSFET sources, switch grounds, and pulldown grounds all share common ground.
- Button inputs use `INPUT_PULLUP`.
- Speaker connects to the Waveshare MX1.25 2-pin speaker header.

## Making Changes

1. Pull latest `main`.
2. Create a branch.
3. Make and test the change.
4. Commit with a clear message.
5. Push the branch.
6. Open a Pull Request.

```powershell
git checkout main
git pull
git checkout -b hardware/button-harness
git add .
git commit -m "Document button harness wiring"
git push -u origin hardware/button-harness
```
