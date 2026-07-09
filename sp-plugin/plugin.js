/**
 * Home Assistant Bridge - Super Productivity Plugin
 *
 * This plugin registers hooks and UI elements in SP to provide
 * visibility into the HA connection and push instant updates
 * to Home Assistant when tasks change.
 */

// HA webhook configuration
// Users should update this to match their HA setup
const HA_CONFIG = {
  // Set these in the plugin config or manually here:
  baseUrl: 'http://homeassistant.local:8123',
  webhookId: null, // Will be set from config or auto-detected
};

// Notify HA of changes via webhook (instant update, no 30s wait)
async function notifyHA(event, data) {
  if (!HA_CONFIG.webhookId) {
    console.log('[HA Bridge] No webhook configured - HA will poll in ~30s');
    return;
  }
  try {
    const url = `${HA_CONFIG.baseUrl}/api/webhook/${HA_CONFIG.webhookId}`;
    await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event, ...data }),
    });
    console.log(`[HA Bridge] Notified HA: ${event}`);
  } catch (e) {
    // Silently fail - HA will still pick up changes on next poll
    console.log(`[HA Bridge] Could not notify HA (will poll): ${e.message}`);
  }
}

// Load config
async function loadConfig() {
  try {
    const config = await PluginAPI.getConfig();
    if (config) {
      if (config.haUrl) HA_CONFIG.baseUrl = config.haUrl;
      if (config.webhookId) HA_CONFIG.webhookId = config.webhookId;
    }
  } catch (e) {
    // Config not set yet - that's fine
  }
}

// Register header button showing HA status
PluginAPI.registerHeaderButton({
  label: 'Home Assistant',
  icon: 'home',
  onClick: async () => {
    const tasks = await PluginAPI.getTasks();
    const todayTasks = tasks.filter(t => !t.isDone);

    const webhookStatus = HA_CONFIG.webhookId
      ? `<p><strong>Webhook:</strong> Active (instant updates)</p>`
      : `<p><strong>Webhook:</strong> Not configured (30s polling)</p>
         <p style="font-size:0.8em; opacity:0.7;">To enable instant updates, set your HA webhook ID in the plugin config.</p>`;

    PluginAPI.openDialog({
      title: 'Home Assistant Bridge',
      htmlContent: `
        <div style="padding: 8px 0;">
          <p><strong>REST API:</strong> Active (port 3876)</p>
          ${webhookStatus}
          <hr style="margin: 12px 0; opacity: 0.3;">
          <p><strong>Active Tasks:</strong> ${tasks.length}</p>
          <p><strong>Pending Today:</strong> ${todayTasks.length}</p>
          <hr style="margin: 12px 0; opacity: 0.3;">
          <p style="font-size: 0.85em; opacity: 0.7;">
            HA integration: Settings > Devices & Services > Super Productivity
          </p>
        </div>
      `,
      buttons: [{ label: 'OK' }],
    });
  },
});

// Register hook: when a task is completed
PluginAPI.registerHook('taskComplete', async (taskId) => {
  console.log(`[HA Bridge] Task completed: ${taskId}`);
  await notifyHA('task_completed', { taskId });
});

// Register hook: when current task changes (start/stop tracking)
PluginAPI.registerHook('currentTaskChange', async (data) => {
  console.log('[HA Bridge] Current task changed:', data);
  await notifyHA('task_changed', { data });
});

// Register hook: end of day
PluginAPI.registerHook('finishDay', async () => {
  console.log('[HA Bridge] Day finished');
  await notifyHA('day_finished', {});
});

// Menu entry
PluginAPI.registerMenuEntry({
  label: 'HA Bridge Status',
  icon: 'home',
  onClick: async () => {
    const status = HA_CONFIG.webhookId ? 'Active (instant)' : 'Polling (30s)';
    PluginAPI.showSnack({
      msg: `HA Bridge: REST API active | Updates: ${status}`,
      type: 'SUCCESS',
    });
  },
});

// Initialize
loadConfig();
console.log('[HA Bridge] Plugin loaded. Home Assistant integration is active.');
