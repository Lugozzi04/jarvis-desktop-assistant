import { useState, useEffect, useRef } from 'react';

const API = 'http://localhost:8400/api';

interface VoiceStatus {
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

function Voice() {
  const [status, setStatus] = useState<VoiceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [recording, setRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [transcription, setTranscription] = useState('');
  const [transcribing, setTranscribing] = useState(false);
  const [ttsText, setTtsText] = useState('');
  const [speaking, setSpeaking] = useState(false);
  const [result, setResult] = useState<{ status: string; response?: string } | null>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => { loadStatus(); }, []);

  const loadStatus = async () => {
    try {
      const res = await fetch(`${API}/voice/status`);
      setStatus(await res.json());
      setLoading(false);
    } catch {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorder.current = rec;
      chunks.current = [];

      rec.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data);
      };
      rec.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' });
        setAudioBlob(blob);
        stream.getTracks().forEach(t => t.stop());
      };

      rec.start();
      setRecording(true);
    } catch (err) {
      alert('Microphone access denied or not available. You can upload an audio file instead.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder.current && mediaRecorder.current.state === 'recording') {
      mediaRecorder.current.stop();
      setRecording(false);
    }
  };

  const transcribe = async () => {
    if (!audioBlob) return;
    setTranscribing(true);
    setTranscription('');
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.webm');
      const res = await fetch(`${API}/voice/command`, { method: 'POST', body: formData });
      const data = await res.json();
      if (data.transcription?.text) {
        setTranscription(data.transcription.text);
      }
      if (data.response) {
        setResult({ status: 'success', response: data.response.response || data.response.error });
      }
    } catch (err) {
      setTranscription('Error: ' + (err instanceof Error ? err.message : 'Failed'));
    } finally {
      setTranscribing(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAudioBlob(file);
    setTranscribing(true);
    setTranscription('');

    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API}/voice/transcribe`, { method: 'POST', body: formData });
      const data = await res.json();
      setTranscription(data.text || data.error || 'No transcription');
    } catch (err) {
      setTranscription('Error: ' + (err instanceof Error ? err.message : 'Failed'));
    } finally {
      setTranscribing(false);
    }
  };

  const speak = async () => {
    if (!ttsText.trim()) return;
    setSpeaking(true);
    try {
      const res = await fetch(`${API}/voice/speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: ttsText }),
      });
      const data = await res.json();
      if (!data.success) {
        alert('TTS failed: ' + (data.error || 'Unknown error'));
      }
    } catch {
      // Mock TTS just logs — nothing to play
    } finally {
      setSpeaking(false);
    }
  };

  if (loading) return <div className="loading"><div className="spinner" /></div>;

  return (
    <div>
      <h2 style={{ marginBottom: 20, fontSize: '1.5rem' }}>Voice</h2>

      {/* Status Cards */}
      <div className="card-grid" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="stat-value">
            <span className={`status-dot ${status?.stt_available ? 'online' : 'offline'}`} />
            {status?.stt_available ? ' Ready' : ' Offline'}
          </div>
          <div className="stat-label">STT: {status?.stt_provider || 'none'}</div>
          {status?.stt_details?.note && (
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>{status.stt_details.note}</div>
          )}
        </div>
        <div className="card">
          <div className="stat-value">
            <span className={`status-dot ${status?.tts_available ? 'online' : 'offline'}`} />
            {status?.tts_available ? ' Ready' : ' Offline'}
          </div>
          <div className="stat-label">TTS: {status?.tts_provider || 'none'}</div>
        </div>
        <div className="card">
          <div className="stat-value">{status?.wake_word_enabled ? '🟢 On' : '⚫ Off'}</div>
          <div className="stat-label">Wake Word — coming in future</div>
        </div>
      </div>

      {/* Push-to-Talk */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">🎤 Push-to-Talk</div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          {!recording ? (
            <button className="btn btn-primary" onClick={startRecording}>
              🎙️ Start Recording
            </button>
          ) : (
            <button className="btn btn-danger" onClick={stopRecording}>
              ⏹️ Stop Recording
            </button>
          )}
          {audioBlob && !recording && (
            <>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                📼 {(audioBlob.size / 1024).toFixed(1)} KB recorded
              </span>
              <button className="btn btn-primary" onClick={transcribe} disabled={transcribing}>
                {transcribing ? 'Transcribing...' : '📝 Transcribe & Send'}
              </button>
            </>
          )}
        </div>
        <div style={{ marginTop: 10, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Or upload an audio file:
          <input type="file" accept="audio/*" onChange={handleFileUpload} style={{ marginLeft: 10, display: 'inline-block', width: 'auto' }} />
        </div>
      </div>

      {/* Transcription */}
      {transcription && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">📝 Transcription</div>
          <div style={{ padding: '12px', background: 'var(--bg-primary)', borderRadius: 'var(--radius)', fontSize: '0.95rem' }}>
            "{transcription}"
          </div>
        </div>
      )}

      {/* Assistant Response */}
      {result && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">🤖 Jarvis Response</div>
          <div style={{ fontSize: '0.9rem', whiteSpace: 'pre-wrap' }}>{result.response}</div>
        </div>
      )}

      {/* TTS Test */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">🔊 Text-to-Speech Test</div>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            type="text"
            value={ttsText}
            onChange={e => setTtsText(e.target.value)}
            placeholder="Type something for Jarvis to say..."
            style={{ flex: 1 }}
          />
          <button className="btn btn-primary" onClick={speak} disabled={speaking}>
            {speaking ? 'Speaking...' : '🔊 Speak'}
          </button>
        </div>
        {status?.tts_provider === 'mock' && (
          <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Mock TTS — text is logged, not spoken aloud. Configure a real TTS provider for audio output.
          </div>
        )}
      </div>

      {/* Setup Guide */}
      <div className="card">
        <div className="card-header">📖 Setup Guide</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
          <p><strong>Default (Mock):</strong> No setup required. Works on VPS and local. Transcriptions return mock text, TTS logs instead of speaking.</p>

          <p style={{ marginTop: 10 }}><strong>Real STT (Faster-Whisper) — Local PC only:</strong></p>
          <ol style={{ paddingLeft: 20 }}>
            <li>Install: <code>pip install faster-whisper</code></li>
            <li>Set in .env: <code>JARVIS_STT_PROVIDER=faster_whisper</code></li>
            <li>Choose model: <code>JARVIS_STT_MODEL=base</code> (or tiny/small/medium)</li>
            <li>Model downloads automatically on first use (~150 MB for base)</li>
            <li>Restart JARVIS</li>
          </ol>

          <p style={{ marginTop: 10 }}><strong>Real TTS — coming in future update.</strong></p>

          <p style={{ marginTop: 10, color: 'var(--text-muted)' }}>
            ⚠️ Wake word ("Jarvis") always-listening is NOT yet implemented. Use push-to-talk for voice input.
          </p>
        </div>
      </div>
    </div>
  );
}

export default Voice;
