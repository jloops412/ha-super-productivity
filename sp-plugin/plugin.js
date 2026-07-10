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
    case 'automation':
      await haApi('POST', 'services/automation/trigger', { entity_id: action.entity });
      break;
    case 'script':
      await haApi('POST', 'services/script/turn_on', { entity_id: action.entity });
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
// CRITICAL: SP has a strict timeout on hook handlers (~2s).
// Hooks must return immediately. All heavy work is deferred via setTimeout.

PluginAPI.registerHook('currentTaskChange', (data) => {
  setTimeout(() => handleTaskChange(data), 10);
});

PluginAPI.registerHook('taskComplete', (taskId) => {
  setTimeout(() => handleTaskComplete(taskId), 10);
});

PluginAPI.registerHook('finishDay', () => {
  setTimeout(() => handleFinishDay(), 10);
});

async function handleTaskChange(data) {
  await loadConfig();
  console.log('[HA Bridge] currentTaskChange:', JSON.stringify(data));

  let taskId = null;
  if (data === null || data === undefined) {
    taskId = null;
  } else if (typeof data === 'string') {
    taskId = data;
  } else if (typeof data === 'object') {
    taskId = data.currentTaskId || data.id || data.taskId || null;
    if (!taskId && data.current) taskId = data.current.id || data.current;
  }

  if (taskId) {
    console.log('[HA Bridge] -> STARTED:', taskId);
    let task = {};
    try { const tasks = await PluginAPI.getTasks(); task = tasks.find(t => t.id === taskId) || {}; } catch(e) {}
    await evaluateRules('task_start', { taskId, title: task.title || '', projectId: task.projectId || null, tagIds: task.tagIds || [] });
    startTimerChecks();
    await notifyWebhook('task_started', { taskId, title: task.title });
  } else {
    console.log('[HA Bridge] -> STOPPED');
    stopTimerChecks();
    await evaluateRules('task_stop', {});
    await notifyWebhook('task_stopped', {});
  }
}

async function handleTaskComplete(taskId) {
  await loadConfig();
  let task = {};
  try { const tasks = await PluginAPI.getTasks(); task = tasks.find(t => t.id === taskId) || {}; } catch(e) {}
  await evaluateRules('task_complete', { taskId, title: task.title || '', projectId: task.projectId || null, tagIds: task.tagIds || [] });
  await notifyWebhook('task_completed', { taskId, title: task.title });
  try {
    const tasks = await PluginAPI.getTasks();
    const todayTasks = tasks.filter(t => t.tagIds && t.tagIds.includes('TODAY'));
    if (todayTasks.length > 0 && todayTasks.every(t => t.isDone)) {
      await evaluateRules('all_done', {});
      await notifyWebhook('all_today_done', { count: todayTasks.length });
    }
  } catch(e) {}
}

async function handleFinishDay() {
  await loadConfig();
  await evaluateRules('day_end', {});
  try {
    const tasks = await PluginAPI.getTasks();
    const done = tasks.filter(t => t.isDone);
    const totalTime = tasks.reduce((s, t) => s + (t.timeSpent || 0), 0);
    await notifyWebhook('day_finished', { completed: done.length, total: tasks.length, hoursWorked: Math.round(totalTime / 3600000 * 100) / 100 });
  } catch(e) {}
}

// --- UI Registration ---
// With iFrame:true and isSkipMenuEntry:false in manifest,
// SP automatically adds "Home Assistant Bridge" to the left sidebar menu.
// No manual registration needed.

// --- Init ---
loadConfig().then(() => {
  console.log(`[HA Bridge v3.2] Loaded. ${config.rules.length} rules configured.`);
});
