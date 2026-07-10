# Super Productivity + Home Assistant Bridge

A **bidirectional bridge** between [Super Productivity](https://super-productivity.com/) and [Home Assistant](https://www.home-assistant.io/) — combining the best task/time management app with the best smart home platform.

**Two components, one system:**
- **Home Assistant Integration** — exposes your SP tasks, tracking, and projects as HA entities with full dashboard control
- **Super Productivity Plugin** — a rules-based automation engine that lets SP control your smart home (lights, scenes, media, notifications) based on your work

## Why?

Your productivity and your environment are connected. This bridge lets you:

- **Auto-adjust lighting** when you start deep work vs. take a break
- **Get Pomodoro break reminders** as phone notifications or TTS announcements
- **Track your work time** on a smart home dashboard visible from any room
- **Create tasks via voice** through HA's Assist
- **Celebrate completion** with lights, sounds, or party scenes when all tasks are done
- **Different ambiance per project** — blue lights for coding, warm for creative work

---

## Quick Start

### 1. Install the HA Integration

**Via HACS (recommended):**
1. HACS > three dots > Custom repositories
2. Add `https://github.com/jloops412/ha-super-productivity` as **Integration**
3. Find "Super Productivity" in HACS > **Download**
4. Restart Home Assistant
5. Settings > Devices & Services > Add Integration > **Super Productivity**
6. Enter your SP machine's IP and port `3876`

**Prerequisites:**
- Super Productivity desktop app (Electron) with **Local REST API enabled** (Settings > Misc > Enable local REST API)
- HA and SP on the same local network

### 2. Install the SP Plugin

1. Download `sp-plugin.zip` from the [latest release](https://github.com/jloops412/ha-super-productivity/releases)
2. In SP: Settings > Plugins > Upload Plugin > select the ZIP
3. Click "HA Bridge" in the left sidebar
4. Go to **Settings** tab > enter your HA URL + Long-Lived Access Token
5. Add rules in the **Rules** tab

---

## Home Assistant Integration

### Entities

| Type | Entities | Purpose |
|------|----------|---------|
| **Sensors** | Current Task, Active Tasks, Today's Tasks (total/pending/done), Time Worked Today, Current Task Time, Per-Project Task Counts, Task Details (Markdown) | Monitor productivity |
| **Binary Sensor** | Tracking Active | Is the timer running? |
| **Todo Lists** | One per SP project + "Today" list | View/manage tasks from HA |
| **Calendar** | SP Schedule | Scheduled tasks as calendar events |
| **Switch** | Time Tracking | Toggle tracking on/off |
| **Select** | Start Task, Active Project | Pick tasks/projects from dropdowns |
| **Text** | Quick Add Task | Type a title to create a task |
| **Buttons** | Stop, Complete, Archive | One-tap task actions |

### Events Fired

| Event | When | Data |
|-------|------|------|
| `super_productivity_task_started` | Tracking begins | task_id, title, project_id |
| `super_productivity_task_stopped` | Tracking ends | task_id |
| `super_productivity_task_completed` | Task marked done | task_id, title, time_spent_ms |
| `super_productivity_all_today_tasks_done` | All today's tasks complete | completed_count, time_worked_ms |

### Services

| Service | Description |
|---------|-------------|
| `super_productivity.create_task` | Create a task (title, project, tags, notes, due date) |
| `super_productivity.start_task` | Start tracking by task ID |
| `super_productivity.stop_task` | Stop current tracking |
| `super_productivity.complete_task` | Mark task done |
| `super_productivity.archive_task` | Archive a task |

### Options

After setup, configure via Settings > Devices & Services > Super Productivity > Configure:
- **Host/Port** — change without removing the integration
- **Poll interval** — 5 to 300 seconds (default 30)

### Webhook

The SP plugin can push instant updates to HA via webhook (no polling delay). The webhook ID is automatically registered and logged at startup:
```
super_productivity_<entry_id>
```
Find it in Settings > System > Logs, or via the API.

---

## Super Productivity Plugin

### Rules Engine

Create unlimited automation rules that fire based on your task activity:

**Triggers:**
| Trigger | Fires When |
|---------|-----------|
| Task Started | You begin tracking any task |
| Task Stopped | You stop tracking |
| Task Completed | A task is marked done |
| First Task of Day | The first task you track in a session |
| All Today's Done | Every today-scheduled task is complete |
| Timer (X min) | After X minutes of continuous tracking |
| Idle (X min) | After X minutes of no tracking |
| Day Finished | You end your work day in SP |

**Conditions (optional filters):**
- Only for a specific **Project**
- Only for a specific **Tag**
- Only if title **contains** text

**Actions:**
| Action | What It Does |
|--------|-------------|
| Activate Scene | Turn on any HA scene |
| Trigger Automation | Fire any HA automation |
| Run Script | Execute any HA script |
| Toggle Entity | Toggle any light/switch/entity |
| Set Light | Set brightness + color temperature |
| Media Control | Play/Pause/Next/Previous/Volume |
| TTS Announcement | Speak a message on any speaker |
| Custom Service | Call any HA service with data |
| Phone Notification | Push notification to your phone |

### Sensor Display

The **Sensors** tab shows live values from any HA sensor you configure — temperature, humidity, energy, whatever you want visible while working.

### Service Caller

The **Services** tab lets you call any HA service on-demand with entity dropdowns and JSON data support.

### Configuration

All settings are in the **Settings** tab within the plugin:
- HA URL (local, not cloud)
- Long-Lived Access Token (stored securely via `setSecret`, never synced/exported)
- Webhook ID (for instant sync)
- Sensor selection (dropdown picker)

### Security

The plugin follows SP's security best practices:
- **Access token** stored exclusively via `PluginAPI.setSecret()` — never in `persistDataSynced` (which syncs to servers/exports/backups)
- **plugin.js** handles all authenticated API calls — the iframe UI never sees or stores the raw token
- Old configs with embedded tokens are auto-migrated to secret storage on load

---

## Dashboard Example

The repo includes a ready-to-use dashboard layout in `examples/dashboard_cards.yaml` using `custom:button-card` for a polished look:

- **Focus section** — live tracking indicator, task picker, control buttons
- **Today section** — colored stat cards (pending/done/hours), todo list
- **Quick Actions** — add task, project picker, archive

Requires the `button-card` custom card (install via HACS > Frontend).

---

## Architecture

```
┌─────────────────────┐         ┌─────────────────────────┐
│  Super Productivity  │  REST   │  Home Assistant          │
│                      │◄───────►│                         │
│  ┌────────────────┐  │  API    │  Integration (polling)   │
│  │ plugin.js      │  │         │  - Sensors              │
│  │ (host context) │──┼────────►│  - Todo lists           │
│  │ - secrets      │  │ webhook │  - Controls             │
│  │ - rules engine │  │         │  - Events               │
│  │ - HA API proxy │  │         │  - Calendar             │
│  └───────┬────────┘  │         └─────────────────────────┘
│          │            │                    │
│  ┌───────▼────────┐  │                    │ Automations
│  │ index.html     │  │                    ▼
│  │ (iframe UI)    │  │            Smart Home Devices
│  │ - rules editor │  │
│  │ - sensor view  │  │
│  │ - service call │  │
│  └────────────────┘  │
└─────────────────────┘
```

**Data flow:**
1. HA integration polls SP's Local REST API every 30s (or instant via webhook)
2. SP plugin.js pushes events to HA webhook on task changes
3. SP plugin.js calls HA services directly based on rules
4. HA fires events that automations can trigger on
5. iframe UI communicates with plugin.js via `window.parent.haBridge`

---

## Installation Details

### Network Requirements

| Scenario | Setup |
|----------|-------|
| SP and HA on same machine | Host: `127.0.0.1`, Port: `3876` |
| SP and HA on same LAN | Host: SP machine's IP, Port: `3876` |
| Accessing HA via Nabu Casa | Use **local URL** for integration setup |

The SP Local REST API binds to localhost only. If HA is on a different machine, use the included `sp_proxy.py` or configure a reverse proxy.

### Compatibility

- **Super Productivity:** v10+ (Local REST API required)
- **Home Assistant:** 2024.1.0+
- **HACS:** Any recent version
- **SP Plugin:** Works in Electron desktop app (not web version)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect" during HA setup | Ensure SP is running with Local REST API enabled. Use local HA URL, not Nabu Casa. |
| Integration shows "Retrying" | SP app isn't running. Start it and HA will reconnect. |
| Plugin shows "Not set" | Go to Settings tab in the plugin and enter your HA URL + token. |
| Rules not firing | Check F12 console for `[HA Bridge]` logs. Ensure rules are enabled (toggle). |
| Duplicate plugin views | Remove plugin, fully quit SP (not just close), restart, reinstall. |
| Sensors not loading | Save settings first, wait for "Connected" badge, then check Sensors tab. |

---

## Contributing

Issues and PRs welcome at https://github.com/jloops412/ha-super-productivity

---

## License

MIT
