import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import type { StudyMaterialSummary, StudyMaterialFull, StudyFlashcard, QuizQuestion } from '../api';
import { PomodoroTimer } from '../components/PomodoroTimer';

type ViewMode = 'list' | 'upload' | 'flashcards' | 'quiz' | 'material';

export default function Study() {
  // ── State ──
  const [view, setView] = useState<ViewMode>('list');
  const [materials, setMaterials] = useState<StudyMaterialSummary[]>([]);
  const [currentMaterial, setCurrentMaterial] = useState<StudyMaterialFull | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Upload
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadText, setUploadText] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  // Flashcards
  const [flashcardIndex, setFlashcardIndex] = useState(0);
  const [showBack, setShowBack] = useState(false);
  const [fcCount, setFcCount] = useState(10);

  // Quiz
  const [quizIndex, setQuizIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [quizAnswered, setQuizAnswered] = useState(false);
  const [quizScore, setQuizScore] = useState({ correct: 0, total: 0 });
  const [quizCount, setQuizCount] = useState(5);

  // Session stats
  const [sessionStats, setSessionStats] = useState({ sessions: 0, focusMinutes: 0 });

  // ── Load materials ──
  const loadMaterials = useCallback(async () => {
    try {
      const data = await api.studyMaterials();
      setMaterials(data.materials);
    } catch (e: any) {
      setError('Backend offline? ' + e.message);
    }
  }, []);

  useEffect(() => { loadMaterials(); }, [loadMaterials]);

  // ── Upload Handlers ──
  const handleUploadPDF = async () => {
    if (!uploadFile) return;
    setLoading(true); setError('');
    try {
      const result = await api.uploadPDF(uploadFile);
      if (result.error) { setError(result.error); return; }
      setUploadFile(null);
      await loadMaterials();
      setView('list');
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const handleUploadText = async () => {
    if (!uploadText.trim()) return;
    setLoading(true); setError('');
    try {
      const result = await api.uploadStudyText(uploadText, uploadTitle || 'Note rapide');
      if (result.error) { setError(result.error); return; }
      setUploadText(''); setUploadTitle('');
      await loadMaterials();
      setView('list');
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  // ── Material Actions ──
  const openMaterial = async (id: string) => {
    setLoading(true); setError('');
    try {
      const mat = await api.studyMaterial(id);
      setCurrentMaterial(mat);
      setView('material');
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const deleteMaterial = async (id: string) => {
    if (!confirm('Eliminare questo materiale?')) return;
    try {
      await api.deleteStudyMaterial(id);
      await loadMaterials();
      if (currentMaterial?.id === id) {
        setCurrentMaterial(null);
        setView('list');
      }
    } catch (e: any) { setError(e.message); }
  };

  const handleSummarize = async () => {
    if (!currentMaterial) return;
    setLoading(true);
    try {
      const result = await api.generateSummary(currentMaterial.id);
      await openMaterial(currentMaterial.id);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const handleGenerateFlashcards = async () => {
    if (!currentMaterial) return;
    setLoading(true);
    try {
      const result = await api.generateFlashcards(currentMaterial.id, fcCount);
      await openMaterial(currentMaterial.id);
      setFlashcardIndex(0);
      setShowBack(false);
      setView('flashcards');
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const handleGenerateQuiz = async () => {
    if (!currentMaterial) return;
    setLoading(true);
    try {
      const result = await api.generateQuiz(currentMaterial.id, quizCount);
      await openMaterial(currentMaterial.id);
      setQuizIndex(0);
      setSelectedOption(null);
      setQuizAnswered(false);
      setQuizScore({ correct: 0, total: 0 });
      setView('quiz');
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  // ── Flashcard Review ──
  const reviewCard = async (quality: number) => {
    if (!currentMaterial) return;
    const cards = currentMaterial.flashcards;
    if (!cards.length) return;
    const card = cards[flashcardIndex];
    try {
      await api.reviewFlashcard(currentMaterial.id, card.id, quality);
    } catch {}
    // Next card
    setShowBack(false);
    if (flashcardIndex < cards.length - 1) {
      setFlashcardIndex(flashcardIndex + 1);
    } else {
      setFlashcardIndex(0); // Loop
    }
  };

  // ── Quiz Answer ──
  const answerQuiz = (optionIndex: number) => {
    if (quizAnswered || !currentMaterial) return;
    setSelectedOption(optionIndex);
    setQuizAnswered(true);
    const q = currentMaterial.quiz_questions[quizIndex];
    if (optionIndex === q.correct_index) {
      setQuizScore(s => ({ ...s, correct: s.correct + 1 }));
    }
    setQuizScore(s => ({ ...s, total: s.total + 1 }));
  };

  const nextQuiz = () => {
    if (!currentMaterial) return;
    setSelectedOption(null);
    setQuizAnswered(false);
    if (quizIndex < currentMaterial.quiz_questions.length - 1) {
      setQuizIndex(quizIndex + 1);
    }
  };

  const handlePomodoroComplete = (type: string, duration: number) => {
    setSessionStats(s => ({
      sessions: s.sessions + 1,
      focusMinutes: s.focusMinutes + (type === 'focus' ? Math.round(duration / 60) : 0),
    }));
  };

  // ── Render Helpers ──

  const renderError = () => error && (
    <div style={{ background: 'var(--danger)', color: '#fff', padding: '12px 16px', borderRadius: 'var(--radius)', marginBottom: 16, fontSize: '0.85rem' }}>
      {error}
      <button onClick={() => setError('')} style={{ float: 'right', background: 'none', border: 'none', color: '#fff', cursor: 'pointer' }}>✕</button>
    </div>
  );

  const spinner = () => loading && (
    <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
      ⚡ Elaborazione in corso...
    </div>
  );

  // ── VIEW: List ──
  const renderList = () => (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2>📚 Materiali di Studio</h2>
        <button className="btn btn-primary" onClick={() => setView('upload')}>
          ＋ Nuovo Materiale
        </button>
      </div>

      {materials.length === 0 && (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
          <div style={{ fontSize: '3rem', marginBottom: 12 }}>📖</div>
          <p>Nessun materiale ancora.</p>
          <p style={{ fontSize: '0.85rem', marginTop: 8 }}>
            Carica un PDF o incolla del testo per iniziare a studiare con JARVIS.
          </p>
          <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => setView('upload')}>
            Carica Materiale
          </button>
        </div>
      )}

      <div style={{ display: 'grid', gap: '12px' }}>
        {materials.map((m) => (
          <div key={m.id} className="study-material-card" onClick={() => openMaterial(m.id)}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{m.title}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {m.source} · {m.flashcard_count} flashcards · {m.quiz_question_count} quiz · {new Date(m.created_at).toLocaleDateString('it-IT')}
              </div>
              {m.summary && (
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: 8, maxHeight: 60, overflow: 'hidden' }}>
                  {m.summary.substring(0, 200)}...
                </div>
              )}
            </div>
            <button
              className="btn btn-ghost btn-sm"
              onClick={(e) => { e.stopPropagation(); deleteMaterial(m.id); }}
              title="Elimina"
            >
              🗑️
            </button>
          </div>
        ))}
      </div>
    </div>
  );

  // ── VIEW: Upload ──
  const renderUpload = () => (
    <div>
      <div style={{ marginBottom: 20 }}>
        <button className="btn btn-ghost" onClick={() => setView('list')}>← Torna ai materiali</button>
      </div>
      <h2 style={{ marginBottom: 20 }}>📤 Carica Materiale</h2>

      {/* PDF Upload */}
      <div className="study-card">
        <h3 style={{ marginBottom: 12 }}>📄 Carica PDF</h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
          JARVIS estrarrà il testo e potrà generare riassunti, flashcard e quiz.
        </p>
        <input
          type="file"
          accept=".pdf"
          onChange={e => setUploadFile(e.target.files?.[0] || null)}
          style={{ marginBottom: 12 }}
        />
        {uploadFile && (
          <div style={{ fontSize: '0.85rem', marginBottom: 12 }}>
            Selezionato: <strong>{uploadFile.name}</strong> ({(uploadFile.size / 1024).toFixed(0)} KB)
          </div>
        )}
        <button className="btn btn-primary" onClick={handleUploadPDF} disabled={!uploadFile || loading}>
          {loading ? '⏳' : '📤'} Carica e Processa PDF
        </button>
      </div>

      {/* Text Upload */}
      <div className="study-card" style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 12 }}>📝 Incolla Testo</h3>
        <input
          type="text"
          placeholder="Titolo (es. Appunti di Biologia)"
          value={uploadTitle}
          onChange={e => setUploadTitle(e.target.value)}
          className="input"
          style={{ marginBottom: 12, width: '100%' }}
        />
        <textarea
          placeholder="Incolla qui il testo da studiare..."
          value={uploadText}
          onChange={e => setUploadText(e.target.value)}
          className="input"
          style={{ width: '100%', minHeight: 150, marginBottom: 12, resize: 'vertical' }}
        />
        <button className="btn btn-primary" onClick={handleUploadText} disabled={!uploadText.trim() || loading}>
          {loading ? '⏳' : '📝'} Salva Testo
        </button>
      </div>
    </div>
  );

  // ── VIEW: Material Detail ──
  const renderMaterialDetail = () => {
    if (!currentMaterial) return null;
    return (
      <div>
        <div style={{ marginBottom: 20 }}>
          <button className="btn btn-ghost" onClick={() => setView('list')}>← Torna ai materiali</button>
        </div>
        <h2 style={{ marginBottom: 8 }}>{currentMaterial.title}</h2>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 20 }}>
          {currentMaterial.source} · {currentMaterial.content.length.toLocaleString()} caratteri · creato il {new Date(currentMaterial.created_at).toLocaleDateString('it-IT')}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
          <button className="btn btn-secondary" onClick={handleSummarize} disabled={loading}>
            🤖 Genera Riassunto
          </button>
          <button className="btn btn-secondary" onClick={handleGenerateFlashcards} disabled={loading}>
            🃏 Genera Flashcards
          </button>
          <button className="btn btn-secondary" onClick={handleGenerateQuiz} disabled={loading}>
            📝 Genera Quiz
          </button>
          {currentMaterial.flashcards.length > 0 && (
            <button className="btn btn-secondary" onClick={() => { setFlashcardIndex(0); setShowBack(false); setView('flashcards'); }}>
              🎴 Studia ({currentMaterial.flashcards.length} cards)
            </button>
          )}
          {currentMaterial.quiz_questions.length > 0 && (
            <button className="btn btn-secondary" onClick={() => { setQuizIndex(0); setSelectedOption(null); setQuizAnswered(false); setQuizScore({ correct: 0, total: 0 }); setView('quiz'); }}>
              ✅ Quiz ({currentMaterial.quiz_questions.length} domande)
            </button>
          )}
        </div>

        {currentMaterial.summary && (
          <div className="study-card" style={{ marginBottom: 16 }}>
            <h3 style={{ marginBottom: 8 }}>📋 Riassunto AI</h3>
            <div style={{ fontSize: '0.9rem', lineHeight: 1.7, whiteSpace: 'pre-line' }}>
              {currentMaterial.summary}
            </div>
          </div>
        )}

        <div className="study-card">
          <h3 style={{ marginBottom: 8 }}>📖 Contenuto Completo</h3>
          <div style={{ fontSize: '0.85rem', lineHeight: 1.7, maxHeight: 400, overflow: 'auto', whiteSpace: 'pre-line', color: 'var(--text-secondary)' }}>
            {currentMaterial.content.substring(0, 3000)}
            {currentMaterial.content.length > 3000 && (
              <div style={{ marginTop: 8, color: 'var(--text-muted)' }}>
                ... ({(currentMaterial.content.length - 3000).toLocaleString()} altri caratteri)
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ── VIEW: Flashcards ──
  const renderFlashcards = () => {
    if (!currentMaterial || !currentMaterial.flashcards.length) {
      return <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>Nessuna flashcard. Generale prima.</div>;
    }
    const card = currentMaterial.flashcards[flashcardIndex];
    return (
      <div>
        <div style={{ marginBottom: 20 }}>
          <button className="btn btn-ghost" onClick={() => setView('material')}>← Torna al materiale</button>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2>🎴 Flashcards</h2>
          <span style={{ color: 'var(--text-muted)' }}>{flashcardIndex + 1} / {currentMaterial.flashcards.length}</span>
        </div>

        <div
          className="flashcard"
          onClick={() => setShowBack(!showBack)}
          style={{ cursor: 'pointer' }}
        >
          <div className="flashcard-inner" style={{ transform: showBack ? 'rotateY(180deg)' : 'rotateY(0deg)' }}>
            <div className="flashcard-front">
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 8 }}>DOMANDA</div>
              <div style={{ fontSize: '1.1rem', lineHeight: 1.6 }}>{card.front}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--accent)', marginTop: 16 }}>Clicca per vedere la risposta</div>
            </div>
            <div className="flashcard-back">
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 8 }}>RISPOSTA</div>
              <div style={{ fontSize: '1.1rem', lineHeight: 1.6 }}>{card.back}</div>
            </div>
          </div>
        </div>

        {showBack && (
          <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
            {[0, 1, 2, 3, 4, 5].map(q => (
              <button
                key={q}
                className={`btn btn-sm ${q >= 3 ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => reviewCard(q)}
                title={q === 0 ? 'Completamente dimenticata' : q === 5 ? 'Perfetta' : ''}
              >
                {q === 0 ? '🔴' : q === 1 ? '🟠' : q === 2 ? '🟡' : q === 3 ? '🟢' : q === 4 ? '🔵' : '⭐'}
                {' '}{q}/5
              </button>
            ))}
          </div>
        )}
      </div>
    );
  };

  // ── VIEW: Quiz ──
  const renderQuiz = () => {
    if (!currentMaterial || !currentMaterial.quiz_questions.length) {
      return <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>Nessun quiz. Generalo prima.</div>;
    }
    if (quizIndex >= currentMaterial.quiz_questions.length) {
      // Quiz complete
      const pct = quizScore.total > 0 ? Math.round((quizScore.correct / quizScore.total) * 100) : 0;
      return (
        <div>
          <div style={{ marginBottom: 20 }}>
            <button className="btn btn-ghost" onClick={() => setView('material')}>← Torna al materiale</button>
          </div>
          <div style={{ textAlign: 'center', padding: 40 }}>
            <div style={{ fontSize: '4rem', marginBottom: 12 }}>{pct >= 80 ? '🎉' : pct >= 50 ? '📚' : '💪'}</div>
            <h2>Quiz Completato!</h2>
            <div style={{ fontSize: '3rem', fontWeight: 700, color: pct >= 80 ? 'var(--success)' : pct >= 50 ? 'var(--warning)' : 'var(--danger)', margin: '16px 0' }}>
              {quizScore.correct}/{quizScore.total}
            </div>
            <p style={{ color: 'var(--text-secondary)' }}>{pct}% corretto</p>
            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => { setQuizIndex(0); setSelectedOption(null); setQuizAnswered(false); setQuizScore({ correct: 0, total: 0 }); }}>
              🔄 Rifai Quiz
            </button>
            <button className="btn btn-secondary" style={{ marginTop: 8, marginLeft: 8 }} onClick={() => setView('material')}>
              📖 Torna al Materiale
            </button>
          </div>
        </div>
      );
    }

    const q = currentMaterial.quiz_questions[quizIndex];
    return (
      <div>
        <div style={{ marginBottom: 20 }}>
          <button className="btn btn-ghost" onClick={() => setView('material')}>← Torna al materiale</button>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2>✅ Quiz</h2>
          <span style={{ color: 'var(--text-muted)' }}>
            {quizIndex + 1} / {currentMaterial.quiz_questions.length} · Punteggio: {quizScore.correct}/{quizScore.total}
          </span>
        </div>

        <div className="study-card">
          <div style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 16 }}>{q.question}</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {q.options.map((opt, i) => {
              let bg = 'var(--bg-hover)';
              if (quizAnswered) {
                if (i === q.correct_index) bg = 'var(--success)';
                else if (i === selectedOption && i !== q.correct_index) bg = 'var(--danger)';
              }
              return (
                <button
                  key={i}
                  className="btn btn-secondary"
                  onClick={() => answerQuiz(i)}
                  disabled={quizAnswered}
                  style={{
                    background: bg,
                    textAlign: 'left',
                    padding: '12px 16px',
                    opacity: quizAnswered && i !== selectedOption && i !== q.correct_index ? 0.6 : 1,
                  }}
                >
                  {String.fromCharCode(65 + i)}. {opt}
                </button>
              );
            })}
          </div>

          {quizAnswered && (
            <div style={{ marginTop: 16 }}>
              {selectedOption === q.correct_index ? (
                <div style={{ color: 'var(--success)', fontWeight: 600 }}>✅ Corretto!</div>
              ) : (
                <div style={{ color: 'var(--danger)', fontWeight: 600 }}>
                  ❌ Sbagliato. La risposta corretta è {String.fromCharCode(65 + q.correct_index)}.
                </div>
              )}
              {q.explanation && (
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: 8 }}>
                  💡 {q.explanation}
                </div>
              )}
              <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={nextQuiz}>
                {quizIndex < currentMaterial.quiz_questions.length - 1 ? '➡️ Prossima Domanda' : '🏁 Vedi Risultato'}
              </button>
            </div>
          )}
        </div>

        {/* Progress bar */}
        <div style={{ marginTop: 12, height: 4, background: 'var(--border)', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            background: 'var(--accent)',
            width: `${((quizIndex + (quizAnswered ? 1 : 0)) / currentMaterial.quiz_questions.length) * 100}%`,
            transition: 'width 0.3s',
          }} />
        </div>
      </div>
    );
  };

  // ── MAIN RENDER ──
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 24, height: '100%' }}>
      {/* Main content */}
      <div style={{ overflow: 'auto', paddingRight: 8 }}>
        {renderError()}
        {spinner()}
        {view === 'list' && renderList()}
        {view === 'upload' && renderUpload()}
        {view === 'material' && renderMaterialDetail()}
        {view === 'flashcards' && renderFlashcards()}
        {view === 'quiz' && renderQuiz()}
      </div>

      {/* Sidebar: Pomodoro + Stats */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <PomodoroTimer onSessionComplete={handlePomodoroComplete} />

        <div className="study-card">
          <h4 style={{ marginBottom: 8, fontSize: '0.9rem' }}>📊 Statistiche</h4>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            <div style={{ marginBottom: 4 }}>🎯 Sessioni focus: <strong>{sessionStats.sessions}</strong></div>
            <div style={{ marginBottom: 4 }}>⏱️ Minuti totali: <strong>{sessionStats.focusMinutes} min</strong></div>
            <div>📚 Materiali: <strong>{materials.length}</strong></div>
          </div>
        </div>

        {currentMaterial && (
          <div className="study-card">
            <h4 style={{ marginBottom: 8, fontSize: '0.9rem' }}>📖 Materiale Corrente</h4>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              <strong>{currentMaterial.title}</strong>
              <div style={{ marginTop: 4 }}>
                🃏 {currentMaterial.flashcards.length} flashcards<br />
                ✅ {currentMaterial.quiz_questions.length} quiz<br />
                📝 {currentMaterial.content.length.toLocaleString()} caratteri
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Styles */}
      <style>{`
        .study-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          padding: 20px;
        }

        .study-material-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 16px;
          display: flex;
          align-items: flex-start;
          gap: 12px;
          cursor: pointer;
          transition: border-color 0.2s, background 0.2s;
        }
        .study-material-card:hover {
          border-color: var(--accent);
          background: var(--bg-hover);
        }

        .flashcard {
          perspective: 1000px;
          height: 280px;
        }

        .flashcard-inner {
          position: relative;
          width: 100%;
          height: 100%;
          transition: transform 0.5s;
          transform-style: preserve-3d;
        }

        .flashcard-front,
        .flashcard-back {
          position: absolute;
          width: 100%;
          height: 100%;
          backface-visibility: hidden;
          border-radius: var(--radius-lg);
          padding: 32px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          text-align: center;
        }

        .flashcard-front {
          background: var(--bg-card);
          border: 2px solid var(--accent);
        }

        .flashcard-back {
          background: var(--bg-card);
          border: 2px solid var(--success);
          transform: rotateY(180deg);
        }

        .input {
          background: var(--bg-primary);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          color: var(--text-primary);
          padding: 10px 14px;
          font-family: inherit;
          font-size: 0.9rem;
        }
        .input:focus {
          outline: none;
          border-color: var(--accent);
        }

        .btn-sm {
          padding: 6px 12px;
          font-size: 0.8rem;
          border-radius: var(--radius);
          border: 1px solid var(--border);
          background: var(--bg-hover);
          color: var(--text-primary);
          cursor: pointer;
        }
        .btn-sm:hover {
          background: var(--bg-card);
        }
      `}</style>
    </div>
  );
}
