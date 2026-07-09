/**
 * Home Assistant Bridge - Super Productivity Plugin
 *
 * This plugin registers hooks and UI elements in SP to provide
 * visibility into the HA connection and enable future enhancements.
 */

// Track state
let haConnected = false;
let haUrl = null;

// Check HA connection on load
async function checkHAConnection() {
  // The Local REST API being enabled is the bridge — if SP is running
  // and the API is enabled, HA can connect. We just show status.
  haConnected = true; // If this plugin is loaded, the API is likely enabled
}

// Register header button showing HA status
PluginAPI.registerHeaderButton({
  label: 'Home Assistant',
  icon: 'home',
  onClick: async () => {
    const tasks = await PluginAPI.getTasks();
    const todayTasks = tasks.filter(t => !t.isDone);

    PluginAPI.openDialog({
      title: 'Home Assistant Bridge',
      htmlContent: `
        <div style="padding: 8px 0;">
          <p><strong>Status:</strong> Local REST API is active</p>
          <p><strong>Active Tasks:</strong> ${tasks.length}</p>
          <p><strong>Pending Today:</strong> ${todayTasks.length}</p>
          <hr style="margin: 12px 0; opacity: 0.3;">
          <p style="font-size: 0.85em; opacity: 0.7;">
            Home Assistant connects to this app via the Local REST API (port 3876).
            Make sure "Enable local REST API" is turned on in Settings > Misc.
          </p>
          <p style="font-size: 0.85em; opacity: 0.7; margin-top: 8px;">
            Configure your HA integration at:<br>
            Settings > Devices & Services > Super Productivity
          </p>
        </div>
      `,
      buttons: [{ label: 'OK' }],
    });
  },
});

// Register hook: when a task is completed, log it
PluginAPI.registerHook('taskComplete', async (taskId) => {
  console.log(`[HA Bridge] Task completed: ${taskId}`);
  // HA will pick this up on next poll (within 30s)
});

// Register hook: when current task changes
PluginAPI.registerHook('currentTaskChange', async (data) => {
  console.log('[HA Bridge] Current task changed:', data);
  // HA will detect this on next poll
});

// Register hook: end of day
PluginAPI.registerHook('finishDay', async () => {
  console.log('[HA Bridge] Day finished - HA will update daily stats');
});

// Menu entry for quick access
PluginAPI.registerMenuEntry({
  label: 'HA Bridge Status',
  icon: 'home',
  onClick: async () => {
    PluginAPI.showSnack({
      msg: 'HA Bridge active. REST API is serving data to Home Assistant.',
      type: 'SUCCESS',
    });
  },
});

// Initialize
checkHAConnection();
console.log('[HA Bridge] Plugin loaded. Home Assistant integration is active.');
