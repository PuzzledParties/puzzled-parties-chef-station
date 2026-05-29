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

- Arcade button LEDs use the lamp supply rail, currently documented as 12V.
- PAM8403 amplifier uses 5V only.
- ESP32, lamp supply negative, PAM8403 GND, MOSFET sources, switch grounds, and pulldown grounds all share common ground.
- Button inputs use `INPUT_PULLUP`.
- Speaker connects across PAM8403 `L+` and `L-`.

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
