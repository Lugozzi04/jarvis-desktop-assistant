import { useEffect, useState } from 'react';
import { api } from '../api';
import type { LogEntry } from '../api';

function Logs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.logs()
      .then(data => { setLogs(data.logs); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  if (loading) return <div className="loading"><div className="spinner" /></div>;
  if (error) return <div className="empty-state"><h3>Error</h3><p>{error}</p></div>;

  return (
    <div>
      <h2 style={{ marginBottom: 20, fontSize: '1.5rem' }}>Logs ({logs.length})</h2>
      {logs.length === 0 ? (
        <div className="empty-state">
          <h3>No logs yet</h3>
          <p>Activity logs will appear here as you use JARVIS.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Input</th>
                  <th>Intent</th>
                  <th>Skill</th>
                  <th>Action</th>
                  <th>Risk</th>
                  <th>Result</th>
                  <th>Duration</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id}>
                    <td style={{ whiteSpace: 'nowrap', fontSize: '0.8rem' }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '-'}
                    </td>
                    <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {log.input_raw}
                    </td>
                    <td>{log.intent_kind}</td>
                    <td>{log.skill || '-'}</td>
                    <td>{log.action || '-'}</td>
                    <td>
                      <span className={`badge ${log.risk === 'dangerous' ? 'badge-danger' : log.risk === 'confirmation' ? 'badge-warning' : 'badge-success'}`}>
                        {log.risk}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: log.result_success ? 'var(--success)' : 'var(--danger)' }}>
                        {log.result_success ? '✓' : '✗'}
                      </span>
                      {log.error && <span style={{ color: 'var(--danger)', fontSize: '0.75rem', marginLeft: 6 }}>{log.error}</span>}
                    </td>
                    <td>{log.duration_ms?.toFixed(0)}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default Logs;
