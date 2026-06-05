import { useState, useEffect, useRef, useCallback } from 'react';

type TimerState = 'idle' | 'focus' | 'short_break' | 'long_break';

interface PomodoroTimerProps {
  onSessionComplete?: (type: TimerState, duration: number) => void;
}

const FOCUS_MINUTES = 25;
const SHORT_BREAK_MINUTES = 5;
const LONG_BREAK_MINUTES = 15;

export function PomodoroTimer({ onSessionComplete }: PomodoroTimerProps) {
  const [state, setState] = useState<TimerState>('idle');
  const [timeLeft, setTimeLeft] = useState(FOCUS_MINUTES * 60);
  const [sessions, setSessions] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const intervalRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);

  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const getDuration = useCallback((s: TimerState) => {
    switch (s) {
      case 'focus': return FOCUS_MINUTES;
      case 'short_break': return SHORT_BREAK_MINUTES;
      case 'long_break': return LONG_BREAK_MINUTES;
      default: return FOCUS_MINUTES;
    }
  }, []);

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
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, [clearTimer, onSessionComplete]);

  useEffect(() => {
    return clearTimer;
  }, [clearTimer]);

  const handleStart = () => {
    if (state === 'idle') {
      startTimer('focus', FOCUS_MINUTES);
    } else {
      // Resume or restart
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
    setTimeLeft(FOCUS_MINUTES * 60);
  };

  const handleSkipToBreak = () => {
    const isLong = (sessions + 1) % 4 === 0;
    const breakType = isLong ? 'long_break' : 'short_break';
    const duration = isLong ? LONG_BREAK_MINUTES : SHORT_BREAK_MINUTES;
    startTimer(breakType, duration);
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
    <div className="pomodoro-card">
      <div className="pomodoro-header">
        <span className="pomodoro-state">{stateLabel[state]}</span>
        <span className="pomodoro-sessions">{sessions} sessioni</span>
      </div>

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
        }

        .pomodoro-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .pomodoro-state {
          font-size: 1rem;
          font-weight: 600;
          color: var(--text-primary);
        }

        .pomodoro-sessions {
          font-size: 0.8rem;
          color: var(--text-secondary);
          background: var(--bg-hover);
          padding: 4px 10px;
          border-radius: 20px;
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
      `}</style>
    </div>
  );
}
