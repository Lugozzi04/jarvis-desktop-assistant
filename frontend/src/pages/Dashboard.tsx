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
  const [splash, setSplash] = useState(true);
  const [language, setLanguage] = useState<string>('it');
  const [langSaving, setLangSaving] = useState(false);
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
    // Auto-dismiss splash after 2.5s
    const timer = setTimeout(() => setSplash(false), 2500);
    return () => clearTimeout(timer);
  }, []);

  // Fetch language
  useEffect(() => {
    fetch('http://localhost:8400/api/settings/language')
      .then(r => r.json())
      .then(d => setLanguage(d.language || 'it'))
      .catch(() => {});
  }, []);

  const handleLanguageChange = async (lang: string) => {
    setLanguage(lang);
    setLangSaving(true);
    try {
      await fetch('http://localhost:8400/api/settings/language', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: lang }),
      });
    } catch {}
    setLangSaving(false);
  };

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
      {/* ── Splash Screen ── */}
      {splash && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          zIndex: 99999, background: 'var(--bg-primary)',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          animation: 'fadeOut 0.6s ease-out 1.9s forwards',
        }}>
          <div style={{
            fontSize: '3rem', marginBottom: 16,
            animation: 'pulseSplash 1s ease-in-out infinite',
          }}>⚡</div>
          <div style={{
            fontSize: '1.6rem', fontWeight: 700,
            color: 'var(--accent, #6366f1)',
            marginBottom: 8,
            animation: 'slideUp 0.5s ease-out',
          }}>JARVIS</div>
          <div style={{
            fontSize: '0.95rem', color: 'var(--text-muted)',
            animation: 'slideUp 0.5s ease-out 0.2s both',
          }}>Waking up...</div>
          <div style={{
            marginTop: 24, width: 120, height: 3,
            background: 'var(--bg-tertiary)', borderRadius: 2, overflow: 'hidden',
          }}>
            <div style={{
              width: '100%', height: '100%',
              background: 'var(--accent, #6366f1)',
              animation: 'loadingBar 2s ease-in-out',
            }} />
          </div>
        </div>
      )}
      <style>{`
        @keyframes fadeOut { to { opacity: 0; pointer-events: none; } }
        @keyframes pulseSplash { 0%,100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.2); opacity: 0.6; } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        @keyframes loadingBar { from { width: 0%; } to { width: 100%; } }
      `}</style>
      <h2 style={{ marginBottom: 20, fontSize: '1.5rem' }}>Dashboard</h2>

      {/* Language Selector */}
      <div style={{
        marginBottom: 20, padding: '10px 14px',
        background: 'var(--bg-secondary)', borderRadius: 10,
        border: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
          🌐 Lingua / Language:
        </span>
        <select
          value={language}
          onChange={(e) => handleLanguageChange(e.target.value)}
          disabled={langSaving}
          style={{
            padding: '6px 12px', borderRadius: 8,
            border: '1px solid var(--accent)',
            background: 'var(--bg-primary)',
            color: 'var(--text-primary)',
            fontSize: '0.85rem',
            cursor: 'pointer',
            outline: 'none',
          }}
        >
          <option value="it">🇮🇹 Italiano</option>
          <option value="en">🇬🇧 English</option>
        </select>
        {langSaving && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Salvando...</span>}
      </div>

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
