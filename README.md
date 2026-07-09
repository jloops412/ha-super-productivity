# Super Productivity Integration for Home Assistant

A custom Home Assistant integration for [Super Productivity](https://super-productivity.com/) - an advanced todo list app with timeboxing and time tracking capabilities.

This integration connects to Super Productivity's **Local REST API** (available in the Electron desktop app) to give you full visibility and control over your tasks, time tracking, and projects from within Home Assistant.

## Prerequisites

- **Super Productivity desktop app** (Electron version) running on your network
- **Local REST API enabled**: In SP, go to Settings > Misc > Enable local REST API
- The API runs on port `3876` (localhost only by default)
- **HA and SP must be on the same machine OR the same local network**

### Network Setup

| Scenario | Configuration |
|----------|--------------|
| SP and HA on the **same machine** | Host: `127.0.0.1`, Port: `3876` |
| SP and HA on **different machines, same LAN** | Host: SP machine's LAN IP, Port: `3876` + run `sp_proxy.py` on the SP machine |
| Accessing HA via **Nabu Casa / cloud URL** | Use your **local HA URL** (e.g., `http://192.168.x.x:8123`) to add the integration, not the cloud URL |

> **Important:** If you're adding the integration via Nabu Casa's cloud URL (e.g., `https://xxx.ui.nabu.casa`), the connection test will fail because the cloud relay can't reach your local network. Switch to your local HA URL to configure.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu > **Custom repositories**
3. Add `https://github.com/jloops412/ha-super-productivity` with category **Integration**
4. Close the dialog, then search for "Super Productivity" in HACS
5. Click **Download**
6. **Restart Home Assistant**
7. Go to Settings > Devices & Services > **Add Integration** > search "Super Productivity"

### Manual

1. Copy the `custom_components/super_productivity` folder to your HA `config/custom_components/` directory
2. Restart Home Assistant
3. Go to Settings > Devices & Services > Add Integration > Super Productivity

## Configuration

The integration uses a UI config flow. Enter:

| Field | Default | Description |
|-------|---------|-------------|
| Host | `127.0.0.1` | IP of the machine running Super Productivity |
| Port | `3876` | Port for the Local REST API |

The integration will be created even if SP isn't currently running - it will retry automatically.

---

## What You Get

### Interactive Controls (Actions)

These let you **do things** from HA dashboards, automations, and voice assistants:

| Entity | Type | What It Does |
|--------|------|-------------|
| **Time Tracking** | Switch | Toggle ON to resume last task, OFF to stop tracking |
| **Start Task** | Select (dropdown) | Pick any of today's pending tasks to start tracking |
| **Active Project** | Select (dropdown) | Choose which project new tasks get added to |
| **Quick Add Task** | Text input | Type a title, press enter = task created in SP |
| **Stop Tracking** | Button | Stop the current timer |
| **Complete Current Task** | Button | Mark current task done and stop timer |
| **Archive Current Task** | Button | Archive current task and stop timer |

### Status Sensors (Monitoring)

| Entity | Type | What It Shows |
|--------|------|-------------|
| **Current Task** | Sensor | Title of the task you're tracking (+ attributes: task_id, project, time spent/estimated) |
| **Tracking Active** | Binary Sensor | ON when timer is running, OFF when idle |
| **Active Tasks** | Sensor | Total count of all non-archived tasks |
| **Today's Tasks** | Sensor | Number of tasks scheduled for today |
| **Today's Pending** | Sensor | Today's unfinished tasks |
| **Today's Completed** | Sensor | Today's finished tasks |
| **Time Worked Today** | Sensor | Hours tracked today (with minutes/seconds in attributes) |

### Todo Lists

| Entity | What It Does |
|--------|-------------|
| **SP: \<Project Name\>** | One list per project - view, create, complete, delete tasks |
| **SP: Today** | All tasks scheduled for today - check off as you go |

These show up in HA's native **To-do panel** (sidebar) for a full task management view.

### Services (For Automations)

| Service | Parameters | Description |
|---------|-----------|-------------|
| `super_productivity.create_task` | `title` (required), `project_id`, `tag_ids`, `notes`, `time_estimate`, `due_day`, `parent_id` | Create a task |
| `super_productivity.start_task` | `task_id` | Start tracking a specific task |
| `super_productivity.stop_task` | (none) | Stop current tracking |
| `super_productivity.complete_task` | `task_id` | Mark a task as done |
| `super_productivity.archive_task` | `task_id` | Archive a task |

---

## Dashboard Setup

### Recommended Card Layout

Add these to a Lovelace dashboard for a productivity control panel:

**Entities Card - Controls:**
```yaml
type: entities
title: Super Productivity
entities:
  - entity: switch.super_productivity_time_tracking
  - entity: select.super_productivity_start_task
  - entity: text.super_productivity_quick_add_task
  - entity: select.super_productivity_active_project
  - entity: button.super_productivity_stop_tracking
  - entity: button.super_productivity_complete_current_task
```

**Glance Card - Status:**
```yaml
type: glance
title: Today's Progress
entities:
  - entity: sensor.super_productivity_today_s_pending_tasks
    name: Pending
  - entity: sensor.super_productivity_today_s_completed_tasks
    name: Done
  - entity: sensor.super_productivity_time_worked_today
    name: Tracked
  - entity: sensor.super_productivity_active_tasks
    name: Total
```

**Conditional Card - Current Task:**
```yaml
type: conditional
conditions:
  - entity: binary_sensor.super_productivity_tracking_active
    state: "on"
card:
  type: entity
  entity: sensor.super_productivity_current_task
  name: Currently Working On
```

**Todo List Card:**
```yaml
type: todo-list
entity: todo.sp_today
title: Today's Tasks
```

---

## Automation Examples

### Focus mode - change lights when tracking starts

```yaml
automation:
  - alias: "Focus mode ON"
    trigger:
      - platform: state
        entity_id: binary_sensor.super_productivity_tracking_active
        to: "on"
    action:
      - service: light.turn_on
        target:
          entity_id: light.office_lamp
        data:
          brightness: 180
          color_temp_kelvin: 4000

  - alias: "Focus mode OFF"
    trigger:
      - platform: state
        entity_id: binary_sensor.super_productivity_tracking_active
        to: "off"
    action:
      - service: light.turn_on
        target:
          entity_id: light.office_lamp
        data:
          brightness: 255
          color_temp_kelvin: 2700
```

### Break reminder after 90 minutes of continuous tracking

```yaml
automation:
  - alias: "Take a break reminder"
    trigger:
      - platform: state
        entity_id: binary_sensor.super_productivity_tracking_active
        to: "on"
        for: "01:30:00"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Break Time"
          message: "You've been working for 90 minutes. Stand up and stretch!"
```

### Daily summary notification at end of work day

```yaml
automation:
  - alias: "Daily work summary"
    trigger:
      - platform: time
        at: "17:30:00"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Work Day Summary"
          message: >
            Completed: {{ states('sensor.super_productivity_today_s_completed_tasks') }} tasks
            Remaining: {{ states('sensor.super_productivity_today_s_pending_tasks') }} tasks
            Time tracked: {{ states('sensor.super_productivity_time_worked_today') }}h
```

### Add a task via voice assistant (HA Assist)

```yaml
automation:
  - alias: "Voice: Add task"
    trigger:
      - platform: conversation
        command:
          - "Add task {task_name}"
          - "New task {task_name}"
          - "Remind me to {task_name}"
    action:
      - service: super_productivity.create_task
        data:
          title: "{{ trigger.slots.task_name }}"
```

### Celebrate when all daily tasks are done

```yaml
automation:
  - alias: "All tasks complete celebration"
    trigger:
      - platform: state
        entity_id: sensor.super_productivity_today_s_pending_tasks
        to: "0"
    condition:
      - condition: numeric_state
        entity_id: sensor.super_productivity_today_s_tasks
        above: 0
    action:
      - service: tts.speak
        target:
          entity_id: tts.google_en
        data:
          message: "All tasks for today are done. Great work!"
          media_player_entity_id: media_player.living_room
```

### Auto-stop tracking at bedtime

```yaml
automation:
  - alias: "Stop tracking at bedtime"
    trigger:
      - platform: time
        at: "22:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.super_productivity_tracking_active
        state: "on"
    action:
      - service: super_productivity.stop_task
```

---

## Technical Details

- **Polling interval:** 30 seconds
- **API:** Super Productivity Local REST API (port 3876)
- **Authentication:** None (API is localhost-only by design)
- **Compatibility:** Super Productivity v10+ with Local REST API enabled
- **HA Version:** 2024.1.0+

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect" during setup | Make sure SP desktop app is running with Local REST API enabled. Use your local HA URL, not Nabu Casa cloud URL. |
| Integration shows "Retrying setup" | SP app is not running or not reachable. Start the app and it will reconnect automatically. |
| Entities show "Unavailable" | SP app was closed or the API was disabled. Entities recover when SP restarts. |
| No tasks in the "Start Task" dropdown | You have no pending tasks scheduled for today in SP. |
| Task created but not in expected project | Select the project in the "Active Project" dropdown first. |

## License

MIT
