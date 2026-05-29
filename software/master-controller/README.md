# Chef Station Master Controller

Raspberry Pi host app for the Chef Station master score/print layer.

The timing is fixed to the requested three-minute game:

- `150` seconds for Simon, chopping, pan motion, and pot balance.
- `30` seconds for the garnish game.
- `180` seconds total.

## Run In Dry-Run Mode

From the repository root:

```powershell
python .\software\master-controller\run_master.py --dry-run --auto-start --once --time-scale 0.02
```

Dry-run mode does not require Raspberry Pi hardware. It logs module UDP
commands, LED/audio actions, and the receipt text.

## Run On Raspberry Pi

On the Pi:

```bash
cd chef-station-repo/software/master-controller
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-pi.txt
python -m chef_station_master --config config.example.json
```

Use a copied config file for the real build and set:

- `module_udp_host` to the module broadcast address or a specific module host.
- `module_udp_port` to `42100` unless the ESP32 firmware is changed.
- `printer_mode` to `usb`, `network`, or `file`.
- `printer_usb_vendor_id` and `printer_usb_product_id` if using USB ESC/POS.
- `printer_network_host` if using Ethernet ESC/POS.
- `led_count` to the installed cooktop overhead LED count.
- `logo_path` to a preprocessed black-and-white R + B Grill logo image.

## Master Timeline

1. `IDLE`: LED strip idles and the Pi waits for the Start Game button on GPIO5.
2. `COUNTDOWN`: Pi plays `3-2-1-GO` beeps and pulses the overhead LED strip.
3. `ACTIVE_MAIN`: Pi sends `START_GAME phase=main duration_s=150` to Simon,
   chop, pan, and pot modules.
4. Main phase ends after `150` seconds. Pi sends `FORCE_END` and
   `REQUEST_SCORE` to the main modules.
5. `GARNISH`: Pi sends `START_GAME phase=garnish duration_s=30` to the garnish
   module.
6. Garnish phase ends after `30` seconds. Pi sends `FORCE_END` and
   `REQUEST_SCORE` to the garnish module.
7. `SCORING`: Pi averages valid module scores, leaving missing modules as
   `NO REPORT` unless `assign_zero_for_missing` is enabled.
8. `PRINTING`: Pi prints the R + B Grill receipt through ESC/POS or writes it
   to `receipts/` in file mode.
9. `RESET`: Pi sends `RESET_GAME target=all` over Ethernet UDP.

## Ethernet UDP Protocol

The master sends compact line commands:

```text
PREPARE_GAME session_id=AB12CD34 total_duration_s=180
START_GAME session_id=AB12CD34 phase=main target=main modules=simon,chop,pan,pot_temp duration_s=150
VOLUME_SET value=18 min=0 max=30
FORCE_END session_id=AB12CD34 phase=main target=main
REQUEST_SCORE session_id=AB12CD34 phase=main target=main
START_GAME session_id=AB12CD34 phase=garnish target=garnish modules=garnish duration_s=30
RESET_GAME session_id=AB12CD34 target=all
```

Modules should send JSON lines or key/value lines. JSON is preferred:

```json
{"module":"simon","event":"score","score":94,"successful_orders":13,"longest_streak":13,"failed_orders":0}
{"module":"chop","event":"complete","seconds":18.42,"score":85}
{"module":"pan","event":"complete","motion_ms":4200,"score":78}
{"module":"pot_temp","event":"score","percent":73,"score":73}
{"module":"garnish","event":"score","zone":"GOOD","score":80}
```

The master sends these payloads over UDP port `42100` by default. Modules should
listen on the same Ethernet network and reply with score/status JSON to the
master.

The master uses the normalized `score` field for the printed total and keeps the
full JSON payload for diagnostics and later score-balance changes.

## Hardware Notes

- Start Game button: GPIO5 to GND, active LOW with internal pullup.
- Module commands and score/status messages use Ethernet UDP port `42100`.
- Hardware START/RESET/DONE sync terminals are not part of the current build
  plan.
- ADS1115 reads the volume pot on A0 and the Pi broadcasts `VOLUME_SET 0-30`.
- LED strip data is GPIO18 through the AHCT level shifter.
- Epson printing uses ESC/POS through `python-escpos`; `file` mode is useful
  for testing receipt contents.
