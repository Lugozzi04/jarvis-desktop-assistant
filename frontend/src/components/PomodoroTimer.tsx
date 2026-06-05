import { useState, useEffect, useRef, useCallback } from 'react';

type TimerState = 'idle' | 'focus' | 'short_break' | 'long_break';

interface PomodoroTimerProps {
  onSessionComplete?: (type: TimerState, duration: number) => void;
}

const STORAGE_KEY = 'jarvis-pomodoro-settings';
const DEFAULT_FOCUS = 25;
const DEFAULT_SHORT_BREAK = 5;
const DEFAULT_LONG_BREAK = 15;

function loadSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { focus: DEFAULT_FOCUS, shortBreak: DEFAULT_SHORT_BREAK, longBreak: DEFAULT_LONG_BREAK };
}

function saveSettings(s: { focus: number; shortBreak: number; longBreak: number }) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); } catch {}
}

// ── Confetti Animation ──

function spawnConfetti(container: HTMLElement) {
  const colors = ['#6366f1', '#a78bfa', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899'];
  const particles: HTMLDivElement[] = [];

  for (let i = 0; i < 60; i++) {
    const el = document.createElement('div');
    el.style.cssText = `
      position: fixed;
      width: ${Math.random() * 10 + 6}px;
      height: ${Math.random() * 10 + 6}px;
      background: ${colors[Math.floor(Math.random() * colors.length)]};
      left: ${Math.random() * 100}vw;
      top: -20px;
      border-radius: ${Math.random() > 0.5 ? '50%' : '2px'};
      pointer-events: none;
      z-index: 99999;
      animation: confetti-fall ${Math.random() * 2 + 2}s ease-out forwards;
      animation-delay: ${Math.random() * 0.5}s;
      opacity: 0;
    `;
    document.body.appendChild(el);
    particles.push(el);
  }

  setTimeout(() => {
    particles.forEach(el => el.remove());
  }, 4000);
}

export function PomodoroTimer({ onSessionComplete }: PomodoroTimerProps) {
  const [settings, setSettings] = useState(loadSettings);
  const [state, setState] = useState<TimerState>('idle');
  const [timeLeft, setTimeLeft] = useState(settings.focus * 60);
  const [sessions, setSessions] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [celebrating, setCelebrating] = useState(false);
  const intervalRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);
  const cardRef = useRef<HTMLDivElement>(null);

  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const getDuration = useCallback((s: TimerState) => {
    switch (s) {
      case 'focus': return settings.focus;
      case 'short_break': return settings.shortBreak;
      case 'long_break': return settings.longBreak;
      default: return settings.focus;
    }
  }, [settings]);

  const startTimer = useCallback((newState: TimerState, duration: number) => {
    clearTimer();
    setState(newState);
    setTimeLeft(duration * 60);
    setIsRunning(true);
    startTimeRef.current = Date.now();

    intervalRef.current = window.setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearTimer();
          setIsRunning(false);
          const elapsed = Math.round((Date.now() - startTimeRef.current) / 1000);
          onSessionComplete?.(newState, elapsed);

          if (newState === 'focus') {
            setSessions(s => s + 1);
            // Celebration!
            setCelebrating(true);
            spawnConfetti(document.body);
            setTimeout(() => setCelebrating(false), 4000);
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, [clearTimer, onSessionComplete]);

  useEffect(() => clearTimer, [clearTimer]);

  const handleStart = () => {
    if (state === 'idle') {
      startTimer('focus', settings.focus);
    } else {
      setIsRunning(!isRunning);
      if (!isRunning && timeLeft > 0) {
        startTimeRef.current = Date.now();
        intervalRef.current = window.setInterval(() => {
          setTimeLeft(prev => {
            if (prev <= 1) { clearTimer(); setIsRunning(false); return 0; }
            return prev - 1;
          });
        }, 1000);
      } else if (isRunning) {
        clearTimer();
      }
    }
  };

  const handleReset = () => {
    clearTimer();
    setIsRunning(false);
    setState('idle');
    setTimeLeft(settings.focus * 60);
    setCelebrating(false);
  };

  const handleSkipToBreak = () => {
    const isLong = (sessions + 1) % 4 === 0;
    const breakType = isLong ? 'long_break' : 'short_break';
    const duration = isLong ? settings.longBreak : settings.shortBreak;
    startTimer(breakType, duration);
  };

  const handleSaveSettings = (field: string, value: number) => {
    const clamped = Math.max(1, Math.min(120, value));
    const newSettings = { ...settings, [field]: clamped };
    setSettings(newSettings);
    saveSettings(newSettings);
    if (state === 'idle') setTimeLeft(newSettings.focus * 60);
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const progress = state === 'idle'
    ? 100
    : Math.round((timeLeft / (getDuration(state) * 60)) * 100);

  const stateLabel: Record<TimerState, string> = {
    idle: '⚡ Pronto',
    focus: '🎯 Focus',
    short_break: '☕ Pausa',
    long_break: '🧘 Pausa Lunga',
  };

  return (
    <div className="pomodoro-card" ref={cardRef}>
      {/* Celebration overlay */}
      {celebrating && (
        <div className="pomodoro-celebration">
          <div className="celebration-text">🎉 Sessione Completata!</div>
          <div className="celebration-sub">{sessions} sessioni oggi</div>
        </div>
      )}

      <div className="pomodoro-header">
        <span className="pomodoro-state">{stateLabel[state]}</span>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span className="pomodoro-sessions">{sessions} sessioni</span>
          <button
            className="btn btn-ghost btn-sm"
            style={{ padding: '2px 6px', fontSize: '0.8rem', borderRadius: 6 }}
            onClick={() => setShowSettings(!showSettings)}
            title="Impostazioni timer"
          >
            ⚙️
          </button>
        </div>
      </div>

      {/* Settings panel */}
      {showSettings && (
        <div className="pomodoro-settings">
          <div className="setting-row">
            <label>🎯 Focus</label>
            <div className="setting-input-group">
              <button onClick={() => handleSaveSettings('focus', settings.focus - 5)}>−5</button>
              <input
                type="number"
                value={settings.focus}
                min={1} max={120}
                onChange={e => handleSaveSettings('focus', parseInt(e.target.value) || 25)}
              />
              <span>min</span>
              <button onClick={() => handleSaveSettings('focus', settings.focus + 5)}>+5</button>
            </div>
          </div>
          <div className="setting-row">
            <label>☕ Pausa</label>
            <div className="setting-input-group">
              <button onClick={() => handleSaveSettings('shortBreak', settings.shortBreak - 1)}>−1</button>
              <input
                type="number"
                value={settings.shortBreak}
                min={1} max={60}
                onChange={e => handleSaveSettings('shortBreak', parseInt(e.target.value) || 5)}
              />
              <span>min</span>
              <button onClick={() => handleSaveSettings('shortBreak', settings.shortBreak + 1)}>+1</button>
            </div>
          </div>
          <div className="setting-row">
            <label>🧘 Pausa lunga</label>
            <div className="setting-input-group">
              <button onClick={() => handleSaveSettings('longBreak', settings.longBreak - 5)}>−5</button>
              <input
                type="number"
                value={settings.longBreak}
                min={1} max={120}
                onChange={e => handleSaveSettings('longBreak', parseInt(e.target.value) || 15)}
              />
              <span>min</span>
              <button onClick={() => handleSaveSettings('longBreak', settings.longBreak + 5)}>+5</button>
            </div>
          </div>
          <button
            className="btn btn-ghost btn-sm"
            style={{ marginTop: 8, width: '100%' }}
            onClick={() => {
              handleSaveSettings('focus', DEFAULT_FOCUS);
              handleSaveSettings('shortBreak', DEFAULT_SHORT_BREAK);
              handleSaveSettings('longBreak', DEFAULT_LONG_BREAK);
            }}
          >
            🔄 Reset default
          </button>
        </div>
      )}

      <div className="pomodoro-timer">
        <svg className="pomodoro-ring" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="54" fill="none" stroke="var(--border)" strokeWidth="4" />
          <circle
            cx="60" cy="60" r="54"
            fill="none"
            stroke={state === 'focus' ? 'var(--accent)' : state.includes('break') ? 'var(--success)' : 'var(--text-muted)'}
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 54}`}
            strokeDashoffset={`${2 * Math.PI * 54 * (1 - progress / 100)}`}
            transform="rotate(-90 60 60)"
            style={{ transition: 'stroke-dashoffset 1s linear, stroke 0.3s' }}
          />
        </svg>
        <div className="pomodoro-time-display">
          <span className="pomodoro-time">{formatTime(timeLeft)}</span>
          <span className="pomodoro-label">{isRunning ? 'in corso...' : state === 'idle' ? 'pronto' : 'in pausa'}</span>
        </div>
      </div>

      <div className="pomodoro-controls">
        <button className="btn btn-primary" onClick={handleStart}>
          {isRunning ? '⏸️ Pausa' : state === 'idle' ? '▶️ Inizia Focus' : '▶️ Riprendi'}
        </button>
        {state === 'focus' && (
          <button className="btn btn-secondary" onClick={handleSkipToBreak}>
            ⏭️ Pausa
          </button>
        )}
        <button className="btn btn-ghost" onClick={handleReset}>
          🔄 Reset
        </button>
      </div>

      <style>{`
        .pomodoro-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          padding: 24px;
          text-align: center;
          position: relative;
          overflow: hidden;
        }

        .pomodoro-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }

        .pomodoro-state {
          font-size: 1rem;
          font-weight: 600;
          color: var(--text-primary);
        }

        .pomodoro-sessions {
          font-size: 0.75rem;
          color: var(--text-secondary);
          background: var(--bg-hover);
          padding: 4px 10px;
          border-radius: 20px;
        }

        .pomodoro-settings {
          background: var(--bg-primary);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 12px;
          margin-bottom: 12px;
          text-align: left;
        }

        .setting-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
          font-size: 0.8rem;
        }

        .setting-row label {
          color: var(--text-secondary);
          min-width: 80px;
        }

        .setting-input-group {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .setting-input-group input {
          width: 50px;
          text-align: center;
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 6px;
          color: var(--text-primary);
          padding: 4px;
          font-size: 0.8rem;
          font-family: inherit;
        }

        .setting-input-group input:focus {
          outline: none;
          border-color: var(--accent);
        }

        .setting-input-group span {
          color: var(--text-muted);
          font-size: 0.7rem;
        }

        .setting-input-group button {
          background: var(--bg-hover);
          border: 1px solid var(--border);
          color: var(--text-secondary);
          border-radius: 4px;
          padding: 2px 8px;
          cursor: pointer;
          font-size: 0.7rem;
        }
        .setting-input-group button:hover {
          background: var(--bg-card);
          color: var(--text-primary);
        }

        .pomodoro-timer {
          position: relative;
          width: 160px;
          height: 160px;
          margin: 0 auto 20px;
        }

        .pomodoro-ring {
          width: 100%;
          height: 100%;
        }

        .pomodoro-time-display {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .pomodoro-time {
          font-size: 2.5rem;
          font-weight: 700;
          font-variant-numeric: tabular-nums;
          color: var(--text-primary);
          letter-spacing: 2px;
        }

        .pomodoro-label {
          font-size: 0.75rem;
          color: var(--text-muted);
          margin-top: 2px;
        }

        .pomodoro-controls {
          display: flex;
          gap: 8px;
          justify-content: center;
          flex-wrap: wrap;
        }

        .pomodoro-celebration {
          position: absolute;
          inset: 0;
          background: rgba(15, 17, 23, 0.85);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          z-index: 100;
          border-radius: var(--radius-lg);
          animation: celebration-pop 0.4s ease-out;
        }

        .celebration-text {
          font-size: 1.3rem;
          font-weight: 700;
          background: linear-gradient(135deg, var(--accent), #a78bfa, var(--success));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          margin-bottom: 4px;
        }

        .celebration-sub {
          font-size: 0.85rem;
          color: var(--text-secondary);
        }

        @keyframes celebration-pop {
          0% { opacity: 0; transform: scale(0.8); }
          60% { transform: scale(1.05); }
          100% { opacity: 1; transform: scale(1); }
        }

        @keyframes confetti-fall {
          0% { opacity: 1; transform: translateY(0) rotate(0deg); }
          100% { opacity: 0; transform: translateY(100vh) rotate(720deg); }
        }
      `}</style>
    </div>
  );
}
