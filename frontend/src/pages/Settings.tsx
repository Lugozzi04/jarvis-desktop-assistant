import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { SettingsInfo } from '../api';

function Settings() {
  const [settings, setSettings] = useState<SettingsInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.settings().then(s => { setSettings(s); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading"><div className="spinner" /></div>;
  if (!settings) return <div className="empty-state"><h3>Error</h3><p>Could not load settings</p></div>;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <h2 style={{ fontSize: '1.5rem', margin: 0 }}>Settings</h2>
        <Link to="/setup">
          <button className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            🚀 Open Setup Wizard
          </button>
        </Link>
      </div>

      <div className="card-grid">
        <div className="card">
          <div className="card-header">General</div>
          <div className="form-group">
            <label>Environment</label>
            <input type="text" value={settings.env} readOnly />
          </div>
          <div className="form-group">
            <label>Log Level</label>
            <input type="text" value={settings.log_level} readOnly />
          </div>
        </div>

        <div className="card">
          <div className="card-header">LLM Configuration</div>
          <div className="form-group">
            <label>Provider</label>
            <input type="text" value={settings.llm.default_provider} readOnly />
          </div>
          <div className="form-group">
            <label>Model</label>
            <input type="text" value={settings.llm.default_model} readOnly />
          </div>
          <div className="form-group">
            <label>API Key</label>
            <input type="text" value={settings.llm.has_api_key ? '••••••••' : 'Not set'} readOnly />
          </div>
          <div className="form-group">
            <label>Cloud LLM</label>
            <input type="text" value={settings.llm.allow_cloud ? 'Allowed' : 'Blocked'} readOnly />
          </div>
          <Link to="/settings/llm">
            <button className="btn btn-primary" style={{ marginTop: 8 }}>Configure LLM</button>
          </Link>
        </div>

        <div className="card">
          <div className="card-header">Appearance</div>
          <div className="form-group">
            <label>Theme</label>
            <input type="text" value="Dark (default)" readOnly />
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 10 }}>
            Theme customization coming in a future release.
          </p>
        </div>

        <div className="card">
          <div className="card-header">About</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            <p><strong>JARVIS Desktop Assistant</strong></p>
            <p style={{ marginTop: 8 }}>Modular AI desktop assistant with skills, workflows, automations, and voice.</p>
            <p style={{ marginTop: 8, color: 'var(--text-muted)' }}>
              Backend: FastAPI · Frontend: React/Vite/TypeScript · DB: SQLite
            </p>
          </div>
          <Link to="/setup">
            <button className="btn btn-secondary" style={{ marginTop: 12, width: '100%' }}>
              🔧 Re-run Setup Wizard
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default Settings;
