import { useState, useEffect } from 'react';

const API = 'http://localhost:8400/api';

interface Suggestion {
  id: string;
  type: string;
  title: string;
  description: string;
  confidence: number;
  evidence: string;
  proposed_automation?: unknown;
  proposed_workflow?: unknown;
  status: string;
  created_at: string;
}

function Habits() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [events, setEvents] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [status, setStatus] = useState('');

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    try {
      const [sRes, eRes] = await Promise.all([
        fetch(`${API}/habits/suggestions`).then(r => r.json()),
        fetch(`${API}/habits/events?limit=20`).then(r => r.json()),
      ]);
      setSuggestions(sRes.suggestions || []);
      setEvents(eRes.events || []);
      setLoading(false);
    } catch { setLoading(false); }
  };

  const analyze = async () => {
    setAnalyzing(true);
    try {
      const res = await fetch(`${API}/habits/analyze`, { method: 'POST' });
      const data = await res.json();
      setStatus(`Analysis done — ${data.suggestion_count || 0} suggestions`);
      loadAll();
    } catch { setStatus('Analysis failed'); }
    setAnalyzing(false);
  };

  const accept = async (id: string) => {
    await fetch(`${API}/habits/suggestions/${id}/accept`, { method: 'POST' });
    loadAll();
  };

  const dismiss = async (id: string) => {
    await fetch(`${API}/habits/suggestions/${id}/dismiss`, { method: 'POST' });
    loadAll();
  };

  const pending = suggestions.filter(s => s.status === 'pending');
  const accepted = suggestions.filter(s => s.status === 'accepted');
  const dismissed = suggestions.filter(s => s.status === 'dismissed');

  if (loading) return <div className="loading"><div className="spinner" /></div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ fontSize: '1.5rem', margin: 0 }}>Habit Learning</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary btn-sm" onClick={loadAll}>🔄</button>
          <button className="btn btn-primary" onClick={analyze} disabled={analyzing}>
            {analyzing ? 'Analyzing...' : '🔍 Analyze'}
          </button>
        </div>
      </div>

      {status && <div className="badge badge-info" style={{ marginBottom: 12 }}>{status}</div>}

      {/* Stats */}
      <div className="card-grid" style={{ marginBottom: 16 }}>
        <div className="card"><div className="stat-value">{events.length}</div><div className="stat-label">Events tracked</div></div>
        <div className="card"><div className="stat-value">{suggestions.length}</div><div className="stat-label">Suggestions</div></div>
        <div className="card"><div className="stat-value">{pending.length}</div><div className="stat-label">Pending</div></div>
        <div className="card"><div className="stat-value">{accepted.length}</div><div className="stat-label">Accepted</div></div>
      </div>

      {/* Pending Suggestions */}
      {pending.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: '1.1rem', marginBottom: 10 }}>📋 Pending Suggestions</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {pending.map(s => (
              <div key={s.id} className="card" style={{ borderColor: 'var(--warning)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <div>
                    <strong>{s.title}</strong>
                    <span className="badge badge-info" style={{ marginLeft: 8, fontSize: '0.65rem' }}>{s.type}</span>
                  </div>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Confidence: {(s.confidence * 100).toFixed(0)}%</span>
                </div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '6px 0' }}>{s.description}</p>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 8 }}>Evidence: {s.evidence}</div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button className="btn btn-primary btn-sm" onClick={() => accept(s.id)}>✅ Accept</button>
                  <button className="btn btn-secondary btn-sm" onClick={() => dismiss(s.id)}>❌ Dismiss</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Accepted */}
      {accepted.length > 0 && (
        <details style={{ marginBottom: 16 }}>
          <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            ✅ Accepted ({accepted.length})
          </summary>
          <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
            {accepted.map(s => (
              <div key={s.id} style={{ fontSize: '0.85rem', color: 'var(--success)' }}>✓ {s.title}</div>
            ))}
          </div>
        </details>
      )}

      {/* Dismissed */}
      {dismissed.length > 0 && (
        <details style={{ marginBottom: 16 }}>
          <summary style={{ cursor: 'pointer', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            ❌ Dismissed ({dismissed.length})
          </summary>
          <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
            {dismissed.map(s => (
              <div key={s.id} style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>✗ {s.title}</div>
            ))}
          </div>
        </details>
      )}

      {suggestions.length === 0 && (
        <div className="empty-state">
          <h3>No suggestions yet</h3>
          <p>Use JARVIS normally and click "Analyze" to detect patterns.</p>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 8 }}>
            JARVIS tracks skill actions, workflows, and app usage to find patterns.
            Tracked data is stored locally and never leaves your machine.
          </p>
        </div>
      )}

      {/* Privacy Note */}
      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">🔒 Privacy</div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          <p>Habit Learning tracks <strong>action types and metadata</strong> only — not message content.</p>
          <p>All data is stored <strong>locally</strong> in your data directory. Nothing is sent externally.</p>
          <p style={{ marginTop: 8 }}>
            <button className="btn btn-sm btn-secondary" onClick={async () => { await fetch(`${API}/habits/clear-events`, { method: 'POST' }); loadAll(); }}>
              🗑 Clear all events
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

export default Habits;
