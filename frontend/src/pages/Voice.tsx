function Voice() {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '60vh',
    }}>
      <div className="card" style={{
        maxWidth: 520,
        textAlign: 'center',
        padding: '40px 48px',
        borderLeft: '4px solid var(--accent, #6366f1)',
      }}>
        <div style={{ fontSize: '3rem', marginBottom: 16 }}>🚧</div>
        <h2 style={{ fontSize: '1.4rem', marginBottom: 12 }}>Work in Progress</h2>
        <p style={{
          fontSize: '0.9rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.7,
          marginBottom: 16,
        }}>
          Voice features are being actively developed. Soon you'll be able to
          activate Jarvis with a wake word, speak naturally, and get voice responses.
        </p>
        <div style={{
          background: 'var(--bg-secondary)',
          borderRadius: 'var(--radius, 8px)',
          padding: '12px 16px',
          fontSize: '0.82rem',
          color: 'var(--text-muted)',
          textAlign: 'left',
          lineHeight: 1.8,
        }}>
          <strong style={{ color: 'var(--text-primary)' }}>Coming soon:</strong>
          <ul style={{ paddingLeft: 18, marginTop: 6, marginBottom: 0 }}>
            <li>Wake-word activation ("Hey Jarvis")</li>
            <li>Real-time speech-to-text with Whisper</li>
            <li>Voice command pipeline</li>
            <li>Natural text-to-speech responses</li>
          </ul>
        </div>
        <p style={{
          fontSize: '0.78rem',
          color: 'var(--text-muted)',
          marginTop: 16,
          marginBottom: 0,
        }}>
          💡 <strong>For now:</strong> use the 🎤 button in Chat to speak and send messages.
        </p>
      </div>
    </div>
  );
}

export default Voice;
