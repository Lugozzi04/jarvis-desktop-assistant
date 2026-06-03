import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from 'react';

const API = 'http://localhost:8400';

// ── Command Tree ──

interface SubOption {
  label: string;        // displayed name
  description?: string; // short hint
  placeholder?: string; // argument placeholder
  dynamic?: string;     // API path to fetch dynamic options (e.g., "/api/apps")
}

interface CommandDef {
  name: string;
  description: string;
  subs?: SubOption[];
}

const COMMANDS: CommandDef[] = [
  {
    name: 'open',
    description: 'Open an app, folder, or URL',
    subs: [
      { label: 'app', description: 'Launch an application', placeholder: '<app-name>', dynamic: '/api/apps' },
      { label: 'folder', description: 'Open a folder in Explorer', placeholder: '<path>' },
      { label: 'url', description: 'Open a URL in browser', placeholder: '<url>' },
    ],
  },
  {
    name: 'search',
    description: 'Search the web with AI summary',
  },
  {
    name: 'ask',
    description: 'Ask the LLM a question',
  },
  {
    name: 'timer',
    description: 'Set a countdown timer',
  },
  {
    name: 'remind',
    description: 'Set a reminder',
  },
  {
    name: 'workflow',
    description: 'Run a saved workflow',
  },
  {
    name: 'system',
    description: 'System info & control',
    subs: [
      { label: 'stats', description: 'CPU, RAM, disk usage' },
      { label: 'info', description: 'Detailed system information' },
      { label: 'processes', description: 'List running processes' },
      { label: 'network', description: 'Network interfaces & IP' },
      { label: 'shutdown', description: 'Shutdown the computer' },
      { label: 'restart', description: 'Restart the computer' },
      { label: 'volume up', description: 'Increase system volume' },
      { label: 'volume down', description: 'Decrease system volume' },
      { label: 'volume mute', description: 'Mute system audio' },
      { label: 'brightness up', description: 'Increase brightness' },
      { label: 'brightness down', description: 'Decrease brightness' },
      { label: 'battery', description: 'Battery status' },
    ],
  },
  {
    name: 'file',
    description: 'File operations',
    subs: [
      { label: 'search', description: 'Search for files by name', placeholder: '<query>' },
      { label: 'open', description: 'Open a file', placeholder: '<path>' },
    ],
  },
  {
    name: 'dev',
    description: 'Developer tools & commands',
    subs: [
      { label: 'lint', description: 'Run linter on project' },
      { label: 'format', description: 'Format code' },
      { label: 'test', description: 'Run test suite' },
      { label: 'coverage', description: 'Run tests with coverage' },
      { label: 'build', description: 'Build the project' },
      { label: 'clean', description: 'Clean build artifacts' },
      { label: 'docker-build', description: 'Build Docker image' },
      { label: 'docker-up', description: 'Start Docker containers' },
      { label: 'docker-down', description: 'Stop Docker containers' },
    ],
  },
  {
    name: 'auto',
    description: 'Automation management',
    subs: [
      { label: 'list', description: 'List all automations' },
      { label: 'disable', description: 'Disable an automation', placeholder: '<name>' },
    ],
  },
  {
    name: 'obs',
    description: 'OBS Studio controls',
    subs: [
      { label: 'open', description: 'Launch OBS Studio' },
    ],
  },
  {
    name: 'discord',
    description: 'Discord controls',
    subs: [
      { label: 'open', description: 'Launch Discord desktop app' },
      { label: 'web', description: 'Open Discord Web' },
    ],
  },
  {
    name: 'spotify',
    description: 'Spotify controls',
    subs: [
      { label: 'open', description: 'Launch Spotify' },
      { label: 'search', description: 'Search Spotify', placeholder: '<query>' },
    ],
  },
  {
    name: 'github',
    description: 'GitHub integration',
    subs: [
      { label: 'status', description: 'Git status of current repo' },
      { label: 'open', description: 'Open repo in browser', placeholder: '<repo>' },
      { label: 'clone', description: 'Clone a repo', placeholder: '<url>' },
      { label: 'issues', description: 'List open issues', placeholder: '<repo>' },
    ],
  },
  {
    name: 'docs',
    description: 'Document memory & search',
    subs: [
      { label: 'list', description: 'List indexed documents' },
      { label: 'index', description: 'Index a file', placeholder: '<path>' },
      { label: 'index-folder', description: 'Index a folder', placeholder: '<path>' },
      { label: 'search', description: 'Search documents', placeholder: '<query>' },
      { label: 'ask', description: 'Ask questions on documents', placeholder: '<question>' },
      { label: 'clear', description: 'Clear document index' },
    ],
  },
];

// ── Props ──

interface Props {
  /** Current input value */
  value: string;
  /** Called when user selects a suggestion — replaces the input */
  onSelect: (text: string) => void;
  /** Whether the input is disabled (loading) */
  disabled?: boolean;
}

interface Suggestion {
  text: string;
  display: string;
  hint: string;
  isCommand?: boolean;
}

export interface SlashAutocompleteHandle {
  handleKeyDown: (e: React.KeyboardEvent) => boolean;
}

// ── Component ──

const SlashAutocomplete = forwardRef<SlashAutocompleteHandle, Props>(
  function SlashAutocomplete({ value, onSelect, disabled }, ref) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [appNames, setAppNames] = useState<string[]>([]);
  const listRef = useRef<HTMLDivElement>(null);

  // Fetch installed apps for /open autocomplete
  useEffect(() => {
    fetch(`${API}/api/apps`)
      .then(r => r.json())
      .then(data => {
        const names: string[] = (data.apps || [])
          .filter((a: { enabled?: boolean }) => a.enabled !== false)
          .map((a: { name: string }) => a.name.toLowerCase())
          .sort();
        setAppNames(names);
      })
      .catch(() => setAppNames([]));
  }, []);

  // Compute suggestions whenever input changes
  useEffect(() => {
    if (!value.startsWith('/') || disabled) {
      setSuggestions([]);
      setActiveIndex(0);
      return;
    }

    const text = value.slice(1); // remove leading "/"
    const parts = text.split(/\s+/);
    const firstToken = parts[0] || '';
    const rest = parts.slice(1).join(' ').trimStart();

    // Case 1: typing the command name (first token incomplete) — "/op" or "/"
    // No space after command yet, or only slash
    if (parts.length === 1 && !text.endsWith(' ')) {
      const matches = COMMANDS
        .filter(c => c.name.startsWith(firstToken.toLowerCase()))
        .map(c => ({
          text: `/${c.name} `,
          display: `/${c.name}`,
          hint: c.description,
          isCommand: true,
        }));
      setSuggestions(matches.slice(0, 5));
      setActiveIndex(0);
      return;
    }

    // Case 2: command typed, space after — "/open " — show sub-commands
    if (parts.length === 1 && text.endsWith(' ')) {
      const cmd = COMMANDS.find(c => c.name === firstToken.toLowerCase());
      if (cmd?.subs) {
        const matches = cmd.subs.map(s => ({
          text: `/${cmd.name} ${s.label} `,
          display: s.label,
          hint: s.description || '',
          isCommand: false,
        }));
        setSuggestions(matches.slice(0, 8));
        setActiveIndex(0);
        return;
      }
      setSuggestions([]);
      setActiveIndex(0);
      return;
    }

    // Case 3: command + partial sub-command — "/open ap" or "/open app "
    if (parts.length >= 2) {
      const cmd = COMMANDS.find(c => c.name === firstToken.toLowerCase());
      const subToken = parts[1] || '';

      if (!cmd?.subs) {
        setSuggestions([]);
        setActiveIndex(0);
        return;
      }

      // If we're on "/open app " (sub-command complete + space)
      if (rest.length > 0 || (parts.length === 2 && text.endsWith(' '))) {
        // Try dynamic fetch for app names
        const sub = cmd.subs.find(s => s.label === subToken.toLowerCase());
        if (sub?.dynamic === '/api/apps' && appNames.length > 0) {
          // Filter app names based on what's typed after
          const afterSub = rest;
          const matches = appNames
            .filter(a => a.startsWith(afterSub.toLowerCase()))
            .slice(0, 8)
            .map(a => ({
              text: `/${cmd.name} ${sub.label} ${a}`,
              display: a,
              hint: 'app',
              isCommand: false,
            }));
          setSuggestions(matches);
          setActiveIndex(0);
          return;
        }
        setSuggestions([]);
        setActiveIndex(0);
        return;
      }

      // Partial sub-command — "/open ap"
      const matches = cmd.subs
        .filter(s => s.label.startsWith(subToken.toLowerCase()))
        .map(s => ({
          text: `/${cmd.name} ${s.label} `,
          display: s.label,
          hint: s.description || '',
          isCommand: false,
        }));
      setSuggestions(matches.slice(0, 5));
      setActiveIndex(0);
      return;
    }

    setSuggestions([]);
    setActiveIndex(0);
  }, [value, disabled, appNames]);

  // Expose handleKeyDown to parent via ref
  useImperativeHandle(ref, () => ({
    handleKeyDown(e: React.KeyboardEvent): boolean {
      if (suggestions.length === 0) return false;

      if (e.key === 'Tab') {
        e.preventDefault();
        onSelect(suggestions[activeIndex].text);
        return true;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex(i => Math.min(i + 1, suggestions.length - 1));
        return true;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex(i => Math.max(i - 1, 0));
        return true;
      }
      if (e.key === 'Enter' && suggestions.length > 0) {
        e.preventDefault();
        onSelect(suggestions[activeIndex].text);
        return true;
      }
      if (e.key === 'Escape') {
        setSuggestions([]);
        return true;
      }
      return false;
    },
  }), [suggestions, activeIndex, onSelect]);

  // Scroll active into view
  useEffect(() => {
    if (listRef.current) {
      const el = listRef.current.children[activeIndex] as HTMLElement | undefined;
      el?.scrollIntoView({ block: 'nearest' });
    }
  }, [activeIndex]);

  if (suggestions.length === 0) return null;

  return (
    <div style={{
      position: 'absolute',
      bottom: 'calc(100% + 4px)',
      left: 72,
      right: 170,
      background: 'var(--bg-secondary, #1e1e2e)',
      border: '1px solid var(--border, #45475a)',
      borderRadius: 10,
      boxShadow: '0 8px 32px rgba(0,0,0,0.35)',
      zIndex: 100,
      overflow: 'hidden',
      maxHeight: 260,
    }}>
      <div style={{
        padding: '4px 10px',
        borderBottom: '1px solid var(--border, #45475a)',
        fontSize: '0.65rem',
        color: 'var(--text-muted, #6c7086)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span>{suggestions[0]?.isCommand ? 'Commands' : 'Options'}</span>
        <span style={{ fontSize: '0.6rem' }}>↹ Tab · ↑↓ · ↵ Enter</span>
      </div>
      <div ref={listRef}>
        {suggestions.map((s, i) => (
          <div
            key={s.text}
            onClick={() => onSelect(s.text)}
            onMouseEnter={() => setActiveIndex(i)}
            style={{
              padding: '7px 12px',
              cursor: 'pointer',
              background: i === activeIndex ? 'var(--accent, #6366f1)' : 'transparent',
              color: i === activeIndex ? '#fff' : 'var(--text-primary, #cdd6f4)',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              transition: 'background 0.08s',
              fontSize: '0.85rem',
            }}
          >
            {/* Leading icon */}
            <span style={{
              fontSize: '0.75rem',
              opacity: 0.6,
              minWidth: 18,
              textAlign: 'center',
            }}>
              {s.isCommand ? '⚡' : '▸'}
            </span>
            {/* Name */}
            <span style={{
              fontWeight: 600,
              fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
              whiteSpace: 'nowrap',
            }}>
              {s.display}
            </span>
            {/* Description */}
            <span style={{
              fontSize: '0.75rem',
              opacity: i === activeIndex ? 0.8 : 0.5,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              flex: 1,
            }}>
              {s.hint}
            </span>
            {/* Tab hint */}
            {i === 0 && (
              <span style={{
                fontSize: '0.6rem',
                padding: '1px 6px',
                borderRadius: 4,
                background: i === activeIndex ? 'rgba(255,255,255,0.2)' : 'var(--bg-tertiary, #313244)',
                opacity: 0.7,
                flexShrink: 0,
              }}>
                Tab
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
});

export { SlashAutocomplete };
export default SlashAutocomplete;
