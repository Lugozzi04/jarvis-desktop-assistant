import { useState, useEffect, useRef, useCallback } from 'react';

interface Timer {
  id: string;
  type: string;
  message: string;
  total_seconds: number;
  remaining_seconds: number;
  remaining_display: string;
}

// Global notification state (module-level, shared across all pages)
let notifyTimerComplete: ((timer: Timer) => void) | null = null;
export function setTimerNotify(fn: (timer: Timer) => void) { notifyTimerComplete = fn; }

export function TimerBar() {
  const [timers, setTimers] = useState<Timer[]>([]);
  const [completedTimer, setCompletedTimer] = useState<Timer | null>(null);
  const [showConfetti, setShowConfetti] = useState(false);
  const notifiedRef = useRef<Set<string>>(new Set());

  // Register global notification callback
  useEffect(() => {
    setTimerNotify((timer: Timer) => {
      setCompletedTimer(timer);
      setShowConfetti(true);
      setTimeout(() => setCompletedTimer(null), 5000);
      setTimeout(() => setShowConfetti(false), 3000);
    });
    return () => { notifyTimerComplete = null; };
  }, []);

  // Dismiss handler
  const dismiss = useCallback(() => {
    setCompletedTimer(null);
    setShowConfetti(false);
  }, []);

  useEffect(() => {
    const poll = async () => {
      try {
        const base = window.location.hostname ? window.location.origin : 'http://localhost:8400';
        const res = await fetch(`${base}/api/timers`);
        const data = await res.json();
        if (data.timers) {
          setTimers(data.timers);

          // Check for newly completed timers
          for (const t of data.timers) {
            if (t.remaining_seconds <= 0 && !notifiedRef.current.has(t.id)) {
              notifiedRef.current.add(t.id);
              if (notifyTimerComplete) {
                notifyTimerComplete(t);
              } else {
                setCompletedTimer(t);
                setShowConfetti(true);
                setTimeout(() => setCompletedTimer(null), 5000);
                setTimeout(() => setShowConfetti(false), 3000);
              }
            }
          }
        }
      } catch {
        // silent — backend not ready yet
      }
    };
    poll();
    const interval = setInterval(poll, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      {/* Confetti Overlay */}
      {showConfetti && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          pointerEvents: 'none',
          zIndex: 9999,
          overflow: 'hidden',
        }}>
          {Array.from({ length: 50 }).map((_, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                top: -20,
                left: `${Math.random() * 100}%`,
                width: 10,
                height: 10,
                background: ['#ef4444', '#f59e0b', '#10b981', '#6366f1', '#ec4899', '#06b6d4'][i % 6],
                borderRadius: Math.random() > 0.5 ? '50%' : 2,
                animation: `confetti-fall ${1.5 + Math.random() * 2}s ease-in forwards`,
                animationDelay: `${Math.random() * 0.8}s`,
                transform: `rotate(${Math.random() * 360}deg)`,
              }}
            />
          ))}
        </div>
      )}

      {/* Timer bars */}
      {timers.length > 0 && (
        <div style={{
          display: 'flex',
          gap: 12,
          padding: '6px 16px',
          background: 'var(--bg-secondary, #1e1e2e)',
          flexWrap: 'wrap',
          borderBottom: '1px solid var(--accent, #6366f1)',
          alignItems: 'center',
          minHeight: 44,
        }}>
          {timers.filter(t => t.remaining_seconds > 0).map(t => {
            const pct = t.total_seconds > 0 ? (t.remaining_seconds / t.total_seconds) * 100 : 0;
            const isUrgent = t.remaining_seconds <= 10;
            return (
              <div key={t.id} style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}>
                <span style={{ fontSize: '0.75rem' }}>
                  {t.type === 'reminder' ? '🔔' : '⏱️'} {t.message}
                </span>
                <span style={{
                  fontWeight: 'bold',
                  fontSize: '0.95rem',
                  fontVariantNumeric: 'tabular-nums',
                  color: isUrgent ? '#ef4444' : 'var(--accent, #6366f1)',
                }}>
                  {String(Math.floor(t.remaining_seconds / 60)).padStart(2, '0')}:
                  {String(Math.floor(t.remaining_seconds % 60)).padStart(2, '0')}
                </span>
                <div style={{
                  width: 40,
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
          {timers.filter(t => t.remaining_seconds <= 0).length > 0 && (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {timers.filter(t => t.remaining_seconds <= 0).length} completed — dismiss in chat
            </span>
          )}
        </div>
      )}

      {/* Timer Completion Notification */}
      {completedTimer && (
        <div
          onClick={dismiss}
          style={{
            position: 'fixed',
            top: 20,
            right: 20,
            zIndex: 10000,
            background: 'var(--accent, #6366f1)',
            color: 'white',
            padding: '16px 24px',
            borderRadius: 12,
            boxShadow: '0 8px 32px rgba(99, 102, 241, 0.4)',
            cursor: 'pointer',
            animation: 'slideIn 0.3s ease-out',
            maxWidth: 320,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <span style={{ fontSize: '1.5rem' }}>⏰</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>
              {completedTimer.type === 'reminder' ? '🔔 Reminder' : '⏱️ Timer Finished'}!
            </div>
            <div style={{ fontSize: '0.85rem', opacity: 0.9 }}>
              {completedTimer.message}
            </div>
            <div style={{ fontSize: '0.7rem', opacity: 0.7, marginTop: 4 }}>
              Click to dismiss
            </div>
          </div>
        </div>
      )}

      {/* Inject keyframes for animations */}
      <style>{`
        @keyframes confetti-fall {
          0% { transform: translateY(0) rotate(0deg); opacity: 1; }
          100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
        }
        @keyframes slideIn {
          from { transform: translateX(100px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </>
  );
}
