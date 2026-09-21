# ESP32-Lab

🇬🇧 **English** | [🇫🇷 Français](README_fr.md)

![Version](https://img.shields.io/badge/version-0.9.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/tests-100%20passing-brightgreen)
![Targets](https://img.shields.io/badge/targets-ESP32--S3%20%7C%20ESP32--C3-orange)
![Mode](https://img.shields.io/badge/hardware-read%20only-success)
![Status](https://img.shields.io/badge/status-in%20development-yellow)
![License](https://img.shields.io/badge/license-GPL--3.0--only-blue)

Diagnostic and test lab for ESP32 microcontrollers, with a web interface.
Detects, identifies and analyses an ESP32 board connected over USB to a
Raspberry Pi (or any other Linux/Windows host).

> **New here?** Start with the [quick-start guide](docs/demarrage-rapide.md).
> The full documentation lives in the [`docs/`](docs/) folder.
> Note: the detailed docs are currently written in **French**.

## Goal

Enable the **non-destructive** identification, analysis and testing of a
connected ESP32, and keep a history of the diagnostics.

## Targets

- ESP32-S3
- ESP32-C3
- Variants with or without PSRAM

## Features

- USB / serial port detection
- SoC identification (chip, revision, frequencies, PSRAM)
- Flash analysis (manufacturer, JEDEC reference, size, type, voltage)
- **eFuse reading**: silicon identity, 128-bit unique ID, security posture,
  calibration, universal MAC addresses (read-only)
- **Flash chip SFDP** (JESD216): density, addressing, erase granularities,
  fast-read modes, and 64-bit unique ID
- **Real partition table reading** (read-only, at `0x8000`)
- **Structural NVS analysis** with human-readable value decoding
- **SQLite database** storing every reading per board, with **redisplay from
  the database** (no board attached) on every section, so an export/import
  restores and shows everything on another workstation
- **No secrets stored**: Wi-Fi passwords and eFuse keys are never written to the
  database (an HMAC-SHA-256 fingerprint tracks changes without keeping the secret)
- **Secret change detection**: compares the HMAC fingerprints of a same key
  between two scans to flag a changed secret - without ever storing it
- Registry of known boards (name, location, note per MAC address)
- Inventory history, **two-scan comparison** and
  **full comparison between two different boards**
- **On-demand NVS analysis** (reads the board's NVS partition)
- **GPIO Inspector** (chip-level, family-aware): per-pin classification
  (strapping, input-only, Flash/PSRAM, USB-JTAG, ADC, DAC), usage status and
  boot caveats - backed by a **local Espressif reference dataset** that works
  offline (curated from Espressif datasheets, manual refresh, integrity-checked)
- **Board profiles**: pick your board model to see the real per-pin exposure
  (BOOT button, LED, native USB, headers or not broken out); the choice is saved
  per board and travels with export/import
- **Firmware & OTA** (read-only): per-app identity from `esp_app_desc`
  (project name, version, ESP-IDF version, build date, anti-rollback, ELF
  sha256) and OTA state from `otadata` (boot-selected slot, per-entry state)
- **morfSystem-ready**: announces itself via morfBeacon (UDP heartbeat) with
  `/healthz` and `/status` endpoints - discoverable by morfMonitor
- CSV export
- Tab-based web interface

## Quick start

```bash
# 1. Install the dependencies in a virtual environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Start the server
PYTHONPATH=src .venv/bin/python -m web.server

# 3. Open the interface
#    http://<server-address>:8765
```

### Launch scripts

Two scripts at the project root automate startup (they check the `.venv`, start
the server, and open or print the access address):

- **Windows**: double-click `launch_esp32_lab.bat` (opens the local browser at
  http://127.0.0.1:8765).
- **Linux / Raspberry Pi**: `./launch_esp32_lab.sh`. On a Pi **with** a screen
  it opens the browser; on a **headless** Pi it opens nothing and **prints the
  addresses to type from another machine** (LAN IP and mDNS name
  `<host>.local`).

Details and alternatives (without a venv, Windows, Raspberry Pi):
see [`docs/installation.md`](docs/installation.md) (in French).

## Project layout

```
ESP32-Lab/
├── VERSION                 Current project version
├── CHANGELOG.md            Change log
├── requirements.txt        Python dependencies
├── docs/                   Documentation (beginner + architecture)
├── reference/espressif/    Curated Espressif GPIO dataset (shipped, offline)
├── data/                   Generated data + local dataset cache (git-ignored)
├── src/
│   ├── core/               Business logic (identification, partitions, NVS…)
│   ├── transport/          Serial access / port detection
│   └── web/                HTTP server + static interface (HTML/CSS/JS)
├── tests/                  Unit tests
└── tools/                  Utilities (SFDP reading, etc.)
```

See [`docs/architecture.md`](docs/architecture.md) for details (in French).

## HTTP API

| Method | Route                       | Description                              |
|--------|-----------------------------|------------------------------------------|
| GET    | `/api/health`               | Service status + version + port          |
| GET    | `/healthz`                  | Liveness (morfBeacon contract)           |
| GET    | `/status`                   | Rich status (morfBeacon contract)        |
| GET    | `/api/ports`                | Detected serial ports                    |
| GET    | `/api/inventory`            | Last saved inventory                     |
| GET    | `/api/inventory/history`    | Inventory history                        |
| GET    | `/api/devices`              | Board registry                           |
| GET    | `/api/device?mac=…`         | A board's record                         |
| GET    | `/api/db/device?mac=…`      | A board's full dossier (database)        |
| GET    | `/api/db/reading?mac=…&section=…` | Latest reading of a section for a board |
| GET    | `/api/db/compare?mac_a=…&mac_b=…` | Comparison of two boards           |
| GET    | `/api/db/changes?mac=…`     | Secret change detection (HMAC fingerprints) |
| GET    | `/api/gpio?chip=…&board=…`  | Chip-level GPIO map (family-aware, optional board exposure) |
| GET    | `/api/boards?family=…`      | Board profiles for a chip family         |
| POST   | `/api/device/board`         | Save a board's model choice              |
| GET    | `/api/espressif/status`     | Local Espressif reference dataset status |
| POST   | `/api/espressif/refresh`    | Update the Espressif dataset (project channel) |
| GET    | `/api/nvs`                  | Last NVS analysis report                 |
| POST   | `/api/inventory/refresh?port=…` | Scan the board and update            |
| POST   | `/api/partitions?port=…`    | Read the partition table (read-only)     |
| POST   | `/api/efuse?port=…`         | Read and analyse the eFuses (read-only)  |
| POST   | `/api/flash?port=…`         | Read the SFDP and Flash unique ID (read-only) |
| POST   | `/api/nvs/analyze?port=…`   | Read and analyse the NVS partition (read-only) |
| POST   | `/api/firmware?port=…`      | Read firmware identity + OTA state (read-only) |
| GET    | `/api/db/export`            | Export the whole database (portable JSON) |
| GET    | `/api/db/verify`            | Check integrity and statistics           |
| POST   | `/api/db/import`            | Import/merge a database export           |
| POST   | `/api/db/reset`             | Reset the database (irreversible)        |
| POST   | `/api/device/update`        | Save a board's record                    |
| POST   | `/api/device/delete`        | Delete a board and all its readings      |

## Principles

- No automatic erasing
- No eFuse modification
- Non-destructive tests by default
- Separation between **detected** and **reported** information
- Multi-family ESP32 compatibility

## Tests

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q
```

## License

This project is licensed under the **GNU General Public License v3.0 only**
(`GPL-3.0-only`). See the [LICENSE](LICENSE) file for the full text.

Copyright (C) 2026 Frédéric Biron.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, version 3 only. It is distributed in the hope that it will be
useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
