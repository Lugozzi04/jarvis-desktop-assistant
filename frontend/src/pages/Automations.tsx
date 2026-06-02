import { useEffect, useState } from 'react';

const API = 'http://localhost:8400/api';

interface AutoSummary {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger_type: string;
  action_count: number;
  last_run_at: string | null;
  last_status: string | null;
  run_count: number;
}

interface AutoDetail {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger: { type: string; config: Record<string, unknown> };
  conditions: { type: string; config: Record<string, unknown> }[];
  actions: { type: string; skill?: string; action?: string; workflow_id?: string; parameters: Record<string, string> }[];
  created_at: string;
  last_run_at: string | null;
  run_count: number;
  last_status: string | null;
}

interface EngineStatus {
  running: boolean;
  loaded_automations: number;
  enabled_automations: number;
  last_tick: string | null;
  errors: string[];
}

interface RunResult {
  automation_id: string;
  automation_name: string;
  status: string;
  triggered_by: string;
  conditions: { type: string; status: string; message: string }[];
  actions: { index: number; type: string; status: string; result?: unknown; error?: string }[];
  error: string | null;
  total_duration_ms: number;
}

const PRESETS: { label: string; json: string }[] = [
  {
    label: 'Daily Reminder',
    json: JSON.stringify({
      name: 'Daily Reminder',
      description: 'Remind me every day at a specific time',
      enabled: false,
      trigger: { type: 'time', config: { time: '09:00', days: ['mon','tue','wed','thu','fri'] } },
      conditions: [],
      actions: [{ type: 'notification', parameters: { message: '⏰ Time for your daily task!' }, risk: 'safe' }],
    }, null, 2),
  },
  {
    label: 'Interval Reminder',
    json: JSON.stringify({
      name: 'Interval Reminder',
      description: 'Periodic reminder',
      enabled: false,
      trigger: { type: 'interval', config: { interval_minutes: 30 } },
      conditions: [],
      actions: [{ type: 'notification', parameters: { message: '🔔 Periodic check-in!' }, risk: 'safe' }],
    }, null, 2),
  },
  {
    label: 'Run Workflow on Startup',
    json: JSON.stringify({
      name: 'Startup Workflow',
      description: 'Run a workflow when Jarvis starts',
      enabled: true,
      trigger: { type: 'startup', config: {} },
      conditions: [],
      actions: [{ type: 'workflow', workflow_id: 'dev-session', parameters: {}, risk: 'safe' }],
    }, null, 2),
  },
  {
    label: 'Manual Workflow',
    json: JSON.stringify({
      name: 'Manual Workflow',
      description: 'Run workflow manually',
      enabled: true,
      trigger: { type: 'manual', config: {} },
      conditions: [],
      actions: [{ type: 'workflow', workflow_id: 'study-session', parameters: {}, risk: 'safe' }],
    }, null, 2),
  },
];

function Automations() {
  const [autos, setAutos] = useState<AutoSummary[]>([]);
  const [selected, setSelected] = useState<AutoDetail | null>(null);
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [engineStatus, setEngineStatus] = useState<EngineStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [running, setRunning] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    try {
      const [aRes, eRes] = await Promise.all([
        fetch(`${API}/automations`).then(r => r.json()),
        fetch(`${API}/automations/engine/status`).then(r => r.json()),
      ]);
      setAutos(aRes.automations || []);
      setEngineStatus(eRes);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
      setLoading(false);
    }
  };

  const loadDetail = async (id: string) => {
    try {
      const res = await fetch(`${API}/automations/${id}`);
      const data = await res.json();
      if (!data.error) setSelected(data);
    } catch { /* ignore */ }
  };

  const runAutomation = async (id: string) => {
    setRunning(true);
    setRunResult(null);
    try {
      const res = await fetch(`${API}/automations/${id}/run`, { method: 'POST' });
      setRunResult(await res.json());
    } catch (err) {
      setRunResult({ automation_id: id, automation_name: id, status: 'error', triggered_by: 'manual', conditions: [], actions: [], error: String(err), total_duration_ms: 0 });
    } finally {
      setRunning(false);
    }
  };

  const toggleEnabled = async (id: string, enabled: boolean) => {
    const ep = enabled ? 'disable' : 'enable';
    await fetch(`${API}/automations/${id}/${ep}`, { method: 'POST' });
    loadAll();
    if (selected?.id === id) loadDetail(id);
  };

  const deleteAuto = async (id: string) => {
    await fetch(`${API}/automations/${id}`, { method: 'DELETE' });
    loadAll();
    if (selected?.id === id) { setSelected(null); setRunResult(null); }
  };

  const statusBadge = (s: string | null) => {
    if (!s) return <span className="badge badge-info">—</span>;
    const map: Record<string, string> = { success: 'badge-success', partial: 'badge-warning', failed: 'badge-danger', skipped: 'badge-warning', skipped_requires_confirmation: 'badge-warning' };
    return <span className={`badge ${map[s] || 'badge-info'}`}>{s}</span>;
  };

  if (loading) return <div className="loading"><div className="spinner" /></div>;
  if (error) return <div className="empty-state"><h3>Error</h3><p>{error}</p></div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ fontSize: '1.5rem', margin: 0 }}>Automations ({autos.length})</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary btn-sm" onClick={loadAll}>🔄 Refresh</button>
          <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
            {showCreate ? 'Cancel' : '+ New'}
          </button>
        </div>
      </div>

      {/* Engine Status */}
      {engineStatus && (
        <div className="card" style={{ marginBottom: 16, padding: '12px 16px', display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap', fontSize: '0.85rem' }}>
          <div><span className={`status-dot ${engineStatus.running ? 'online' : 'offline'}`} /> Scheduler: <strong>{engineStatus.running ? 'Running' : 'Stopped'}</strong></div>
          <div>Loaded: <strong>{engineStatus.loaded_automations}</strong></div>
          <div>Enabled: <strong>{engineStatus.enabled_automations}</strong></div>
          {engineStatus.last_tick && <div>Last tick: <strong>{new Date(engineStatus.last_tick).toLocaleTimeString()}</strong></div>}
          {engineStatus.errors.length > 0 && (
            <div style={{ color: 'var(--danger)' }}>⚠ {engineStatus.errors.length} error{engineStatus.errors.length > 1 ? 's' : ''}</div>
          )}
        </div>
      )}

      {showCreate && <CreateForm onDone={() => { setShowCreate(false); loadAll(); }} />}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {autos.map(auto => (
            <div
              key={auto.id}
              className="card"
              style={{
                cursor: 'pointer', padding: 12,
                borderColor: selected?.id === auto.id ? 'var(--accent)' : 'var(--border)',
                opacity: auto.enabled ? 1 : 0.65,
              }}
              onClick={() => loadDetail(auto.id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                    {auto.enabled ? '🟢' : '⚫'} {auto.name}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {auto.trigger_type} · {auto.action_count} action{auto.action_count !== 1 ? 's' : ''}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  {statusBadge(auto.last_status)}
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 2 }}>
                    {auto.run_count} run{auto.run_count !== 1 ? 's' : ''}
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                <button className="btn btn-primary btn-sm" onClick={e => { e.stopPropagation(); runAutomation(auto.id); }} disabled={running}>▶ Run</button>
                <button className="btn btn-secondary btn-sm" onClick={e => { e.stopPropagation(); toggleEnabled(auto.id, auto.enabled); }}>
                  {auto.enabled ? 'Disable' : 'Enable'}
                </button>
                <button className="btn btn-secondary btn-sm" onClick={e => { e.stopPropagation(); deleteAuto(auto.id); }}>🗑</button>
              </div>
            </div>
          ))}
        </div>

        {/* Detail + Run Result */}
        <div>
          {selected && (
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="card-header">{selected.name}</div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 10 }}>{selected.description}</p>

              <div style={{ fontSize: '0.8rem', marginBottom: 10 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Trigger</div>
                <div style={{ color: 'var(--accent)' }}>{selected.trigger?.type}</div>
                <pre style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2, background: 'var(--bg-primary)', padding: '4px 8px', borderRadius: 4, overflow: 'auto' }}>
                  {JSON.stringify(selected.trigger?.config, null, 2)}
                </pre>
              </div>

              {selected.conditions?.length > 0 && (
                <div style={{ fontSize: '0.8rem', marginBottom: 10 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>Conditions ({selected.conditions.length})</div>
                  {selected.conditions.map((c, i) => (
                    <div key={i} style={{ color: 'var(--text-secondary)' }}>{c.type}: {JSON.stringify(c.config)}</div>
                  ))}
                </div>
              )}

              <div style={{ fontSize: '0.8rem', marginBottom: 10 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Actions ({selected.actions?.length})</div>
                {selected.actions?.map((a, i) => (
                  <div key={i} style={{ color: 'var(--text-secondary)', padding: '2px 0' }}>
                    {a.type}: {a.skill ? `${a.skill}.${a.action}` : a.workflow_id ? `workflow:${a.workflow_id}` : JSON.stringify(a.parameters)}
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', gap: 6 }}>
                <button className="btn btn-primary btn-sm" onClick={() => runAutomation(selected.id)} disabled={running}>▶ Run</button>
                <button className="btn btn-secondary btn-sm" onClick={() => toggleEnabled(selected.id, selected.enabled)}>
                  {selected.enabled ? 'Disable' : 'Enable'}
                </button>
              </div>
            </div>
          )}

          {runResult && (
            <div className="card" style={{
              borderColor: runResult.status === 'success' ? 'var(--success)' : runResult.status === 'partial' ? 'var(--warning)' : 'var(--danger)',
            }}>
              <div className="card-header">
                Run: {runResult.status?.toUpperCase()}
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: 8 }}>
                  {runResult.total_duration_ms?.toFixed(0)}ms · {runResult.triggered_by}
                </span>
              </div>
              <div style={{ fontSize: '0.8rem' }}>
                {runResult.conditions?.length > 0 && runResult.conditions.map((c, i) => (
                  <div key={i} style={{ color: c.status === 'passed' ? 'var(--success)' : 'var(--danger)' }}>
                    {c.status === 'passed' ? '✅' : '❌'} Condition: {c.type} — {c.message}
                  </div>
                ))}
                {runResult.actions?.map(a => (
                  <div key={a.index} style={{ padding: '2px 0' }}>
                    <span>{a.status === 'success' ? '✅' : a.status === 'failed' ? '❌' : '⏭️'}</span>
                    <span style={{ marginLeft: 6 }}>Action {a.index}: {a.type}</span>
                    {a.error && <span style={{ color: 'var(--danger)', marginLeft: 6, fontSize: '0.75rem' }}>{a.error}</span>}
                  </div>
                ))}
              </div>
              {runResult.error && (
                <div style={{ marginTop: 8, padding: '6px 10px', background: 'rgba(239,68,68,0.08)', borderRadius: 'var(--radius)', color: 'var(--danger)', fontSize: '0.8rem' }}>
                  {runResult.error}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CreateForm({ onDone }: { onDone: () => void }) {
  const [activeTab, setActiveTab] = useState<'preset' | 'json'>('preset');
  const [jsonInput, setJsonInput] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const usePreset = (presetJson: string) => {
    setJsonInput(presetJson);
    setActiveTab('json');
    setError('');
  };

  const handleCreate = async () => {
    if (!jsonInput.trim()) { setError('Enter JSON for the automation'); return; }
    setSaving(true);
    setError('');
    try {
      const data = JSON.parse(jsonInput);
      const res = await fetch(`${API}/automations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const result = await res.json();
      if (result.error) {
        setError(result.error);
      } else {
        onDone();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid JSON');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card" style={{ marginBottom: 16, borderColor: 'var(--accent)' }}>
      <div className="card-header">Create Automation</div>

      <div style={{ display: 'flex', gap: 0, marginBottom: 12 }}>
        <button className={`btn btn-sm ${activeTab === 'preset' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ borderRadius: 'var(--radius) 0 0 var(--radius)' }}
          onClick={() => setActiveTab('preset')}>Presets</button>
        <button className={`btn btn-sm ${activeTab === 'json' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ borderRadius: '0 var(--radius) var(--radius) 0' }}
          onClick={() => setActiveTab('json')}>JSON Editor</button>
      </div>

      {activeTab === 'preset' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 12 }}>
          {PRESETS.map(p => (
            <button key={p.label} className="btn btn-secondary btn-sm" onClick={() => usePreset(p.json)}
              style={{ textAlign: 'left', justifyContent: 'flex-start' }}>
              📋 {p.label}
            </button>
          ))}
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
            Click a preset to load it into the JSON editor, then customize and save.
          </div>
        </div>
      )}

      {activeTab === 'json' && (
        <>
          <textarea
            value={jsonInput}
            onChange={e => setJsonInput(e.target.value)}
            placeholder='{"name": "My Automation", "trigger": {"type": "manual", "config": {}}, "actions": [{"type": "notification", "parameters": {"message": "Hello"}}]}'
            rows={14}
            style={{ fontFamily: 'monospace', fontSize: '0.75rem', marginBottom: 10 }}
          />
          {error && <div style={{ color: 'var(--danger)', fontSize: '0.8rem', marginBottom: 8 }}>{error}</div>}
          <button className="btn btn-primary" onClick={handleCreate} disabled={saving}>
            {saving ? 'Creating...' : 'Create Automation'}
          </button>
        </>
      )}
    </div>
  );
}

export default Automations;
