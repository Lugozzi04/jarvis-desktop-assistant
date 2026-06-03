import { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { ChatResponse } from '../api';

interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  details?: string;
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
    { id: 0, role: 'assistant', content: 'Hello! I\'m JARVIS. How can I help you?\n\nTry slash commands:\n• /open <app>\n• /search <query>\n• /timer <duration> <message>\n• /system stats\n• /ask <question>' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const msgId = useRef(1);

  // Conversation state
  const [convId, setConvId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [showHistory, setShowHistory] = useState(true);

  // Voice recording via Whisper backend
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Handle ?cmd= from Dashboard quick actions
  useEffect(() => {
    const cmd = searchParams.get('cmd');
    if (cmd) {
      sendMessage(cmd);
    }
  }, []);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when conversation changes
  useEffect(() => {
    inputRef.current?.focus();
  }, [convId]);

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
      { id: 0, role: 'assistant', content: 'Hello! I\'m JARVIS. How can I help you?\n\nTry slash commands:\n• /open <app>\n• /search <query>\n• /timer <duration> <message>\n• /system stats\n• /ask <question>' },
    ]);
    msgId.current = 1;
    setConvId(null);
    inputRef.current?.focus();
  };

  const selectConversation = async (id: string) => {
    try {
      const res = await fetch(`${API}/api/conversations/${id}`);
      const data = await res.json();
      if (data.messages) {
        const msgs: Message[] = [
          { id: 0, role: 'assistant', content: 'Hello! I\'m JARVIS. How can I help you?' },
        ];
        data.messages.forEach((m: { id: number; role: string; content: string }, i: number) => {
          msgs.push({ id: i + 1, role: m.role as Message['role'], content: m.content });
        });
        msgId.current = msgs.length;
        setMessages(msgs);
      }
      setConvId(id);
    } catch {}
  };

  const deleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await fetch(`${API}/api/conversations/${id}`, { method: 'DELETE' });
      setConversations(prev => prev.filter(c => c.id !== id));
      if (convId === id) {
        startNewChat();
      }
    } catch {}
  };

  // ── Voice Recording (Whisper backend) ──

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      mediaRecorderRef.current = rec;
      audioChunksRef.current = [];

      rec.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      rec.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await transcribeAudio(blob);
      };

      rec.start();
      setRecording(true);
    } catch (err) {
      alert('Microphone access denied. Please allow microphone access in your browser settings.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setRecording(false);
    }
  };

  const transcribeAudio = async (blob: Blob) => {
    setTranscribing(true);
    try {
      const formData = new FormData();
      formData.append('file', blob, 'recording.webm');
      const res = await fetch(`${API}/api/voice/command`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (data.transcription?.text) {
        const text = data.transcription.text.trim();
        setInput(prev => (prev + ' ' + text).trim());
        // Focus input
        inputRef.current?.focus();
      } else if (data.error) {
        // Fallback: show error
        setInput(prev => prev + ' [Voice transcription failed]');
      }
    } catch (err) {
      setInput(prev => prev + ' [Voice error]');
    } finally {
      setTranscribing(false);
    }
  };

  // ── Messaging ──

  const addMessage = (role: Message['role'], content: string, details?: string) => {
    setMessages(prev => [...prev, { id: msgId.current++, role, content, details }]);
  };

  const formatResult = (res: ChatResponse): string => {
    if (res.needs_confirmation) {
      return `⚠️ **Confirmation required**\n${res.confirmation_message}`;
    }
    if (res.result) {
      if (res.result.success) {
        return `✅ ${res.result.result || 'Done'}\n_${res.result.skill}.${res.result.action} — ${res.duration_ms?.toFixed(0)}ms_`;
      } else {
        return `❌ ${res.result.error || 'Action failed'}`;
      }
    }
    return res.response;
  };

  const sendMessage = async (text?: string) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;

    setInput('');
    addMessage('user', msg);
    setLoading(true);

    // Auto-create conversation on first message
    let cid = convId;
    if (!cid) {
      try {
        const res = await fetch(`${API}/api/conversations`, { method: 'POST' });
        const data = await res.json();
        cid = data.id;
        setConvId(cid);
        // Immediately refresh sidebar to show new conversation
        loadConversations();
      } catch {}
    }

    try {
      const isSlash = msg.startsWith('/');
      const res = isSlash ? await api.command(msg) : await api.chat(msg);
      addMessage('assistant', formatResult(res));
      if (res.intent) {
        const intentInfo = `Intent: ${res.intent.kind} → ${res.intent.skill || '?'}.${res.intent.action || '?'} (${(res.intent.confidence * 100).toFixed(0)}%)`;
        addMessage('system', intentInfo);
      }
      // Refresh conversation list to update counts/titles
      loadConversations();
    } catch (err) {
      addMessage('assistant', `❌ Error: ${err instanceof Error ? err.message : 'Connection failed'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // ── Render ──

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - var(--topbar-height) - 60px)', flexDirection: 'row-reverse' }}>
      {/* History Sidebar — RIGHT side */}
      {showHistory && (
        <div style={{
          width: 230,
          minWidth: 230,
          borderLeft: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg-secondary)',
        }}>
          <div style={{
            padding: '10px 12px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>💬 History</span>
            <button
              className="btn btn-sm btn-primary"
              style={{ padding: '3px 8px', fontSize: '0.7rem', borderRadius: 6 }}
              onClick={startNewChat}
            >
              ＋ New
            </button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '2px 0' }}>
            {conversations.length === 0 && (
              <div style={{
                padding: '20px 12px',
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
                textAlign: 'center',
                lineHeight: 1.6,
              }}>
                No conversations yet.<br />Start chatting to<br />create one!
              </div>
            )}
            {conversations.map(conv => (
              <div
                key={conv.id}
                onClick={() => selectConversation(conv.id)}
                style={{
                  padding: '8px 10px',
                  cursor: 'pointer',
                  background: convId === conv.id ? 'var(--bg-primary)' : 'transparent',
                  borderLeft: convId === conv.id ? '3px solid var(--accent)' : '3px solid transparent',
                  borderRight: convId === conv.id ? '3px solid var(--accent)' : '3px solid transparent',
                  transition: 'background 0.12s',
                  margin: '1px 0',
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.background =
                    convId === conv.id ? 'var(--bg-primary)' : 'var(--bg-hover, rgba(255,255,255,0.03))';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.background =
                    convId === conv.id ? 'var(--bg-primary)' : 'transparent';
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontWeight: convId === conv.id ? 600 : 400,
                      fontSize: '0.8rem',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      color: convId === conv.id ? 'var(--text-primary)' : 'var(--text-secondary)',
                    }}>
                      {conv.title}
                    </div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 1 }}>
                      {conv.message_count} msg
                    </div>
                  </div>
                  <button
                    style={{
                      padding: '2px 5px',
                      fontSize: '0.65rem',
                      background: 'transparent',
                      color: 'var(--text-muted)',
                      border: 'none',
                      cursor: 'pointer',
                      borderRadius: 4,
                      flexShrink: 0,
                      opacity: 0.6,
                    }}
                    onClick={(e) => deleteConversation(conv.id, e)}
                    title="Delete"
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.opacity = '1';
                      (e.currentTarget as HTMLElement).style.color = 'var(--danger)';
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.opacity = '0.6';
                      (e.currentTarget as HTMLElement).style.color = 'var(--text-muted)';
                    }}
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Chat Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Messages */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}>
          {messages.map(msg => (
            <div
              key={msg.id}
              style={{
                padding: '10px 14px',
                borderRadius: 12,
                maxWidth: '85%',
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                background: msg.role === 'user'
                  ? 'var(--accent, #6366f1)'
                  : msg.role === 'system'
                    ? 'var(--bg-tertiary, #313244)'
                    : 'var(--bg-secondary, #1e1e2e)',
                color: msg.role === 'user' ? 'white' : 'var(--text-primary)',
                fontSize: '0.9rem',
                lineHeight: 1.55,
                border: msg.role === 'system' ? '1px dashed var(--border)' : 'none',
              }}
            >
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
              {msg.details && (
                <div style={{ fontSize: '0.7rem', opacity: 0.55, marginTop: 4 }}>{msg.details}</div>
              )}
            </div>
          ))}
          {loading && (
            <div style={{
              padding: '10px 14px',
              borderRadius: 12,
              alignSelf: 'flex-start',
              background: 'var(--bg-secondary, #1e1e2e)',
            }}>
              <div className="spinner" style={{ width: 16, height: 16 }} />
            </div>
          )}
          {transcribing && (
            <div style={{
              padding: '8px 14px',
              borderRadius: 12,
              alignSelf: 'flex-start',
              background: 'var(--bg-secondary, #1e1e2e)',
              fontSize: '0.8rem',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}>
              <span>🎤</span> Transcribing with Whisper...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div style={{
          padding: '8px 12px',
          borderTop: '1px solid var(--border)',
          background: 'var(--bg-primary)',
        }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {/* Toggle history */}
            <button
              className="btn btn-sm btn-secondary"
              style={{
                padding: '4px 8px',
                fontSize: '0.7rem',
                flexShrink: 0,
                borderRadius: 8,
              }}
              onClick={() => setShowHistory(!showHistory)}
              title="Toggle history sidebar"
            >
              {showHistory ? '◀' : '📋'}
            </button>

            {/* Input */}
            <input
              ref={inputRef}
              type="text"
              placeholder={
                recording ? '🔴 Recording...' :
                transcribing ? '🎤 Transcribing...' :
                'Type a message or slash command...'
              }
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading || transcribing}
              style={{
                flex: 1,
                padding: '10px 14px',
                borderRadius: 10,
                border: recording ? '2px solid var(--danger)' : '1px solid var(--border)',
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                fontSize: '0.9rem',
                outline: 'none',
                transition: 'border 0.15s',
              }}
            />

            {/* Mic button — Whisper backend */}
            <button
              className={`btn ${recording ? 'btn-danger' : 'btn-secondary'}`}
              style={{
                padding: '6px 14px',
                fontSize: '1.1rem',
                flexShrink: 0,
                borderRadius: 10,
                animation: recording ? 'pulse 0.8s infinite' : 'none',
                background: recording ? 'var(--danger)' : undefined,
                color: recording ? 'white' : undefined,
              }}
              onClick={recording ? stopRecording : startRecording}
              disabled={loading || transcribing}
              title={recording ? 'Stop recording' : 'Voice input (Whisper)'}
            >
              {recording ? '⏹' : transcribing ? '⏳' : '🎤'}
            </button>

            {/* Send */}
            <button
              className="btn btn-primary"
              onClick={() => sendMessage()}
              disabled={loading || transcribing || !input.trim()}
              style={{
                padding: '6px 18px',
                borderRadius: 10,
                fontSize: '0.9rem',
                flexShrink: 0,
              }}
            >
              Send
            </button>
          </div>
          {recording && (
            <div style={{
              fontSize: '0.7rem',
              color: 'var(--danger)',
              marginTop: 4,
              textAlign: 'center',
            }}>
              🔴 Recording — click ⏹ to stop and transcribe
            </div>
          )}
        </div>
      </div>

      {/* Animations */}
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
