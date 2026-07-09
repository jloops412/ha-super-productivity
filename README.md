# Super Productivity Integration for Home Assistant

A custom Home Assistant integration for [Super Productivity](https://super-productivity.com/) - an advanced todo list app with timeboxing and time tracking capabilities.

This integration connects to Super Productivity's **Local REST API** (available in the Electron desktop app) to expose your tasks, tracking status, and projects as Home Assistant entities.

## Prerequisites

- **Super Productivity desktop app** (Electron) running on your network
- **Local REST API enabled**: Settings > Misc > Enable local REST API
- The API runs on port `3876` by default (localhost only)

> **Note:** If Home Assistant runs on a different machine than Super Productivity, you'll need to set up a reverse proxy or SSH tunnel to forward port 3876, since the API only listens on localhost by default.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu > Custom repositories
3. Add this repository URL with category "Integration"
4. Search for "Super Productivity" and install
5. Restart Home Assistant
6. Go to Settings > Integrations > Add Integration > Super Productivity

### Manual

1. Copy the `custom_components/super_productivity` folder to your HA `config/custom_components/` directory
2. Restart Home Assistant
3. Go to Settings > Integrations > Add Integration > Super Productivity

## Configuration

The integration uses a UI config flow. You'll be asked for:

| Field | Default | Description |
|-------|---------|-------------|
| Host | `127.0.0.1` | IP/hostname where Super Productivity is running |
| Port | `3876` | Port for the Local REST API |

## Entities

### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.super_productivity_current_task` | Title of the currently tracked task |
| `sensor.super_productivity_active_tasks` | Total number of active (non-archived) tasks |
| `sensor.super_productivity_today_s_tasks` | Number of tasks scheduled for today |
| `sensor.super_productivity_today_s_pending_tasks` | Pending tasks for today |
| `sensor.super_productivity_today_s_completed_tasks` | Completed tasks for today |
| `sensor.super_productivity_time_worked_today` | Total time worked today (hours) |

### Binary Sensors

| Entity | Description |
|--------|-------------|
| `binary_sensor.super_productivity_tracking_active` | Whether time tracking is currently running |

### Todo Lists

| Entity | Description |
|--------|-------------|
| `todo.sp_<project_name>` | One todo list per SP project (full CRUD) |
| `todo.sp_today` | Virtual list of today's scheduled tasks |

## Services

| Service | Description |
|---------|-------------|
| `super_productivity.create_task` | Create a new task |
| `super_productivity.start_task` | Start tracking a task |
| `super_productivity.stop_task` | Stop tracking the current task |
| `super_productivity.complete_task` | Mark a task as done |
| `super_productivity.archive_task` | Archive a task |

## Automation Examples

### Turn on focus lights when tracking starts

```yaml
automation:
  - alias: "Focus mode on"
    trigger:
      - platform: state
        entity_id: binary_sensor.super_productivity_tracking_active
        to: "on"
    action:
      - service: light.turn_on
        target:
          entity_id: light.desk_lamp
        data:
          color_name: blue
          brightness: 200
```

### Send notification when all today's tasks are done

```yaml
automation:
  - alias: "All tasks done"
    trigger:
      - platform: state
        entity_id: sensor.super_productivity_today_s_pending_tasks
        to: "0"
    condition:
      - condition: numeric_state
        entity_id: sensor.super_productivity_today_s_tasks
        above: 0
    action:
      - service: notify.mobile_app
        data:
          message: "All tasks for today are completed!"
```

### Create a task via voice assistant

```yaml
automation:
  - alias: "Add task from voice"
    trigger:
      - platform: conversation
        command: "Add task {task_name}"
    action:
      - service: super_productivity.create_task
        data:
          title: "{{ trigger.slots.task_name }}"
```

## Technical Details

- **Polling interval:** 30 seconds
- **API:** Super Productivity Local REST API (port 3876)
- **Authentication:** None (API is localhost-only by design)
- **Compatibility:** Super Productivity v10+ (Local REST API was added in v10)

## License

MIT
