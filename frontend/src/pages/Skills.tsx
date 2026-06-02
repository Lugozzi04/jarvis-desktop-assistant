import { useEffect, useState } from 'react';
import { api } from '../api';
import type { SkillInfo } from '../api';

function Skills() {
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.skills()
      .then(data => { setSkills(data.skills); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  if (loading) return <div className="loading"><div className="spinner" /></div>;
  if (error) return <div className="empty-state"><h3>Error</h3><p>{error}</p></div>;

  return (
    <div>
      <h2 style={{ marginBottom: 20, fontSize: '1.5rem' }}>Skills ({skills.length})</h2>
      <div className="card-grid">
        {skills.map(skill => (
          <div key={skill.name} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 8 }}>
              <div>
                <div className="card-header" style={{ margin: 0 }}>
                  {skill.enabled ? '✅' : '⛔'} {skill.display_name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                  {skill.name} · v{skill.version}
                </div>
              </div>
              <span className={`badge ${skill.enabled ? 'badge-success' : 'badge-danger'}`}>
                {skill.enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 10 }}>
              {skill.description}
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {skill.actions.map(action => (
                <span key={action} className="badge badge-info" style={{ fontSize: '0.7rem' }}>
                  {action}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Skills;
