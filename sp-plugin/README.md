# Home Assistant Bridge - Super Productivity Plugin

A rules-based automation engine that connects Super Productivity to Home Assistant, letting your task activity control your smart home.

## Installation

1. Download `sp-plugin.zip` from the [latest release](https://github.com/jloops412/ha-super-productivity/releases)
2. In Super Productivity: **Settings > Plugins > Upload Plugin**
3. Select the ZIP file
4. "HA Bridge" appears in the left sidebar

## Setup

1. Click **HA Bridge** in the sidebar
2. Go to the **Settings** tab
3. Enter your **Home Assistant URL** (e.g., `http://homeassistant.local:8123`)
4. Enter a **Long-Lived Access Token** (HA Profile > Long-Lived Access Tokens > Create)
5. Optionally enter your **Webhook ID** for instant sync
6. Click **Save Settings**
7. Badge should show "Connected" with your HA version

## Creating Rules

1. Go to the **Rules** tab
2. Click **+ Add Rule**
3. Choose a **Trigger** (when should this fire?)
4. Optionally set **Conditions** (only for certain projects/tags)
5. Choose an **Action** (what should happen in HA?)
6. Pick your target from the dropdown (scenes, lights, automations — all auto-discovered from HA)
7. **Save Rule**

### Example Rules

| Name | Trigger | Action |
|------|---------|--------|
| Focus lights | Task Started | Scene: focus_mode |
| Relax mode | Task Stopped | Scene: relax |
| Break reminder | Timer: 25 min | Phone Notification: "Pomodoro break!" |
| Deep work music | Task Started (tag: deep-work) | Media: Play |
| Celebrate | All Today's Done | Scene: party |
| Dim for late work | Timer: 120 min | Light: brightness 100, temp 2700K |

## Tabs

| Tab | Purpose |
|-----|---------|
| **Rules** | Create/edit/toggle automation rules |
| **Sensors** | View live HA sensor data while working |
| **Services** | Call any HA service manually |
| **Settings** | Configure connection + sensor display |

## Requirements

- Super Productivity v10+ (Electron desktop app)
- Home Assistant with a Long-Lived Access Token
- Both on the same local network

## How It Works

- **plugin.js** (host context, survives navigation):
  - Stores HA token securely via `setSecret`/`getSecret`
  - Handles ALL authenticated HA API calls
  - Runs the rules engine and hook handlers
  - Exposes `window.haBridge` bridge for the iframe
- **index.html** (iframe, destroyed on navigation):
  - Pure UI — rules editor, sensor display, service caller, settings
  - Communicates with plugin.js via `window.parent.haBridge`
  - Never stores or directly uses credentials
- **Hooks** fire non-blocking (via `setTimeout`) to avoid SP's ~2s timeout
- **Timer/Idle** rules use background intervals in plugin.js
- **Config** persists via `persistDataSynced` (from plugin.js), token via `setSecret`

## Security

- Access token stored via `PluginAPI.setSecret()` — **never in synced/exported data**
- `setSecret`/`getSecret` only available from plugin.js (not iframe)
- Iframe never handles raw credentials
- Old configs with embedded tokens auto-migrate to secret storage

## Version History

- **5.0** — Architecture rewrite: plugin.js owns secrets + API, iframe is pure UI (bridge pattern)
- **4.2** — Security: token moved to setSecret/getSecret, today detection fixed
- **4.0** — All 12 SP hooks, 20 triggers, correct currentTaskChange payload handling
- **3.2** — Full rewrite: 8 triggers, 9 action types, sensor picker, media/TTS/light control
- **3.0** — Rules engine, timer/idle triggers, deferred hooks
- **2.0** — Config via persistDataSynced, tabbed UI
- **1.0** — Basic scene toggle, webhook push
