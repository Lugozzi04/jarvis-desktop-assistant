import { useState, useEffect } from 'react';

interface ModelInfo {
  name: string;
  display: string;
  size_gb: number;
  category: string;
  description: string;
  speed: string;
  quality: string;
  recommended: boolean;
  installed: boolean;
  download_command: string;
  reason: string;
  tier_badge: string;
}

interface TierInfo {
  key: string;
  label: string;
  max_ram_gb: number;
  models: ModelInfo[];
  installed_count: number;
}

interface ModelSelectorProps {
  selectedModel: string | null;
  onSelectModel: (model: string | null) => void;
}

export function ModelSelector({ selectedModel, onSelectModel }: ModelSelectorProps) {
  const [tiers, setTiers] = useState<TierInfo[]>([]);
  const [ollamaRunning, setOllamaRunning] = useState(false);
  const [installedCount, setInstalledCount] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState('');

  useEffect(() => {
    loadModels();
  }, []);

  // Also try to load from localStorage on first render
  useEffect(() => {
    const saved = localStorage.getItem('jarvis_selected_model');
    if (saved && !selectedModel) {
      onSelectModel(saved);
    }
  }, []);

  const loadModels = async () => {
    try {
      const res = await fetch('http://localhost:8400/api/models');
      const data = await res.json();
      setTiers(data.tiers || []);
      setOllamaRunning(data.ollama_running);
      setInstalledCount(data.installed_count);
    } catch {}
  };

  const handleCopyDownload = async (cmd: string) => {
    try {
      await navigator.clipboard.writeText(cmd);
      setCopiedCmd(cmd);
      setTimeout(() => setCopiedCmd(''), 2000);
    } catch {}
  };

  const handleSelect = (modelName: string) => {
    onSelectModel(modelName);
    localStorage.setItem('jarvis_selected_model', modelName);
  };

  const handleReset = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectModel(null);
    localStorage.removeItem('jarvis_selected_model');
  };

  const getCurrentModelName = (): string => {
    if (!selectedModel) return 'Default (.env)';
    for (const tier of tiers) {
      for (const m of tier.models) {
        if (m.name === selectedModel) return m.display;
      }
    }
    return selectedModel;
  };

  const currentDisplay = getCurrentModelName();

  return (
    <div className="dash-model-selector">
      {/* ── Toggle button (compact card style) ── */}
      <div
        className="dash-model-toggle"
        onClick={() => { setExpanded(!expanded); if (!expanded) loadModels(); }}
      >
        <div className="dash-model-toggle-left">
          <span className="dash-model-icon">🧠</span>
          <div className="dash-model-toggle-info">
            <span className="dash-model-toggle-label">Modello AI</span>
            <span className="dash-model-toggle-name">
              {selectedModel ? (
                <>
                  <span className="dot-selected" /> {currentDisplay}
                </>
              ) : (
                <>
                  <span className="dot-default" /> {currentDisplay}
                </>
              )}
            </span>
          </div>
        </div>
        <div className="dash-model-toggle-right">
          {ollamaRunning ? (
            <span className="dash-model-badge installed">{installedCount} installati</span>
          ) : (
            <span className="dash-model-badge offline">Ollama offline</span>
          )}
          <span className="dash-model-arrow">{expanded ? '▴' : '▾'}</span>
        </div>
      </div>

      {/* ── Expanded panel ── */}
      {expanded && (
        <div className="dash-model-panel">
          {/* Header */}
          <div className="dash-model-panel-header">
            <div>
              <strong>🧠 Selettore Modelli</strong>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: 8 }}>
                {ollamaRunning
                  ? `🟢 Ollama online · ${installedCount} modelli installati`
                  : '⚫ Ollama non raggiungibile'}
              </span>
            </div>
            {selectedModel && (
              <button className="btn btn-sm btn-ghost" onClick={handleReset} style={{ padding: '2px 8px', fontSize: '0.7rem' }}>
                ↩ Default
              </button>
            )}
          </div>

          {/* Tiers */}
          {tiers.map(tier => {
            if (tier.models.length === 0) return null;

            return (
              <div key={tier.key} className="dash-model-tier">
                <div className="dash-model-tier-header">
                  <span className="dash-model-tier-label">{tier.label}</span>
                  {tier.installed_count > 0 && (
                    <span className="dash-model-tier-count">{tier.installed_count}/{tier.models.length} installati</span>
                  )}
                </div>
                <div className="dash-model-tier-models">
                  {tier.models.map(m => (
                    <div
                      key={m.name}
                      className={`dash-model-card ${m.installed ? 'installed' : 'not-installed'} ${selectedModel === m.name ? 'selected' : ''}`}
                      onClick={() => m.installed && handleSelect(m.name)}
                      title={m.installed ? `Usa ${m.display}` : `Non installato — ${m.download_command}`}
                    >
                      <div className="dash-model-card-left">
                        <span className="dash-model-card-name">
                          {m.installed ? '🟢' : '⚫'} {m.display}
                          {m.recommended && (
                            <span className="dash-model-star" title={m.tier_badge || 'Consigliato'}>
                              {m.tier_badge || '⭐ Consigliato'}
                            </span>
                          )}
                          {selectedModel === m.name && (
                            <span className="dash-model-active-badge">✅ In uso</span>
                          )}
                        </span>
                        <span className="dash-model-card-meta">
                          {m.speed} · {m.quality} · {m.size_gb} GB
                          {m.reason && ` — ${m.reason}`}
                        </span>
                      </div>
                      <div className="dash-model-card-right">
                        {!m.installed ? (
                          <button
                            className="dash-model-dl-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCopyDownload(m.download_command);
                            }}
                            title={`Copia: ${m.download_command}`}
                          >
                            {copiedCmd === m.download_command ? '✅ Copiato!' : '📥 Scarica'}
                          </button>
                        ) : selectedModel === m.name ? (
                          <span className="dash-model-check">✅</span>
                        ) : (
                          <span className="dash-model-click-hint">Clicca per usare</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}

          {/* Footer */}
          <div className="dash-model-panel-footer">
            <span>💡 Scarica nuovi modelli: <code>ollama pull nome-modello</code></span>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
              I modelli non installati appaiono in grigio. Clicca "📥 Scarica" per copiare il comando.
            </span>
          </div>
        </div>
      )}

      <style>{`
        .dash-model-selector {
          margin-bottom: 16px;
        }

        /* ── Toggle (card style) ── */
        .dash-model-toggle {
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: var(--bg-card, #1a1d2e);
          border: 1px solid var(--border, #2a2d3e);
          border-radius: var(--radius-lg, 12px);
          padding: 12px 16px;
          cursor: pointer;
          transition: all 0.2s;
          gap: 12px;
        }
        .dash-model-toggle:hover {
          border-color: var(--accent, #6366f1);
          box-shadow: 0 0 0 2px rgba(99,102,241,0.15);
        }

        .dash-model-toggle-left {
          display: flex;
          align-items: center;
          gap: 10px;
          flex: 1;
          min-width: 0;
        }

        .dash-model-icon {
          font-size: 1.6rem;
          flex-shrink: 0;
        }

        .dash-model-toggle-info {
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 0;
        }

        .dash-model-toggle-label {
          font-size: 0.7rem;
          color: var(--text-muted, #8b8fa3);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .dash-model-toggle-name {
          font-size: 0.9rem;
          font-weight: 600;
          color: var(--text-primary, #e4e6f0);
          display: flex;
          align-items: center;
          gap: 6px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .dot-selected {
          width: 8px; height: 8px; border-radius: 50%;
          background: #22c55e;
          flex-shrink: 0;
        }
        .dot-default {
          width: 8px; height: 8px; border-radius: 50%;
          background: var(--text-muted, #8b8fa3);
          flex-shrink: 0;
        }

        .dash-model-toggle-right {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-shrink: 0;
        }

        .dash-model-badge {
          font-size: 0.65rem;
          padding: 2px 8px;
          border-radius: 10px;
          font-weight: 500;
        }
        .dash-model-badge.installed {
          background: rgba(34,197,94,0.15);
          color: #22c55e;
        }
        .dash-model-badge.offline {
          background: rgba(239,68,68,0.15);
          color: #ef4444;
        }

        .dash-model-arrow {
          color: var(--text-muted, #8b8fa3);
          font-size: 0.65rem;
        }

        /* ── Expanded Panel ── */
        .dash-model-panel {
          margin-top: 8px;
          background: var(--bg-secondary, #161822);
          border: 1px solid var(--border, #2a2d3e);
          border-radius: var(--radius-lg, 12px);
          overflow: hidden;
          animation: slideDown 0.2s ease-out;
        }

        @keyframes slideDown {
          from { opacity: 0; transform: translateY(-8px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .dash-model-panel-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          border-bottom: 1px solid var(--border, #2a2d3e);
          font-size: 0.85rem;
          background: var(--bg-card, #1a1d2e);
        }

        .dash-model-panel-footer {
          display: flex;
          flex-direction: column;
          gap: 4px;
          padding: 10px 16px;
          border-top: 1px solid var(--border, #2a2d3e);
          font-size: 0.7rem;
          color: var(--text-muted, #8b8fa3);
          background: var(--bg-card, #1a1d2e);
        }
        .dash-model-panel-footer code {
          background: var(--bg-tertiary, #313244);
          padding: 1px 6px;
          border-radius: 4px;
          font-size: 0.7rem;
        }

        /* ── Tier sections ── */
        .dash-model-tier {
          border-bottom: 1px solid var(--border, #2a2d3e);
        }
        .dash-model-tier:last-child {
          border-bottom: none;
        }

        .dash-model-tier-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 16px 4px;
        }

        .dash-model-tier-label {
          font-size: 0.75rem;
          font-weight: 700;
          color: var(--accent, #6366f1);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .dash-model-tier-count {
          font-size: 0.65rem;
          color: var(--text-muted, #8b8fa3);
        }

        .dash-model-tier-models {
          padding: 4px 12px 8px;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        /* ── Model cards ── */
        .dash-model-card {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 12px;
          border-radius: 8px;
          transition: background 0.15s;
          gap: 10px;
          position: relative;
        }
        .dash-model-card.installed {
          cursor: pointer;
        }
        .dash-model-card.installed:hover {
          background: var(--bg-hover, rgba(99,102,241,0.08));
        }
        .dash-model-card.not-installed {
          cursor: default;
          opacity: 0.5;
        }
        .dash-model-card.selected {
          background: rgba(99,102,241,0.12);
          border: 1px solid var(--accent, #6366f1);
        }

        .dash-model-card-left {
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 0;
          flex: 1;
        }

        .dash-model-card-name {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-primary, #e4e6f0);
          display: flex;
          align-items: center;
          gap: 6px;
          flex-wrap: wrap;
        }

        .dash-model-star {
          font-size: 0.65rem;
          background: rgba(250,204,21,0.2);
          color: #facc15;
          padding: 1px 6px;
          border-radius: 4px;
          font-weight: 600;
          white-space: nowrap;
        }

        .dash-model-active-badge {
          font-size: 0.65rem;
          background: rgba(34,197,94,0.2);
          color: #22c55e;
          padding: 1px 6px;
          border-radius: 4px;
          font-weight: 600;
        }

        .dash-model-card-meta {
          font-size: 0.7rem;
          color: var(--text-muted, #8b8fa3);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .dash-model-card-right {
          flex-shrink: 0;
          display: flex;
          align-items: center;
        }

        .dash-model-click-hint {
          font-size: 0.65rem;
          color: var(--text-muted, #8b8fa3);
          opacity: 0;
          transition: opacity 0.15s;
        }
        .dash-model-card.installed:hover .dash-model-click-hint {
          opacity: 1;
        }

        .dash-model-dl-btn {
          background: var(--accent, #6366f1);
          color: #fff;
          border: none;
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 0.7rem;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.2s;
        }
        .dash-model-dl-btn:hover {
          background: #818cf8;
        }

        .dash-model-check {
          font-size: 0.85rem;
        }
      `}</style>
    </div>
  );
}
