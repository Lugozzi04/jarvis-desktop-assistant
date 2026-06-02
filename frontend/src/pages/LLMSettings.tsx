import { useState } from 'react';
import { api } from '../api';
import type { LLMTestResult } from '../api';

function LLMSettings() {
  const [provider, setProvider] = useState('ollama');
  const [baseUrl, setBaseUrl] = useState('http://localhost:11434');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('llama3.1:8b');
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<LLMTestResult | null>(null);
  const [status, setStatus] = useState('');

  const handleProviderChange = (p: string) => {
    setProvider(p);
    setResult(null);
    if (p === 'ollama') {
      setBaseUrl('http://localhost:11434');
      setModel('llama3.1:8b');
    } else if (p === 'openai_compatible') {
      setBaseUrl('https://api.openai.com/v1');
      setModel('gpt-4o-mini');
    }
  };

  const testConnection = async () => {
    setTesting(true);
    setResult(null);
    setStatus('Testing connection...');
    try {
      const res = await api.testLLM(provider, baseUrl, apiKey, model);
      setResult(res);
      setStatus(res.success ? '✅ Connection successful' : `❌ ${res.error || 'Connection failed'}`);
    } catch (err) {
      setStatus(`❌ ${err instanceof Error ? err.message : 'Error'}`);
      setResult({ success: false, provider, available: false, error: String(err) });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div>
      <h2 style={{ marginBottom: 20, fontSize: '1.5rem' }}>LLM Settings</h2>

      <div className="card" style={{ maxWidth: 600 }}>
        <div className="card-header">Provider Configuration</div>

        <div className="form-group">
          <label>Provider</label>
          <select value={provider} onChange={e => handleProviderChange(e.target.value)}>
            <option value="ollama">Ollama (Local)</option>
            <option value="openai_compatible">OpenAI Compatible</option>
            <option value="deepseek">DeepSeek</option>
            <option value="custom">Custom Endpoint</option>
          </select>
        </div>

        <div className="form-group">
          <label>Base URL</label>
          <input
            type="text"
            value={baseUrl}
            onChange={e => setBaseUrl(e.target.value)}
            placeholder="http://localhost:11434 or https://api.openai.com/v1"
          />
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
            {provider === 'ollama' && 'Default: http://localhost:11434'}
            {provider === 'openai_compatible' && 'Default: https://api.openai.com/v1'}
            {provider === 'deepseek' && 'Use: https://api.deepseek.com/v1'}
          </div>
        </div>

        <div className="form-group">
          <label>Model</label>
          <input
            type="text"
            value={model}
            onChange={e => setModel(e.target.value)}
            placeholder="llama3.1:8b, gpt-4o-mini, deepseek-chat"
          />
        </div>

        {provider !== 'ollama' && (
          <div className="form-group">
            <label>API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="sk-..."
            />
          </div>
        )}

        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 16 }}>
          <button
            className="btn btn-primary"
            onClick={testConnection}
            disabled={testing}
          >
            {testing ? 'Testing...' : 'Test Connection'}
          </button>
          {status && (
            <span style={{
              fontSize: '0.9rem',
              color: result?.success ? 'var(--success)' : 'var(--danger)',
            }}>
              {status}
            </span>
          )}
        </div>

        {result && (
          <div className="card" style={{
            marginTop: 16,
            background: result.success ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
            border: `1px solid ${result.success ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
          }}>
            <div className="card-header">Test Result</div>
            <div style={{ fontSize: '0.85rem' }}>
              <div>Provider: <strong>{result.provider}</strong></div>
              <div>Available: <strong>{result.available ? 'Yes' : 'No'}</strong></div>
              {result.test_response && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>Response:</div>
                  <div style={{ padding: '8px 12px', background: 'var(--bg-primary)', borderRadius: 'var(--radius)' }}>
                    {result.test_response}
                  </div>
                </div>
              )}
              {result.error && (
                <div style={{ marginTop: 8, color: 'var(--danger)' }}>Error: {result.error}</div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="card" style={{ maxWidth: 600, marginTop: 16 }}>
        <div className="card-header">Setup Guide</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
          <p><strong>Ollama (Local):</strong></p>
          <ol style={{ paddingLeft: 20 }}>
            <li>Install Ollama: <code>curl -fsSL https://ollama.com/install.sh | sh</code></li>
            <li>Pull a model: <code>ollama pull llama3.1:8b</code></li>
            <li>Set provider to "Ollama", test connection</li>
          </ol>
          <p style={{ marginTop: 12 }}><strong>OpenAI:</strong></p>
          <ol style={{ paddingLeft: 20 }}>
            <li>Get API key from platform.openai.com</li>
            <li>Set provider to "OpenAI Compatible"</li>
            <li>Base URL: https://api.openai.com/v1</li>
            <li>Enter API key, test connection</li>
          </ol>
          <p style={{ marginTop: 12 }}><strong>DeepSeek:</strong></p>
          <ol style={{ paddingLeft: 20 }}>
            <li>Get API key from platform.deepseek.com</li>
            <li>Set provider to "DeepSeek" or "OpenAI Compatible"</li>
            <li>Base URL: https://api.deepseek.com/v1</li>
            <li>Model: deepseek-chat</li>
          </ol>
        </div>
      </div>
    </div>
  );
}

export default LLMSettings;
