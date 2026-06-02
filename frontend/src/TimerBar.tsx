import { useState, useEffect } from 'react';

interface Timer {
  id: string;
  type: string;
  message: string;
  total_seconds: number;
  remaining_seconds: number;
  remaining_display: string;
}

export function TimerBar() {
  const [timers, setTimers] = useState<Timer[]>([]);

  useEffect(() => {
    const poll = async () => {
      try {
        const base = window.location.hostname ? window.location.origin : 'http://localhost:8400';
        const res = await fetch(`${base}/api/timers`);
        const data = await res.json();
        if (data.timers) {
          setTimers(data.timers);
        }
      } catch {
        // silent — backend not ready yet
      }
    };
    poll();
    const interval = setInterval(poll, 1000);
    return () => clearInterval(interval);
  }, []);

  if (timers.length === 0) return null;

  return (
    <div style={{
      display: 'flex',
      gap: 12,
      padding: '8px 16px',
      background: 'var(--bg-secondary, #1e1e2e)',
      borderRadius: 8,
      flexWrap: 'wrap',
      marginBottom: 8,
      border: '1px solid var(--accent, #6366f1)',
    }}>
      {timers.map(t => {
        const pct = t.total_seconds > 0 ? (t.remaining_seconds / t.total_seconds) * 100 : 0;
        const isUrgent = t.remaining_seconds <= 10;
        return (
          <div key={t.id} style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
          }}>
            <span style={{ fontSize: '0.7rem', opacity: 0.6 }}>{t.type === 'reminder' ? '🔔' : '⏱️'} {t.message}</span>
            <div style={{
              fontWeight: 'bold',
              fontSize: '1.1rem',
              fontVariantNumeric: 'tabular-nums',
              color: isUrgent ? '#ef4444' : 'var(--accent, #6366f1)',
            }}>
              {String(Math.floor(t.remaining_seconds / 60)).padStart(2, '0')}:
              {String(Math.floor(t.remaining_seconds % 60)).padStart(2, '0')}
            </div>
            <div style={{
              width: 60,
              height: 3,
              background: 'var(--bg-tertiary, #313244)',
              borderRadius: 2,
              overflow: 'hidden',
            }}>
              <div style={{
                width: `${pct}%`,
                height: '100%',
                background: isUrgent ? '#ef4444' : 'var(--accent, #6366f1)',
                transition: 'width 0.3s linear',
              }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
