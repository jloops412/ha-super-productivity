/**
 * Home Assistant Bridge v2.1 - Super Productivity Plugin
 * 
 * Unified bridge: auto-scenes, webhook push, HA control.
 * Config stored via PluginAPI.persistDataSynced().
 */

let config = {};

async function loadConfig() {
  try {
    const raw = await PluginAPI.loadSyncedData();
    if (raw) {
      config = JSON.parse(raw);
    }
  } catch (e) {
    config = {};
  }
  return config;
}

async function haApi(method, path, body = null) {
  if (!config.haUrl || !config.haToken) return null;
  const url = `${config.haUrl.replace(/\/$/, '')}/api/${path}`;
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
    return null;
  } catch (e) {
    return null;
  }
}

async function notifyWebhook(event, data = {}) {
  if (!config.webhookId || !config.haUrl) return;
  try {
    await fetch(`${config.haUrl.replace(/\/$/, '')}/api/webhook/${config.webhookId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event, ...data, timestamp: Date.now() }),
    });
  } catch (e) { /* silent */ }
}

async function activateScene(sceneName) {
  if (!sceneName || !config.haToken) return;
  await haApi('POST', 'services/scene/turn_on', { entity_id: sceneName });
}

// --- Hooks ---

PluginAPI.registerHook('currentTaskChange', async (data) => {
  await loadConfig();
  if (data && data.currentTaskId) {
    if (config.focusScene) await activateScene(config.focusScene);
    await notifyWebhook('task_started', { taskId: data.currentTaskId });
  } else {
    if (config.relaxScene) await activateScene(config.relaxScene);
    await notifyWebhook('task_stopped', {});
  }
});

PluginAPI.registerHook('taskComplete', async (taskId) => {
  await loadConfig();
  await notifyWebhook('task_completed', { taskId });
});

PluginAPI.registerHook('finishDay', async () => {
  await loadConfig();
  const tasks = await PluginAPI.getTasks();
  const done = tasks.filter(t => t.isDone);
  const totalTime = tasks.reduce((s, t) => s + (t.timeSpent || 0), 0);
  await notifyWebhook('day_finished', {
    completed: done.length,
    total: tasks.length,
    hoursWorked: Math.round(totalTime / 3600000 * 100) / 100,
  });
  if (config.haToken) {
    await haApi('POST', 'events/super_productivity_day_summary', {
      completed: done.length,
      total: tasks.length,
      hours_worked: Math.round(totalTime / 3600000 * 100) / 100,
    });
  }
});

// --- UI: Side Panel Button ---

PluginAPI.registerSidePanelButton({
  label: 'Home Assistant',
  icon: 'home',
  onClick: () => {
    PluginAPI.showIndexHtmlAsView();
  },
});

// --- Init ---
loadConfig().then(() => {
  const s = config.haToken ? 'configured' : 'not configured';
  console.log(`[HA Bridge v2.1] Loaded. Status: ${s}`);
});
