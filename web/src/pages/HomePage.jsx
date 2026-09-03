import { useEffect, useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  RefreshCw,
  Trash2,
  LayoutGrid,
  Ticket,
  Sparkles,
  FolderKanban,
  ChevronRight,
} from 'lucide-react';
import { listProjects, deleteProject } from '../services/api';
import { useProjectStore } from '../store/projectStore';
import { useUiStore } from '../store/uiStore';
import { useBoardStore } from '../store/boardStore';
import { DEMO_PROJECT_ID } from '../demo/demoData';

const STATUS_CHIP = {
  pending: { color: '#8b949e', bg: '#21262d', label: 'Pending' },
  ready:   { color: '#58a6ff', bg: '#0d2030', label: 'Ready' },
  running: { color: '#d29922', bg: '#2d2208', label: 'Running' },
  done:    { color: '#3fb950', bg: '#0d2010', label: 'Done' },
  error:   { color: '#f85149', bg: '#2d0f0f', label: 'Error' },
};

const DELETABLE_STATUSES = new Set(['pending', 'ready', 'running', 'error', 'done']);

function StatusChip({ status }) {
  const chip = STATUS_CHIP[status] || STATUS_CHIP.pending;
  return (
    <span
      className="chip dash-chip"
      style={{ background: chip.bg, borderColor: chip.color, color: chip.color }}
    >
      {chip.label}
    </span>
  );
}

function DashStat({ label, value, hint }) {
  return (
    <div className="dash-stat">
      <div className="dash-stat-value">{value}</div>
      <div className="dash-stat-label">{label}</div>
      {hint ? <div className="dash-stat-hint">{hint}</div> : null}
    </div>
  );
}

function BatchRow({ project, onOpen, onDelete, deleting, variant = 'jira' }) {
  const canDelete = DELETABLE_STATUSES.has(project.status);
  const ticketCount = project.ticket_count ?? 0;
  const inProgress = project.in_progress_count ?? 0;
  const date = new Date(project.created_at).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });

  return (
    <div className={`dash-row${variant === 'jira' ? ' dash-row-jira' : ''}`}>
      <button type="button" className="dash-row-main" onClick={onOpen}>
        <div className="dash-row-top">
          <span className="dash-row-title">{project.name}</span>
          <StatusChip status={project.status} />
        </div>
        <div className="dash-row-meta">
          {variant === 'jira' ? (
            <span>
              {ticketCount} ticket{ticketCount === 1 ? '' : 's'}
              {inProgress > 0 ? ` · ${inProgress} active` : ''}
            </span>
          ) : (
            <span className="dash-row-brief">{project.brief || 'Greenfield session'}</span>
          )}
          <span className="dash-row-dot">·</span>
          <span>{project.provider?.toUpperCase()} · {project.model || 'default'}</span>
          <span className="dash-row-dot">·</span>
          <span>{date}</span>
        </div>
      </button>
      <div className="dash-row-actions">
        <button type="button" className="dash-row-open" onClick={onOpen} title="Open">
          {variant === 'jira' ? (
            <>
              <LayoutGrid size={14} />
              Board
            </>
          ) : (
            <>
              Open
              <ChevronRight size={14} />
            </>
          )}
        </button>
        {canDelete && (
          <button
            type="button"
            className="dash-row-delete"
            title="Delete"
            disabled={deleting}
            onClick={(e) => {
              e.stopPropagation();
              onDelete(project);
            }}
          >
            <Trash2 size={15} />
          </button>
        )}
      </div>
    </div>
  );
}

export default function HomePage() {
  const navigate = useNavigate();
  const { setProjects, setActiveProject, resetRun, clearBoardRunState } = useProjectStore();
  const { setInterfaceMode, startDemo } = useUiStore();
  const { resetDemoBoard } = useBoardStore();
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

  const openBoard = (project) => {
    setActiveProject(project);
    clearBoardRunState();
    setInterfaceMode('minimal');
    navigate(`/board/${project.id}`);
  };

  const openProject = (project) => {
    setActiveProject(project);
    resetRun();
    navigate(`/project/${project.id}`);
  };

  const handleDelete = async (project) => {
    if (project.id === DEMO_PROJECT_ID) return;
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

  const startDemoMode = () => {
    resetRun();
    resetDemoBoard();
    setInterfaceMode('minimal');
    startDemo();
    setActiveProject(null);
    navigate(`/project/${DEMO_PROJECT_ID}`, { replace: true });
  };

  const jiraProjects = projects.filter(p => p.mode === 'jira');
  const greenfieldProjects = projects.filter(p => p.mode !== 'jira');

  const stats = useMemo(() => {
    const tickets = jiraProjects.reduce((n, p) => n + (p.ticket_count ?? 0), 0);
    const active = jiraProjects.reduce((n, p) => n + (p.in_progress_count ?? 0), 0);
    return {
      batches: jiraProjects.length,
      tickets,
      active,
      greenfield: greenfieldProjects.length,
    };
  }, [jiraProjects, greenfieldProjects]);

  return (
    <div className="screen dashboard-page">
      <header className="dash-header">
        <div>
          <h1 className="dash-title">Dashboard</h1>
          <p className="dash-subtitle">Jira batches, ticket boards, and greenfield sessions</p>
        </div>
        <button
          type="button"
          className="icon-btn"
          onClick={onRefresh}
          title="Refresh"
          disabled={refreshing}
        >
          <RefreshCw size={18} className={refreshing ? 'spin-icon' : ''} />
        </button>
      </header>

      <div className="dash-stats">
        <DashStat label="Jira batches" value={stats.batches} />
        <DashStat label="Open tickets" value={stats.tickets} />
        <DashStat label="In progress" value={stats.active} hint={stats.active ? 'Across all boards' : undefined} />
        <DashStat label="Greenfield" value={stats.greenfield} />
      </div>

      <div className="dash-toolbar">
        <button type="button" className="dash-action" onClick={startDemoMode}>
          <Sparkles size={15} />
          Demo
        </button>
        <div className="dash-toolbar-group">
          <button type="button" className="dash-action" onClick={() => navigate('/new/jira')}>
            <Ticket size={15} />
            Jira ticket
          </button>
          <button type="button" className="dash-action" onClick={() => navigate('/new')}>
            <FolderKanban size={15} />
            Greenfield
          </button>
        </div>
      </div>

      <div className="dash-content">
        {projects.length === 0 ? (
          <div className="dash-empty">
            <Ticket size={32} strokeWidth={1.5} className="dash-empty-icon" />
            <div className="dash-empty-title">No sessions yet</div>
            <p className="dash-empty-text">
              Start with a Jira ticket batch or create a greenfield multi-agent project.
            </p>
            <div className="dash-toolbar dash-empty-actions">
              <div className="dash-toolbar-group">
                <button type="button" className="dash-action" onClick={() => navigate('/new/jira')}>
                  Jira ticket
                </button>
                <button type="button" className="dash-action" onClick={() => navigate('/new')}>
                  Greenfield project
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            {jiraProjects.length > 0 && (
              <section className="dash-section">
                <div className="dash-section-head">
                  <h2 className="dash-section-title">Jira batches</h2>
                  <button
                    type="button"
                    className="home-section-link"
                    onClick={() => { clearBoardRunState(); navigate('/board'); }}
                  >
                    All tickets
                  </button>
                </div>
                <div className="dash-list">
                  {jiraProjects.map(item => (
                    <BatchRow
                      key={item.id}
                      project={item}
                      variant="jira"
                      onOpen={() => openBoard(item)}
                      onDelete={handleDelete}
                      deleting={deletingId === item.id}
                    />
                  ))}
                </div>
              </section>
            )}

            {greenfieldProjects.length > 0 && (
              <section className="dash-section">
                <div className="dash-section-head">
                  <h2 className="dash-section-title">Greenfield projects</h2>
                </div>
                <div className="dash-list">
                  {greenfieldProjects.map(item => (
                    <BatchRow
                      key={item.id}
                      project={item}
                      variant="greenfield"
                      onOpen={() => openProject(item)}
                      onDelete={handleDelete}
                      deleting={deletingId === item.id}
                    />
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>

      <button className="fab" type="button" onClick={() => navigate('/new')} title="New greenfield project">
        <Plus size={28} />
      </button>
    </div>
  );
}
