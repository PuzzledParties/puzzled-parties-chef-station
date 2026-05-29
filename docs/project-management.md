# Project Management

Use this repository as the project home for Chef Station.

## GitHub

- Issues are the task list.
- Branches are where work happens.
- Pull Requests are where changes get reviewed, tested, and merged.
- Decision records in `docs/decisions` explain why we chose a hardware/software direction.
- Build notes in `docs/build-notes` capture messy real-world findings while assembling and testing.

## Suggested Issue Labels

- `hardware` - wiring, components, panel layout, enclosure, soldering.
- `firmware` - ESP32 code, game state, audio, inputs, outputs.
- `docs` - checklists, setup guides, decisions.
- `test` - bench testing, validation, measurements.
- `question` - unresolved design choice.
- `bug` - something that used to work or should work but does not.

## Branch Names

Use short, descriptive names:

```text
hardware/button-harness
hardware/panel-layout
firmware/simon-game
firmware/audio-driver
docs/collaborator-setup
test/button-led-current
```

## Codex Client Workflow

In the Codex client, start work from the local repo folder:

```text
C:\Users\homes\OneDrive\Desktop\Puzzled Parties\Puzzle Assets\Chef Station Simon Wiring
```

That folder is the project root. Ask Codex to work on a GitHub Issue, a branch, or a specific file in this repo. Good prompts look like:

```text
Create a branch for issue #3 and implement the ESP32 Simon game skeleton.
```

```text
Review the current wiring checklist and update it for the latest Fritzing diagram.
```

```text
Open a PR for the firmware/audio-driver branch with a short test plan.
```

## Keeping Main Stable

Keep `main` usable for collaborators. Put experiments on branches, and use PRs even for small changes so the discussion and test notes stay attached to the work.
