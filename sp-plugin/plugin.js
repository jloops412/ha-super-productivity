/**
 * Home Assistant Bridge v3.0 - Super Productivity Plugin
 * 
 * Rules-based automation engine:
 * - Define triggers (task start, stop, complete, project, tag, time thresholds)
 * - Map to HA actions (scenes, services, notifications)
 * - Persistent config via PluginAPI.persistDataSynced()
 */

let config = { haUrl: '', haToken: '', webhookId: '', rules: [] };
let trackingStartTime = null;
let timerCheckInterval = null;
let firedTimerRules = new Set(); // track which timer rules fired this session

async function loadConfig() {
  try {
    const raw = await PluginAPI.loadSyncedData();
    if (raw) config = JSON.parse(raw);
    if (!config.rules) config.rules = [];
  } catch (e) { config = { haUrl: '', haToken: '', webhookId: '', rules: [] }; }
  return config;
}

async function saveConfig() {
  await PluginAPI.persistDataSynced(JSON.stringify(config));
}

// --- HA API ---
async function haApi(method, path, body = null) {
  if (!config.haUrl || !config.haToken) return null;
  const url = `${config.haUrl.replace(/\/$/, '')}/api/${path}`;
  const opts = { method, headers: { 'Authorization': `Bearer ${config.haToken}`, 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  try { const r = await fetch(url, opts); return r.ok ? await r.json() : null; }
  catch (e) { return null; }
}

async function executeAction(action) {
  if (!action || !config.haToken) return;
  switch (action.type) {
    case 'scene':
      await haApi('POST', 'services/scene/turn_on', { entity_id: action.entity });
      break;
    case 'service':
      const [domain, svc] = (action.service || '').split('.');
      const data = action.entity ? { entity_id: action.entity, ...(action.data || {}) } : (action.data || {});
      if (domain && svc) await haApi('POST', `services/${domain}/${svc}`, data);
      break;
    case 'notify':
      await haApi('POST', 'services/notify/mobile_app_jphone', { 
        title: action.title || 'Super Productivity',
        message: action.message || ''
      });
      break;
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

// --- Rules Engine ---
async function evaluateRules(trigger, context = {}) {
  await loadConfig();
  for (const rule of config.rules) {
    if (!rule.enabled) continue;
    if (rule.trigger !== trigger) continue;

    // Check conditions
    let match = true;
    if (rule.conditions) {
      if (rule.conditions.projectId && context.projectId !== rule.conditions.projectId) match = false;
      if (rule.conditions.tagId && !(context.tagIds || []).includes(rule.conditions.tagId)) match = false;
      if (rule.conditions.titleContains && !(context.title || '').toLowerCase().includes(rule.conditions.titleContains.toLowerCase())) match = false;
    }

    if (match) {
      console.log(`[HA Bridge] Rule fired: ${rule.name}`);
      await executeAction(rule.action);
    }
  }
}

// --- Timer rules (duration-based) ---
function startTimerChecks() {
  if (timerCheckInterval) clearInterval(timerCheckInterval);
  trackingStartTime = Date.now();
  firedTimerRules.clear();

  timerCheckInterval = setInterval(async () => {
    if (!trackingStartTime) return;
    const elapsed = Date.now() - trackingStartTime;
    const elapsedMin = elapsed / 60000;

    await loadConfig();
    for (const rule of config.rules) {
      if (!rule.enabled || rule.trigger !== 'timer') continue;
      const threshold = rule.conditions?.minutes || 0;
      if (threshold > 0 && elapsedMin >= threshold && !firedTimerRules.has(rule.id)) {
        firedTimerRules.add(rule.id);
        console.log(`[HA Bridge] Timer rule fired: ${rule.name} (${threshold}min)`);
        await executeAction(rule.action);
      }
    }
  }, 30000); // check every 30s
}

function stopTimerChecks() {
  if (timerCheckInterval) { clearInterval(timerCheckInterval); timerCheckInterval = null; }
  trackingStartTime = null;
  firedTimerRules.clear();
}

// --- Hooks ---
PluginAPI.registerHook('currentTaskChange', async (data) => {
  await loadConfig();
  if (data && data.currentTaskId) {
    // Task started
    const tasks = await PluginAPI.getTasks();
    const task = tasks.find(t => t.id === data.currentTaskId) || {};
    await evaluateRules('task_start', {
      taskId: data.currentTaskId,
      title: task.title,
      projectId: task.projectId,
      tagIds: task.tagIds || [],
    });
    startTimerChecks();
    await notifyWebhook('task_started', { taskId: data.currentTaskId, title: task.title });
  } else {
    // Task stopped
    stopTimerChecks();
    await evaluateRules('task_stop', {});
    await notifyWebhook('task_stopped', {});
  }
});

PluginAPI.registerHook('taskComplete', async (taskId) => {
  await loadConfig();
  const tasks = await PluginAPI.getTasks();
  const task = tasks.find(t => t.id === taskId) || {};
  await evaluateRules('task_complete', {
    taskId,
    title: task.title,
    projectId: task.projectId,
    tagIds: task.tagIds || [],
  });
  await notifyWebhook('task_completed', { taskId, title: task.title });

  // Check if all today's tasks done
  const todayTasks = tasks.filter(t => t.tagIds && t.tagIds.includes('TODAY'));
  const allDone = todayTasks.length > 0 && todayTasks.every(t => t.isDone);
  if (allDone) {
    await evaluateRules('all_done', {});
    await notifyWebhook('all_today_done', { count: todayTasks.length });
  }
});

PluginAPI.registerHook('finishDay', async () => {
  await loadConfig();
  await evaluateRules('day_end', {});
  const tasks = await PluginAPI.getTasks();
  const done = tasks.filter(t => t.isDone);
  const totalTime = tasks.reduce((s, t) => s + (t.timeSpent || 0), 0);
  await notifyWebhook('day_finished', {
    completed: done.length, total: tasks.length,
    hoursWorked: Math.round(totalTime / 3600000 * 100) / 100,
  });
});

// --- UI ---
PluginAPI.registerSidePanelButton({
  label: 'Home Assistant',
  icon: 'home',
  onClick: () => { PluginAPI.showIndexHtmlAsView(); },
});

// --- Init ---
loadConfig().then(() => {
  console.log(`[HA Bridge v3.0] Loaded. ${config.rules.length} rules configured.`);
});
