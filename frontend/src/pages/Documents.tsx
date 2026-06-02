import { useState, useEffect } from 'react';
import { api } from '../api';
import type { DocumentInfo, MemoryStatus, SearchResult, RAGAnswer, IndexFolderResponse } from '../api';

function Documents() {
  const [status, setStatus] = useState<MemoryStatus | null>(null);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Index
  const [indexPath, setIndexPath] = useState('');
  const [indexRecursive, setIndexRecursive] = useState(true);
  const [indexing, setIndexing] = useState(false);

  // Search
  const [searchQuery, setSearchQuery] = useState('');
  const [searchTopK, setSearchTopK] = useState(5);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  // Ask
  const [askQuestion, setAskQuestion] = useState('');
  const [askTopK, setAskTopK] = useState(5);
  const [ragAnswer, setRagAnswer] = useState<RAGAnswer | null>(null);
  const [asking, setAsking] = useState(false);

  // Action feedback
  const [message, setMessage] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, d] = await Promise.all([
        api.documentsStatus(),
        api.documentsList(),
      ]);
      setStatus(s);
      setDocuments(d.documents || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const flash = (msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(null), 4000);
  };

  const handleIndex = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!indexPath.trim()) return;
    setIndexing(true);
    try {
      const resp = await api.indexFile(indexPath.trim());
      flash(`✅ Indexed: ${resp.document.filename} — ${resp.document.chunk_count} chunks`);
      setIndexPath('');
      loadData();
    } catch (e) {
      flash(`❌ ${e instanceof Error ? e.message : 'Index failed'}`);
    } finally {
      setIndexing(false);
    }
  };

  const handleIndexFolder = async () => {
    if (!indexPath.trim()) return;
    setIndexing(true);
    try {
      const resp: IndexFolderResponse = await api.indexFolder(indexPath.trim(), indexRecursive);
      flash(`📁 Indexed ${resp.indexed} files from ${indexPath} (${resp.failed} failed)`);
      setIndexPath('');
      loadData();
    } catch (e) {
      flash(`❌ ${e instanceof Error ? e.message : 'Folder index failed'}`);
    } finally {
      setIndexing(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const resp = await api.searchDocuments(searchQuery.trim(), searchTopK);
      setSearchResults(resp.results);
      if (resp.results.length === 0) flash('No results found.');
    } catch (e) {
      flash(`❌ ${e instanceof Error ? e.message : 'Search failed'}`);
    } finally {
      setSearching(false);
    }
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!askQuestion.trim()) return;
    setAsking(true);
    setRagAnswer(null);
    try {
      const resp = await api.askDocuments(askQuestion.trim(), askTopK);
      setRagAnswer(resp);
    } catch (e) {
      flash(`❌ ${e instanceof Error ? e.message : 'Ask failed'}`);
    } finally {
      setAsking(false);
    }
  };

  const handleDelete = async (id: string, filename: string) => {
    if (!confirm(`Delete "${filename}" from index?`)) return;
    try {
      await api.deleteDocument(id);
      flash(`🗑️ Deleted: ${filename}`);
      setRagAnswer(null);
      setSearchResults([]);
      loadData();
    } catch (e) {
      flash(`❌ ${e instanceof Error ? e.message : 'Delete failed'}`);
    }
  };

  const handleClear = async () => {
    if (!confirm('Delete ALL indexed documents? This cannot be undone.')) return;
    try {
      await api.clearDocuments();
      flash('🗑️ All documents cleared');
      setRagAnswer(null);
      setSearchResults([]);
      loadData();
    } catch (e) {
      flash(`❌ ${e instanceof Error ? e.message : 'Clear failed'}`);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return '-';
    return new Date(iso).toLocaleString();
  };

  if (loading) return <div className="page"><h2>📚 Documents</h2><p>Loading...</p></div>;
  if (error) return <div className="page"><h2>📚 Documents</h2><div className="card error">❌ {error}</div></div>;

  return (
    <div className="page">
      <h2>📚 Documents</h2>

      {message && <div className="toast">{message}</div>}

      {/* Status Card */}
      <div className="card">
        <h3>📊 Memory Status</h3>
        <div className="stats-grid">
          <div className="stat">
            <div className="stat-value">{status?.documents ?? 0}</div>
            <div className="stat-label">Documents</div>
          </div>
          <div className="stat">
            <div className="stat-value">{status?.chunks ?? 0}</div>
            <div className="stat-label">Chunks</div>
          </div>
          <div className="stat">
            <div className="stat-value">{status?.embedding_provider ?? 'none'}</div>
            <div className="stat-label">Provider</div>
          </div>
          <div className="stat">
            <div className="stat-value">
              <span className={`badge ${status?.ready ? 'badge-success' : 'badge-warning'}`}>
                {status?.ready ? 'READY' : 'OFFLINE'}
              </span>
            </div>
            <div className="stat-label">Status</div>
          </div>
        </div>
        {!status?.ready && (
          <div style={{ marginTop: 12, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            💡 <strong>Setup:</strong> Simple embeddings work offline (hash-based). For better quality, install Ollama and run{' '}
            <code>ollama pull nomic-embed-text</code>, then set <code>EMBEDDING_PROVIDER=ollama</code> in .env
          </div>
        )}
      </div>

      {/* Index Form */}
      <div className="card">
        <h3>📥 Index Files</h3>
        <form onSubmit={handleIndex} style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ flex: 1, minWidth: 250 }}>
            <label>Path (file or folder)</label>
            <input
              type="text"
              value={indexPath}
              onChange={(e) => setIndexPath(e.target.value)}
              placeholder="/home/user/Documents/notes.md"
            />
          </div>
          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={indexRecursive}
                onChange={(e) => setIndexRecursive(e.target.checked)}
              />
              Recursive
            </label>
          </div>
          <button type="submit" disabled={indexing || !indexPath.trim()} className="btn-primary">
            {indexing ? '⏳ Indexing...' : '📄 Index File'}
          </button>
          <button type="button" onClick={handleIndexFolder} disabled={indexing || !indexPath.trim()} className="btn-secondary">
            📁 Index Folder
          </button>
        </form>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 8 }}>
          Supported: .txt, .md, .py, .js, .ts, .tsx, .html, .css, .json, .csv, .pdf (requires pypdf), and more.
        </div>
      </div>

      {/* Ask Documents */}
      <div className="card">
        <h3>🤖 Ask Your Documents</h3>
        <form onSubmit={handleAsk} style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ flex: 1, minWidth: 300 }}>
            <input
              type="text"
              value={askQuestion}
              onChange={(e) => setAskQuestion(e.target.value)}
              placeholder="What do my notes say about Docker?"
            />
          </div>
          <div style={{ width: 80 }}>
            <label>Top-K</label>
            <input
              type="number"
              value={askTopK}
              onChange={(e) => setAskTopK(Number(e.target.value))}
              min={1}
              max={20}
            />
          </div>
          <button type="submit" disabled={asking || !askQuestion.trim()} className="btn-primary">
            {asking ? '🤔 Thinking...' : '🔍 Ask'}
          </button>
        </form>

        {ragAnswer && (
          <div style={{ marginTop: 16 }}>
            <div style={{
              background: 'var(--bg-secondary)',
              padding: 16,
              borderRadius: 8,
              whiteSpace: 'pre-wrap',
              lineHeight: 1.6,
              fontSize: '0.95rem',
              marginBottom: 12,
            }}>
              {ragAnswer.answer}
            </div>
            {ragAnswer.error && (
              <div className="badge badge-warning" style={{ marginBottom: 8 }}>
                ⚠️ {ragAnswer.error}
              </div>
            )}
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Provider: {ragAnswer.provider}
              {ragAnswer.sources.length > 0 && ` · ${ragAnswer.sources.length} sources`}
            </div>
            {ragAnswer.sources.length > 0 && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: 'pointer', fontSize: '0.9rem' }}>Sources ({ragAnswer.sources.length})</summary>
                <div style={{ marginTop: 8 }}>
                  {ragAnswer.sources.map((s, i) => (
                    <div key={s.chunk_id} style={{
                      background: 'var(--bg-primary)',
                      padding: 10,
                      borderRadius: 6,
                      marginBottom: 6,
                      fontSize: '0.85rem',
                    }}>
                      <strong>{i + 1}. {s.filename}</strong> (chunk {s.chunk_index}, score: {s.score.toFixed(2)})
                      <div style={{ color: 'var(--text-muted)', marginTop: 4 }}>{s.text_preview}...</div>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}
      </div>

      {/* Search */}
      <div className="card">
        <h3>🔎 Search</h3>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ flex: 1, minWidth: 300 }}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search your documents..."
            />
          </div>
          <div style={{ width: 80 }}>
            <label>Top-K</label>
            <input type="number" value={searchTopK} onChange={(e) => setSearchTopK(Number(e.target.value))} min={1} max={20} />
          </div>
          <button type="submit" disabled={searching || !searchQuery.trim()} className="btn-primary">
            {searching ? '🔍 Searching...' : '🔍 Search'}
          </button>
        </form>

        {searchResults.length > 0 && (
          <div style={{ marginTop: 12 }}>
            {searchResults.map((r, i) => (
              <div key={r.chunk_id} style={{
                background: 'var(--bg-secondary)',
                padding: 12,
                borderRadius: 6,
                marginBottom: 8,
              }}>
                <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                  {i + 1}. {r.filename} — chunk {r.chunk_index}
                  <span style={{ marginLeft: 8, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    score: {r.score.toFixed(3)}
                  </span>
                </div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: 4 }}>
                  {r.text_preview}...
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Document List */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3>📋 Indexed Documents ({documents.length})</h3>
          {documents.length > 0 && (
            <button onClick={handleClear} className="btn-danger" style={{ fontSize: '0.8rem', padding: '4px 12px' }}>
              Clear All
            </button>
          )}
        </div>
        {documents.length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>No documents indexed yet. Use the form above to add one.</p>
        ) : (
          <div style={{ maxHeight: 400, overflowY: 'auto' }}>
            {documents.map((doc) => (
              <div key={doc.id} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '10px 0',
                borderBottom: '1px solid var(--border-color)',
              }}>
                <div>
                  <div style={{ fontWeight: 500 }}>
                    {doc.status === 'indexed' ? '✅' : doc.status === 'error' ? '❌' : '⏳'}{' '}
                    {doc.filename}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {doc.file_type} · {formatBytes(doc.size_bytes)} · {doc.chunk_count} chunks · {formatDate(doc.indexed_at)}
                  </div>
                  {doc.error && <div style={{ fontSize: '0.8rem', color: 'var(--error)' }}>{doc.error}</div>}
                </div>
                <button
                  onClick={() => handleDelete(doc.id, doc.filename)}
                  className="btn-danger"
                  style={{ fontSize: '0.8rem', padding: '4px 10px' }}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Documents;
