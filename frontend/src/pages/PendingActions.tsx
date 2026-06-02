import { useEffect, useState } from 'react';
import { api } from '../api';
import type { PendingAction } from '../api';

function PendingActions() {
  const [actions, setActions] = useState<PendingAction[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionStates, setActionStates] = useState<Record<string, { loading: boolean; result?: string; error?: string }>>({});
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [cleaning, setCleaning] = useState(false);

  const loadActions = () => {
    setLoading(true);
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

  const handleCleanOld = async () => {
    setCleaning(true);
    try {
      const result = await api.cleanupPendingActions(1);
      // Refresh the list after cleanup
      const data = await api.pendingActions();
      setActions(data.actions);
      setCount(data.count);
      setCleaning(false);
      // eslint-disable-next-line no-console
      console.log(`Cleanup removed ${result.removed} old actions`);
    } catch (err) {
      setCleaning(false);
      setError(err instanceof Error ? err.message : 'Cleanup failed');
    }
  };

  const toggleExpand = (id: string) => {
    setExpandedId(prev => (prev === id ? null : id));
  };

  const statusBadge = (status: string) => {
    const styles: Record<string, { bg: string; color: string; label: string }> = {
      pending:   { bg: '#fef3c7', color: '#92400e', label: '⏳ PENDING' },
      approved:  { bg: '#d1fae5', color: '#065f46', label: '✅ APPROVED' },
      rejected:  { bg: '#fee2e2', color: '#991b1b', label: '❌ REJECTED' },
      executed:  { bg: '#dbeafe', color: '#1e40af', label: '🔵 EXECUTED' },
      failed:    { bg: '#fee2e2', color: '#991b1b', label: '💥 FAILED' },
      expired:   { bg: '#f3f4f6', color: '#6b7280', label: '⏰ EXPIRED' },
    };
    const s = styles[status] || { bg: '#f3f4f6', color: '#6b7280', label: status.toUpperCase() };
    return (
      <span style={{
        display: 'inline-block',
        padding: '2px 10px',
        borderRadius: '12px',
        fontSize: '0.7rem',
        fontWeight: 700,
        backgroundColor: s.bg,
        color: s.color,
        letterSpacing: '0.03em',
      }}>
        {s.label}
      </span>
    );
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
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleCleanOld}
            disabled={cleaning}
          >
            {cleaning ? '🧹 Cleaning...' : '🧹 Clean Old'}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={loadActions}>🔄 Refresh</button>
        </div>
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
            const resolved = !!state?.result || (action.status !== 'pending' && action.status !== 'approved');

            return (
              <div
                key={action.id}
                className="card"
                style={{
                  opacity: resolved ? 0.5 : 1,
                  transition: 'opacity 0.3s ease',
                }}
              >
                {/* ── Header: action name, risk badge, status badge ── */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: '1rem', marginBottom: 2 }}>
                      {action.skill}.{action.action}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {action.created_at ? new Date(action.created_at).toLocaleString() : '—'}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    {statusBadge(action.status)}
                    {riskBadge(action.risk)}
                  </div>
                </div>

                {/* ── Preview: skill.action + reason ── */}
                <div style={{ marginBottom: 8, padding: '8px 12px', background: 'var(--bg-primary)', borderRadius: 'var(--radius)', fontSize: '0.85rem' }}>
                  <strong style={{ color: 'var(--accent)' }}>{action.skill}.{action.action}</strong>
                  {action.reason && (
                    <span style={{ color: 'var(--text-secondary)', marginLeft: 8 }}>
                      — {action.reason}
                    </span>
                  )}
                </div>

                {/* ── Reason ── */}
                {action.reason && (
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 2 }}>Reason</div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{action.reason}</div>
                  </div>
                )}

                {/* ── Reject reason ── */}
                {action.reject_reason && (
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--danger)', marginBottom: 2 }}>Rejection Reason</div>
                    <div style={{
                      fontSize: '0.85rem',
                      color: 'var(--danger)',
                      padding: '6px 10px',
                      background: 'rgba(239,68,68,0.06)',
                      borderRadius: 'var(--radius)',
                    }}>
                      {action.reject_reason}
                    </div>
                  </div>
                )}

                {/* ── Collapsible JSON details ── */}
                {action.parameters && Object.keys(action.parameters).length > 0 && (
                  <div style={{ marginBottom: 8 }}>
                    <div
                      onClick={() => toggleExpand(action.id)}
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: 'var(--accent)',
                        cursor: 'pointer',
                        userSelect: 'none',
                        marginBottom: 4,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      <span>{expandedId === action.id ? '▼' : '▶'}</span>
                      Parameters ({Object.keys(action.parameters).length})
                    </div>
                    {expandedId === action.id && (
                      <pre style={{
                        fontSize: '0.72rem',
                        color: 'var(--text-muted)',
                        background: 'var(--bg-primary)',
                        padding: '8px 12px',
                        borderRadius: 'var(--radius)',
                        overflow: 'auto',
                        maxHeight: 160,
                        margin: 0,
                      }}>
                        {JSON.stringify(action.parameters, null, 2)}
                      </pre>
                    )}
                  </div>
                )}

                {/* ── Error display ── */}
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

                {/* ── Action error from execution ── */}
                {action.error && (
                  <div style={{
                    marginBottom: 10,
                    padding: '6px 10px',
                    background: 'rgba(239,68,68,0.06)',
                    borderRadius: 'var(--radius)',
                    color: 'var(--danger)',
                    fontSize: '0.8rem',
                  }}>
                    <strong>Error:</strong> {action.error}
                  </div>
                )}

                {/* ── Result feedback ── */}
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

                {/* ── Action buttons (only for unresolved pending) ── */}
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
