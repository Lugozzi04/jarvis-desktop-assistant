import { useEffect, useState } from 'react';
import { api } from '../api';
import type { PendingAction } from '../api';

function PendingActions() {
  const [actions, setActions] = useState<PendingAction[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionStates, setActionStates] = useState<Record<string, { loading: boolean; result?: string; error?: string }>>({});

  const loadActions = () => {
    api.pendingActions()
      .then(data => {
        setActions(data.actions);
        setCount(data.count);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => { loadActions(); }, []);

  const handleApprove = async (id: string) => {
    setActionStates(prev => ({ ...prev, [id]: { loading: true } }));
    try {
      const result = await api.approvePendingAction(id);
      setActionStates(prev => ({ ...prev, [id]: { loading: false, result: result.status } }));
      // Remove the action from the list after a brief delay
      setTimeout(() => {
        setActions(prev => prev.filter(a => a.id !== id));
        setCount(prev => prev - 1);
      }, 600);
    } catch (err) {
      setActionStates(prev => ({
        ...prev,
        [id]: { loading: false, error: err instanceof Error ? err.message : 'Failed' },
      }));
    }
  };

  const handleReject = async (id: string) => {
    setActionStates(prev => ({ ...prev, [id]: { loading: true } }));
    try {
      const result = await api.rejectPendingAction(id);
      setActionStates(prev => ({ ...prev, [id]: { loading: false, result: result.status } }));
      setTimeout(() => {
        setActions(prev => prev.filter(a => a.id !== id));
        setCount(prev => prev - 1);
      }, 600);
    } catch (err) {
      setActionStates(prev => ({
        ...prev,
        [id]: { loading: false, error: err instanceof Error ? err.message : 'Failed' },
      }));
    }
  };

  const riskBadge = (risk: string) => {
    if (risk === 'dangerous') return <span className="badge badge-danger">DANGEROUS</span>;
    if (risk === 'confirmation') return <span className="badge badge-warning">CONFIRMATION</span>;
    return <span className="badge badge-info">{risk.toUpperCase()}</span>;
  };

  if (loading) return <div className="loading"><div className="spinner" /></div>;
  if (error) return <div className="empty-state"><h3>Error</h3><p>{error}</p></div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: '1.5rem', margin: 0 }}>Pending Actions ({count})</h2>
        <button className="btn btn-secondary btn-sm" onClick={loadActions}>🔄 Refresh</button>
      </div>

      {actions.length === 0 ? (
        <div className="empty-state">
          <h3>No pending actions</h3>
          <p>All security actions have been resolved.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {actions.map(action => {
            const state = actionStates[action.id];
            const resolved = !!state?.result;

            return (
              <div
                key={action.id}
                className="card"
                style={{
                  opacity: resolved ? 0.5 : 1,
                  transition: 'opacity 0.3s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '1rem', marginBottom: 2 }}>
                      {action.skill}.{action.action}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {action.created_at ? new Date(action.created_at).toLocaleString() : '—'}
                    </div>
                  </div>
                  <div>{riskBadge(action.risk)}</div>
                </div>

                {action.reason && (
                  <div style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 2 }}>Reason</div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{action.reason}</div>
                  </div>
                )}

                {action.parameters && Object.keys(action.parameters).length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 4 }}>Parameters</div>
                    <pre style={{
                      fontSize: '0.75rem',
                      color: 'var(--text-muted)',
                      background: 'var(--bg-primary)',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius)',
                      overflow: 'auto',
                      maxHeight: 120,
                      margin: 0,
                    }}>
                      {JSON.stringify(action.parameters, null, 2)}
                    </pre>
                  </div>
                )}

                {state?.error && (
                  <div style={{
                    marginBottom: 10,
                    padding: '6px 10px',
                    background: 'rgba(239,68,68,0.08)',
                    borderRadius: 'var(--radius)',
                    color: 'var(--danger)',
                    fontSize: '0.8rem',
                  }}>
                    {state.error}
                  </div>
                )}

                {state?.result && (
                  <div style={{
                    marginBottom: 10,
                    padding: '6px 10px',
                    background: 'rgba(34,197,94,0.08)',
                    borderRadius: 'var(--radius)',
                    color: 'var(--success)',
                    fontSize: '0.8rem',
                  }}>
                    {state.result === 'approved' ? '✅ Approved' : state.result === 'rejected' ? '❌ Rejected' : state.result}
                  </div>
                )}

                {!resolved && (
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      className="btn btn-success"
                      onClick={() => handleApprove(action.id)}
                      disabled={state?.loading}
                    >
                      {state?.loading ? '...' : '✓ Approve'}
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={() => handleReject(action.id)}
                      disabled={state?.loading}
                    >
                      {state?.loading ? '...' : '✗ Reject'}
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default PendingActions;
