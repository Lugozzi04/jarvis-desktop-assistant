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
  stt_details: {
    available: boolean;
    model?: string;
    error?: string;
    setup_required?: boolean;
    setup_command?: string;
  };
  tts_details: {
    available: boolean;
    voice?: string;
    error?: string;
    setup_required?: boolean;
    setup_command?: string;
  };
  errors: string[];
}

function Voice() {
  const [status, setStatus] = useState<VoiceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [recording, setRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [transcription, setTranscription] = useState('');
  const [transcribing, setTranscribing] = useState(false);
  const [result, setResult] = useState<{ response?: string; error?: string } | null>(null);
  const [ttsText, setTtsText] = useState('');
  const [speaking, setSpeaking] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => { loadStatus(); }, []);

  const loadStatus = async () => {
    try {
      const res = await fetch(`${API}/voice/status`);
      const data = await res.json();
      setStatus(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  // ── Push-to-Talk ──
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
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
    } catch {
      // Mic not available — handled in UI
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
        setResult({ response: data.response.response || data.response.error });
      }
    } catch (err) {
      setTranscription('Error: ' + (err instanceof Error ? err.message : 'Failed'));
    } finally {
      setTranscribing(false);
    }
  };

  // ── File Upload ──
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setTranscribing(true);
    setTranscription('');
    setResult(null);

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

  // ── TTS ──
  const speak = async () => {
    if (!ttsText.trim()) return;
    setSpeaking(true);
    setAudioUrl(null);
    try {
      const res = await fetch(`${API}/voice/speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: ttsText }),
      });
      const data = await res.json();
      if (data.success && data.audio_path) {
        setAudioUrl(`${API.replace('/api', '')}${data.audio_path}`);
      } else if (data.audio_data) {
        // Could play from bytes, but for now show success
        setResult({ response: '✅ Audio generated' });
      } else if (data.error) {
        setResult({ error: data.error });
      }
    } catch (err) {
      setResult({ error: err instanceof Error ? err.message : 'TTS failed' });
    } finally {
      setSpeaking(false);
    }
  };

  // ── Render ──
  if (loading) return <div className="loading"><div className="spinner" /></div>;

  const sttOk = status?.stt_available ?? false;
  const ttsOk = status?.tts_available ?? false;
  const micAvailable = typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia;

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <h2 style={{ fontSize: '1.5rem', margin: 0 }}>🎤 Voice</h2>
        <div style={{ display: 'flex', gap: 6 }}>
          <span className={`badge ${sttOk ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '0.7rem' }}>
            STT: {status?.stt_provider || 'none'} {sttOk ? '✓' : '✗'}
          </span>
          <span className={`badge ${ttsOk ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '0.7rem' }}>
            TTS: {status?.tts_provider || 'none'} {ttsOk ? '✓' : '✗'}
          </span>
        </div>
      </div>

      {/* WIP Banner */}
      <div className="card" style={{
        marginBottom: 20,
        borderLeft: '4px solid #f59e0b',
        background: 'linear-gradient(135deg, rgba(245,158,11,0.06), transparent)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: '1.5rem' }}>🚧</span>
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#f59e0b' }}>Work in Progress</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 2 }}>
              Voice features are evolving. Wake-word ("Jarvis") always-listening coming soon.
            </div>
          </div>
        </div>
      </div>

      {/* ── Push-to-Talk ── */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          🎙️ Push-to-Talk
          {!micAvailable && (
            <span style={{ fontSize: '0.7rem', color: 'var(--warning)', fontWeight: 400 }}>
              Mic not available — use file upload below
            </span>
          )}
        </div>

        {micAvailable ? (
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            {!recording ? (
              <button className="btn btn-primary" onClick={startRecording} disabled={transcribing}>
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
                  📼 {(audioBlob.size / 1024).toFixed(1)} KB
                </span>
                <button className="btn btn-primary" onClick={transcribe} disabled={transcribing}>
                  {transcribing ? '⏳ Transcribing...' : '📝 Transcribe & Send'}
                </button>
                <button className="btn btn-sm btn-secondary" onClick={() => { setAudioBlob(null); setResult(null); }}>
                  Clear
                </button>
              </>
            )}
          </div>
        ) : (
          <div style={{ padding: '20px 12px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '2rem', marginBottom: 8 }}>🎤❌</div>
            <div style={{ fontSize: '0.85rem', marginBottom: 4 }}>Microphone not available</div>
            <div style={{ fontSize: '0.75rem' }}>
              Use the <strong>file upload</strong> below or the{' '}
              <strong>🎤 button in Chat</strong> (Chrome/Edge required).
            </div>
          </div>
        )}
      </div>

      {/* ── File Upload ── */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          📁 Upload Audio File
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <input
            type="file"
            accept="audio/*"
            onChange={handleFileUpload}
            disabled={transcribing}
            style={{ fontSize: '0.85rem' }}
          />
          {transcribing && <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>⏳ Transcribing...</span>}
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 8 }}>
          Supports WAV, MP3, WebM, OGG, FLAC. Processed by {status?.stt_provider || 'mock'}.
        </div>
      </div>

      {/* ── Transcription Result ── */}
      {transcription && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">📝 Transcription</div>
          <div style={{
            padding: '12px 16px',
            background: 'var(--bg-primary)',
            borderRadius: 'var(--radius)',
            fontSize: '0.95rem',
            lineHeight: 1.6,
            whiteSpace: 'pre-wrap',
            fontStyle: 'italic',
            color: 'var(--text-primary)',
          }}>
            "{transcription}"
          </div>
        </div>
      )}

      {/* ── Assistant Response ── */}
      {result && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">🤖 Jarvis Response</div>
          {result.response && (
            <div style={{ fontSize: '0.9rem', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{result.response}</div>
          )}
          {result.error && (
            <div style={{ fontSize: '0.9rem', color: 'var(--danger)' }}>❌ {result.error}</div>
          )}
        </div>
      )}

      {/* ── TTS Test ── */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">🔊 Text-to-Speech</div>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            type="text"
            value={ttsText}
            onChange={e => setTtsText(e.target.value)}
            placeholder="Type something for Jarvis to say..."
            style={{ flex: 1 }}
          />
          <button className="btn btn-primary" onClick={speak} disabled={speaking || !ttsText.trim()}>
            {speaking ? '⏳ Generating...' : '🔊 Speak'}
          </button>
        </div>
        {audioUrl && (
          <div style={{ marginTop: 10 }}>
            <audio controls src={audioUrl} style={{ width: '100%' }} />
          </div>
        )}
        {status?.tts_provider === 'mock' && (
          <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Mock TTS — text is logged, not spoken. Install edge-tts: <code>pip install edge-tts</code>
          </div>
        )}
        {status?.tts_provider === 'edge' && !ttsOk && (
          <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--warning)' }}>
            edge-tts not installed. Run: <code>{status?.tts_details?.setup_command || 'pip install edge-tts'}</code>
          </div>
        )}
      </div>

      {/* ── Setup Guide ── */}
      <div className="card">
        <div className="card-header">📖 Setup Guide</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
          <p>
            <strong>Speech-to-Text ({status?.stt_provider || 'mock'}):</strong>{' '}
            {sttOk ? (
              <span style={{ color: 'var(--success)' }}>✅ Active — model: {status?.stt_details?.model || 'base'}</span>
            ) : (
              <span style={{ color: 'var(--warning)' }}>
                ⚠️ Not active.{' '}
                {status?.stt_details?.setup_command && (
                  <>Run: <code>{status.stt_details.setup_command}</code></>
                )}
              </span>
            )}
          </p>
          <p>
            <strong>Text-to-Speech ({status?.tts_provider || 'mock'}):</strong>{' '}
            {ttsOk ? (
              <span style={{ color: 'var(--success)' }}>✅ Active — voice: {status?.tts_details?.voice || 'default'}</span>
            ) : (
              <span style={{ color: 'var(--warning)' }}>
                ⚠️ Not active.{' '}
                {status?.tts_details?.setup_command && (
                  <>Run: <code>{status.tts_details.setup_command}</code></>
                )}
              </span>
            )}
          </p>
          <p style={{ marginTop: 10, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            For real STT: <code>pip install faster-whisper</code> + set <code>VOICE_STT_PROVIDER=faster_whisper</code> in .env<br />
            For real TTS: <code>pip install edge-tts</code> + set <code>VOICE_TTS_PROVIDER=edge</code> in .env
          </p>
        </div>
      </div>
    </div>
  );
}

export default Voice;
