import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { LLMStatus, MemoryStatus, SkillDetail } from '../api';

const API_BASE = 'http://localhost:8400';

// ── Types ──────────────────────────────────────────────────────────────────

interface FullHealth {
  status: string;
  version: string;
  env: string;
  uptime_seconds: number;
  backend: { status: string; version: string; env: string; uptime_seconds: number };
  llm: {
    provider: string;
    available: boolean;
    model: string;
    allow_cloud: boolean;
    providers: Record<string, { configured: boolean }>;
    reachable: boolean;
    error: string | null;
  };
  voice: {
    enabled: boolean;
    stt_available: boolean;
    tts_available: boolean;
    stt_provider: string;
    tts_provider: string;
    wake_word_enabled: boolean;
    push_to_talk_enabled: boolean;
    errors: string[];
  };
  documents: {
    ready: boolean;
    provider: string;
    count: number;
    chunks: number;
    error: string | null;
  };
  skills: string[];
}

interface VoiceStatusRaw {
  voice_enabled: boolean;
  stt_provider: string;
  stt_available: boolean;
  tts_provider: string;
  tts_available: boolean;
  push_to_talk_enabled: boolean;
  wake_word_enabled: boolean;
  stt_details: { available: boolean; model?: string; error?: string; note?: string };
  tts_details: { available: boolean; error?: string; note?: string };
  errors: string[];
}

interface LLMTestResultRaw {
  success: boolean;
  provider: string;
  available: boolean;
  test_response?: string;
  error?: string;
}

interface DiagnosticsData {
  timestamp: string;
  version: string;
  environment: {
    python: string;
    system: string;
    release: string;
    machine: string;
    node: string;
  };
  config_public: {
    version: string;
    env: string;
    llm_provider: string;
    llm_model: string;
    allow_cloud: boolean;
    embedding_provider: string;
    voice_enabled: boolean;
  };
  skills: { loaded: string[] };
  backend: { online: boolean; version: string; skills_loaded: number; initialized: boolean };
  llm: {
    provider: string;
    available: boolean;
    model: string;
    error?: string;
    providers?: Record<string, { configured: boolean }>;
    allow_cloud?: boolean;
  };
}

interface SmokeTestResult {
  name: string;
  endpoint: string;
  status: 'pass' | 'fail' | 'running' | 'pending';
  detail: string;
  response_time_ms?: number;
}

// ── Steps definition ───────────────────────────────────────────────────────

const STEPS = [
  { num: 1, title: 'Welcome', icon: '👋' },
  { num: 2, title: 'System Health', icon: '🔍' },
  { num: 3, title: 'Usage Mode', icon: '⚙️' },
  { num: 4, title: 'LLM Setup', icon: '🧠' },
  { num: 5, title: 'Common Apps', icon: '📱' },
  { num: 6, title: 'Documents', icon: '📄' },
  { num: 7, title: 'Voice', icon: '🎤' },
  { num: 8, title: 'Integrations', icon: '🔌' },
  { num: 9, title: 'Security', icon: '🔒' },
  { num: 10, title: 'Diagnostics', icon: '🩺' },
  { num: 11, title: 'Smoke Test', icon: '🧪' },
  { num: 12, title: 'Finish', icon: '✅' },
];

// ── Usage mode options ─────────────────────────────────────────────────────

type UsageMode = 'mock' | 'ollama' | 'cloud';

const USAGE_MODES: { key: UsageMode; label: string; desc: string; icon: string; pro: string; con: string }[] = [
  {
    key: 'mock',
    label: 'Mock Demo',
    desc: 'Try JARVIS without any LLM setup. Uses simulated responses.',
    icon: '🎭',
    pro: 'Zero setup, works instantly',
    con: 'No real AI — canned responses only',
  },
  {
    key: 'ollama',
    label: 'Local Ollama',
    desc: 'Run AI fully offline with Ollama. Private and no API costs.',
    icon: '🏠',
    pro: 'Private, offline, free, unlimited',
    con: 'Requires local GPU/RAM for good performance',
  },
  {
    key: 'cloud',
    label: 'Cloud LLM',
    desc: 'Use OpenAI / Anthropic / DeepSeek via API key. Fast, smart, no local GPU needed.',
    icon: '☁️',
    pro: 'Best quality, no local hardware needed',
    con: 'Requires API key, pay-per-use, sends data to cloud',
  },
];

// ── Known common apps ──────────────────────────────────────────────────────

const COMMON_APPS = [
  { key: 'discord', label: 'Discord', icon: '🎮', command: 'discord' },
  { key: 'spotify', label: 'Spotify', icon: '🎵', command: 'spotify' },
  { key: 'vscode', label: 'VS Code', icon: '💻', command: 'code' },
  { key: 'obs', label: 'OBS Studio', icon: '🎥', command: 'obs' },
  { key: 'terminal', label: 'Terminal', icon: '⬛', command: 'gnome-terminal' },
  { key: 'browser', label: 'Browser', icon: '🌐', command: 'firefox' },
  { key: 'files', label: 'File Manager', icon: '📁', command: 'nautilus' },
  { key: 'calculator', label: 'Calculator', icon: '🔢', command: 'gnome-calculator' },
  { key: 'settings', label: 'Settings', icon: '⚙️', command: 'gnome-control-center' },
];

// ── Component ──────────────────────────────────────────────────────────────

function SetupWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState(false);
  const [stepLoading, setStepLoading] = useState(false);

  // Step 2: System Check
  const [fullHealth, setFullHealth] = useState<FullHealth | null>(null);

  // Step 3: Usage Mode
  const [usageMode, setUsageMode] = useState<UsageMode>('ollama');

  // Step 4: LLM
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null);
  const [testingLLM, setTestingLLM] = useState(false);
  const [llmTestResult, setLlmTestResult] = useState<LLMTestResultRaw | null>(null);

  // Step 5: Common Apps
  const [appsSkill, setAppsSkill] = useState<SkillDetail | null>(null);
  const [enabledApps, setEnabledApps] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    COMMON_APPS.forEach(a => { initial[a.key] = true; });
    return initial;
  });

  // Step 6: Documents
  const [docStatus, setDocStatus] = useState<MemoryStatus | null>(null);

  // Step 7: Voice
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatusRaw | null>(null);

  // Step 8: Integrations
  const [integrations, setIntegrations] = useState({
    obs: false,
    discord: false,
    spotify: false,
    github: false,
  });

  // Step 10: Diagnostics
  const [diagnosticsData, setDiagnosticsData] = useState<DiagnosticsData | null>(null);
  const [diagnosticsError, setDiagnosticsError] = useState<string | null>(null);

  // Step 11: Smoke Test
  const [smokeResults, setSmokeResults] = useState<SmokeTestResult[]>([]);
  const [smokeRunning, setSmokeRunning] = useState(false);
  const [smokeSummary, setSmokeSummary] = useState<{ pass: number; fail: number } | null>(null);

  const toggleIntegration = (key: keyof typeof integrations) => {
    setIntegrations(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // ── Data loading ──────────────────────────────────────────────────────

  const loadSystemCheck = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/health/full`);
      setFullHealth(await res.json());
    } catch { /* ignore */ }
  }, []);

  const loadLLM = useCallback(async () => {
    try {
      setLlmStatus(await api.llmStatus());
    } catch { /* ignore */ }
  }, []);

  const loadApps = useCallback(async () => {
    try {
      const skill = await api.skillDetail('apps');
      setAppsSkill(skill);
    } catch { /* ignore - apps skill may not be loaded */ }
  }, []);

  const loadDocuments = useCallback(async () => {
    try {
      setDocStatus(await api.documentsStatus());
    } catch { /* ignore */ }
  }, []);

  const loadVoice = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/voice/status`);
      setVoiceStatus(await res.json());
    } catch { /* ignore */ }
  }, []);

  const loadDiagnostics = useCallback(async () => {
    setStepLoading(true);
    setDiagnosticsError(null);
    try {
      const res = await fetch(`${API_BASE}/api/diagnostics`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDiagnosticsData(await res.json());
    } catch (err) {
      setDiagnosticsError(err instanceof Error ? err.message : 'Failed to load diagnostics');
    } finally {
      setStepLoading(false);
    }
  }, []);

  // Load system check on mount
  useEffect(() => {
    loadSystemCheck().finally(() => setLoading(false));
  }, [loadSystemCheck]);

  // Load step-specific data when arriving at that step
  useEffect(() => {
    if (step === 3) loadLLM();
    if (step === 4) loadApps();
    if (step === 5) loadDocuments();
    if (step === 6) loadVoice();
    if (step === 9) loadDiagnostics();
  }, [step, loadLLM, loadApps, loadDocuments, loadVoice, loadDiagnostics]);

  // ── LLM test ──────────────────────────────────────────────────────────

  const testLLMConnection = async () => {
    setTestingLLM(true);
    setLlmTestResult(null);
    try {
      const resp = await fetch(`${API_BASE}/api/settings/llm/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: 'ollama' }),
      });
      const data = await resp.json();
      setLlmTestResult(data);
    } catch (err) {
      setLlmTestResult({
        success: false,
        provider: 'ollama',
        available: false,
        error: err instanceof Error ? err.message : 'Connection failed',
      });
    } finally {
      setTestingLLM(false);
    }
  };

  // ── Smoke test ────────────────────────────────────────────────────────

  const smokeEndpoints = [
    { name: 'Health Check', endpoint: '/health', method: 'GET' },
    { name: 'Full Health', endpoint: '/api/health/full', method: 'GET' },
    { name: 'Skills List', endpoint: '/api/skills', method: 'GET' },
    { name: 'LLM Status', endpoint: '/api/llm/status', method: 'GET' },
    { name: 'Documents Status', endpoint: '/api/documents/status', method: 'GET' },
    { name: 'Voice Status', endpoint: '/api/voice/status', method: 'GET' },
    { name: 'Workflows', endpoint: '/api/workflows', method: 'GET' },
    { name: 'Automations', endpoint: '/api/automations', method: 'GET' },
    { name: 'Diagnostics', endpoint: '/api/diagnostics', method: 'GET' },
    { name: 'Config Public', endpoint: '/api/config/public', method: 'GET' },
    { name: 'Setup Status', endpoint: '/api/setup/status', method: 'GET' },
  ];

  const runSmokeTest = async () => {
    setSmokeRunning(true);
    setSmokeSummary(null);
    const results: SmokeTestResult[] = [];

    for (const check of smokeEndpoints) {
      setSmokeResults([...results, { name: check.name, endpoint: check.endpoint, status: 'running', detail: 'Testing...' }]);
      const start = performance.now();
      try {
        const res = await fetch(`${API_BASE}${check.endpoint}`);
        const elapsed = Math.round(performance.now() - start);
        if (res.ok) {
          results.push({ name: check.name, endpoint: check.endpoint, status: 'pass', detail: `OK (${res.status})`, response_time_ms: elapsed });
        } else {
          results.push({ name: check.name, endpoint: check.endpoint, status: 'fail', detail: `HTTP ${res.status}`, response_time_ms: elapsed });
        }
      } catch (err) {
        const elapsed = Math.round(performance.now() - start);
        results.push({ name: check.name, endpoint: check.endpoint, status: 'fail', detail: err instanceof Error ? err.message : 'Connection failed', response_time_ms: elapsed });
      }
      setSmokeResults([...results]);
    }

    setSmokeResults(results);
    setSmokeSummary({
      pass: results.filter(r => r.status === 'pass').length,
      fail: results.filter(r => r.status === 'fail').length,
    });
    setSmokeRunning(false);
  };

  // ── Copy to clipboard ─────────────────────────────────────────────────

  const copyCommand = (cmd: string) => {
    navigator.clipboard.writeText(cmd).catch(() => {});
  };

  // ── Finish ────────────────────────────────────────────────────────────

  const finishSetup = async () => {
    setCompleting(true);
    try {
      await fetch(`${API_BASE}/api/setup/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
    } catch { /* ignore errors */ }
    setCompleting(false);
    navigate('/');
  };

  // ── Navigation ────────────────────────────────────────────────────────

  const goNext = () => { if (step < STEPS.length - 1) setStep(s => s + 1); };
  const goPrev = () => { if (step > 0) setStep(s => s - 1); };
  const isFirst = step === 0;
  const isLast = step === STEPS.length - 1;

  // ── Loading state ─────────────────────────────────────────────────────

  if (loading) return <div className="loading"><div className="spinner" /></div>;

  // ── Helper: status badge ──────────────────────────────────────────────

  const StatusBadge = ({ ok, okLabel, failLabel }: { ok: boolean; okLabel?: string; failLabel?: string }) => (
    <span className={`badge ${ok ? 'badge-success' : 'badge-danger'}`}>
      {ok ? (okLabel || 'Online') : (failLabel || 'Offline')}
    </span>
  );

  // ── Step renderers ────────────────────────────────────────────────────

  const renderStep1Welcome = () => (
    <div style={{ textAlign: 'center', maxWidth: 520, margin: '0 auto', paddingTop: 40 }}>
      <div style={{ fontSize: '3.5rem', marginBottom: 20 }}>🚀</div>
      <h2 style={{ fontSize: '1.75rem', marginBottom: 12 }}>Welcome to JARVIS</h2>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: 1.7, marginBottom: 32 }}>
        Your modular AI desktop assistant — with skills, workflows, automations,
        voice commands, and document memory. Let's get everything configured
        in just a few minutes.
      </p>

      <div className="card-grid" style={{ maxWidth: 500, margin: '0 auto 32px' }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 4 }}>🧠</div>
          <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>Local LLM</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Private, offline AI</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 4 }}>🔧</div>
          <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>15+ Skills</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>System, web, automation</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 4 }}>📄</div>
          <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>RAG Memory</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Index your documents</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 4 }}>🎤</div>
          <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>Voice Control</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Push-to-talk ready</div>
        </div>
      </div>

      <button className="btn btn-primary" onClick={goNext} style={{ padding: '12px 40px', fontSize: '1rem' }}>
        Get Started ⏵
      </button>
    </div>
  );

  const renderStep2SystemCheck = () => {
    const fh = fullHealth;
    const backendOk = fh?.backend?.status === 'ok' || fh?.status === 'ok';
    const llmOk = fh?.llm?.available ?? false;
    const voiceOk = ((fh?.voice?.stt_available || fh?.voice?.tts_available) ?? false) || (fh?.voice?.enabled ?? false);
    const docsOk = fh?.documents?.ready ?? false;

    return (
      <div style={{ maxWidth: 700, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <h2 style={{ fontSize: '1.5rem', marginBottom: 8 }}>System Health Check</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Checking all core services...
          </p>
        </div>

        <div className="card-grid" style={{ marginBottom: 24 }}>
          {/* Backend */}
          <div className="card">
            <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>🖥️</span> Backend
              <StatusBadge ok={backendOk} okLabel="Online" failLabel="Offline" />
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {fh ? (
                <>
                  <div>Version: {fh.version || fh.backend?.version || '—'}</div>
                  <div>Env: {fh.env || fh.backend?.env || '—'}</div>
                  <div>Skills: {fh.skills?.length ?? 0} loaded</div>
                </>
              ) : (
                <div style={{ color: 'var(--text-muted)' }}>No data available</div>
              )}
            </div>
          </div>

          {/* LLM */}
          <div className="card">
            <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>🧠</span> LLM
              <span className={`badge ${llmOk ? 'badge-success' : 'badge-warning'}`} style={{ marginLeft: 'auto' }}>
                {llmOk ? 'Connected' : 'Unavailable'}
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {fh?.llm ? (
                <>
                  <div>Provider: {fh.llm.provider || 'none'}</div>
                  <div>Model: {fh.llm.model || 'none'}</div>
                  <div>Cloud: {fh.llm.allow_cloud ? 'Allowed' : 'Blocked'}</div>
                </>
              ) : (
                <div style={{ color: 'var(--text-muted)' }}>No data available</div>
              )}
            </div>
          </div>

          {/* Voice */}
          <div className="card">
            <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>🎤</span> Voice
              <span className={`badge ${voiceOk ? 'badge-success' : 'badge-warning'}`} style={{ marginLeft: 'auto' }}>
                {voiceOk ? 'Available' : 'Mock Only'}
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {fh?.voice ? (
                <>
                  <div>STT: {fh.voice.stt_provider || 'mock'} — {fh.voice.stt_available ? '✅' : '❌'}</div>
                  <div>TTS: {fh.voice.tts_provider || 'mock'} — {fh.voice.tts_available ? '✅' : '❌'}</div>
                </>
              ) : (
                <div style={{ color: 'var(--text-muted)' }}>No data available</div>
              )}
            </div>
          </div>

          {/* Documents */}
          <div className="card">
            <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>📄</span> Documents
              <span className={`badge ${docsOk ? 'badge-success' : 'badge-warning'}`} style={{ marginLeft: 'auto' }}>
                {docsOk ? 'Ready' : 'Not Ready'}
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {fh?.documents ? (
                <>
                  <div>Provider: {fh.documents.provider || 'none'}</div>
                  <div>Docs: {fh.documents.count ?? 0} · Chunks: {fh.documents.chunks ?? 0}</div>
                </>
              ) : (
                <div style={{ color: 'var(--text-muted)' }}>No data available</div>
              )}
            </div>
          </div>
        </div>

        <div className="card" style={{
          background: backendOk ? 'rgba(34,197,94,0.04)' : 'rgba(239,68,68,0.04)',
          borderColor: backendOk ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: '1.1rem' }}>{backendOk ? '✅' : '⚠️'}</span>
            <div style={{ fontSize: '0.85rem' }}>
              {backendOk
                ? 'All core services are reachable. Click Next to configure each component.'
                : 'Some services are offline. You can continue setup — they will be configured as you go.'
              }
            </div>
            <button className="btn btn-sm btn-secondary" style={{ marginLeft: 'auto' }} onClick={loadSystemCheck}>
              🔄 Refresh
            </button>
          </div>
        </div>
      </div>
    );
  };

  const renderStep3UsageMode = () => (
    <div style={{ maxWidth: 750, margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 28 }}>
        <h2 style={{ fontSize: '1.5rem', marginBottom: 8 }}>Choose Usage Mode</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          How do you want to use JARVIS?
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 28 }}>
        {USAGE_MODES.map(mode => (
          <div
            key={mode.key}
            className="card"
            onClick={() => setUsageMode(mode.key)}
            style={{
              cursor: 'pointer',
              borderColor: usageMode === mode.key ? 'var(--accent)' : 'var(--border)',
              background: usageMode === mode.key ? 'var(--accent-glow)' : 'var(--bg-card)',
              transition: 'all 0.2s',
            }}
          >
            <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
              <div style={{ fontSize: '2.2rem', flexShrink: 0, lineHeight: 1 }}>{mode.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: '1rem' }}>{mode.label}</span>
                  {usageMode === mode.key && (
                    <span className="badge badge-success" style={{ fontSize: '0.65rem' }}>Selected</span>
                  )}
                </div>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: 8 }}>{mode.desc}</p>
                <div style={{ display: 'flex', gap: 16, fontSize: '0.75rem' }}>
                  <span style={{ color: 'var(--success)' }}>✅ {mode.pro}</span>
                  <span style={{ color: 'var(--text-muted)' }}>⚠️ {mode.con}</span>
                </div>
              </div>
              <div style={{
                width: 22, height: 22,
                borderRadius: '50%',
                border: `2px solid ${usageMode === mode.key ? 'var(--accent)' : 'var(--border)'}`,
                background: usageMode === mode.key ? 'var(--accent)' : 'transparent',
                flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                {usageMode === mode.key && <span style={{ color: 'white', fontSize: '0.7rem' }}>✓</span>}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="card" style={{
        borderColor: 'rgba(99,102,241,0.3)',
        background: 'rgba(99,102,241,0.04)',
      }}>
        <div className="card-header">💡 Recommendation</div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          {usageMode === 'mock' && 'Mock Demo is great for exploring the UI and testing skills without any dependencies. Switch to Ollama or Cloud later for real AI power.'}
          {usageMode === 'ollama' && 'Local Ollama is the recommended setup for privacy-first users. Install Ollama, pull a model (like qwen2.5:7b), and you\'re ready. Best experience on a machine with 8GB+ RAM.'}
          {usageMode === 'cloud' && 'Cloud LLM gives you the best quality responses instantly. You\'ll need an API key from your preferred provider. Configure it in the next step.'}
        </p>
      </div>
    </div>
  );

  const renderStep4LLM = () => {
    const ls = llmStatus;
    const recommendedCmd = usageMode === 'cloud' ? 'Set your API key in Settings → LLM' : 'ollama pull qwen2.5:7b';
    const provider = ls?.provider || 'none';
    const model = ls?.model || 'none';
    const available = ls?.available ?? false;

    return (
      <div style={{ maxWidth: 700, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <h2 style={{ fontSize: '1.5rem', marginBottom: 8 }}>LLM Setup</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            {usageMode === 'mock'
              ? 'No LLM needed — using mock responses for demo mode'
              : usageMode === 'cloud'
                ? 'Configure your cloud LLM provider and API key'
                : 'Connect to Ollama for private, offline AI'
            }
          </p>
        </div>

        {/* Current Status */}
        <div className="card-grid" style={{ marginBottom: 20 }}>
          <div className="card">
            <div className="stat-value">
              <span className={`status-dot ${available ? 'online' : 'offline'}`} />
              {available ? ' Ready' : ' Offline'}
            </div>
            <div className="stat-label">Connection Status</div>
          </div>
          <div className="card">
            <div className="stat-value">{provider}</div>
            <div className="stat-label">Provider — {model}</div>
          </div>
        </div>

        {/* Provider Details */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">Provider Details</div>
          <div style={{ fontSize: '0.85rem', display: 'grid', gap: 8 }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Current Provider: </span>
              <span style={{ fontWeight: 500 }}>{provider}</span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Current Model: </span>
              <code style={{ background: 'var(--bg-primary)', padding: '2px 8px', borderRadius: 4 }}>{model}</code>
            </div>
            {ls?.providers && Object.keys(ls.providers).length > 0 && (
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Configured Providers: </span>
                <span style={{ fontWeight: 500 }}>
                  {Object.entries(ls.providers)
                    .filter(([, v]) => v.configured)
                    .map(([k]) => k)
                    .join(', ') || 'none'}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Action card — changes based on usage mode */}
        {usageMode === 'ollama' && (
          <div className="card" style={{
            marginBottom: 20,
            borderColor: 'var(--warning)',
            background: 'rgba(245,158,11,0.05)',
          }}>
            <div className="card-header">⚡ Recommended Model: qwen2.5:7b</div>
            <p style={{ fontSize: '0.85rem', marginBottom: 12, color: 'var(--text-secondary)' }}>
              Run this command on your <strong>local machine</strong> to pull the recommended Ollama model:
            </p>
            <div style={{
              display: 'flex', gap: 8, alignItems: 'center',
              background: 'var(--bg-primary)', padding: '12px 16px',
              borderRadius: 'var(--radius)', fontFamily: 'monospace', fontSize: '0.9rem',
            }}>
              <code style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'auto' }}>{recommendedCmd}</code>
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => copyCommand(recommendedCmd)}
                style={{ flexShrink: 0 }}
              >
                📋 Copy
              </button>
            </div>
            <p style={{ marginTop: 10, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              After pulling, restart JARVIS and refresh below to see the model ready.
            </p>
          </div>
        )}

        {usageMode === 'cloud' && (
          <div className="card" style={{
            marginBottom: 20,
            borderColor: 'rgba(99,102,241,0.3)',
            background: 'rgba(99,102,241,0.04)',
          }}>
            <div className="card-header">☁️ Cloud LLM Setup</div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
              Go to <strong>Settings → LLM</strong> to configure your cloud provider. Supported: OpenAI, Anthropic, DeepSeek, OpenRouter, Groq.
            </p>
            <ol style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', paddingLeft: 20, lineHeight: 2 }}>
              <li>Choose your provider (OpenAI, Anthropic, etc.)</li>
              <li>Paste your API key</li>
              <li>Select a model (e.g., gpt-4o, claude-3.5-sonnet)</li>
              <li>Enable "Allow Cloud LLM"</li>
            </ol>
          </div>
        )}

        {usageMode === 'mock' && (
          <div className="card" style={{
            marginBottom: 20,
            borderColor: 'rgba(99,102,241,0.3)',
            background: 'rgba(99,102,241,0.04)',
          }}>
            <div className="card-header">🎭 Mock Demo Mode</div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Mock mode uses simulated responses so you can explore JARVIS without any setup.
              Skills and commands still work — responses are pre-written examples.
              Switch to Ollama or Cloud anytime from the LLM Settings page.
            </p>
          </div>
        )}

        {/* Test Connection */}
        <div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 12 }}>
            <button
              className="btn btn-primary"
              onClick={testLLMConnection}
              disabled={testingLLM}
            >
              {testingLLM ? 'Testing...' : '🔌 Test Connection'}
            </button>
            <button className="btn btn-secondary" onClick={loadLLM}>
              🔄 Refresh Status
            </button>
          </div>

          {llmTestResult && (
            <div className="card" style={{
              background: llmTestResult.success ? 'rgba(34,197,94,0.06)' : 'rgba(239,68,68,0.06)',
              border: `1px solid ${llmTestResult.success ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
            }}>
              <div className="card-header">Test Result</div>
              <div style={{ fontSize: '0.85rem' }}>
                {llmTestResult.success && (
                  <div style={{ color: 'var(--success)' }}>✅ Connection successful</div>
                )}
                {llmTestResult.test_response && (
                  <div style={{ marginTop: 8, padding: '8px 12px', background: 'var(--bg-primary)', borderRadius: 'var(--radius)' }}>
                    Response: {llmTestResult.test_response}
                  </div>
                )}
                {llmTestResult.error && (
                  <div style={{ color: 'var(--danger)', marginTop: 4 }}>{llmTestResult.error}</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderStep5CommonApps = () => {
    const skillLoaded = appsSkill !== null;
    const enabledCount = Object.values(enabledApps).filter(Boolean).length;

    const toggleApp = (key: string) => {
      setEnabledApps(prev => ({ ...prev, [key]: !prev[key] }));
    };

    return (
      <div style={{ maxWidth: 700, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <h2 style={{ fontSize: '1.5rem', marginBottom: 8 }}>Configure Common Apps</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            JARVIS can open and manage these desktop applications by voice or chat command
          </p>
        </div>

        {/* Skill status */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: '1.3rem' }}>📱</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                Apps Skill — {skillLoaded ? (
                  <span style={{ color: 'var(--success)' }}>✅ Loaded</span>
                ) : (
                  <span style={{ color: 'var(--warning)' }}>⚠️ Not detected</span>
                )}
              </div>
              {appsSkill && (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                  v{appsSkill.version} · {appsSkill.actions?.length || 0} actions: {appsSkill.actions?.map(a => a.name).join(', ') || 'open, close, list'}
                </div>
              )}
            </div>
            <button className="btn btn-sm btn-secondary" onClick={loadApps}>🔄 Refresh</button>
          </div>
        </div>

        {/* App cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
          {COMMON_APPS.map(app => (
            <div
              key={app.key}
              className="card"
              onClick={() => toggleApp(app.key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                cursor: 'pointer',
                borderColor: enabledApps[app.key] ? 'rgba(34,197,94,0.3)' : 'var(--border)',
                background: enabledApps[app.key] ? 'rgba(34,197,94,0.03)' : 'var(--bg-card)',
                transition: 'all 0.15s',
              }}
            >
              <div style={{ fontSize: '1.4rem', flexShrink: 0 }}>{app.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{app.label}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <code style={{ background: 'var(--bg-primary)', padding: '1px 6px', borderRadius: 3, fontSize: '0.7rem' }}>{app.command}</code>
                </div>
              </div>
              <div style={{
                width: 42, height: 24,
                borderRadius: 12,
                background: enabledApps[app.key] ? 'var(--success)' : 'var(--border)',
                position: 'relative',
                transition: 'background 0.15s',
                flexShrink: 0,
              }}>
                <div style={{
                  width: 18, height: 18,
                  borderRadius: '50%',
                  background: 'white',
                  position: 'absolute',
                  top: 3,
                  left: enabledApps[app.key] ? 21 : 3,
                  transition: 'left 0.15s',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                }} />
              </div>
            </div>
          ))}
        </div>

        {/* Summary */}
        <div className="card" style={{
          borderColor: 'rgba(99,102,241,0.2)',
          background: 'rgba(99,102,241,0.04)',
        }}>
          <div style={{ textAlign: 'center', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            <strong>{enabledCount}</strong> of {COMMON_APPS.length} apps enabled.
            {enabledCount === 0
              ? ' Enable at least a few for the best experience.'
              : ' Use "open &lt;app name&gt;" in chat or voice to launch them.'
            }
          </div>
        </div>
      </div>
    );
  };

  const renderStep6Documents = () => {
    const ds = docStatus;
    const provider = ds?.embedding_provider || 'none';
    const ready = ds?.ready ?? false;
    const docCount = ds?.documents ?? 0;
    const chunkCount = ds?.chunks ?? 0;

    return (
      <div style={{ maxWidth: 700, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <h2 style={{ fontSize: '1.5rem', marginBottom: 8 }}>Document Memory Setup</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Index your documents for AI-powered search and Q&A
          </p>
        </div>

        {/* Status Cards */}
        <div className="card-grid" style={{ marginBottom: 20 }}>
          <div className="card">
            <div className="stat-value">
              <span className={`status-dot ${ready ? 'online' : 'offline'}`} />
              {ready ? ' Ready' : ' Not Ready'}
            </div>
            <div className="stat-label">Embedding Provider</div>
          </div>
          <div className="card">
            <div className="stat-value">{docCount}</div>
            <div className="stat-label">Documents Indexed</div>
          </div>
          <div className="card">
            <div className="stat-value">{chunkCount}</div>
            <div className="stat-label">Chunks</div>
          </div>
        </div>

        {/* Provider Info */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">Embedding Configuration</div>
          <div style={{ fontSize: '0.85rem' }}>
            <div style={{ marginBottom: 8 }}>
              <span style={{ color: 'var(--text-muted)' }}>Provider: </span>
              <span className={`badge ${provider !== 'none' ? 'badge-info' : 'badge-warning'}`}>
                {provider}
              </span>
            </div>
            {ds?.error && (
              <div style={{
                padding: '8px 12px',
                background: 'rgba(239,68,68,0.08)',
                border: '1px solid rgba(239,68,68,0.2)',
                borderRadius: 'var(--radius)',
                color: 'var(--danger)',
                fontSize: '0.85rem',
              }}>
                {ds.error}
              </div>
            )}
            {!ready && !ds?.error && (
              <div style={{
                padding: '8px 12px',
                background: 'rgba(245,158,11,0.08)',
                border: '1px solid rgba(245,158,11,0.2)',
                borderRadius: 'var(--radius)',
                color: 'var(--warning)',
                fontSize: '0.85rem',
              }}>
                No embedding provider configured yet. You can set it up later in Documents settings.
              </div>
            )}
          </div>
        </div>

        {/* Index suggestion */}
        <div className="card" style={{
          borderColor: 'rgba(99,102,241,0.3)',
          background: 'rgba(99,102,241,0.04)',
        }}>
          <div className="card-header">💡 Index Suggestion</div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
            After setup, go to the <strong>Documents</strong> page to index your files:
          </p>
          <ul style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', paddingLeft: 20, lineHeight: 2 }}>
            <li>Index individual files: Select a file and click <strong>Index</strong></li>
            <li>Index a whole folder: Choose a folder to recursively index all supported files</li>
            <li>Ask questions: Use the Q&A tab to query your indexed documents with AI</li>
          </ul>
          <p style={{ marginTop: 12, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Supported formats: .txt, .md, .pdf, .docx, .csv, .json, .py, .js, .ts, .html, .css, and more.
          </p>
        </div>
      </div>
    );
  };

  const renderStep7Voice = () => {
    const vs = voiceStatus;
    const sttOk = vs?.stt_available ?? false;
    const ttsOk = vs?.tts_available ?? false;
    const voiceEnabled = vs?.voice_enabled ?? false;

    return (
      <div style={{ maxWidth: 700, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <h2 style={{ fontSize: '1.5rem', marginBottom: 8 }}>Voice Setup</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Configure speech-to-text and text-to-speech
          </p>
        </div>

        {/* Status Cards */}
        <div className="card-grid" style={{ marginBottom: 20 }}>
          <div className="card">
            <div className="stat-value">
              <span className={`status-dot ${sttOk ? 'online' : 'offline'}`} />
              {sttOk ? ' Ready' : ' Offline'}
            </div>
            <div className="stat-label">STT: {vs?.stt_provider || 'mock'}</div>
            {vs?.stt_details?.note && (
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>{vs.stt_details.note}</div>
            )}
          </div>
          <div className="card">
            <div className="stat-value">
              <span className={`status-dot ${ttsOk ? 'online' : 'offline'}`} />
              {ttsOk ? ' Ready' : ' Offline'}
            </div>
            <div className="stat-label">TTS: {vs?.tts_provider || 'mock'}</div>
          </div>
          <div className="card">
            <div className="stat-value">{vs?.push_to_talk_enabled ? '🟢 On' : '⚫ Off'}</div>
            <div className="stat-label">Push-to-Talk</div>
          </div>
        </div>

        {/* Current Config */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">Voice Configuration</div>
          <div style={{ fontSize: '0.85rem' }}>
            <div style={{ marginBottom: 8 }}>
              <span style={{ color: 'var(--text-muted)' }}>Voice Engine: </span>
              <span className={`badge ${voiceEnabled ? 'badge-success' : 'badge-warning'}`}>
                {voiceEnabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            {!voiceEnabled && (
              <p style={{ color: 'var(--text-secondary)', marginTop: 4 }}>
                Voice features are currently disabled. You can enable them in Voice settings.
              </p>
            )}
          </div>
        </div>

        {/* Setup Note */}
        <div className="card" style={{
          borderColor: 'rgba(99,102,241,0.3)',
          background: 'rgba(99,102,241,0.04)',
        }}>
          <div className="card-header">📖 Optional Setup Note</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
            <p>
              <strong>Default (Mock):</strong> No setup required. Works immediately.
              Transcriptions return mock text, TTS logs instead of speaking.
            </p>
            <p style={{ marginTop: 10 }}>
              <strong>Real STT (Faster-Whisper) — Local PC only:</strong>
            </p>
            <ol style={{ paddingLeft: 20 }}>
              <li>Install: <code style={{ background: 'var(--bg-primary)', padding: '2px 6px', borderRadius: 4 }}>pip install faster-whisper</code></li>
              <li>Set in .env: <code style={{ background: 'var(--bg-primary)', padding: '2px 6px', borderRadius: 4 }}>JARVIS_STT_PROVIDER=faster_whisper</code></li>
              <li>Choose model: <code style={{ background: 'var(--bg-primary)', padding: '2px 6px', borderRadius: 4 }}>JARVIS_STT_MODEL=base</code></li>
              <li>Restart JARVIS after configuration</li>
            </ol>
            <p style={{ marginTop: 10, color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              ⚠️ Wake word ("Jarvis") always-listening is not yet implemented. Use push-to-talk for voice input.
            </p>
          </div>
        </div>
      </div>
    );
  };

  const renderStep8Integrations = () => {
    const integrationOptions = [
      { key: 'obs' as const, label: 'OBS Studio', desc: 'Streaming & recording control', icon: '🎥' },
      { key: 'discord' as const, label: 'Discord', desc: 'Rich presence & notifications', icon: '🎮' },
      { key: 'spotify' as const, label: 'Spotify', desc: 'Music playback control', icon: '🎵' },
      { key: 'github' as const, label: 'GitHub', desc: 'Repo & issue management', icon: '🐙' },
    ];

    const anySelected = Object.values(integrations).some(Boolean);

    return (
      <div style={{ maxWidth: 700, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <h2 style={{ fontSize: '1.5rem', marginBottom: 8 }}>Integrations</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Connect external services — all optional, configure anytime later
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {integrationOptions.map(opt => (
            <div
              key={opt.key}
              className="card"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 16,
                cursor: 'pointer',
                borderColor: integrations[opt.key] ? 'var(--accent)' : 'var(--border)',
                background: integrations[opt.key] ? 'var(--accent-glow)' : 'var(--bg-card)',
                transition: 'all 0.15s',
              }}
              onClick={() => toggleIntegration(opt.key)}
            >
              <div style={{ fontSize: '2rem', flexShrink: 0 }}>{opt.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{opt.label}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{opt.desc}</div>
              </div>
              <div style={{
                width: 22, height: 22,
                borderRadius: 4,
                border: `2px solid ${integrations[opt.key] ? 'var(--accent)' : 'var(--border)'}`,
                background: integrations[opt.key] ? 'var(--accent)' : 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
                transition: 'all 0.15s',
              }}>
                {integrations[opt.key] && <span style={{ color: 'white', fontSize: '0.65rem' }}>✓</span>}
              </div>
            </div>
          ))}
        </div>

        <div className="card" style={{
          marginTop: 20,
          borderColor: 'rgba(99,102,241,0.2)',
          background: 'rgba(99,102,241,0.04)',
        }}>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', textAlign: 'center' }}>
            {anySelected
              ? `${Object.entries(integrations).filter(([, v]) => v).length} integration(s) selected. You can configure each one later in Settings.`
              : 'No integrations selected — you can always add them later from Settings.'
            }
          </p>
        </div>
      </div>
    );
  };

  const renderStep9Security = () => (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 28 }}>
        <h2 style={{ fontSize: '1.5rem', marginBottom: 8 }}>Security</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Understand how JARVIS keeps you in control
        </p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">🔒 Pending Actions Queue</div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          JARVIS uses a <strong>pending actions queue</strong> for sensitive operations.
          When a skill wants to perform an action that could affect your system
          (e.g., file deletion, system commands, configuration changes), the action is
          placed in the queue and requires your explicit confirmation before execution.
        </p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">⚙️ How It Works</div>
        <ul style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', paddingLeft: 20, lineHeight: 2 }}>
          <li>Each action has a <strong>risk level</strong> (low / medium / high)</li>
          <li>Medium and high-risk actions are placed in the <strong>pending queue</strong></li>
          <li>You review and <strong>approve or deny</strong> each action individually</li>
          <li>Low-risk actions (e.g., reading files) execute automatically</li>
          <li>The queue appears in the dashboard when actions are waiting</li>
        </ul>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">🛡️ Local-First Design</div>
        <ul style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', paddingLeft: 20, lineHeight: 2 }}>
          <li>All LLM inference runs <strong>locally</strong> via Ollama by default</li>
          <li>Cloud LLMs are <strong>disabled</strong> unless you explicitly enable them</li>
          <li>Your data stays on your machine — no telemetry, no cloud uploads</li>
          <li>API keys stored in local environment variables only</li>
        </ul>
      </div>

      <div className="card" style={{
        borderColor: 'rgba(99,102,241,0.2)',
        background: 'rgba(99,102,241,0.04)',
      }}>
        <div className="card-header">💡 Pro Tip</div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          You can adjust risk thresholds and confirmation settings at any time from
          the <strong>Settings</strong> page. Review the <strong>Logs</strong> page
          to audit all actions JARVIS has performed.
        </p>
      </div>
    </div>
  );

  const renderStep10Diagnostics = () => (
    <div style={{ maxWidth: 750, margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 28 }}>
        <h2 style={{ fontSize: '1.5rem', marginBottom: 8 }}>Run Diagnostics</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          System diagnostic information — no secrets, safe to share
        </p>
      </div>

      {stepLoading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <div className="spinner" style={{ margin: '0 auto' }} />
          <p style={{ color: 'var(--text-muted)', marginTop: 12 }}>Loading diagnostics...</p>
        </div>
      )}

      {diagnosticsError && !stepLoading && (
        <div className="card" style={{
          background: 'rgba(239,68,68,0.06)',
          border: '1px solid rgba(239,68,68,0.2)',
          marginBottom: 16,
        }}>
          <div className="card-header">⚠️ Failed to load diagnostics</div>
          <p style={{ fontSize: '0.85rem', color: 'var(--danger)' }}>{diagnosticsError}</p>
          <button className="btn btn-primary" style={{ marginTop: 8 }} onClick={loadDiagnostics}>
            🔄 Retry
          </button>
        </div>
      )}

      {diagnosticsData && !stepLoading && (
        <>
          {/* Summary banner */}
          <div className="card" style={{
            background: diagnosticsData.backend?.online ? 'rgba(34,197,94,0.04)' : 'rgba(239,68,68,0.04)',
            borderColor: diagnosticsData.backend?.online ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
            marginBottom: 20,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: '1.2rem' }}>{diagnosticsData.backend?.online ? '✅' : '❌'}</span>
              <div style={{ flex: 1, fontSize: '0.85rem' }}>
                <strong>JARVIS v{diagnosticsData.version}</strong> ·
                Backend: {diagnosticsData.backend?.online ? 'Online' : 'Offline'} ·
                Skills: {diagnosticsData.skills?.loaded?.length ?? 0} loaded
              </div>
              <button className="btn btn-sm btn-secondary" onClick={loadDiagnostics}>🔄 Refresh</button>
            </div>
          </div>

          {/* Environment */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header">💻 Environment</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: '0.83rem' }}>
              <div><span style={{ color: 'var(--text-muted)' }}>System:</span> <strong>{diagnosticsData.environment.system} {diagnosticsData.environment.release}</strong></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Machine:</span> <strong>{diagnosticsData.environment.machine}</strong></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Python:</span> <strong>{diagnosticsData.environment.python}</strong></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Node:</span> <strong>{diagnosticsData.environment.node}</strong></div>
            </div>
          </div>

          {/* Configuration */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header">⚙️ Public Configuration</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: '0.83rem' }}>
              <div><span style={{ color: 'var(--text-muted)' }}>Env:</span> <span className="badge badge-info">{diagnosticsData.config_public.env}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>LLM Provider:</span> <strong>{diagnosticsData.config_public.llm_provider}</strong></div>
              <div><span style={{ color: 'var(--text-muted)' }}>LLM Model:</span> <strong>{diagnosticsData.config_public.llm_model}</strong></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Cloud LLM:</span> <span className={`badge ${diagnosticsData.config_public.allow_cloud ? 'badge-success' : 'badge-warning'}`}>{diagnosticsData.config_public.allow_cloud ? 'Allowed' : 'Blocked'}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Embeddings:</span> <strong>{diagnosticsData.config_public.embedding_provider}</strong></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Voice:</span> <span className={`badge ${diagnosticsData.config_public.voice_enabled ? 'badge-success' : 'badge-warning'}`}>{diagnosticsData.config_public.voice_enabled ? 'Enabled' : 'Disabled'}</span></div>
            </div>
          </div>

          {/* LLM */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header">🧠 LLM Status</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: '0.83rem' }}>
              <div><span style={{ color: 'var(--text-muted)' }}>Provider:</span> <strong>{diagnosticsData.llm.provider || 'none'}</strong></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Model:</span> <strong>{diagnosticsData.llm.model || 'none'}</strong></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Available:</span> <span className={`badge ${diagnosticsData.llm.available ? 'badge-success' : 'badge-warning'}`}>{diagnosticsData.llm.available ? 'Yes' : 'No'}</span></div>
              {diagnosticsData.llm.error && (
                <div style={{ gridColumn: '1 / -1' }}><span style={{ color: 'var(--text-muted)' }}>Error:</span> <span style={{ color: 'var(--danger)' }}>{diagnosticsData.llm.error}</span></div>
              )}
            </div>
          </div>

          {/* Skills */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header">🔧 Loaded Skills ({diagnosticsData.skills?.loaded?.length ?? 0})</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {diagnosticsData.skills?.loaded?.length > 0
                ? diagnosticsData.skills.loaded.map(s => (
                    <span key={s} className="badge badge-info" style={{ fontSize: '0.72rem' }}>{s}</span>
                  ))
                : <span style={{ color: 'var(--text-muted)', fontSize: '0.83rem' }}>No skills loaded</span>
              }
            </div>
          </div>

          {/* Timestamp */}
          <div style={{ textAlign: 'center', fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 8 }}>
            Snapshot taken: {new Date(diagnosticsData.timestamp).toLocaleString()}
          </div>
        </>
      )}
    </div>
  );

  const renderStep11SmokeTest = () => (
    <div style={{ maxWidth: 750, margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 28 }}>
        <h2 style={{ fontSize: '1.5rem', marginBottom: 8 }}>Smoke Test</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Quick validation — checks all API endpoints respond correctly
        </p>
      </div>

      {/* Run button */}
      {!smokeRunning && smokeResults.length === 0 && (
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: 16 }}>
            This will run {smokeEndpoints.length} quick checks against the backend API.
            All checks are read-only and safe to run.
          </p>
          <button className="btn btn-primary" onClick={runSmokeTest} style={{ padding: '12px 36px', fontSize: '1rem' }}>
            🧪 Run Smoke Test ({smokeEndpoints.length} checks)
          </button>
        </div>
      )}

      {/* Running state */}
      {smokeRunning && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ textAlign: 'center', marginBottom: 16 }}>
            <div className="spinner" style={{ margin: '0 auto' }} />
            <p style={{ color: 'var(--text-muted)', marginTop: 8, fontSize: '0.85rem' }}>
              Running {smokeEndpoints.length} checks...
            </p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {smokeResults.map((r, i) => (
              <div key={i} className="card" style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '10px 14px',
                borderColor: r.status === 'pass' ? 'rgba(34,197,94,0.2)' : r.status === 'fail' ? 'rgba(239,68,68,0.2)' : 'var(--border)',
                background: r.status === 'running' ? 'rgba(99,102,241,0.03)' : 'var(--bg-card)',
              }}>
                <span style={{ fontSize: '1rem', width: 24, textAlign: 'center' }}>
                  {r.status === 'pass' ? '✅' : r.status === 'fail' ? '❌' : r.status === 'running' ? '⏳' : '⬜'}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>{r.name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {r.status === 'running' ? 'Testing...' : r.detail}
                  </div>
                </div>
                {r.response_time_ms && (
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                    {r.response_time_ms}ms
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results summary */}
      {smokeSummary && !smokeRunning && (
        <>
          <div className="card" style={{
            marginBottom: 20,
            background: smokeSummary.fail === 0 ? 'rgba(34,197,94,0.04)' : 'rgba(239,68,68,0.04)',
            borderColor: smokeSummary.fail === 0 ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', marginBottom: 8 }}>
                {smokeSummary.fail === 0 ? '🎉' : '⚠️'}
              </div>
              <div style={{ fontWeight: 600, fontSize: '1.1rem', marginBottom: 4 }}>
                {smokeSummary.fail === 0
                  ? 'All checks passed!'
                  : `${smokeSummary.fail} check(s) failed`
                }
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {smokeSummary.pass} passed · {smokeSummary.fail} failed · {smokeResults.length} total
              </div>
              <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={runSmokeTest}>
                🔄 Run Again
              </button>
            </div>
          </div>

          {/* Detailed results */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {smokeResults.map((r, i) => (
              <div key={i} className="card" style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '10px 14px',
                borderColor: r.status === 'pass' ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)',
              }}>
                <span style={{ fontSize: '1rem', width: 24, textAlign: 'center' }}>
                  {r.status === 'pass' ? '✅' : '❌'}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>{r.name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <code style={{ fontSize: '0.7rem' }}>{r.endpoint}</code> · {r.detail}
                  </div>
                </div>
                {r.response_time_ms !== undefined && (
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                    {r.response_time_ms}ms
                  </span>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );

  const renderStep12Finish = () => (
    <div style={{ textAlign: 'center', maxWidth: 520, margin: '0 auto', paddingTop: 40 }}>
      <div style={{ fontSize: '4rem', marginBottom: 20 }}>🎉</div>
      <h2 style={{ fontSize: '1.75rem', marginBottom: 12 }}>You're All Set!</h2>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: 1.7, marginBottom: 32 }}>
        JARVIS is ready to go. You chose <strong>{USAGE_MODES.find(m => m.key === usageMode)?.label}</strong> mode.
        You can always revisit any configuration later from the Settings page.
      </p>

      <div className="card-grid" style={{ marginBottom: 32 }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 4 }}>💬</div>
          <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>Chat</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Talk to JARVIS</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 4 }}>🔧</div>
          <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>Skills</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Browse capabilities</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 4 }}>⚡</div>
          <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>Automations</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Set up workflows</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: 4 }}>📄</div>
          <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>Documents</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Index & search</div>
        </div>
      </div>

      <button
        className="btn btn-primary"
        onClick={finishSetup}
        disabled={completing}
        style={{ padding: '12px 40px', fontSize: '1rem' }}
      >
        {completing ? 'Finishing...' : '🚀 Open Dashboard'}
      </button>
    </div>
  );

  // ── Step content map ──────────────────────────────────────────────────

  const stepContent = [
    renderStep1Welcome,
    renderStep2SystemCheck,
    renderStep3UsageMode,
    renderStep4LLM,
    renderStep5CommonApps,
    renderStep6Documents,
    renderStep7Voice,
    renderStep8Integrations,
    renderStep9Security,
    renderStep10Diagnostics,
    renderStep11SmokeTest,
    renderStep12Finish,
  ];

  // ── Progress bar ──────────────────────────────────────────────────────

  const progressPercent = ((step + 1) / STEPS.length) * 100;

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <h2 style={{ fontSize: '1.3rem', marginBottom: 4 }}>Setup Wizard</h2>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Step {step + 1} of {STEPS.length}: {STEPS[step].title}
        </div>
      </div>

      {/* Step dots / indicator — show labels on hover, wrap if needed */}
      <div style={{
        display: 'flex', justifyContent: 'center', gap: 4, marginBottom: 32,
        flexWrap: 'wrap', maxWidth: 800, margin: '0 auto 32px',
      }}>
        {STEPS.map((s, i) => (
          <button
            key={s.num}
            onClick={() => setStep(i)}
            style={{
              width: 28, height: 28,
              borderRadius: '50%',
              border: `2px solid ${i === step ? 'var(--accent)' : i < step ? 'var(--success)' : 'var(--border)'}`,
              background: i < step ? 'var(--success)' : i === step ? 'var(--accent)' : 'transparent',
              color: i < step || i === step ? 'white' : 'var(--text-muted)',
              fontSize: '0.68rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
              flexShrink: 0,
            }}
            title={`${s.icon} ${s.title}`}
          >
            {i < step ? '✓' : s.num}
          </button>
        ))}
      </div>

      {/* Progress bar */}
      <div style={{
        height: 4,
        background: 'var(--border)',
        borderRadius: 2,
        marginBottom: 32,
        maxWidth: 700,
        margin: '0 auto 32px',
      }}>
        <div style={{
          height: '100%',
          width: `${progressPercent}%`,
          background: 'linear-gradient(90deg, var(--accent), var(--success))',
          borderRadius: 2,
          transition: 'width 0.3s ease',
        }} />
      </div>

      {/* Step Content */}
      <div style={{ minHeight: 360 }}>
        {stepContent[step]()}
      </div>

      {/* Navigation */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        marginTop: 40,
        maxWidth: 700,
        margin: '40px auto 0',
        paddingTop: 24,
        borderTop: '1px solid var(--border)',
      }}>
        <button
          className="btn btn-secondary"
          onClick={goPrev}
          disabled={isFirst}
          style={{ visibility: isFirst ? 'hidden' : 'visible' }}
        >
          ⏴ Previous
        </button>

        {!isLast && (
          <button className="btn btn-primary" onClick={goNext}>
            Next ⏵
          </button>
        )}

        {isLast && (
          <button
            className="btn btn-primary"
            onClick={finishSetup}
            disabled={completing}
          >
            {completing ? 'Finishing...' : '🚀 Open Dashboard'}
          </button>
        )}
      </div>
    </div>
  );
}

export default SetupWizard;
