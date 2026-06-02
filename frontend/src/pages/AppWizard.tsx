import { useState, useEffect } from 'react';

const API = 'http://localhost:8400';

interface DetectedApp {
  name: string;
  command: string;
  path: string;
  category: string;
  aliases: string[];
  builtin: boolean;
  detected: boolean;
}

interface ConfiguredApp {
  name: string;
  command: string;
  path: string;
  aliases: string[];
  enabled: boolean;
  builtin: boolean;
  detected: boolean;
}

function AppWizard() {
  const [configured, setConfigured] = useState<ConfiguredApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [message, setMessage] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [newApp, setNewApp] = useState({ name: '', command: '', aliases: '' });

  useEffect(() => { loadApps(); }, []);

  const loadApps = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/apps`);
      const data = await res.json();
      setConfigured(data.apps || []);
    } catch (err) {
      setMessage('Failed to load apps');
    } finally {
      setLoading(false);
    }
  };

  const handleScan = async () => {
    setScanning(true);
    setMessage('Scanning for installed apps...');
    try {
      const res = await fetch(`${API}/api/apps/import`, { method: 'POST' });
      const data = await res.json();
      setConfigured(data.apps || []);
      setMessage(`✅ Found ${data.total} apps, imported ${data.imported} new ones`);
    } catch (err) {
      setMessage('❌ Scan failed');
    } finally {
      setScanning(false);
    }
  };

  const handleToggle = async (name: string, enabled: boolean) => {
    try {
      await fetch(`${API}/api/apps/${encodeURIComponent(name)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !enabled }),
      });
      setConfigured(prev =>
        prev.map(a => a.name === name ? { ...a, enabled: !enabled } : a)
      );
    } catch (err) {
      setMessage('Failed to update app');
    }
  };

  const handleUpdateCommand = async (name: string, command: string) => {
    try {
      await fetch(`${API}/api/apps/${encodeURIComponent(name)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command }),
      });
      setConfigured(prev =>
        prev.map(a => a.name === name ? { ...a, command, path: command } : a)
      );
      setMessage('✅ Path updated');
    } catch (err) {
      setMessage('Failed to update path');
    }
  };

  const handleDelete = async (name: string) => {
    try {
      await fetch(`${API}/api/apps/${encodeURIComponent(name)}`, { method: 'DELETE' });
      setConfigured(prev => prev.filter(a => a.name !== name));
      setMessage('🗑️ App removed');
    } catch (err) {
      setMessage('Failed to remove app');
    }
  };

  const handleAdd = async () => {
    if (!newApp.name || !newApp.command) return;
    try {
      const res = await fetch(`${API}/api/apps`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newApp.name,
          command: newApp.command,
          aliases: newApp.aliases ? newApp.aliases.split(',').map(s => s.trim()) : undefined,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setConfigured(prev => [...prev, { ...data.app, enabled: true, builtin: false, detected: true }]);
        setNewApp({ name: '', command: '', aliases: '' });
        setShowAddForm(false);
        setMessage('✅ App added');
      }
    } catch (err) {
      setMessage('Failed to add app');
    }
  };

  const enabledCount = configured.filter(a => a.enabled).length;
  const detectedCount = configured.filter(a => a.detected).length;

  if (loading) return <div className="loading"><div className="spinner" /></div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', margin: 0 }}>⚡ App Setup Wizard</h2>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: 4 }}>
            {enabledCount}/{configured.length} apps enabled · {detectedCount} detected
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn btn-primary"
            onClick={handleScan}
            disabled={scanning}
          >
            {scanning ? '🔍 Scanning...' : '🔍 Scan for Apps'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => setShowAddForm(!showAddForm)}
          >
            ➕ Add Custom App
          </button>
        </div>
      </div>

      {message && (
        <div className="card" style={{
          marginBottom: 12,
          padding: '8px 16px',
          background: message.startsWith('✅') ? 'var(--success-bg, #e8f5e9)' : 'var(--warning-bg, #fff3e0)',
          color: message.startsWith('✅') ? 'var(--success)' : 'var(--warning)',
          fontSize: '0.9rem',
        }}>
          {message}
        </div>
      )}

      {/* Add Custom App Form */}
      {showAddForm && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">➕ Add Custom Application</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={{ fontSize: '0.85rem', fontWeight: 500, marginBottom: 4, display: 'block' }}>App Name</label>
              <input
                type="text"
                placeholder="e.g., My Custom App"
                value={newApp.name}
                onChange={e => setNewApp({ ...newApp, name: e.target.value })}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.85rem', fontWeight: 500, marginBottom: 4, display: 'block' }}>Command / Path</label>
              <input
                type="text"
                placeholder="e.g., C:\\Program Files\\MyApp\\app.exe"
                value={newApp.command}
                onChange={e => setNewApp({ ...newApp, command: e.target.value })}
              />
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
                Full path to the .exe or a command on PATH
              </div>
            </div>
            <div>
              <label style={{ fontSize: '0.85rem', fontWeight: 500, marginBottom: 4, display: 'block' }}>Aliases (comma-separated)</label>
              <input
                type="text"
                placeholder="e.g., myapp, custom, ma"
                value={newApp.aliases}
                onChange={e => setNewApp({ ...newApp, aliases: e.target.value })}
              />
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
                Words you can use with /open (e.g., /open myapp)
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary" onClick={handleAdd}>✅ Add App</button>
              <button className="btn btn-secondary" onClick={() => setShowAddForm(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* App List */}
      <div className="card-grid">
        {configured.map(app => (
          <div
            key={app.name}
            className="card"
            style={{
              opacity: app.enabled ? 1 : 0.5,
              borderLeft: app.enabled ? '3px solid var(--success)' : '3px solid var(--border)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: 4 }}>
                  {app.builtin ? '⚙️ ' : app.detected ? '✅ ' : '❓ '}
                  {app.name}
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', wordBreak: 'break-all' }}>
                  {app.path || app.command || 'no path'}
                </div>
                {app.aliases?.length > 0 && (
                  <div style={{ fontSize: '0.72rem', color: 'var(--accent)', marginTop: 4 }}>
                    Aliases: /open {app.aliases.slice(0, 5).join(', /open ')}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: '0.85rem' }}>
                  <input
                    type="checkbox"
                    checked={app.enabled}
                    onChange={() => handleToggle(app.name, app.enabled)}
                    style={{ width: 18, height: 18 }}
                  />
                  {app.enabled ? 'Enabled' : 'Disabled'}
                </label>
                {!app.builtin && (
                  <button
                    className="btn btn-sm btn-secondary"
                    style={{ fontSize: '0.75rem', padding: '2px 8px' }}
                    onClick={() => {
                      const newCmd = prompt('Enter new path/command:', app.command);
                      if (newCmd && newCmd !== app.command) {
                        handleUpdateCommand(app.name, newCmd);
                      }
                    }}
                  >
                    ✏️ Edit Path
                  </button>
                )}
                {!app.builtin && (
                  <button
                    className="btn btn-sm btn-danger"
                    style={{ fontSize: '0.75rem', padding: '2px 8px' }}
                    onClick={() => handleDelete(app.name)}
                  >
                    🗑️
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {configured.length === 0 && (
        <div className="empty-state">
          <h3>No apps configured</h3>
          <p>Click "Scan for Apps" to detect installed applications, or add custom ones manually.</p>
        </div>
      )}

      {/* Instructions */}
      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">📖 How to use /open</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
          <p>After configuring apps, open them via chat with:</p>
          <ul style={{ paddingLeft: 20 }}>
            <li><code>/open discord</code> — opens Discord</li>
            <li><code>/open spotify</code> — opens Spotify</li>
            <li><code>/open calc</code> — opens Calculator (alias)</li>
            <li><code>/open vscode</code> — opens VS Code</li>
          </ul>
          <p style={{ marginTop: 10 }}>
            <strong>Tip:</strong> If an app doesn't open, use "Edit Path" to set the correct
            executable location. JARVIS will remember it.
          </p>
        </div>
      </div>
    </div>
  );
}

export default AppWizard;
