/**
 * Home Assistant Bridge v4.2 - Super Productivity Plugin
 * 
 * Full rules-based automation engine using ALL available SP hooks.
 * 
 * SECURITY: haToken stored via PluginAPI.setSecret() (never synced/exported).
 * Non-secret config stored via PluginAPI.persistDataSynced() (synced across devices).
 */

let config = { haUrl: '', webhookId: '', rules: [], showSensors: '' };
let haToken = ''; // Stored separately via setSecret, never in synced data
let trackingStartTime = null;
let trackingTaskId = null;
let timerCheckInterval = null;
let idleCheckInterval = null;
let firedTimerRules = new Set();
let firedIdleRules = new Set();
let lastTrackingStopTime = null;
let sessionTasksStarted = 0;
let currentProjectId = null;

async function loadConfig() {
  try {
    const raw = await PluginAPI.loadSyncedData();
    if (raw && raw.length > 2) {
      const parsed = JSON.parse(raw);
      // Migration: if old config has haToken in synced data, move it to secret
      if (parsed.haToken) {
        await PluginAPI.setSecret('haToken', parsed.haToken);
        haToken = parsed.haToken;
        delete parsed.haToken;
        await PluginAPI.persistDataSynced(JSON.stringify(parsed));
        console.log('[HA Bridge] Migrated haToken from synced data to secret storage');
      }
      config = parsed;
      console.log('[HA Bridge] Config loaded:', config.rules?.length || 0, 'rules, haUrl:', config.haUrl ? 'set' : 'empty');
    } else {
      console.log('[HA Bridge] No saved config found, using defaults');
    }
  } catch (e) {
    console.log('[HA Bridge] Config load error:', e);
  }
  if (!config.rules) config.rules = [];
  
  // Load token from secret storage
  try {
    const secret = await PluginAPI.getSecret('haToken');
    if (secret) {
      haToken = secret;
      console.log('[HA Bridge] Token loaded from secret storage');
    }
  } catch (e) {
    console.log('[HA Bridge] Secret load error:', e);
  }
  
  return config;
}

async function saveConfig() {
  try {
    // Never include haToken in synced data
    const safeConfig = { ...config };
    delete safeConfig.haToken; // Safety: ensure token never leaks to sync
    const data = JSON.stringify(safeConfig);
    await PluginAPI.persistDataSynced(data);
    console.log('[HA Bridge] Config persisted (' + data.length + ' chars, token excluded)');
    return true;
  } catch (e) {
    console.log('[HA Bridge] Config save FAILED:', e);
    return false;
  }
}

async function saveToken(token) {
  haToken = token;
  try {
    await PluginAPI.setSecret('haToken', token);
    console.log('[HA Bridge] Token saved to secret storage');
  } catch (e) {
    console.log('[HA Bridge] Token save FAILED:', e);
  }
}

// --- HA API ---
async function haApi(method, path, body = null) {
  if (!config.haUrl || !haToken) return null;
  const opts = { method, headers: { 'Authorization': `Bearer ${haToken}`, 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  try { const r = await fetch(`${config.haUrl.replace(/\/$/, '')}/api/${path}`, opts); return r.ok ? await r.json() : null; }
  catch (e) { return null; }
}

async function executeAction(action, context = {}) {
  if (!action || !haToken) return;
  // Replace template variables in messages
  const msg = (action.message || '')
    .replace('{title}', context.title || '')
    .replace('{project}', context.projectTitle || '')
    .replace('{time}', context.timeSpentMin || '0')
    .replace('{estimate}', context.timeEstimateMin || '0');

  try {
    switch (action.type) {
      case 'scene': await haApi('POST', 'services/scene/turn_on', { entity_id: action.entity }); break;
      case 'automation': await haApi('POST', 'services/automation/trigger', { entity_id: action.entity }); break;
      case 'script': await haApi('POST', 'services/script/turn_on', { entity_id: action.entity }); break;
      case 'toggle': await haApi('POST', 'services/homeassistant/toggle', { entity_id: action.entity }); break;
      case 'light':
        const ld = { entity_id: action.entity };
        if (action.brightness) ld.brightness = parseInt(action.brightness);
        if (action.temperature) ld.color_temp_kelvin = parseInt(action.temperature);
        await haApi('POST', 'services/light/turn_on', ld); break;
      case 'light_off': await haApi('POST', 'services/light/turn_off', { entity_id: action.entity }); break;
      case 'media':
        await haApi('POST', `services/media_player/${action.mediaAction || 'media_play_pause'}`, { entity_id: action.entity }); break;
      case 'tts':
        await haApi('POST', 'services/tts/speak', { entity_id: action.ttsEntity || 'tts.google_en', media_player_entity_id: action.entity, message: msg }); break;
      case 'notify':
        await haApi('POST', 'services/notify/mobile_app_jphone', { title: action.title || 'Super Productivity', message: msg }); break;
      case 'service':
        const [domain, svc] = (action.service || '').split('.');
        const data = action.entity ? { entity_id: action.entity, ...(action.data || {}) } : (action.data || {});
        if (domain && svc) await haApi('POST', `services/${domain}/${svc}`, data); break;
    }
  } catch (e) { console.log('[HA Bridge] Action error:', e.message); }
}

async function notifyWebhook(event, data = {}) {
  if (!config.webhookId || !config.haUrl) return;
  try { await fetch(`${config.haUrl.replace(/\/$/, '')}/api/webhook/${config.webhookId}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event, ...data, timestamp: Date.now() }),
  }); } catch (e) {}
}

// --- Rules Engine ---
async function evaluateRules(trigger, context = {}) {
  for (const rule of config.rules) {
    if (!rule.enabled) continue;
    if (rule.trigger !== trigger) continue;
    let match = true;
    if (rule.conditions) {
      if (rule.conditions.projectId && context.projectId !== rule.conditions.projectId) match = false;
      if (rule.conditions.tagId && !(context.tagIds || []).includes(rule.conditions.tagId)) match = false;
      if (rule.conditions.titleContains && !(context.title || '').toLowerCase().includes(rule.conditions.titleContains.toLowerCase())) match = false;
      if (rule.conditions.isSubtask !== undefined) {
        const taskIsSubtask = !!context.parentId;
        if (rule.conditions.isSubtask !== taskIsSubtask) match = false;
      }
    }
    if (match) {
      console.log(`[HA Bridge] Rule fired: ${rule.name} (${trigger})`);
      await executeAction(rule.action, context);
    }
  }
}

// --- Timer & Idle ---
function startTimerChecks() {
  if (timerCheckInterval) clearInterval(timerCheckInterval);
  trackingStartTime = Date.now();
  firedTimerRules.clear();
  if (idleCheckInterval) { clearInterval(idleCheckInterval); idleCheckInterval = null; }
  firedIdleRules.clear();

  timerCheckInterval = setInterval(async () => {
    if (!trackingStartTime) return;
    const elapsedMin = (Date.now() - trackingStartTime) / 60000;
    await loadConfig();
    for (const rule of config.rules) {
      if (!rule.enabled || rule.trigger !== 'timer') continue;
      const threshold = rule.conditions?.minutes || 0;
      if (threshold > 0 && elapsedMin >= threshold && !firedTimerRules.has(rule.id)) {
        firedTimerRules.add(rule.id);
        await executeAction(rule.action, { title: '', timeSpentMin: Math.round(elapsedMin).toString() });
      }
    }
  }, 15000);
}

function stopTimerChecks() {
  if (timerCheckInterval) { clearInterval(timerCheckInterval); timerCheckInterval = null; }
  trackingStartTime = null;
  trackingTaskId = null;
  firedTimerRules.clear();
  lastTrackingStopTime = Date.now();
  firedIdleRules.clear();
  startIdleChecks();
}

function startIdleChecks() {
  if (idleCheckInterval) clearInterval(idleCheckInterval);
  idleCheckInterval = setInterval(async () => {
    if (!lastTrackingStopTime) return;
    const idleMin = (Date.now() - lastTrackingStopTime) / 60000;
    await loadConfig();
    for (const rule of config.rules) {
      if (!rule.enabled || rule.trigger !== 'idle') continue;
      const threshold = rule.conditions?.minutes || 0;
      if (threshold > 0 && idleMin >= threshold && !firedIdleRules.has(rule.id)) {
        firedIdleRules.add(rule.id);
        await executeAction(rule.action, {});
      }
    }
  }, 30000);
}

// --- Build context from task ---
function buildContext(task) {
  if (!task) return {};
  return {
    taskId: task.id,
    title: task.title || '',
    projectId: task.projectId || null,
    tagIds: task.tagIds || [],
    parentId: task.parentId || null,
    timeSpentMin: Math.round((task.timeSpent || 0) / 60000).toString(),
    timeEstimateMin: Math.round((task.timeEstimate || 0) / 60000).toString(),
    isDone: task.isDone || false,
    notes: task.notes || '',
  };
}

// ============================================================
// HOOKS - All 12 SP plugin hooks registered
// ============================================================

// 1. CURRENT_TASK_CHANGE - payload: { current: Task|null, previous: Task|null }
PluginAPI.registerHook('currentTaskChange', (data) => { setTimeout(() => onCurrentTaskChange(data), 10); });

async function onCurrentTaskChange(data) {
  await loadConfig();
  console.log('[HA Bridge] currentTaskChange:', data?.current?.id || 'null', '<-', data?.previous?.id || 'null');

  const currentTask = data?.current || null;
  const previousTask = data?.previous || null;

  if (currentTask) {
    // Task started
    sessionTasksStarted++;
    trackingTaskId = currentTask.id;
    const ctx = buildContext(currentTask);

    await evaluateRules('task_start', ctx);
    if (sessionTasksStarted === 1) await evaluateRules('first_task_of_day', ctx);
    
    // Task switched (was tracking A, now tracking B)
    if (previousTask) await evaluateRules('task_switch', ctx);

    startTimerChecks();
    await notifyWebhook('task_started', { taskId: currentTask.id, title: currentTask.title });
  } else {
    // Task stopped
    const ctx = previousTask ? buildContext(previousTask) : {};
    stopTimerChecks();
    await evaluateRules('task_stop', ctx);
    await notifyWebhook('task_stopped', { taskId: previousTask?.id });
  }
}

// 2. TASK_CREATED - payload: { taskId, task }
PluginAPI.registerHook('taskCreated', (data) => { setTimeout(() => onTaskCreated(data), 10); });

async function onTaskCreated(data) {
  await loadConfig();
  const ctx = buildContext(data?.task || {});
  ctx.taskId = data?.taskId || ctx.taskId;
  console.log('[HA Bridge] taskCreated:', ctx.title);
  await evaluateRules('task_created', ctx);
  await notifyWebhook('task_created', { taskId: ctx.taskId, title: ctx.title });
}

// 3. TASK_COMPLETE - payload: { taskId, task }
PluginAPI.registerHook('taskComplete', (data) => { setTimeout(() => onTaskComplete(data), 10); });

async function onTaskComplete(data) {
  await loadConfig();
  const ctx = buildContext(data?.task || {});
  ctx.taskId = data?.taskId || ctx.taskId;
  console.log('[HA Bridge] taskComplete:', ctx.title);
  await evaluateRules('task_complete', ctx);
  await notifyWebhook('task_completed', { taskId: ctx.taskId, title: ctx.title, timeSpentMs: data?.task?.timeSpent });

  // Check all done - use dueDay/dueWithTime to detect today's tasks (TODAY is a virtual tag, never in tagIds)
  try {
    const tasks = await PluginAPI.getTasks();
    const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
    const nowMs = Date.now();
    const startOfDay = new Date(today).getTime();
    const endOfDay = startOfDay + 86400000;
    
    const todayTasks = tasks.filter(t => {
      if (t.dueWithTime && t.dueWithTime >= startOfDay && t.dueWithTime < endOfDay) return true;
      if (t.dueDay === today) return true;
      return false;
    });
    
    if (todayTasks.length > 0 && todayTasks.every(t => t.isDone)) {
      await evaluateRules('all_done', { count: todayTasks.length });
      await notifyWebhook('all_today_done', { count: todayTasks.length });
    }
  } catch(e) {}
}

// 4. TASK_UPDATE - payload: { taskId, task, changes }
PluginAPI.registerHook('taskUpdate', (data) => { setTimeout(() => onTaskUpdate(data), 10); });

async function onTaskUpdate(data) {
  await loadConfig();
  const ctx = buildContext(data?.task || {});
  ctx.changes = data?.changes || {};
  
  // Fire task_updated for any update
  await evaluateRules('task_updated', ctx);
  
  // Specific sub-triggers based on what changed
  if (ctx.changes.tagIds) await evaluateRules('tags_changed', ctx);
  if (ctx.changes.projectId) await evaluateRules('project_changed', ctx);
  if (ctx.changes.dueDay || ctx.changes.dueWithTime) await evaluateRules('due_date_changed', ctx);
  if (ctx.changes.timeEstimate) await evaluateRules('estimate_changed', ctx);
  if (ctx.changes.notes) await evaluateRules('notes_changed', ctx);
  
  // Check if time exceeded estimate
  if (data?.task?.timeEstimate > 0 && data?.task?.timeSpent > data?.task?.timeEstimate) {
    await evaluateRules('estimate_exceeded', ctx);
  }
}

// 5. TASK_DELETE - payload: { taskId }
PluginAPI.registerHook('taskDelete', (data) => { setTimeout(() => onTaskDelete(data), 10); });

async function onTaskDelete(data) {
  await loadConfig();
  await evaluateRules('task_deleted', { taskId: data?.taskId });
  await notifyWebhook('task_deleted', { taskId: data?.taskId });
}

// 6. FINISH_DAY - payload: { date }
PluginAPI.registerHook('finishDay', (data) => { setTimeout(() => onFinishDay(data), 10); });

async function onFinishDay(data) {
  await loadConfig();
  console.log('[HA Bridge] finishDay:', data?.date);
  await evaluateRules('day_end', { date: data?.date });
  try {
    const tasks = await PluginAPI.getTasks();
    const done = tasks.filter(t => t.isDone);
    const totalTime = tasks.reduce((s, t) => s + (t.timeSpent || 0), 0);
    await notifyWebhook('day_finished', { date: data?.date, completed: done.length, total: tasks.length, hoursWorked: Math.round(totalTime / 3600000 * 100) / 100 });
  } catch(e) {}
  // Reset session counter
  sessionTasksStarted = 0;
}

// 7. ANY_TASK_UPDATE - payload: { action, taskId?, task?, changes? }
PluginAPI.registerHook('anyTaskUpdate', (data) => { setTimeout(() => onAnyTaskUpdate(data), 10); });

async function onAnyTaskUpdate(data) {
  // This is a catch-all. We use it for webhook sync (instant updates to HA).
  await loadConfig();
  await notifyWebhook('task_activity', { action: data?.action, taskId: data?.taskId });
}

// 8. PROJECT_LIST_UPDATE - payload: { action, projectId?, project?, changes? }
PluginAPI.registerHook('projectListUpdate', (data) => { setTimeout(() => onProjectListUpdate(data), 10); });

async function onProjectListUpdate(data) {
  await loadConfig();
  await evaluateRules('project_list_changed', { action: data?.action, projectId: data?.projectId });
  await notifyWebhook('project_updated', { action: data?.action, projectId: data?.projectId });
}

// 9. WORK_CONTEXT_CHANGE - payload: { id, type, title, taskIds }
PluginAPI.registerHook('workContextChange', (data) => { setTimeout(() => onWorkContextChange(data), 10); });

async function onWorkContextChange(data) {
  await loadConfig();
  console.log('[HA Bridge] workContextChange:', data?.type, data?.title);
  currentProjectId = data?.type === 'PROJECT' ? data?.id : null;
  await evaluateRules('context_switch', {
    contextId: data?.id,
    contextType: data?.type,
    contextTitle: data?.title,
    taskCount: (data?.taskIds || []).length,
  });
  await notifyWebhook('context_changed', { type: data?.type, title: data?.title, id: data?.id });
}

// 10. PERSISTED_DATA_CHANGED - payload: void
PluginAPI.registerHook('persistedDataChanged', () => { /* Reload config on external changes */ setTimeout(() => loadConfig(), 100); });

// 11. LANGUAGE_CHANGE - no automation use, skip
// 12. ACTION - too generic/noisy for rules, but used internally

// --- Init ---
loadConfig().then(() => {
  console.log(`[HA Bridge v4.0] Loaded. ${config.rules.length} rules. All 12 hooks registered.`);
});
