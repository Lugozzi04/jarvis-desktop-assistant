function Automations() {
  return (
    <div>
      <h2 style={{ marginBottom: 20, fontSize: '1.5rem' }}>Automations</h2>
      <div className="empty-state">
        <h3>⚙️ Coming in M8</h3>
        <p>
          Automations will trigger actions based on events (time, app open, system events).
          Configure triggers, conditions, and actions from the UI.
        </p>
        <div style={{ marginTop: 20, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Planned features:
          <ul style={{ listStyle: 'none', marginTop: 8 }}>
            <li>• Time-based triggers (schedules)</li>
            <li>• App event triggers (opened, closed)</li>
            <li>• System event triggers (startup, idle)</li>
            <li>• Conditional logic (if X then Y)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default Automations;
