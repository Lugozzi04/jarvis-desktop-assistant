import { useState, useEffect } from 'react';

interface LLMStatus {
  provider: string;
  base_url?: string;
  model?: string;
  reachable?: boolean;
  model_available?: boolean;
  available_models?: string[];
  ready?: boolean;
  setup_required?: boolean;
  recommended_command?: string;
  recommended_models?: string[];
  error?: string;
}

interface RecommendedModels {
  primary: { name: string; command: string; description: string; size: string };
  fallback_light: { name: string; command: string; description: string; size: string };
  fallback_heavy: { name: string; command: string; description: string; size: string };
}

interface SetupGuide {
  title: string;
  steps: {
    step: number;
    title: string;
    description: string;
    commands: Record<string, string>;
  }[];
  alternative_models: { name: string; command: string; when: string }[];
}

function LLMSettings() {
  const [status, setStatus] = useState<LLMStatus | null>(null);
  const [recommended, setRecommended] = useState<RecommendedModels | null>(null);
  const [guide, setGuide] = useState<SetupGuide | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; error?: string; test_response?: string } | null>(null);
  const [activeTab, setActiveTab] = useState<'status' | 'setup'>('status');

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [statusRes, recRes, guideRes] = await Promise.all([
        fetch('http://localhost:8400/api/llm/status').then(r => r.json()),
        fetch('http://localhost:8400/api/llm/recommended').then(r => r.json()),
        fetch('http://localhost:8400/api/llm/ollama-setup-guide').then(r => r.json()),
      ]);
      setStatus(statusRes);
      setRecommended(recRes);
      setGuide(guideRes);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const resp = await fetch('http://localhost:8400/api/settings/llm/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: 'ollama' }),
      });
      setTestResult(await resp.json());
    } catch (err) {
      setTestResult({ success: false, error: err instanceof Error ? err.message : 'Error' });
    } finally {
      setTesting(false);
    }
  };

  const copyCommand = (cmd: string) => {
    navigator.clipboard.writeText(cmd).catch(() => {});
  };

  if (loading) return <div className="loading"><div className="spinner" /></div>;

  const ready = status?.ready ?? false;
  const reachable = status?.reachable ?? false;
  const modelAvailable = status?.model_available ?? false;

  return (
    <div>
      <h2 style={{ marginBottom: 20, fontSize: '1.5rem' }}>LLM Settings</h2>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 20 }}>
        <button
          className={`btn ${activeTab === 'status' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ borderRadius: 'var(--radius) 0 0 var(--radius)' }}
          onClick={() => setActiveTab('status')}
        >
          Status
        </button>
        <button
          className={`btn ${activeTab === 'setup' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ borderRadius: '0 var(--radius) var(--radius) 0' }}
          onClick={() => setActiveTab('setup')}
        >
          Setup Guide
        </button>
      </div>

      {activeTab === 'status' && (
        <>
          {/* Status Overview */}
          <div className="card-grid" style={{ marginBottom: 20 }}>
            <div className="card">
              <div className="stat-value">
                <span className={`status-dot ${ready ? 'online' : 'offline'}`} />
                {ready ? ' Ready' : reachable ? ' Model Missing' : ' Offline'}
              </div>
              <div className="stat-label">
                {!reachable && 'Ollama not reachable'}
                {reachable && !modelAvailable && 'Model not pulled'}
                {ready && 'Fully operational'}
              </div>
            </div>
            <div className="card">
              <div className="stat-value">{status?.provider || 'none'}</div>
              <div className="stat-label">Provider — {status?.model || 'no model'}</div>
            </div>
            <div className="card">
              <div className="stat-value">{status?.available_models?.length ?? 0}</div>
              <div className="stat-label">Models Available</div>
            </div>
          </div>

          {/* Status Details */}
          {status && (
            <div className="card" style={{ maxWidth: 700, marginBottom: 20 }}>
              <div className="card-header">Connection Details</div>
              <div style={{ fontSize: '0.85rem', display: 'grid', gap: 8 }}>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Base URL: </span>
                  <code style={{ background: 'var(--bg-primary)', padding: '2px 8px', borderRadius: 4 }}>
                    {status.base_url || 'http://localhost:11434'}
                  </code>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Reachable: </span>
                  <span style={{ color: status.reachable ? 'var(--success)' : 'var(--danger)' }}>
                    {status.reachable ? 'Yes' : 'No'}
                  </span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Model Available: </span>
                  <span style={{ color: status.model_available ? 'var(--success)' : 'var(--warning)' }}>
                    {status.model_available ? 'Yes' : 'No'}
                  </span>
                </div>
                {status.available_models && status.available_models.length > 0 && (
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Installed Models: </span>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                      {status.available_models.map(m => (
                        <span key={m} className="badge badge-info" style={{ fontSize: '0.75rem' }}>
                          {m}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {status.error && (
                  <div style={{
                    padding: '8px 12px',
                    background: 'rgba(239,68,68,0.08)',
                    border: '1px solid rgba(239,68,68,0.2)',
                    borderRadius: 'var(--radius)',
                    color: 'var(--danger)',
                    fontSize: '0.85rem',
                  }}>
                    {status.error}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Recommended command if needed */}
          {status?.recommended_command && (
            <div className="card" style={{
              maxWidth: 700,
              marginBottom: 20,
              borderColor: 'var(--warning)',
              background: 'rgba(245,158,11,0.05)',
            }}>
              <div className="card-header">⚡ Action Required</div>
              <p style={{ fontSize: '0.85rem', marginBottom: 12, color: 'var(--text-secondary)' }}>
                Run this command on your <strong>local PC</strong> (not the server):
              </p>
              <div style={{
                display: 'flex', gap: 8, alignItems: 'center',
                background: 'var(--bg-primary)', padding: '10px 14px',
                borderRadius: 'var(--radius)', fontFamily: 'monospace', fontSize: '0.9rem',
              }}>
                <code style={{ flex: 1 }}>{status.recommended_command}</code>
                <button
                  className="btn btn-sm btn-secondary"
                  onClick={() => copyCommand(status.recommended_command || '')}
                >
                  📋 Copy
                </button>
              </div>
            </div>
          )}

          {/* Recommended Models */}
          {recommended && (
            <div className="card" style={{ maxWidth: 700, marginBottom: 20 }}>
              <div className="card-header">Recommended Models</div>
              <div style={{ fontSize: '0.85rem' }}>
                {[
                  { ...recommended.primary, tag: 'PRIMARY', badge: 'badge-success' },
                  { ...recommended.fallback_light, tag: 'LIGHT', badge: 'badge-info' },
                  { ...recommended.fallback_heavy, tag: 'HEAVY', badge: 'badge-warning' },
                ].map(m => (
                  <div key={m.name} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '10px 0', borderBottom: '1px solid var(--border)',
                  }}>
                    <div>
                      <div style={{ fontWeight: 500 }}>
                        {m.name}
                        <span className={`badge ${m.badge}`} style={{ marginLeft: 8, fontSize: '0.65rem' }}>
                          {m.tag}
                        </span>
                      </div>
                      <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                        {m.description} · {m.size}
                      </div>
                    </div>
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => copyCommand(m.command)}
                      title="Copy pull command"
                    >
                      📋
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Test Connection */}
          <div style={{ maxWidth: 700 }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <button
                className="btn btn-primary"
                onClick={testConnection}
                disabled={testing}
              >
                {testing ? 'Testing...' : '🔌 Test Connection'}
              </button>
              <button className="btn btn-secondary" onClick={loadAll}>
                🔄 Refresh Status
              </button>
            </div>

            {testResult && (
              <div className="card" style={{
                marginTop: 12,
                background: testResult.success ? 'rgba(34,197,94,0.06)' : 'rgba(239,68,68,0.06)',
                border: `1px solid ${testResult.success ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
              }}>
                <div className="card-header">Test Result</div>
                <div style={{ fontSize: '0.85rem' }}>
                  {testResult.success && <div style={{ color: 'var(--success)' }}>✅ Connection successful</div>}
                  {testResult.test_response && (
                    <div style={{ marginTop: 8, padding: '8px 12px', background: 'var(--bg-primary)', borderRadius: 'var(--radius)' }}>
                      Response: {testResult.test_response}
                    </div>
                  )}
                  {testResult.error && (
                    <div style={{ color: 'var(--danger)', marginTop: 4 }}>{testResult.error}</div>
                  )}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {activeTab === 'setup' && guide && (
        <div style={{ maxWidth: 700 }}>
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">{guide.title}</div>
            <div style={{ fontSize: '0.85rem' }}>
              {guide.steps.map(s => (
                <div key={s.step} style={{
                  padding: '12px 0', borderBottom: '1px solid var(--border)',
                }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>
                    Step {s.step}: {s.title}
                  </div>
                  <p style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>
                    {s.description}
                  </p>
                  {Object.entries(s.commands).map(([os, cmd]) => (
                    <div key={os} style={{
                      display: 'flex', gap: 8, alignItems: 'center',
                      background: 'var(--bg-primary)', padding: '6px 12px',
                      borderRadius: 'var(--radius)', marginBottom: 4,
                      fontFamily: 'monospace', fontSize: '0.8rem',
                    }}>
                      <span style={{ color: 'var(--text-muted)', minWidth: 60, fontSize: '0.7rem' }}>
                        {os === 'all' ? 'ALL' : os.toUpperCase()}:
                      </span>
                      <code style={{ flex: 1 }}>{cmd}</code>
                      <button
                        className="btn btn-sm btn-secondary"
                        style={{ padding: '2px 8px', fontSize: '0.7rem' }}
                        onClick={() => copyCommand(cmd)}
                      >
                        📋
                      </button>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-header">Alternative Models</div>
            <div style={{ fontSize: '0.85rem' }}>
              {guide.alternative_models.map(m => (
                <div key={m.name} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '10px 0', borderBottom: '1px solid var(--border)',
                }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>{m.name}</div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{m.when}</div>
                  </div>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => copyCommand(m.command)}
                  >
                    📋 Copy
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginTop: 20, textAlign: 'center' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Setup scripts are also available in the <code>scripts/</code> directory:
            </p>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap', marginTop: 8 }}>
              {['setup_ollama_linux.sh', 'setup_ollama_windows.ps1', 'setup_ollama_macos.sh', 'check_ollama.py'].map(s => (
                <code key={s} style={{
                  background: 'var(--bg-primary)', padding: '4px 10px',
                  borderRadius: 'var(--radius)', fontSize: '0.75rem',
                }}>
                  scripts/{s}
                </code>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default LLMSettings;
