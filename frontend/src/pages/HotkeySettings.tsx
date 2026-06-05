import { useState, useCallback, useEffect, useRef } from 'react';
import { api } from '../api';

type ModifierKey = 'ctrl' | 'alt' | 'shift' | 'cmd';

const MODIFIER_LABELS: Record<ModifierKey, string> = {
  ctrl: 'Ctrl',
  alt: 'Alt',
  shift: 'Shift',
  cmd: 'Win',
};

export default function HotkeySettings() {
  const [modifiers, setModifiers] = useState<ModifierKey[]>(['alt']);
  const [key, setKey] = useState('space');
  const [listening, setListening] = useState(false);
  const [saved, setSaved] = useState(true);
  const [status, setStatus] = useState('');
  const keyRef = useRef<HTMLDivElement>(null);

  // Load current config
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('http://localhost:8400/api/hotkeys');
        const data = await res.json();
        const mods = (data.modifiers || ['alt']).filter((m: string) =>
          ['ctrl', 'alt', 'shift', 'cmd'].includes(m)
        ) as ModifierKey[];
        setModifiers(mods.length ? mods : ['alt']);
        setKey(data.key || 'space');
      } catch {}
    })();
  }, []);

  // Save
  const save = async () => {
    try {
      const m = modifiers.length ? modifiers : ['alt'];
      await fetch('http://localhost:8400/api/hotkeys', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modifiers: m, key }),
      });
      setSaved(true);
      setStatus('Salvato! Riavvia la modalità tray per applicare.');
    } catch {
      setStatus('Errore nel salvataggio.');
    }
  };

  // Auto-save on change
  useEffect(() => {
    if (!saved && modifiers.length && key) {
      const t = setTimeout(save, 500);
      return () => clearTimeout(t);
    }
  }, [modifiers, key]);

  // Toggle modifier
  const toggleMod = (mod: ModifierKey) => {
    setModifiers(prev =>
      prev.includes(mod) ? prev.filter(m => m !== mod) : [...prev, mod]
    );
    setSaved(false);
  };

  // Key capture
  const startListening = () => {
    setListening(true);
    setSaved(false);
    keyRef.current?.focus();
  };

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!listening) return;

      // Map key
      let keyName = '';
      if (e.code === 'Space') keyName = 'space';
      else if (e.code === 'Enter') keyName = 'enter';
      else if (e.code === 'Escape') keyName = 'escape';
      else if (e.code === 'Tab') keyName = 'tab';
      else if (e.code === 'Backspace') keyName = 'backspace';
      else if (e.code.startsWith('F') && e.code.length <= 3) keyName = e.code.toLowerCase();
      else if (e.code.startsWith('Key')) keyName = e.code.replace('Key', '').toLowerCase();
      else if (e.code.startsWith('Digit')) keyName = e.code.replace('Digit', '');
      else keyName = e.key?.toLowerCase() || '';

      if (keyName && keyName.length <= 10) {
        setKey(keyName);
        setListening(false);
        setSaved(false);
      }
    },
    [listening]
  );

  const resetToDefault = () => {
    setModifiers(['alt']);
    setKey('space');
    setSaved(false);
  };

  const comboLabel = [...modifiers.map(m => MODIFIER_LABELS[m]), key.toUpperCase()].join(' + ');

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: '20px 0' }}>
      <h2 style={{ marginBottom: 24 }}>⌨️ Scorciatoia Globale</h2>

      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 24 }}>
        Scegli la combinazione di tasti per attivare JARVIS ovunque ti trovi.
        Premi la combo e JARVIS analizzerà lo schermo.
      </p>

      {/* Combo preview */}
      <div className="hotkey-combo-card">
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>SCORCIATOIA ATTUALE</div>
        <div className="hotkey-combo">{comboLabel}</div>
      </div>

      {/* Modifiers */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: 10 }}>Tasti modificatori</div>
        <div style={{ display: 'flex', gap: 8 }}>
          {(Object.keys(MODIFIER_LABELS) as ModifierKey[]).map(mod => (
            <button
              key={mod}
              className={`hotkey-mod-btn ${modifiers.includes(mod) ? 'active' : ''}`}
              onClick={() => toggleMod(mod)}
            >
              {MODIFIER_LABELS[mod]}
            </button>
          ))}
        </div>
      </div>

      {/* Key selector */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: 10 }}>Tasto</div>
        <div
          ref={keyRef}
          tabIndex={0}
          className={`hotkey-key-box ${listening ? 'listening' : ''}`}
          onClick={startListening}
          onKeyDown={handleKeyDown}
          onBlur={() => setListening(false)}
        >
          {listening ? (
            <span className="hotkey-listening">Premi un tasto...</span>
          ) : (
            <span className="hotkey-key-name">{key.toUpperCase()}</span>
          )}
          <span className="hotkey-key-hint">
            {listening ? 'in ascolto...' : 'clicca per cambiare'}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <button className="btn btn-secondary" onClick={resetToDefault}>
          🔄 Reset (Alt+Spazio)
        </button>
        {status && (
          <span style={{ fontSize: '0.85rem', color: 'var(--success)' }}>{status}</span>
        )}
      </div>

      <div style={{ marginTop: 24, padding: 12, background: 'var(--bg-card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        💡 <strong>Nota:</strong> Le modifiche hanno effetto al prossimo riavvio della modalità tray
        (<code>start.ps1 --tray</code>). La modalità finestra normale non usa la scorciatoia globale.
      </div>

      <style>{`
        .hotkey-combo-card {
          background: var(--bg-card);
          border: 2px solid var(--accent);
          border-radius: var(--radius-lg);
          padding: 20px 24px;
          text-align: center;
          margin-bottom: 24px;
        }

        .hotkey-combo {
          font-size: 2rem;
          font-weight: 700;
          font-variant-numeric: tabular-nums;
          letter-spacing: 2px;
          background: linear-gradient(135deg, var(--accent), #a78bfa);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .hotkey-mod-btn {
          padding: 8px 18px;
          border-radius: var(--radius);
          border: 1px solid var(--border);
          background: var(--bg-primary);
          color: var(--text-secondary);
          cursor: pointer;
          font-size: 0.85rem;
          font-weight: 500;
          transition: all 0.2s;
        }
        .hotkey-mod-btn:hover {
          background: var(--bg-hover);
          border-color: var(--accent);
          color: var(--text-primary);
        }
        .hotkey-mod-btn.active {
          background: var(--accent);
          border-color: var(--accent);
          color: #fff;
          box-shadow: 0 0 12px rgba(99, 102, 241, 0.3);
        }

        .hotkey-key-box {
          width: 100%;
          padding: 20px;
          border-radius: var(--radius-lg);
          border: 2px dashed var(--border);
          background: var(--bg-primary);
          text-align: center;
          cursor: pointer;
          transition: all 0.2s;
          outline: none;
        }
        .hotkey-key-box:hover {
          border-color: var(--accent);
          background: var(--bg-hover);
        }
        .hotkey-key-box:focus,
        .hotkey-key-box.listening {
          border-color: var(--accent);
          border-style: solid;
          box-shadow: 0 0 20px rgba(99, 102, 241, 0.15);
          animation: hotkey-pulse 1.5s infinite;
        }

        @keyframes hotkey-pulse {
          0%, 100% { box-shadow: 0 0 20px rgba(99, 102, 241, 0.15); }
          50% { box-shadow: 0 0 30px rgba(99, 102, 241, 0.3); }
        }

        .hotkey-key-name {
          display: block;
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--text-primary);
          margin-bottom: 4px;
        }

        .hotkey-listening {
          display: block;
          font-size: 1.2rem;
          font-weight: 600;
          color: var(--accent);
          margin-bottom: 4px;
        }

        .hotkey-key-hint {
          display: block;
          font-size: 0.7rem;
          color: var(--text-muted);
        }
      `}</style>
    </div>
  );
}
