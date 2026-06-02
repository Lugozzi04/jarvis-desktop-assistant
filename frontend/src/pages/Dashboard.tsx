import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { HealthStatus } from '../api';

function Dashboard() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.health().then(h => { setHealth(h); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const online = health?.status === 'ok';
  const skillsCount = health?.skills?.length || 0;
  const llmAvailable = health?.llm?.available ?? false;

  const quickActions = [
    { label: '/open discord', icon: '🎮' },
    { label: '/system stats', icon: '📊' },
    { label: '/timer 25m study', icon: '⏱️' },
    { label: '/search best local LLM', icon: '🔍' },
    { label: '/ask explain Docker', icon: '💡' },
  ];

  const handleQuickAction = (cmd: string) => {
    navigate(`/chat?cmd=${encodeURIComponent(cmd)}`);
  };

  if (loading) return <div className="loading"><div className="spinner" /></div>;
  if (!online) return <div className="empty-state"><h3>Backend offline</h3><p>Start the JARVIS backend on port 8400</p></div>;

  return (
    <div>
      <h2 style={{ marginBottom: 20, fontSize: '1.5rem' }}>Dashboard</h2>

      <div className="card-grid">
        <div className="card">
          <div className="stat-value">{online ? '✅ Online' : '❌ Offline'}</div>
          <div className="stat-label">Backend Status</div>
        </div>
        <div className="card">
          <div className="stat-value">{skillsCount}</div>
          <div className="stat-label">Skills Loaded</div>
        </div>
        <div className="card">
          <div className="stat-value">{llmAvailable ? '🟢 Ready' : '⚫ Offline'}</div>
          <div className="stat-label">LLM Provider — {health?.llm?.provider || 'none'}</div>
        </div>
        <div className="card">
          <div className="stat-value">{health?.version || '0.2.0'}</div>
          <div className="stat-label">Version — {health?.env || 'dev'}</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">Quick Actions</div>
        <div className="quick-actions">
          {quickActions.map(a => (
            <button key={a.label} className="quick-action" onClick={() => handleQuickAction(a.label)}>
              {a.icon} {a.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-header">System Info</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: '0.85rem' }}>
          <div><span style={{ color: 'var(--text-muted)' }}>Environment:</span> {health?.env}</div>
          <div><span style={{ color: 'var(--text-muted)' }}>LLM Model:</span> {health?.llm?.model || 'none'}</div>
          <div><span style={{ color: 'var(--text-muted)' }}>Cloud LLM:</span> {health?.llm?.allow_cloud ? 'Allowed' : 'Blocked'}</div>
          <div><span style={{ color: 'var(--text-muted)' }}>Providers:</span> {Object.keys(health?.llm?.providers || {}).join(', ') || 'none'}</div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
