import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Plus, Trash2 } from 'lucide-react';
import { createProject, listModels, listCodingAgents } from '../services/api';
import { useProjectStore } from '../store/projectStore';

const PROVIDERS = [
  { key: 'openai',    label: 'OpenAI',    icon: '🤖', desc: 'Cloud — best quality' },
  { key: 'anthropic', label: 'Anthropic', icon: '🧠', desc: 'Cloud — strong reasoning' },
  { key: 'ollama',    label: 'Ollama',    icon: '🦙', desc: 'Local — recommended for Jira mode' },
];

const EXAMPLE_BRIEFS = [
  "A task management app with AI-powered priority suggestions and natural language task entry",
  "A recipe generator that creates weekly meal plans based on dietary restrictions and pantry items",
  "A personal finance dashboard that categorizes spending with AI and predicts future expenses",
];

const emptyTicket = () => ({
  jira_url: '',
  manual: { title: '', description: '', acceptance_criteria: '' },
  useManual: false,
});

export default function NewProjectPage() {
  const navigate = useNavigate();
  const { setActiveProject, resetRun } = useProjectStore();

  const [mode, setMode]               = useState('greenfield');
  const [name, setName]               = useState('');
  const [brief, setBrief]             = useState('');
  const [repoPath, setRepoPath]       = useState('');
  const [tickets, setTickets]         = useState([emptyTicket()]);
  const [provider, setProvider]       = useState('ollama');
  const [models, setModels]           = useState({});
  const [codingAgents, setCodingAgents] = useState(null);
  const [loading, setLoading]         = useState(false);

  useEffect(() => {
    listModels().then(setModels).catch(() => {});
    listCodingAgents().then(setCodingAgents).catch(() => {});
  }, []);

  const providerAvailable = (key) => {
    if (key === 'ollama') return true;
    return models.providers?.[key]?.available ?? false;
  };

  const updateTicket = (idx, patch) => {
    setTickets(prev => prev.map((t, i) => i === idx ? { ...t, ...patch } : t));
  };

  const handleCreate = async () => {
    if (!name.trim()) { window.alert('Give your session a name.'); return; }

    if (mode === 'greenfield') {
      if (!brief.trim()) { window.alert('Describe what you want to build.'); return; }
    } else {
      if (!repoPath.trim()) { window.alert('Repo context path is required for Jira mode.'); return; }
      const valid = tickets.some(t =>
        t.jira_url.trim() || (t.useManual && t.manual.title.trim())
      );
      if (!valid) { window.alert('Add at least one Jira URL or manual ticket.'); return; }
    }

    setLoading(true);
    try {
      const payload = {
        name: name.trim(),
        brief: brief.trim(),
        provider,
        mode,
      };

      if (mode === 'jira') {
        payload.repo_context_path = repoPath.trim();
        payload.tickets = tickets
          .filter(t => t.jira_url.trim() || (t.useManual && t.manual.title.trim()))
          .map(t => ({
            jira_url: t.jira_url.trim() || undefined,
            manual: t.useManual ? {
              title: t.manual.title,
              description: t.manual.description,
              acceptance_criteria: t.manual.acceptance_criteria,
            } : (t.jira_url.trim() ? undefined : t.manual),
          }));
      }

      const project = await createProject(payload);
      setActiveProject(project);
      resetRun();
      navigate(`/project/${project.id}`, { replace: true });
    } catch (e) {
      window.alert(e.response?.data?.detail || e.message || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="screen">
      <div className="navbar">
        <button className="icon-btn" onClick={() => navigate(-1)}>
          <ChevronLeft size={24} color="#58a6ff" />
        </button>
        <span className="nav-title">New Project</span>
        <span className="spacer-40" />
      </div>

      <div className="content">
        <div className="label">Mode</div>
        <div className="provider-row">
          <button
            className={`provider-card${mode === 'greenfield' ? ' selected' : ''}`}
            onClick={() => setMode('greenfield')}
          >
            <div className="provider-icon">🚀</div>
            <div className="provider-label">Greenfield</div>
            <div className="provider-desc">4-agent pipeline builds a new app from scratch</div>
          </button>
          <button
            className={`provider-card${mode === 'jira' ? ' selected' : ''}`}
            onClick={() => setMode('jira')}
          >
            <div className="provider-icon">🎫</div>
            <div className="provider-label">Jira Mode</div>
            <div className="provider-desc">Senior dev agents work tickets in parallel</div>
          </button>
        </div>

        <div className="label">Session Name</div>
        <input className="input" placeholder="e.g. Sprint 42 fixes" value={name} onChange={e => setName(e.target.value)} autoFocus />

        {mode === 'greenfield' ? (
          <>
            <div className="label">Project Brief</div>
            <textarea className="input" placeholder="Describe what you want to build…" value={brief} onChange={e => setBrief(e.target.value)} />
            <div className="sublabel">Examples — click to use:</div>
            <div className="examples">
              {EXAMPLE_BRIEFS.map((ex, i) => (
                <button key={i} className="example-chip" onClick={() => { setBrief(ex); if (!name) setName(ex.split(' ').slice(0, 4).join(' ')); }}>
                  {ex}
                </button>
              ))}
            </div>
          </>
        ) : (
          <>
            <div className="label">Repository Context Path</div>
            <input
              className="input"
              placeholder="/path/to/repo or /path/to/repos-directory"
              value={repoPath}
              onChange={e => setRepoPath(e.target.value)}
            />
            <div className="hint">Single git repo or a directory containing multiple repos. Agents read `.cursor/*`, `AGENTS.md`, etc.</div>

            <div className="label">Jira Tickets</div>
            {tickets.map((t, idx) => (
              <div key={idx} className="card" style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span className="meta-text">Ticket {idx + 1}</span>
                  {tickets.length > 1 && (
                    <button className="delete-btn" onClick={() => setTickets(prev => prev.filter((_, i) => i !== idx))}>
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
                <input
                  className="input"
                  style={{ marginBottom: 8 }}
                  placeholder="Jira URL (https://org.atlassian.net/browse/PROJ-123)"
                  value={t.jira_url}
                  onChange={e => updateTicket(idx, { jira_url: e.target.value })}
                />
                <label style={{ fontSize: 12, color: '#8b949e', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                  <input type="checkbox" checked={t.useManual} onChange={e => updateTicket(idx, { useManual: e.target.checked })} />
                  Paste ticket manually (fallback if Jira API not configured)
                </label>
                {t.useManual && (
                  <>
                    <input className="input" style={{ marginBottom: 8 }} placeholder="Title" value={t.manual.title}
                      onChange={e => updateTicket(idx, { manual: { ...t.manual, title: e.target.value } })} />
                    <textarea className="input" style={{ marginBottom: 8, height: 80 }} placeholder="Description"
                      value={t.manual.description}
                      onChange={e => updateTicket(idx, { manual: { ...t.manual, description: e.target.value } })} />
                    <textarea className="input" style={{ height: 60 }} placeholder="Acceptance criteria"
                      value={t.manual.acceptance_criteria}
                      onChange={e => updateTicket(idx, { manual: { ...t.manual, acceptance_criteria: e.target.value } })} />
                  </>
                )}
              </div>
            ))}
            <button className="btn-outline" style={{ width: '100%', marginBottom: 16 }} onClick={() => setTickets(prev => [...prev, emptyTicket()])}>
              <Plus size={16} /> Add another ticket
            </button>

            {codingAgents && (
              <div className="hint" style={{ marginBottom: 12 }}>
                <strong>Recommended local coding models:</strong>{' '}
                {codingAgents.recommended.slice(0, 5).map(m => m.display).join(', ')}
                {codingAgents.best_for_jira_mode && (
                  <> · Best installed: <code>{codingAgents.best_for_jira_mode}</code></>
                )}
                {!codingAgents.jira_api_configured && (
                  <><br />Jira API not configured — manual paste will be used unless you set JIRA_* in backend .env</>
                )}
              </div>
            )}
          </>
        )}

        <div className="label">AI Provider</div>
        <div className="provider-row">
          {PROVIDERS.map(p => {
            const available = providerAvailable(p.key);
            const selected = provider === p.key;
            return (
              <button key={p.key}
                className={`provider-card${selected ? ' selected' : ''}${!available ? ' disabled' : ''}`}
                onClick={() => available && setProvider(p.key)}>
                <div className="provider-icon">{p.icon}</div>
                <div className={`provider-label${selected ? ' selected' : ''}`}>{p.label}</div>
                <div className="provider-desc">{p.desc}</div>
                {!available && <div className="not-configured">Not configured</div>}
              </button>
            );
          })}
        </div>

        <button className="btn-primary" onClick={handleCreate} disabled={loading}>
          {loading ? 'Creating…' : mode === 'jira' ? '🎫 Launch Jira Agents' : '🚀 Launch AI Team'}
        </button>
      </div>
    </div>
  );
}
