import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { HealthFullResponse } from '../api';

interface StatusCardProps {
  icon: string;
  title: string;
  children: React.ReactNode;
  variant?: 'success' | 'warning' | 'danger' | 'default';
  onClick?: () => void;
}

function StatusCard({ icon, title, children, variant = 'default', onClick }: StatusCardProps) {
  const borderColors: Record<string, string> = {
    success: 'var(--success)',
    warning: 'var(--warning)',
    danger: 'var(--danger)',
    default: 'var(--border)',
  };

  return (
    <div
      className="card"
      style={{
        borderLeft: `3px solid ${borderColors[variant]}`,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'border-color 0.2s',
      }}
      onClick={onClick}
    >
      <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: '1.2rem' }}>{icon}</span>
        {title}
      </div>
      {children}
    </div>
  );
}

function Dashboard() {
  const [health, setHealth] = useState<HealthFullResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.healthFull()
      .then((h) => {
        setHealth(h);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to connect to backend');
        setLoading(false);
      });
  }, []);

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

  if (loading)
    return (
      <div className="loading">
        <div className="spinner" />
      </div>
    );

  if (error)
    return (
      <div className="empty-state">
        <h3>Backend Unreachable</h3>
        <p>{error} — start the JARVIS backend on port 8400</p>
      </div>
    );

  if (!health)
    return (
      <div className="empty-state">
        <h3>No data</h3>
        <p>Health check returned empty — try again</p>
      </div>
    );

  const backendOnline = health.backend?.online ?? false;
  const llmAvailable = health.llm?.available ?? false;
  const docReady = health.documents?.ready ?? false;
  const voiceAvailable = health.voice?.available ?? false;
  const schedulerRunning = health.automations?.scheduler_running ?? false;
  const hasWarnings = health.warnings?.length > 0;
  const pendingCount = health.pending_actions?.count ?? 0;

  return (
    <div>
      <h2 style={{ marginBottom: 20, fontSize: '1.5rem' }}>Dashboard</h2>

      {/* Status Cards */}
      <div className="card-grid">
        {/* Backend Status */}
        <StatusCard
          icon={backendOnline ? '🟢' : '🔴'}
          title="Backend"
          variant={backendOnline ? 'success' : 'danger'}
        >
          <div className="stat-value" style={{ fontSize: '1.25rem' }}>
            {backendOnline ? 'Online' : 'Offline'}
          </div>
          <div className="stat-label">
            v{health.backend?.version || '?'} · {health.backend?.skills_loaded ?? 0} skills loaded
            {!health.backend?.initialized && ' · Not initialized'}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>
            Python {health.environment?.python} · {health.environment?.system} {health.environment?.release}
          </div>
        </StatusCard>

        {/* LLM Status */}
        <StatusCard
          icon={llmAvailable ? '🧠' : '🧠'}
          title="LLM"
          variant={llmAvailable ? 'success' : 'warning'}
        >
          <div className="stat-value" style={{ fontSize: '1.25rem' }}>
            {llmAvailable ? '🟢 Ready' : '⚫ Offline'}
          </div>
          <div className="stat-label">
            Provider: {health.llm?.provider || 'none'} · Model: {health.llm?.model || 'none'}
          </div>
          {health.llm?.error && (
            <div style={{ fontSize: '0.75rem', color: 'var(--danger)', marginTop: 4 }}>
              {health.llm.error}
            </div>
          )}
        </StatusCard>

        {/* Document Memory */}
        <StatusCard
          icon="📚"
          title="Document Memory"
          variant={docReady ? 'success' : 'warning'}
          onClick={() => navigate('/documents')}
        >
          <div className="stat-value" style={{ fontSize: '1.25rem' }}>
            {health.documents?.documents ?? 0} docs
          </div>
          <div className="stat-label">
            Provider: {health.documents?.embedding_provider || 'none'}
            {docReady ? ' · Ready' : ' · Not ready'}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
            {health.documents?.chunks ?? 0} chunks indexed
          </div>
          {health.documents?.error && (
            <div style={{ fontSize: '0.75rem', color: 'var(--danger)', marginTop: 4 }}>
              {health.documents.error}
            </div>
          )}
        </StatusCard>

        {/* Voice */}
        <StatusCard
          icon="🎤"
          title="Voice"
          variant={voiceAvailable ? 'success' : 'warning'}
          onClick={() => navigate('/voice')}
        >
          <div className="stat-value" style={{ fontSize: '1.25rem' }}>
            {voiceAvailable ? '🟢 Ready' : '⚫ Offline'}
          </div>
          <div className="stat-label">
            STT: {health.voice?.stt || 'none'} · TTS: {health.voice?.tts || 'none'}
          </div>
        </StatusCard>

        {/* Automations */}
        <StatusCard
          icon="⚙️"
          title="Automations"
          variant={schedulerRunning ? 'success' : 'default'}
          onClick={() => navigate('/automations')}
        >
          <div className="stat-value" style={{ fontSize: '1.25rem' }}>
            {schedulerRunning ? '▶ Running' : '⏸ Stopped'}
          </div>
          <div className="stat-label">
            {health.automations?.automations_loaded ?? 0} automations loaded
          </div>
          {health.workflows && (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
              {health.workflows.workflows_loaded} workflows
            </div>
          )}
        </StatusCard>

        {/* Pending Actions */}
        <StatusCard
          icon="⏳"
          title="Pending Actions"
          variant={pendingCount > 0 ? 'warning' : 'success'}
          onClick={() => navigate('/pending-actions')}
        >
          <div className="stat-value" style={{ fontSize: '1.25rem' }}>
            {pendingCount > 0 ? (
              <span style={{ color: 'var(--warning)' }}>● {pendingCount} pending</span>
            ) : (
              <span style={{ color: 'var(--success)' }}>✓ Clear</span>
            )}
          </div>
          <div className="stat-label">
            {pendingCount > 0
              ? `${pendingCount} action${pendingCount > 1 ? 's' : ''} awaiting approval`
              : 'No pending actions'}
          </div>
          {pendingCount > 0 && (
            <button
              className="btn btn-sm btn-secondary"
              style={{ marginTop: 10 }}
              onClick={(e) => {
                e.stopPropagation();
                navigate('/pending-actions');
              }}
            >
              Review →
            </button>
          )}
        </StatusCard>
      </div>

      {/* Quick Actions */}
      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header">Quick Actions</div>
        <div className="quick-actions">
          {quickActions.map((a) => (
            <button
              key={a.label}
              className="quick-action"
              onClick={() => handleQuickAction(a.label)}
            >
              {a.icon} {a.label}
            </button>
          ))}
        </div>
      </div>

      {/* Recommended Next Steps */}
      {(hasWarnings || (health.recommended_next_steps?.length ?? 0) > 0) && (
        <div className="card" style={{ marginTop: 16 }}>
          <div
            className="card-header"
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            💡 Recommended Next Steps
          </div>
          <ul
            style={{
              listStyle: 'none',
              padding: 0,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            {health.recommended_next_steps?.map((step, i) => (
              <li
                key={`step-${i}`}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                  fontSize: '0.85rem',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.5,
                }}
              >
                <span style={{ color: 'var(--accent)', flexShrink: 0 }}>▸</span>
                {step}
              </li>
            ))}
            {health.warnings?.map((w, i) => (
              <li
                key={`warn-${i}`}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                  fontSize: '0.85rem',
                  color: 'var(--warning)',
                  lineHeight: 1.5,
                }}
              >
                <span style={{ flexShrink: 0 }}>⚠</span>
                {w}
              </li>
            ))}
          </ul>
          {hasWarnings && (
            <button
              className="btn btn-sm btn-primary"
              style={{ marginTop: 12 }}
              onClick={() => navigate('/settings')}
            >
              Open Setup Wizard
            </button>
          )}
        </div>
      )}

      {/* System Info */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-header">System Info</div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 12,
            fontSize: '0.85rem',
          }}
        >
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Python:</span>{' '}
            {health.environment?.python}
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>System:</span>{' '}
            {health.environment?.system} {health.environment?.release}
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Architecture:</span>{' '}
            {health.environment?.machine}
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Desktop:</span>{' '}
            {health.desktop?.electron ? 'Electron' : 'Browser'}
            {health.desktop?.portable_mode ? ' · Portable' : ''}
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Skills:</span>{' '}
            {health.skills?.loaded?.length ?? 0} loaded
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Errors:</span>{' '}
            {health.errors?.length ?? 0}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
