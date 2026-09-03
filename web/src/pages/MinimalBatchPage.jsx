import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Plus, X } from 'lucide-react';
import { createProject } from '../services/api';
import { useProjectStore } from '../store/projectStore';
import { useUiStore } from '../store/uiStore';

function parseTicketLine(line) {
  const trimmed = line.trim();
  if (!trimmed) return null;
  if (/^https?:\/\//i.test(trimmed)) return { jira_url: trimmed };
  const keyMatch = trimmed.match(/^([A-Z][A-Z0-9]+-\d+)/);
  if (keyMatch) return { ticket_key: keyMatch[1] };
  return { manual: { title: trimmed, description: '', acceptance_criteria: '' } };
}

function linesToTickets(text) {
  return text
    .split('\n')
    .map(parseTicketLine)
    .filter(Boolean);
}

export default function MinimalBatchPage() {
  const navigate = useNavigate();
  const { setActiveProject, resetRun, clearBoardRunState } = useProjectStore();
  const { lastRepoPath, setLastRepoPath, setInterfaceMode } = useUiStore();

  const [name, setName] = useState('');
  const [repoPath, setRepoPath] = useState(lastRepoPath);
  const [ticketLines, setTicketLines] = useState('');
  const [lineItems, setLineItems] = useState(['']);
  const [provider] = useState('ollama');
  const [loading, setLoading] = useState(false);
  const [useTextarea, setUseTextarea] = useState(false);

  const allLines = useTextarea
    ? ticketLines
    : lineItems.filter(l => l.trim()).join('\n');

  const ticketCount = linesToTickets(allLines).length;

  const handleCreate = async () => {
    if (!name.trim()) {
      window.alert('Name this batch (e.g. Sprint 42).');
      return;
    }
    if (!repoPath.trim()) {
      window.alert('Set the repo path once for the whole batch.');
      return;
    }
    const tickets = linesToTickets(allLines);
    if (!tickets.length) {
      window.alert('Add at least one ticket key or Jira URL.');
      return;
    }

    setLoading(true);
    setLastRepoPath(repoPath.trim());
    setInterfaceMode('minimal');

    try {
      const project = await createProject({
        name: name.trim(),
        brief: `Jira batch — ${tickets.length} ticket(s)`,
        provider,
        mode: 'jira',
        repo_context_path: repoPath.trim(),
        tickets,
      });
      setActiveProject(project);
      clearBoardRunState();
      navigate(`/board/${project.id}`, { replace: true });
    } catch (e) {
      window.alert(e.response?.data?.detail || e.message || 'Failed to create batch');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="screen minimal-batch">
      <div className="navbar">
        <button className="icon-btn" type="button" onClick={() => navigate(-1)}>
          <ChevronLeft size={24} color="#58a6ff" />
        </button>
        <span className="nav-title">Ticket batch</span>
        <span className="spacer-40" />
      </div>

      <div className="content">
        <p className="hint" style={{ marginTop: 0 }}>
          One repo path for the whole group. Add tickets like a to-do list — keys or URLs, one per line.
        </p>

        <div className="label">Batch name</div>
        <input
          className="input"
          placeholder="Sprint 42 fixes"
          value={name}
          onChange={e => setName(e.target.value)}
          autoFocus
        />

        <div className="label">Repository (shared context)</div>
        <input
          className="input"
          placeholder="/path/to/your/repo"
          value={repoPath}
          onChange={e => setRepoPath(e.target.value)}
        />

        <div className="label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Tickets ({ticketCount})</span>
          <button
            type="button"
            className="meta-text"
            style={{ color: 'var(--blue)', background: 'none', border: 'none', cursor: 'pointer' }}
            onClick={() => setUseTextarea(v => !v)}
          >
            {useTextarea ? 'Line-by-line' : 'Paste block'}
          </button>
        </div>

        {useTextarea ? (
          <textarea
            className="input"
            style={{ minHeight: 140, fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 13 }}
            placeholder={'FTSWB-5641\nFTSWB-5602\nhttps://teamfox.atlassian.net/browse/FTSWB-5588'}
            value={ticketLines}
            onChange={e => setTicketLines(e.target.value)}
          />
        ) : (
          <div className="todo-list">
            {lineItems.map((line, idx) => (
              <div key={idx} className="todo-row">
                <span className="todo-bullet">○</span>
                <input
                  className="input todo-input"
                  placeholder="FTSWB-1234 or Jira URL"
                  value={line}
                  onChange={e => {
                    const next = [...lineItems];
                    next[idx] = e.target.value;
                    setLineItems(next);
                  }}
                  onKeyDown={e => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      if (idx === lineItems.length - 1) {
                        setLineItems([...lineItems, '']);
                      }
                    }
                  }}
                />
                {lineItems.length > 1 && (
                  <button
                    type="button"
                    className="icon-btn"
                    onClick={() => setLineItems(lineItems.filter((_, i) => i !== idx))}
                  >
                    <X size={16} />
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              className="btn-outline todo-add"
              onClick={() => setLineItems([...lineItems, ''])}
            >
              <Plus size={16} /> Add ticket
            </button>
          </div>
        )}

        <button type="button" className="btn-primary" onClick={handleCreate} disabled={loading}>
          {loading ? 'Launching…' : `Launch ${ticketCount || ''} ticket${ticketCount === 1 ? '' : 's'}`}
        </button>
      </div>
    </div>
  );
}
