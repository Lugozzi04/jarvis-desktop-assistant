import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';
import type { ChatResponse } from '../api';
import { TimerBar } from '../TimerBar';

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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const msgId = useRef(1);

  // Conversation state
  const [convId, setConvId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [showSidebar, setShowSidebar] = useState(true);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    const cmd = searchParams.get('cmd');
    if (cmd) {
      sendMessage(cmd);
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    // Focus input
    inputRef.current?.focus();
  }, [convId]);

  const loadConversations = async () => {
    try {
      const res = await fetch(`${API}/api/conversations`);
      const data = await res.json();
      setConversations(data.conversations || []);
    } catch {}
  };

  const createNewChat = async () => {
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

  const deleteConversation = async (id: string) => {
    try {
      await fetch(`${API}/api/conversations/${id}`, { method: 'DELETE' });
      setConversations(prev => prev.filter(c => c.id !== id));
      if (convId === id) {
        createNewChat();
      }
    } catch {}
  };

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

    // Auto-create conversation if needed
    let cid = convId;
    if (!cid) {
      try {
        const res = await fetch(`${API}/api/conversations`, { method: 'POST' });
        const data = await res.json();
        cid = data.id;
        setConvId(cid);
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
      // Refresh conversation list
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

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - var(--topbar-height) - 60px)' }}>
      {/* Conversation Sidebar */}
      {showSidebar && (
        <div style={{
          width: 260,
          minWidth: 260,
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg-secondary)',
        }}>
          <div style={{
            padding: '12px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>💬 Chats</span>
            <button
              className="btn btn-sm btn-primary"
              style={{ padding: '4px 10px', fontSize: '0.75rem' }}
              onClick={createNewChat}
            >
              ＋ New
            </button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
            {conversations.length === 0 && (
              <div style={{ padding: '16px 12px', fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                No conversations yet.<br />Start chatting!
              </div>
            )}
            {conversations.map(conv => (
              <div
                key={conv.id}
                onClick={() => selectConversation(conv.id)}
                style={{
                  padding: '10px 12px',
                  cursor: 'pointer',
                  background: convId === conv.id ? 'var(--bg-primary)' : 'transparent',
                  borderLeft: convId === conv.id ? '3px solid var(--accent)' : '3px solid transparent',
                  transition: 'background 0.15s',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontWeight: 500,
                      fontSize: '0.85rem',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}>
                      {conv.title}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
                      {conv.message_count} messages
                    </div>
                  </div>
                  <button
                    className="btn btn-sm"
                    style={{
                      padding: '2px 6px',
                      fontSize: '0.7rem',
                      background: 'transparent',
                      color: 'var(--text-muted)',
                      border: 'none',
                      cursor: 'pointer',
                      marginLeft: 4,
                      flexShrink: 0,
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteConversation(conv.id);
                    }}
                    title="Delete conversation"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Chat Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <TimerBar />
        <div className="chat-messages" style={{ flex: 1 }}>
          {messages.map(msg => (
            <div key={msg.id} className={`message ${msg.role}`}>
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
              {msg.details && <div style={{ fontSize: '0.75rem', opacity: 0.6, marginTop: 4 }}>{msg.details}</div>}
            </div>
          ))}
          {loading && (
            <div className="message assistant">
              <div className="spinner" />
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className="chat-input-area" style={{ padding: '10px 16px' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className="btn btn-sm btn-secondary"
              style={{ padding: '4px 8px', fontSize: '0.75rem', flexShrink: 0 }}
              onClick={() => setShowSidebar(!showSidebar)}
              title="Toggle sidebar"
            >
              {showSidebar ? '◀' : '▶'}
            </button>
            <input
              ref={inputRef}
              type="text"
              placeholder="Type a message or slash command..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary" onClick={() => sendMessage()} disabled={loading}>
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chat;
