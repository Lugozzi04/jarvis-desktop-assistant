import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';
import type { ChatResponse } from '../api';

interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  details?: string;
  timestamp: string;
}

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  llm_model: string;
}

const API = 'http://localhost:8400';

function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    { id: 0, role: 'assistant', content: 'Hello! I\'m JARVIS. How can I help you?\n\nTry slash commands:\n• /open <app>\n• /search <query>\n• /timer <duration> <message>\n• /system stats\n• /ask <question>', timestamp: '' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchParams] = useSearchParams();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const msgId = useRef(1);

  // Conversation state — null = temporary (unsaved)
  const [convId, setConvId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [showHistory, setShowHistory] = useState(true);

  // Voice recording
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => { loadConversations(); }, []);
  useEffect(() => {
    const cmd = searchParams.get('cmd');
    if (cmd) sendMessage(cmd);
  }, []);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => { inputRef.current?.focus(); }, [convId]);

  // ── Conversations ──

  const loadConversations = async () => {
    try {
      const res = await fetch(`${API}/api/conversations`);
      const data = await res.json();
      setConversations(data.conversations || []);
    } catch {}
  };

  const startNewChat = () => {
    setMessages([
      { id: 0, role: 'assistant', content: 'Hello! I\'m JARVIS. How can I help you?\n\nTry slash commands:\n• /open <app>\n• /search <query>\n• /timer <duration> <message>\n• /system stats\n• /ask <question>', timestamp: '' },
    ]);
    msgId.current = 1;
    setConvId(null); // Temporary — NOT saved
    inputRef.current?.focus();
  };

  const selectConversation = async (id: string) => {
    try {
      const res = await fetch(`${API}/api/conversations/${id}`);
      const data = await res.json();
      if (data.messages) {
        const msgs: Message[] = [
          { id: 0, role: 'assistant', content: 'Hello! I\'m JARVIS. How can I help you?', timestamp: '' },
        ];
        data.messages.forEach((m: { id: number; role: string; content: string }, i: number) => {
          msgs.push({ id: i + 1, role: m.role as Message['role'], content: m.content, timestamp: '' });
        });
        msgId.current = msgs.length;
        setMessages(msgs);
      }
      setConvId(id); // Saved conversation
    } catch {}
  };

  const deleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await fetch(`${API}/api/conversations/${id}`, { method: 'DELETE' });
      setConversations(prev => prev.filter(c => c.id !== id));
      if (convId === id) startNewChat();
    } catch {}
  };

  // ── Save current temp chat ──
  const saveConversation = async () => {
    if (convId) return; // Already saved
    try {
      const res = await fetch(`${API}/api/conversations`, { method: 'POST' });
      const data = await res.json();
      const cid = data.id;
      setConvId(cid);
      loadConversations();
      // Now save existing messages to backend
      for (const msg of messages) {
        if (msg.id > 0 && msg.role !== 'system') {
          try {
            await fetch(`${API}/api/chat`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ message: msg.content, session_id: cid, source: 'text' }),
            });
          } catch {}
        }
      }
      // Don't re-send — just mark conversation as saved
      loadConversations();
    } catch {}
  };

  // ── Voice ──

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      mediaRecorderRef.current = rec;
      audioChunksRef.current = [];
      rec.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      rec.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        await transcribeAudio(new Blob(audioChunksRef.current, { type: 'audio/webm' }));
      };
      rec.start();
      setRecording(true);
    } catch {
      alert('Microphone access denied.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
      setRecording(false);
    }
  };

  const transcribeAudio = async (blob: Blob) => {
    setTranscribing(true);
    try {
      const formData = new FormData();
      formData.append('file', blob, 'recording.webm');
      const res = await fetch(`${API}/api/voice/command`, { method: 'POST', body: formData });
      const data = await res.json();
      if (data.transcription?.text) {
        setInput(prev => (prev + ' ' + data.transcription.text).trim());
        inputRef.current?.focus();
      }
    } catch {}
    setTranscribing(false);
  };

  // ── Messaging ──

  const addMessage = (role: Message['role'], content: string, details?: string) => {
    setMessages(prev => [...prev, {
      id: msgId.current++, role, content, details,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }]);
  };

  const formatResult = (res: ChatResponse): string => {
    if (res.needs_confirmation) return `⚠️ **Confirmation required**\n${res.confirmation_message}`;
    if (res.result) {
      return res.result.success
        ? `✅ ${res.result.result || 'Done'}\n_${res.result.skill}.${res.result.action} — ${res.duration_ms?.toFixed(0)}ms_`
        : `❌ ${res.result.error || 'Action failed'}`;
    }
    return res.response;
  };

  const sendMessage = async (text?: string) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;

    setInput('');
    addMessage('user', msg);
    setLoading(true);

    const cid = convId;

    try {
      const isSlash = msg.startsWith('/');
      const res = isSlash
        ? await api.command(msg, cid || undefined)
        : await api.chat(msg, cid || undefined);
      addMessage('assistant', formatResult(res));
      if (res.intent) {
        addMessage('system', `Intent: ${res.intent.kind} → ${res.intent.skill || '?'}.${res.intent.action || '?'} (${(res.intent.confidence * 100).toFixed(0)}%)`);
      }
      if (cid) loadConversations();
    } catch (err) {
      addMessage('assistant', `❌ Error: ${err instanceof Error ? err.message : 'Connection failed'}`);
    }
    setLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const isTemp = !convId;

  // ── Render ──

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - var(--topbar-height) - 60px)', flexDirection: 'row-reverse' }}>
      {/* History Sidebar — RIGHT */}
      {showHistory && (
        <div style={{ width: 230, minWidth: 230, borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column', background: 'var(--bg-secondary)' }}>
          <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>💬 History</span>
            <button className="btn btn-sm btn-primary" style={{ padding: '3px 8px', fontSize: '0.7rem', borderRadius: 6 }} onClick={startNewChat}>＋ New</button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '2px 0' }}>
            {conversations.length === 0 && (
              <div style={{ padding: '20px 12px', fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'center', lineHeight: 1.6 }}>
                No saved chats yet.
              </div>
            )}
            {conversations.map(conv => (
              <div key={conv.id} onClick={() => selectConversation(conv.id)} style={{ padding: '8px 10px', cursor: 'pointer', background: convId === conv.id ? 'var(--bg-primary)' : 'transparent', borderLeft: convId === conv.id ? '3px solid var(--accent)' : '3px solid transparent', borderRight: convId === conv.id ? '3px solid var(--accent)' : '3px solid transparent', margin: '1px 0', transition: 'background 0.12s' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: convId === conv.id ? 600 : 400, fontSize: '0.8rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: convId === conv.id ? 'var(--text-primary)' : 'var(--text-secondary)' }}>{conv.title}</div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 1 }}>{conv.message_count} msg</div>
                  </div>
                  <button style={{ padding: '2px 5px', fontSize: '0.65rem', background: 'transparent', color: 'var(--text-muted)', border: 'none', cursor: 'pointer', borderRadius: 4, flexShrink: 0, opacity: 0.6 }}
                    onClick={(e) => deleteConversation(conv.id, e)} title="Delete">×</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Chat Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, position: 'relative' }}>

        {/* ── Save Box (only on temporary chats) ── */}
        {isTemp && (
          <div style={{
            position: 'absolute',
            top: 10,
            right: 14,
            zIndex: 50,
            background: 'var(--bg-secondary, #1e1e2e)',
            border: '1px solid var(--accent, #6366f1)',
            borderRadius: 10,
            padding: '8px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            boxShadow: '0 2px 12px rgba(0,0,0,0.15)',
            cursor: 'pointer',
            transition: 'transform 0.15s, box-shadow 0.15s',
          }}
            onClick={saveConversation}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.transform = 'scale(1.04)';
              (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 20px rgba(99,102,241,0.3)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.transform = 'scale(1)';
              (e.currentTarget as HTMLElement).style.boxShadow = '0 2px 12px rgba(0,0,0,0.15)';
            }}
            title="Save this conversation"
          >
            <span style={{ fontSize: '1rem' }}>💾</span>
            <span style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--accent, #6366f1)' }}>Save Chat</span>
          </div>
        )}

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px 40px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {messages.map(msg => (
            <div key={msg.id} style={{
              padding: '10px 14px', borderRadius: 12, maxWidth: '85%',
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              background: msg.role === 'user' ? 'var(--accent, #6366f1)' : msg.role === 'system' ? 'var(--bg-tertiary, #313244)' : 'var(--bg-secondary, #1e1e2e)',
              color: msg.role === 'user' ? 'white' : 'var(--text-primary)',
              fontSize: '0.9rem', lineHeight: 1.55,
              border: msg.role === 'system' ? '1px dashed var(--border)' : 'none',
            }}>
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
                {msg.details && <div style={{ fontSize: '0.7rem', opacity: 0.55 }}>{msg.details}</div>}
                {msg.timestamp && <div style={{ fontSize: '0.65rem', opacity: 0.45, marginLeft: 'auto' }}>{msg.timestamp}</div>}
              </div>
            </div>
          ))}
          {loading && <div style={{ padding: '10px 14px', borderRadius: 12, alignSelf: 'flex-start', background: 'var(--bg-secondary)' }}><div className="spinner" style={{ width: 16, height: 16 }} /></div>}
          {transcribing && <div style={{ padding: '8px 14px', borderRadius: 12, alignSelf: 'flex-start', background: 'var(--bg-secondary)', fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}><span>🎤</span> Transcribing with Whisper...</div>}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div style={{ padding: '8px 12px', borderTop: '1px solid var(--border)', background: 'var(--bg-primary)' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button className="btn btn-sm btn-secondary" style={{ padding: '4px 8px', fontSize: '0.7rem', flexShrink: 0, borderRadius: 8 }} onClick={() => setShowHistory(!showHistory)} title="Toggle history sidebar">
              {showHistory ? '◀' : '📋'}
            </button>
            <input ref={inputRef} type="text" placeholder={recording ? '🔴 Recording...' : transcribing ? '🎤 Transcribing...' : 'Type a message or slash command...'}
              value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown} disabled={loading || transcribing}
              style={{ flex: 1, padding: '10px 14px', borderRadius: 10, border: recording ? '2px solid var(--danger)' : '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.9rem', outline: 'none', transition: 'border 0.15s' }} />
            <button className={`btn ${recording ? 'btn-danger' : 'btn-secondary'}`}
              style={{ padding: '6px 14px', fontSize: '1.1rem', flexShrink: 0, borderRadius: 10, animation: recording ? 'pulse 0.8s infinite' : 'none', background: recording ? 'var(--danger)' : undefined, color: recording ? 'white' : undefined }}
              onClick={recording ? stopRecording : startRecording} disabled={loading || transcribing}
              title={recording ? 'Stop recording' : 'Voice input (Whisper)'}>
              {recording ? '⏹' : transcribing ? '⏳' : '🎤'}
            </button>
            <button className="btn btn-primary" onClick={() => sendMessage()} disabled={loading || transcribing || !input.trim()}
              style={{ padding: '6px 18px', borderRadius: 10, fontSize: '0.9rem', flexShrink: 0 }}>Send</button>
          </div>
          {recording && <div style={{ fontSize: '0.7rem', color: 'var(--danger)', marginTop: 4, textAlign: 'center' }}>🔴 Recording — click ⏹ to stop and transcribe</div>}
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239,68,68,0.4); }
          50% { transform: scale(1.08); box-shadow: 0 0 0 8px rgba(239,68,68,0); }
        }
      `}</style>
    </div>
  );
}

export default Chat;
