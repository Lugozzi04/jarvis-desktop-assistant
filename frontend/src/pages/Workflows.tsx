import { useEffect, useState } from 'react';
import { api } from '../api';

interface WorkflowSummary {
  id: string;
  name: string;
  description: string;
  step_count: number;
  created_at: string;
}

interface WorkflowStep {
  order: number;
  skill: string;
  action: string;
  parameters: Record<string, string>;
  description: string;
}

interface WorkflowDetail {
  id: string;
  name: string;
  description: string;
  steps: WorkflowStep[];
  created_at: string;
}

interface RunResult {
  workflow_id: string;
  workflow_name: string;
  status: string;
  steps: {
    order: number;
    skill: string;
    action: string;
    status: string;
    result?: string;
    error?: string;
    duration_ms: number;
  }[];
  started_at: string;
  total_duration_ms: number;
}

function Workflows() {
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<WorkflowDetail | null>(null);
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [running, setRunning] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    loadWorkflows();
  }, []);

  const loadWorkflows = async () => {
    try {
      const data = await api.workflows() as unknown as { workflows: WorkflowSummary[] };
      setWorkflows(data.workflows || []);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
      setLoading(false);
    }
  };

  const loadDetail = async (id: string) => {
    try {
      const resp = await fetch(`http://localhost:8400/api/workflows/${id}`);
      const data = await resp.json();
      if (!data.error) {
        setSelected(data);
      }
    } catch {
      // ignore
    }
  };

  const runWorkflow = async (id: string) => {
    setRunning(true);
    setRunResult(null);
    try {
      const resp = await fetch(`http://localhost:8400/api/workflows/${id}/run`, { method: 'POST' });
      const data = await resp.json();
      setRunResult(data);
    } catch (err) {
      setRunResult({ workflow_id: id, workflow_name: id, status: 'error', steps: [], started_at: '', total_duration_ms: 0 } as RunResult);
    } finally {
      setRunning(false);
    }
  };

  const deleteWorkflow = async (id: string) => {
    try {
      await fetch(`http://localhost:8400/api/workflows/${id}`, { method: 'DELETE' });
      loadWorkflows();
      if (selected?.id === id) setSelected(null);
    } catch {
      // ignore
    }
  };

  if (loading) return <div className="loading"><div className="spinner" /></div>;
  if (error) return <div className="empty-state"><h3>Error</h3><p>{error}</p></div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: '1.5rem', margin: 0 }}>Workflows ({workflows.length})</h2>
        <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ New Workflow'}
        </button>
      </div>

      {showCreate && (
        <WorkflowCreateForm
          onCreated={() => { setShowCreate(false); loadWorkflows(); }}
        />
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Workflow list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {workflows.map(wf => (
            <div
              key={wf.id}
              className={`card ${selected?.id === wf.id ? '' : ''}`}
              style={{
                cursor: 'pointer',
                borderColor: selected?.id === wf.id ? 'var(--accent)' : 'var(--border)',
                padding: 14,
              }}
              onClick={() => loadDetail(wf.id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{wf.name}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                    {wf.description}
                  </div>
                </div>
                <span className="badge badge-info">{wf.step_count} steps</span>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={(e) => { e.stopPropagation(); runWorkflow(wf.id); }}
                  disabled={running}
                >
                  ▶ Run
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={(e) => { e.stopPropagation(); deleteWorkflow(wf.id); }}
                >
                  🗑 Delete
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Detail + Run Result */}
        <div>
          {selected && (
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="card-header">{selected.name}</div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
                {selected.description}
              </p>
              <div style={{ fontSize: '0.85rem' }}>
                {selected.steps.map(step => (
                  <div key={step.order} style={{
                    display: 'flex', gap: 10, padding: '6px 0',
                    borderBottom: '1px solid var(--border)',
                  }}>
                    <span style={{ color: 'var(--text-muted)', minWidth: 24 }}>{step.order}.</span>
                    <span style={{ color: 'var(--accent)' }}>{step.skill}.{step.action}</span>
                    <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                      {step.description || JSON.stringify(step.parameters)}
                    </span>
                  </div>
                ))}
              </div>
              <button
                className="btn btn-primary"
                style={{ marginTop: 12 }}
                onClick={() => runWorkflow(selected.id)}
                disabled={running}
              >
                {running ? 'Running...' : '▶ Run Workflow'}
              </button>
            </div>
          )}

          {runResult && (
            <div className="card" style={{
              borderColor: runResult.status === 'success' ? 'var(--success)' :
                runResult.status === 'partial' ? 'var(--warning)' : 'var(--danger)',
            }}>
              <div className="card-header">
                Run Result — {runResult.status?.toUpperCase()}
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: 10 }}>
                  {runResult.total_duration_ms?.toFixed(0)}ms
                </span>
              </div>
              <div style={{ fontSize: '0.85rem' }}>
                {runResult.steps?.map(step => {
                  const iconMap: Record<string, string> = { success: '✅', failed: '❌', skipped: '⏭️' };
                  return (
                    <div key={step.order} style={{
                      display: 'flex', gap: 8, padding: '4px 0',
                      alignItems: 'center',
                    }}>
                      <span>{iconMap[step.status] || '❓'}</span>
                      <span style={{ color: 'var(--text-primary)' }}>
                        {step.skill}.{step.action}
                      </span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                        {step.duration_ms?.toFixed(0)}ms
                      </span>
                      {step.error && (
                        <span style={{ color: 'var(--danger)', fontSize: '0.75rem' }}>
                          {step.error}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function WorkflowCreateForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [steps, setSteps] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) { setError('Name is required'); return; }
    setSaving(true);
    setError('');

    let parsedSteps = [];
    try {
      if (steps.trim()) {
        parsedSteps = JSON.parse(steps);
      }
    } catch {
      setError('Invalid JSON in steps');
      setSaving(false);
      return;
    }

    try {
      const resp = await fetch('http://localhost:8400/api/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: name.toLowerCase().replace(/\s+/g, '-'),
          name: name.trim(),
          description: description.trim(),
          steps: parsedSteps,
        }),
      });
      const data = await resp.json();
      if (data.error) {
        setError(data.error);
      } else {
        onCreated();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card" style={{ marginBottom: 16, borderColor: 'var(--accent)' }}>
      <div className="card-header">Create Workflow</div>
      <div className="form-group">
        <label>Name</label>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g., Morning Routine" />
      </div>
      <div className="form-group">
        <label>Description</label>
        <input value={description} onChange={e => setDescription(e.target.value)} placeholder="What this workflow does" />
      </div>
      <div className="form-group">
        <label>Steps (JSON array)</label>
        <textarea
          value={steps}
          onChange={e => setSteps(e.target.value)}
          placeholder={'[{"order":1,"skill":"apps","action":"open","parameters":{"app_name":"Discord"}}]'}
          rows={6}
          style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
        />
      </div>
      {error && <div style={{ color: 'var(--danger)', fontSize: '0.85rem', marginBottom: 10 }}>{error}</div>}
      <button className="btn btn-primary" onClick={handleCreate} disabled={saving}>
        {saving ? 'Creating...' : 'Create Workflow'}
      </button>
    </div>
  );
}

export default Workflows;
