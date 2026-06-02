import { NavLink, Outlet } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api } from './api';
import type { HealthStatus } from './api';

function Layout() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [pendingCount, setPendingCount] = useState<number>(0);

  useEffect(() => {
    const check = async () => {
      try {
        const h = await api.health();
        setHealth(h);
      } catch {
        setHealth(null);
      }
    };
    const checkPending = async () => {
      try {
        const p = await api.pendingActionsCount();
        setPendingCount(p.count);
      } catch {
        setPendingCount(0);
      }
    };
    check();
    checkPending();
    const interval = setInterval(() => { check(); checkPending(); }, 15000);
    return () => clearInterval(interval);
  }, []);

  const online = health?.status === 'ok';
  const llmAvailable = health?.llm?.available ?? false;

  return (
    <>
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>⚡ JARVIS</h1>
          <div className="version">v{health?.version || '0.2.0'}</div>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">📊</span> Dashboard
          </NavLink>
          <NavLink to="/chat" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">💬</span> Chat
          </NavLink>
          <NavLink to="/skills" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">🧩</span> Skills
          </NavLink>
          <NavLink to="/workflows" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">🔄</span> Workflows
          </NavLink>
          <NavLink to="/automations" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">⚙️</span> Automations
          </NavLink>
          <NavLink to="/pending-actions" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">⏳</span> Pending
            {pendingCount > 0 && (
              <span className="badge badge-warning" style={{ marginLeft: 'auto', fontSize: '0.7rem', padding: '2px 8px' }}>
                {pendingCount}
              </span>
            )}
          </NavLink>
          <NavLink to="/logs" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">📋</span> Logs
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">🔧</span> Settings
          </NavLink>
          <NavLink to="/voice" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">🎤</span> Voice
          </NavLink>
          <NavLink to="/habits" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">🧠</span> Habits
          </NavLink>
          <NavLink to="/documents" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-icon">📚</span> Documents
          </NavLink>
        </nav>
        <div className="sidebar-footer">
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            <span className={`status-dot ${online ? 'online' : 'offline'}`} />
            {online ? 'Backend online' : 'Backend offline'}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
            LLM: {llmAvailable ? '🟢 Ready' : '⚫ Offline'}
          </div>
        </div>
      </aside>
      <main className="main">
        <div className="topbar">
          <div className="topbar-left">
            <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>
              {health?.status === 'ok' ? '✅ System Ready' : '❌ System Offline'}
            </span>
          </div>
          <div className="topbar-right">
            {health && (
              <>
                <span className={`badge ${online ? 'badge-success' : 'badge-danger'}`}>
                  {online ? 'ONLINE' : 'OFFLINE'}
                </span>
                <span className="badge badge-info">
                  {health.skills?.length || 0} Skills
                </span>
                <span className={`badge ${llmAvailable ? 'badge-success' : 'badge-warning'}`}>
                  LLM: {health.llm?.provider || 'none'}
                </span>
                {pendingCount > 0 && (
                  <span className="badge badge-warning" style={{ cursor: 'pointer' }}>
                    ⏳ {pendingCount} Pending
                  </span>
                )}
              </>
            )}
          </div>
        </div>
        <div className="content">
          <Outlet />
        </div>
      </main>
    </>
  );
}

export default Layout;
