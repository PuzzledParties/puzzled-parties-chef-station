# Chef Station Build Wiring Diagrams

No GitHub account is needed. On an iPad, if GitHub asks to open the app, choose
to continue in the browser. Tap a PNG link to open the diagram, then pinch to
zoom or use Share to save it.

## Build Set

| Build area | Diagram PNG | Checklist / tables | Editable Fritzing sketch |
|---|---|---|---|
| Master power and network | [Open diagram](../hardware/fritzing/master-power-network/chef_station_master_power_network_layout.png) | [Open checklist](../hardware/fritzing/master-power-network/master_power_network_tables_and_checklist.md) | [Open Fritzing file](../hardware/fritzing/master-power-network/chef_station_master_power_network_editable.fzz) |
| Master controller, score, and receipt printer | [Open diagram](../hardware/fritzing/master-controller-score-print/chef_station_master_controller_score_print_wiring_diagram.png) | [Open checklist](../hardware/fritzing/master-controller-score-print/wiring_checklist_master_controller_score_print.md) | [Open Fritzing file](../hardware/fritzing/master-controller-score-print/chef_station_master_controller_score_print_editable.fzz) |
| Simon ingredient buttons and audio | [Open diagram](../hardware/fritzing/library-art/chef_station_simon_4btn_audio_editable.png) | [Open checklist](../hardware/fritzing/library-art/wiring_checklist_4btn_audio.md) | [Open Fritzing file](../hardware/fritzing/library-art/chef_station_simon_4btn_audio_editable.fzz) |
| Chopping module | [Open diagram](../hardware/fritzing/chopping-module/chef_station_chopping_module_wiring_diagram.png) | [Open checklist](../hardware/fritzing/chopping-module/wiring_checklist_chopping_module.md) | [Open Fritzing file](../hardware/fritzing/chopping-module/chef_station_chopping_module_editable.fzz) |
| Pan motion cooktop | [Open diagram](../hardware/fritzing/pan-motion-cooktop/chef_station_pan_motion_cooktop_wiring_diagram.png) | [Open checklist](../hardware/fritzing/pan-motion-cooktop/wiring_checklist_pan_motion_cooktop.md) | [Open Fritzing file](../hardware/fritzing/pan-motion-cooktop/chef_station_pan_motion_cooktop_editable.fzz) |
| Pot temperature / heat balance | [Open diagram](../hardware/fritzing/pot-temperature-heat-balance/chef_station_pot_temperature_heat_balance_wiring_diagram.png) | [Open checklist](../hardware/fritzing/pot-temperature-heat-balance/wiring_checklist_pot_temperature_heat_balance.md) | [Open Fritzing file](../hardware/fritzing/pot-temperature-heat-balance/chef_station_pot_temperature_heat_balance_editable.fzz) |
| Garnish placement | [Open diagram](../hardware/fritzing/garnish-placement/chef_station_garnish_placement_wiring_diagram.png) | [Open checklist](../hardware/fritzing/garnish-placement/wiring_checklist_garnish_placement.md) | [Open Fritzing file](../hardware/fritzing/garnish-placement/chef_station_garnish_placement_editable.fzz) |

## Before Powering Anything

- Verify every adjustable adapter or buck converter output with a multimeter.
- Keep 12V devices on `12V_SHOW` and 5V devices on the named 5V rails.
- Do not tie separate positive supply outputs together.
- Use `COMMON_GND` where GPIO, data, or control signals cross between boards and accessory power.
- Do not route high-current LED, servo, lamp, or audio return current through ESP32 ground pins.
- Label both ends of every power, ground, signal, and accessory cable.
