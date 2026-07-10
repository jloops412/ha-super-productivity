/**
 * Home Assistant Bridge v2.0 - Super Productivity Plugin
 *
 * Features:
 * - Control HA scenes/services from SP (focus mode, relax mode)
 * - Push instant task updates to HA via webhook
 * - Auto-activate focus scene when tracking starts
 * - Auto-activate relax scene when tracking stops
 * - Send daily summary to HA on day finish
 */

let config = {
  haUrl: '',
  haToken: '',
  webhookId: '',
  focusScene: '',
  relaxScene: '',
  showSensors: '',
};

// ---- HA API Helper ----

async function haApi(method, path, body = null) {
  if (!config.haUrl || !config.haToken) return null;
  const url = `${config.haUrl}/api/${path}`;
  const options = {
    method,
    headers: {
      'Authorization': `Bearer ${config.haToken}`,
      'Content-Type': 'application/json',
    },
  };
  if (body) options.body = JSON.stringify(body);
  try {
    const resp = await fetch(url, options);
    if (resp.ok) return await resp.json();
    console.log(`[HA Bridge] API ${resp.status}: ${await resp.text()}`);
    return null;
  } catch (e) {
    console.log(`[HA Bridge] API error: ${e.message}`);
    return null;
  }
}

async function haCallService(domain, service, data = {}) {
  return haApi('POST', `services/${domain}/${service}`, data);
}

async function haGetState(entityId) {
  return haApi('GET', `states/${entityId}`);
}

async function notifyWebhook(event, data = {}) {
  if (!config.webhookId || !config.haUrl) return;
  try {
    await fetch(`${config.haUrl}/api/webhook/${config.webhookId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event, ...data }),
    });
  } catch (e) {
    // Silent fail
  }
}

// ---- Scene Control ----

async function activateFocusMode() {
  if (!config.focusScene) return;
  await haCallService('scene', 'turn_on', {
    entity_id: config.focusScene,
  });
  console.log('[HA Bridge] Focus scene activated:', config.focusScene);
}

async function activateRelaxMode() {
  if (!config.relaxScene) return;
  await haCallService('scene', 'turn_on', {
    entity_id: config.relaxScene,
  });
  console.log('[HA Bridge] Relax scene activated:', config.relaxScene);
}

// ---- Load Config ----

async function loadConfig() {
  try {
    const cfg = await PluginAPI.getConfig();
    if (cfg) {
      config.haUrl = (cfg.haUrl || '').replace(/\/$/, ''); // strip trailing slash
      config.haToken = cfg.haToken || '';
      config.webhookId = cfg.webhookId || '';
      config.focusScene = cfg.focusScene || '';
      config.relaxScene = cfg.relaxScene || '';
      config.showSensors = cfg.showSensors || '';
    }
  } catch (e) {
    console.log('[HA Bridge] Config not set yet');
  }
}

// ---- Hooks ----

// When tracking starts -> activate focus scene + notify HA
PluginAPI.registerHook('currentTaskChange', async (data) => {
  await loadConfig(); // refresh config in case it changed
  if (data && data.currentTaskId) {
    // Task started
    await activateFocusMode();
    await notifyWebhook('task_started', { taskId: data.currentTaskId });
  } else {
    // Task stopped
    await activateRelaxMode();
    await notifyWebhook('task_stopped', {});
  }
});

// When a task is completed -> notify HA
PluginAPI.registerHook('taskComplete', async (taskId) => {
  await notifyWebhook('task_completed', { taskId });
});

// When day finishes -> send summary to HA
PluginAPI.registerHook('finishDay', async () => {
  const tasks = await PluginAPI.getTasks();
  const doneTasks = tasks.filter(t => t.isDone);
  const totalTimeSpent = tasks.reduce((sum, t) => sum + (t.timeSpent || 0), 0);

  await notifyWebhook('day_finished', {
    totalTasks: tasks.length,
    completedTasks: doneTasks.length,
    totalTimeMs: totalTimeSpent,
    totalTimeHours: Math.round(totalTimeSpent / 3600000 * 100) / 100,
  });

  // Also fire an HA event for automation triggers
  if (config.haToken) {
    await haApi('POST', 'events/super_productivity_day_summary', {
      completed: doneTasks.length,
      total: tasks.length,
      hours_worked: Math.round(totalTimeSpent / 3600000 * 100) / 100,
    });
  }
});

// ---- UI Registration ----

// Header button: Quick toggle focus mode
PluginAPI.registerHeaderButton({
  label: 'HA Focus',
  icon: 'lightbulb',
  onClick: async () => {
    await loadConfig();
    if (!config.haToken) {
      PluginAPI.showSnack({
        msg: 'HA Bridge: Configure your HA URL and token in plugin settings first.',
        type: 'WARN',
      });
      return;
    }
    if (config.focusScene) {
      await activateFocusMode();
      PluginAPI.showSnack({ msg: 'Focus scene activated!', type: 'SUCCESS' });
    } else {
      PluginAPI.showSnack({
        msg: 'No focus scene configured. Set it in plugin settings.',
        type: 'WARN',
      });
    }
  },
});

// Menu entries for scene control
PluginAPI.registerMenuEntry({
  label: 'HA: Activate Focus Mode',
  icon: 'lightbulb',
  onClick: async () => {
    await loadConfig();
    await activateFocusMode();
    PluginAPI.showSnack({ msg: 'Focus mode activated', type: 'SUCCESS' });
  },
});

PluginAPI.registerMenuEntry({
  label: 'HA: Activate Relax Mode',
  icon: 'self_improvement',
  onClick: async () => {
    await loadConfig();
    await activateRelaxMode();
    PluginAPI.showSnack({ msg: 'Relax mode activated', type: 'SUCCESS' });
  },
});

PluginAPI.registerMenuEntry({
  label: 'HA: Connection Status',
  icon: 'home',
  onClick: async () => {
    await loadConfig();
    if (!config.haToken) {
      PluginAPI.showSnack({ msg: 'Not configured. Add HA URL & token in plugin settings.', type: 'WARN' });
      return;
    }
    const result = await haApi('GET', 'config');
    if (result) {
      PluginAPI.showSnack({
        msg: `Connected to HA ${result.version} (${result.location_name})`,
        type: 'SUCCESS',
      });
    } else {
      PluginAPI.showSnack({ msg: 'Cannot reach Home Assistant', type: 'ERROR' });
    }
  },
});

// Keyboard shortcut for focus toggle
PluginAPI.registerShortcut({
  keys: 'ctrl+shift+f',
  label: 'Toggle HA Focus Mode',
  action: async () => {
    await loadConfig();
    await activateFocusMode();
    PluginAPI.showSnack({ msg: 'Focus mode toggled', type: 'SUCCESS' });
  },
});

// ---- Init ----
loadConfig().then(() => {
  const status = config.haToken ? 'configured' : 'not configured';
  console.log(`[HA Bridge v2.0] Loaded. HA: ${status}`);
});
