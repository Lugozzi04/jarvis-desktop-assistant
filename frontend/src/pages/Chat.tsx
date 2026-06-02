import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';
import type { ChatResponse } from '../api';

interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  details?: string;
}

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

  useEffect(() => {
    const cmd = searchParams.get('cmd');
    if (cmd) {
      sendMessage(cmd);
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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

    try {
      const isSlash = msg.startsWith('/');
      const res = isSlash ? await api.command(msg) : await api.chat(msg);
      addMessage('assistant', formatResult(res));
      if (res.intent) {
        const intentInfo = `Intent: ${res.intent.kind} → ${res.intent.skill || '?'}.${res.intent.action || '?'} (${(res.intent.confidence * 100).toFixed(0)}%)`;
        addMessage('system', intentInfo);
      }
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
    <div className="chat-container" style={{ height: 'calc(100vh - var(--topbar-height) - 60px)' }}>
      <div className="chat-messages">
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
      <div className="chat-input-area">
        <input
          ref={inputRef}
          type="text"
          placeholder="Type a message or slash command..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button className="btn btn-primary" onClick={() => sendMessage()} disabled={loading}>
          Send
        </button>
      </div>
    </div>
  );
}

export default Chat;
