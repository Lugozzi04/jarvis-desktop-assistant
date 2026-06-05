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
}

interface CategoryInfo {
  key: string;
  label: string;
  models: ModelInfo[];
}

interface ModelSelectorProps {
  selectedModel: string | null;
  onSelectModel: (model: string) => void;
}

export function ModelSelector({ selectedModel, onSelectModel }: ModelSelectorProps) {
  const [categories, setCategories] = useState<CategoryInfo[]>([]);
  const [ollamaRunning, setOllamaRunning] = useState(false);
  const [installedCount, setInstalledCount] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState('');

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const res = await fetch('http://localhost:8400/api/models');
      const data = await res.json();
      setCategories(data.categories || []);
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

  const getCurrentModelName = () => {
    if (!selectedModel) return 'Default (qwen2.5:7b)';
    // Find display name
    for (const cat of categories) {
      for (const m of cat.models) {
        if (m.name === selectedModel) return m.display;
      }
    }
    return selectedModel;
  };

  return (
    <div className="model-selector">
      <button
        className="model-selector-toggle"
        onClick={() => { setExpanded(!expanded); if (!expanded) loadModels(); }}
      >
        <span className="model-icon">🧠</span>
        <span className="model-name">{getCurrentModelName()}</span>
        <span className="model-arrow">{expanded ? '▴' : '▾'}</span>
      </button>

      {expanded && (
        <div className="model-dropdown">
          <div className="model-dropdown-header">
            <span>{ollamaRunning ? `🟢 ${installedCount} modelli installati` : '⚫ Ollama offline'}</span>
          </div>

          {categories.map(cat => {
            const installedInCat = cat.models.filter(m => m.installed);
            if (installedInCat.length === 0 && cat.key !== 'other') return null;

            return (
              <div key={cat.key} className="model-category">
                <div className="model-category-label">{cat.label}</div>
                {cat.models.map(m => (
                  <div
                    key={m.name}
                    className={`model-item ${m.installed ? 'installed' : 'not-installed'} ${selectedModel === m.name ? 'selected' : ''}`}
                    onClick={() => m.installed && onSelectModel(m.name)}
                  >
                    <div className="model-item-left">
                      <span className="model-item-name">
                        {m.recommended && <span className="model-star" title="Consigliato">⭐</span>}
                        {m.display}
                      </span>
                      <span className="model-item-speed">
                        {m.speed} · {m.quality} · {m.size_gb} GB
                      </span>
                    </div>
                    <div className="model-item-right">
                      {!m.installed ? (
                        <button
                          className="model-download-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCopyDownload(m.download_command);
                          }}
                          title="Copia comando download"
                        >
                          {copiedCmd === m.download_command ? '✅ Copiato!' : '📥 Scarica'}
                        </button>
                      ) : selectedModel === m.name ? (
                        <span className="model-check">✅</span>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            );
          })}

          <div className="model-dropdown-footer">
            <small>💡 Scarica nuovi modelli dal terminale con <code>ollama pull nome-modello</code></small>
          </div>
        </div>
      )}

      <style>{`
        .model-selector {
          position: relative;
          z-index: 200;
        }

        .model-selector-toggle {
          display: flex;
          align-items: center;
          gap: 6px;
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 10px;
          padding: 6px 12px;
          cursor: pointer;
          font-size: 0.8rem;
          color: var(--text-primary);
          transition: all 0.2s;
        }
        .model-selector-toggle:hover {
          border-color: var(--accent);
          background: var(--bg-hover);
        }

        .model-icon { font-size: 1rem; }
        .model-name { 
          font-weight: 500; 
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 140px;
        }
        .model-arrow { color: var(--text-muted); font-size: 0.65rem; }

        .model-dropdown {
          position: absolute;
          top: 100%;
          right: 0;
          margin-top: 4px;
          width: 320px;
          max-height: 420px;
          overflow-y: auto;
          background: var(--bg-secondary);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          box-shadow: 0 8px 32px rgba(0,0,0,0.4);
          z-index: 200;
        }

        .model-dropdown-header {
          padding: 10px 14px;
          font-size: 0.75rem;
          color: var(--text-muted);
          border-bottom: 1px solid var(--border);
          position: sticky;
          top: 0;
          background: var(--bg-secondary);
        }

        .model-category {
          padding: 4px 0;
        }

        .model-category-label {
          padding: 6px 14px 2px;
          font-size: 0.7rem;
          font-weight: 600;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .model-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 14px;
          cursor: pointer;
          transition: background 0.15s;
          gap: 8px;
        }
        .model-item.installed:hover {
          background: var(--bg-hover);
        }
        .model-item.not-installed {
          cursor: default;
          opacity: 0.55;
        }
        .model-item.selected {
          background: var(--accent-glow);
          border-left: 3px solid var(--accent);
        }

        .model-item-left {
          display: flex;
          flex-direction: column;
          min-width: 0;
          flex: 1;
        }

        .model-item-name {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-primary);
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .model-star { font-size: 0.8rem; }

        .model-item-speed {
          font-size: 0.68rem;
          color: var(--text-muted);
          margin-top: 1px;
        }

        .model-item-right {
          flex-shrink: 0;
        }

        .model-check {
          font-size: 0.8rem;
        }

        .model-download-btn {
          background: var(--accent);
          color: #fff;
          border: none;
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 0.7rem;
          cursor: pointer;
          font-weight: 500;
          opacity: 0.9;
          transition: opacity 0.2s;
        }
        .model-download-btn:hover {
          opacity: 1;
        }

        .model-dropdown-footer {
          padding: 10px 14px;
          border-top: 1px solid var(--border);
          font-size: 0.7rem;
          color: var(--text-muted);
          position: sticky;
          bottom: 0;
          background: var(--bg-secondary);
        }

        .model-dropdown-footer code {
          background: var(--bg-card);
          padding: 1px 5px;
          border-radius: 4px;
          font-size: 0.7rem;
        }
      `}</style>
    </div>
  );
}
