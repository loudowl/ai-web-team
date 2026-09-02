import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Settings, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { listProjects, deleteProject } from '../services/api';
import { useProjectStore } from '../store/projectStore';

const STATUS_CHIP = {
  pending: { color: '#8b949e', bg: '#21262d', label: 'Pending' },
  running: { color: '#d29922', bg: '#2d2208', label: 'Running' },
  done:    { color: '#3fb950', bg: '#0d2010', label: 'Done' },
  error:   { color: '#f85149', bg: '#2d0f0f', label: 'Error' },
};

const DELETABLE_STATUSES = new Set(['pending', 'running', 'error', 'done']);

function ProjectCard({ project, onClick, onDelete, deleting }) {
  const chip = STATUS_CHIP[project.status] || STATUS_CHIP.pending;
  const canDelete = DELETABLE_STATUSES.has(project.status);

  return (
    <div className="card-wrap">
      <button className="card" onClick={onClick}>
        <div className="card-top">
          <span className="card-name">{project.name}</span>
          <span className="chip" style={{ background: chip.bg, borderColor: chip.color, color: chip.color }}>
            {chip.label}
          </span>
        </div>
        <div className="card-brief">{project.brief}</div>
        <div className="card-meta">
          <span className="meta-text">
            {(project.mode === 'jira' ? 'JIRA' : project.provider?.toUpperCase())} · {project.model}
          </span>
          <span className="meta-text">{new Date(project.created_at).toLocaleDateString()}</span>
        </div>
        {project.github_url ? (
          <div className="github-link">⎋ {project.github_url}</div>
        ) : null}
      </button>
      {canDelete && (
        <button
          className="card-delete"
          title="Delete session"
          disabled={deleting}
          onClick={(e) => {
            e.stopPropagation();
            onDelete(project);
          }}
        >
          <Trash2 size={18} />
        </button>
      )}
    </div>
  );
}

export default function HomePage() {
  const navigate = useNavigate();
  const { setProjects, setActiveProject, resetRun } = useProjectStore();
  const [projects, setLocal] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const load = useCallback(async () => {
    try {
      const data = await listProjects();
      const safe = Array.isArray(data) ? data : [];
      setLocal(safe);
      setProjects(safe);
    } catch (e) {
      console.warn('Failed to load projects', e);
    }
  }, [setProjects]);

  useEffect(() => { load(); }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const openProject = (project) => {
    setActiveProject(project);
    resetRun();
    navigate(`/project/${project.id}`);
  };

  const handleDelete = async (project) => {
    if (!window.confirm(`Delete "${project.name}"? This cannot be undone.`)) return;
    setDeletingId(project.id);
    try {
      await deleteProject(project.id);
      await load();
    } catch (e) {
      window.alert(e.response?.data?.detail || e.message || 'Failed to delete session');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="screen">
      <div className="header">
        <div>
          <div className="header-title">AI Web Team</div>
          <div className="header-sub">Multi-agent project generator</div>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="icon-btn" onClick={onRefresh} title="Refresh">
            <RefreshCw size={20} className={refreshing ? 'spin-icon' : ''}
              style={refreshing ? { animation: 'spin 0.7s linear infinite' } : undefined} />
          </button>
          <button className="icon-btn" onClick={() => navigate('/settings')} title="Settings">
            <Settings size={22} />
          </button>
        </div>
      </div>

      <div className="content list">
        {projects.length === 0 ? (
          <div className="empty">
            <div className="empty-icon">🤖</div>
            <div className="empty-title">No projects yet</div>
            <div className="empty-text">Tap + to describe a web project and watch your AI team build it.</div>
          </div>
        ) : (
          projects.map(item => (
            <ProjectCard
              key={item.id}
              project={item}
              onClick={() => openProject(item)}
              onDelete={handleDelete}
              deleting={deletingId === item.id}
            />
          ))
        )}
      </div>

      <button className="fab" onClick={() => navigate('/new')} title="New project">
        <Plus size={28} />
      </button>
    </div>
  );
}
