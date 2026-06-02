function Workflows() {
  return (
    <div>
      <h2 style={{ marginBottom: 20, fontSize: '1.5rem' }}>Workflows</h2>
      <div className="empty-state">
        <h3>🔄 Coming in M7</h3>
        <p>
          Workflows will allow you to chain multiple skill actions into automated sequences.
          Create, edit, and run multi-step workflows from the UI.
        </p>
        <div style={{ marginTop: 20, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Planned features:
          <ul style={{ listStyle: 'none', marginTop: 8 }}>
            <li>• Drag-and-drop workflow editor</li>
            <li>• Sequential & conditional steps</li>
            <li>• Workflow templates (streaming, study, dev)</li>
            <li>• Execution history and logs</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default Workflows;
