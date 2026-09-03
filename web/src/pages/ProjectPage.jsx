import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ChevronLeft, Settings, FileText, Github, ExternalLink, X, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import AgentKanban from '../components/AgentKanban';
import ActivityFeed from '../components/ActivityFeed';
import TicketBoard from '../components/TicketBoard';
import TicketProgressGrid from '../components/TicketProgressGrid';
import TicketModal from '../components/TicketModal';
import { connectWS, getProject, pushToGitHub, listTickets, deleteProject } from '../services/api';
import { useProjectStore } from '../store/projectStore';
import { useUiStore } from '../store/uiStore';
import { isDemoProjectId } from '../demo/demoData';
import { startDemoSimulation, getDemoProject, getDemoTickets } from '../demo/demoSimulator';

export default function ProjectPage() {
  const navigate = useNavigate();
  const { projectId } = useParams();

  const {
    activeProject, setActiveProject,
    agentStates, handleWsEvent, setWs, setTickets, resetRun,
    tickets, ticketStates,
    AGENTS, AGENT_META,
  } = useProjectStore();

  const { interfaceMode, endDemo } = useUiStore();

  const wsRef = useRef(null);
  const demoStopRef = useRef(null);
  const [project, setProject]         = useState(activeProject);
  const [modalAgent, setModalAgent]   = useState(null);
  const [modalTicketId, setModalTicketId] = useState(null);
  const [pushing, setPushing]         = useState(false);
  const [deleting, setDeleting]       = useState(false);

  const isDemo = isDemoProjectId(projectId);
  const isMinimal = interfaceMode === 'minimal' || isDemo;
  const isJira = project?.mode === 'jira' || isDemo;
  const canDelete = !isDemo && ['pending', 'running', 'error', 'done'].includes(project?.status);

  const exitDemo = () => {
    demoStopRef.current?.();
    demoStopRef.current = null;
    wsRef.current?.close();
    endDemo();
    resetRun();
    navigate('/', { replace: true });
  };

  useEffect(() => {
    let mounted = true;

    if (isDemo) {
      const demoProject = getDemoProject();
      const demoTickets = getDemoTickets();
      setProject(demoProject);
      setActiveProject(demoProject);
      setTickets(demoTickets);

      demoStopRef.current = startDemoSimulation(
        (event) => { handleWsEvent(event); },
        (updated) => { if (mounted) setProject(updated); },
      );

      return () => {
        mounted = false;
        demoStopRef.current?.();
        demoStopRef.current = null;
      };
    }

    getProject(projectId).then(p => {
      if (!mounted) return;
      setProject(p);
      setActiveProject(p);
      if (p?.mode === 'jira') {
        listTickets(projectId).then(t => { if (mounted) setTickets(t); });
      }
    }).catch(() => {
      if (mounted) navigate('/', { replace: true });
    });

    const ws = connectWS(
      projectId,
      (event) => { handleWsEvent(event); },
      () => {
        getProject(projectId).then(p => {
          if (!mounted) return;
          setProject(p);
          setActiveProject(p);
          if (p?.mode === 'jira') {
            listTickets(projectId).then(t => setTickets(t));
          }
        }).catch(() => {});
      }
    );
    wsRef.current = ws;
    setWs(ws);

    return () => {
      mounted = false;
      ws.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, isDemo]);

  const handleDelete = async () => {
    if (isDemo) return exitDemo();
    if (!canDelete || !project) return;
    if (!window.confirm(`Delete "${project.name}"? This cannot be undone.`)) return;

    setDeleting(true);
    try {
      wsRef.current?.close();
      await deleteProject(projectId);
      navigate('/', { replace: true });
    } catch (e) {
      window.alert(e.response?.data?.detail || e.message || 'Failed to delete session');
    } finally {
      setDeleting(false);
    }
  };

  const handlePushToGitHub = async () => {
    if (isJira) {
      window.alert('GitHub push is not yet supported for Jira mode. Work happens in local worktrees.');
      return;
    }
    if (!project?.github_url && project?.status !== 'done') {
      window.alert('Wait for all agents to finish before pushing to GitHub.');
      return;
    }
    if (project?.github_url) {
      window.open(project.github_url, '_blank', 'noopener');
      return;
    }
    if (!window.confirm('Create a new GitHub repo and push the generated project?')) return;

    setPushing(true);
    try {
      const result = await pushToGitHub(projectId);
      const updated = await getProject(projectId);
      setProject(updated);
      setActiveProject(updated);
      if (window.confirm(`✅ Pushed to ${result.github_url}\n\nOpen it on GitHub?`)) {
        window.open(result.github_url, '_blank', 'noopener');
      }
    } catch (e) {
      window.alert(e.response?.data?.detail || e.message);
    } finally {
      setPushing(false);
    }
  };

  const isDone    = project?.status === 'done';
  const isRunning = project?.status === 'running';
  const dotColor  = isRunning ? '#d29922' : isDone ? '#3fb950' : '#8b949e';
  const jiraPrUrl = isJira && !isDemo
    ? (tickets.find(t => t.pr_url)?.pr_url
      || tickets.map(t => ticketStates[t.id]?.prUrl).find(Boolean))
    : null;

  const openViewOutput = () => {
    if (isJira) {
      const { tickets, ticketStates } = useProjectStore.getState();
      const withPr = tickets.find(t => t.pr_url || ticketStates[t.id]?.prUrl);
      if (withPr?.pr_url || ticketStates[withPr?.id]?.prUrl) {
        window.open(withPr.pr_url || ticketStates[withPr.id].prUrl, '_blank', 'noopener');
        return;
      }
      const active = tickets.find(t => ticketStates[t.id]?.output);
      if (active) setModalTicketId(active.id);
      return;
    }
    const lastDone = [...AGENTS].reverse().find(a => agentStates[a].output);
    if (lastDone) setModalAgent(lastDone);
  };

  return (
    <div className={`screen${isMinimal ? ' minimal-project' : ''}`}>
      <div className="navbar">
        <button className="icon-btn" type="button" onClick={() => (isDemo ? exitDemo() : navigate(-1))}>
          <ChevronLeft size={24} color="#58a6ff" />
        </button>
        <div className="nav-center">
          <span className="nav-title">{project?.name || 'Project'}</span>
          <span className="status-dot" style={{ background: dotColor }} />
          {isDemo && (
            <span className="chip demo-chip">DEMO</span>
          )}
          {isJira && !isDemo && (
            <span className="chip" style={{ marginLeft: 8, fontSize: 9, color: '#58a6ff', borderColor: '#58a6ff' }}>JIRA</span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {isDemo ? (
            <button type="button" className="btn-outline demo-exit-btn" onClick={exitDemo}>
              Exit demo
            </button>
          ) : (
            <>
              {canDelete && (
                <button className="icon-btn" type="button" onClick={handleDelete} disabled={deleting} title="Delete session">
                  <Trash2 size={20} color="#f85149" />
                </button>
              )}
              <button className="icon-btn" type="button" onClick={() => navigate('/settings')}>
                <Settings size={20} />
              </button>
            </>
          )}
        </div>
      </div>

      {isDemo && (
        <div className="demo-banner">
          Sample data only — no backend, no real PRs. Exit demo to clear.
        </div>
      )}

      {isMinimal && isJira ? (
        <div className="content minimal-ticket-scroll">
          <TicketProgressGrid onTicketPress={setModalTicketId} />
        </div>
      ) : isJira ? (
        <TicketBoard onTicketPress={setModalTicketId} />
      ) : (
        <AgentKanban onAgentPress={key => setModalAgent(key)} />
      )}

      {!isMinimal && <ActivityFeed />}

      <div className={`action-bar${isMinimal ? ' minimal-action-bar' : ''}`}>
        <button type="button" className="btn-outline" onClick={openViewOutput}>
          <FileText size={18} />
          View Output
        </button>

        {!isJira ? (
          <button
            type="button"
            className={`btn-push${(!isDone && !project?.github_url) ? ' btn-disabled' : ''}`}
            onClick={handlePushToGitHub}
            disabled={pushing}
          >
            {pushing ? (
              <span className="spinner" />
            ) : (
              <>
                {project?.github_url ? <ExternalLink size={18} /> : <Github size={18} />}
                {project?.github_url ? 'View on GitHub' : 'Push to GitHub'}
              </>
            )}
          </button>
        ) : jiraPrUrl ? (
          <button type="button" className="btn-push" onClick={() => window.open(jiraPrUrl, '_blank', 'noopener')}>
            <ExternalLink size={18} />
            View Pull Request
          </button>
        ) : null}
      </div>

      {modalTicketId && (
        <TicketModal ticketId={modalTicketId} onClose={() => setModalTicketId(null)} />
      )}

      {modalAgent && !isJira && (
        <div className="modal-overlay" onClick={() => setModalAgent(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">
                {AGENT_META[modalAgent]?.icon} {AGENT_META[modalAgent]?.label} Output
              </span>
              <button className="icon-btn" type="button" onClick={() => setModalAgent(null)}>
                <X size={24} color="#e6edf3" />
              </button>
            </div>
            <div className="agent-tabs">
              {AGENTS.map(a => (
                <button key={a} type="button" className={`agent-tab${modalAgent === a ? ' active' : ''}`} onClick={() => setModalAgent(a)}>
                  {AGENT_META[a].icon} {AGENT_META[a].label}
                </button>
              ))}
            </div>
            <div className="modal-body">
              <div className="markdown">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {agentStates[modalAgent]?.output || '_No output yet._'}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
