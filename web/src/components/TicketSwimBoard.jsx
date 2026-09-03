import { useState, useEffect } from 'react';
import { Archive, ExternalLink, Play } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useProjectStore } from '../store/projectStore';
import { useBoardStore } from '../store/boardStore';
import { BOARD_LANES, WORKFLOWS, groupTicketsByLane, laneOverrideKey } from '../utils/boardLanes';
import { isDemoProjectId } from '../demo/demoData';
import { runDemoTicket } from '../demo/demoSimulator';
import {
  addBoardTicket,
  archiveTicket,
  runBoardTicket,
  updateTicketLane,
  listTickets,
} from '../services/api';
import { checkOllamaModel, parseOllamaMissingError } from '../utils/ollamaPull';
import OllamaPullModal from './OllamaPullModal';
import { getTicketActivity, formatElapsed } from './ThinkingIndicator';

function AddTicketForm({ projectId, isDemo, onAdded }) {
  const { addDemoTicket } = useProjectStore();
  const [line, setLine] = useState('');
  const [busy, setBusy] = useState(false);

  const parseLine = (raw) => {
    const trimmed = raw.trim();
    if (!trimmed) return null;
    if (/^https?:\/\//i.test(trimmed)) return { jira_url: trimmed };
    const keyMatch = trimmed.match(/^([A-Z][A-Z0-9]+-\d+)/);
    if (keyMatch) return { ticket_key: keyMatch[1] };
    return { manual: { title: trimmed, description: '', acceptance_criteria: '' } };
  };

  const handleAdd = async () => {
    const payload = parseLine(line);
    if (!payload) return;
    setBusy(true);
    try {
      if (isDemo) {
        addDemoTicket(payload);
        setLine('');
        onAdded?.();
        return;
      }
      await addBoardTicket(projectId, payload);
      setLine('');
      if (onAdded) {
        onAdded();
      } else {
        const refreshed = await listTickets(projectId);
        useProjectStore.getState().setTickets(refreshed);
      }
    } catch (e) {
      window.alert(e.response?.data?.detail || e.message || 'Failed to add ticket');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="swim-add">
      <input
        className="input swim-add-input"
        placeholder="FTSWB-123 or Jira URL"
        value={line}
        onChange={e => setLine(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && handleAdd()}
      />
      <button type="button" className="btn-outline swim-add-btn" onClick={handleAdd} disabled={busy || !line.trim()}>
        Add
      </button>
    </div>
  );
}

function SwimCard({
  ticket,
  lane,
  projectId,
  isDemo,
  globalMode,
  onOpen,
  onRunDemo,
  runningDemo,
  onModelMissing,
}) {
  const effectiveProjectId = projectId || ticket.project_id;
  const { ticketStates, JIRA_MILESTONES, removeDemoTicket, updateTicketRow, activeProject } = useProjectStore();
  const { setLaneOverride, archiveDemoTicket } = useBoardStore();
  const ts = ticketStates[ticket.id] || {};
  const activity = getTicketActivity(ts, JIRA_MILESTONES);
  const prUrl = ts.prUrl || ticket.pr_url;
  const isRunning = ts.status === 'running' || ts.active || runningDemo;
  const cardProvider = ticket.assigned_provider || ticket.project_provider || activeProject?.provider;
  const cardModel = ticket.assigned_model || ticket.project_model || activeProject?.model;

  const launch = async (workflow) => {
    updateTicketRow(ticket.id, {
      workflow,
      assigned_provider: cardProvider,
      assigned_model: cardModel,
    });
    if (isDemo) {
      onRunDemo(ticket.id, workflow);
      return;
    }
    if (!effectiveProjectId) {
      window.alert('No project batch found for this ticket.');
      return;
    }

    const pendingRun = {
      projectId: effectiveProjectId,
      ticketId: ticket.id,
      workflow,
      ticketLabel: ticket.ticket_key || ticket.title,
    };

    if (cardProvider === 'ollama' && cardModel) {
      try {
        const check = await checkOllamaModel(cardModel);
        if (!check.installed) {
          onModelMissing?.(check, pendingRun);
          return;
        }
      } catch (e) {
        console.warn('Ollama model check failed', e);
      }
    }

    try {
      await runBoardTicket(effectiveProjectId, ticket.id, workflow);
    } catch (e) {
      const missing = parseOllamaMissingError(e);
      if (missing) {
        onModelMissing?.(missing, pendingRun);
        return;
      }
      window.alert(e.response?.data?.detail || e.message || 'Failed to start ticket');
    }
  };

  const handleArchive = async () => {
    if (!window.confirm(`Archive ${ticket.ticket_key || ticket.title}?`)) return;
    if (isDemo) {
      archiveDemoTicket(ticket);
      removeDemoTicket(ticket.id);
      return;
    }
    if (!effectiveProjectId) {
      window.alert('No project batch found for this ticket.');
      return;
    }
    try {
      await archiveTicket(effectiveProjectId, ticket.id);
      if (globalMode) {
        await useProjectStore.getState().syncGlobalBoardTickets();
      } else {
        const refreshed = await listTickets(effectiveProjectId);
        useProjectStore.getState().setTickets(refreshed);
      }
    } catch (e) {
      window.alert(e.response?.data?.detail || e.message || 'Failed to archive');
    }
  };

  const handleDragStart = (e) => {
    e.dataTransfer.setData('text/ticket-id', ticket.id);
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      className={`swim-card${isRunning ? ' running' : ''}`}
      draggable={lane !== 'todo' || !isRunning}
      onDragStart={handleDragStart}
    >
      <button type="button" className="swim-card-main" onClick={() => onOpen(ticket.id)}>
        <div className="swim-card-key">{ticket.ticket_key || ticket.id}</div>
        {globalMode && ticket.project_name && (
          <div className="swim-card-batch">{ticket.project_name}</div>
        )}
        <div className="swim-card-title">{ticket.title}</div>
        {activity && (
          <div className="swim-card-activity">
            {activity.label}
            {' · '}
            {formatElapsed(Date.now() - (activity.since || Date.now()))}
          </div>
        )}
        {prUrl && (
          <a
            className="swim-card-pr"
            href={prUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
          >
            <ExternalLink size={12} /> PR
          </a>
        )}
      </button>

      {lane === 'todo' && !isRunning && (
        <div className="swim-card-actions">
          {WORKFLOWS.map(w => (
            <button
              key={w.id}
              type="button"
              className="swim-action-btn"
              title={w.title}
              onClick={() => launch(w.id)}
            >
              <Play size={11} /> {w.label}
            </button>
          ))}
        </div>
      )}

      <button type="button" className="swim-archive-btn" title="Archive" onClick={handleArchive}>
        <Archive size={14} />
      </button>
    </div>
  );
}

export default function TicketSwimBoard({ projectId, globalMode = false, defaultProjectId, onTicketPress }) {
  const navigate = useNavigate();
  const isDemo = !globalMode && isDemoProjectId(projectId);
  const addProjectId = globalMode ? defaultProjectId : projectId;
  const { tickets, ticketStates, setTickets, handleWsEvent, syncTicketsFromApi, syncGlobalBoardTickets } = useProjectStore();
  const { laneOverrides, setLaneOverride, demoArchived } = useBoardStore();
  const [demoRunning, setDemoRunning] = useState({});
  const [pullRequest, setPullRequest] = useState(null);

  const startPendingRun = async (pendingRun) => {
    if (!pendingRun) return;
    try {
      await runBoardTicket(pendingRun.projectId, pendingRun.ticketId, pendingRun.workflow);
    } catch (e) {
      const missing = parseOllamaMissingError(e);
      if (missing) {
        setPullRequest({ ...missing, pendingRun });
        return;
      }
      window.alert(e.response?.data?.detail || e.message || 'Failed to start ticket');
    }
  };

  const handleModelMissing = (info, pendingRun) => {
    setPullRequest({ ...info, pendingRun });
  };

  const handlePullReady = async () => {
    const pendingRun = pullRequest?.pendingRun;
    setTimeout(() => setPullRequest(null), 800);
    await startPendingRun(pendingRun);
  };

  useEffect(() => {
    if (globalMode) {
      syncGlobalBoardTickets();
      return;
    }
    if (!isDemo && projectId) {
      syncTicketsFromApi(projectId);
    }
  }, [projectId, isDemo, globalMode, syncTicketsFromApi, syncGlobalBoardTickets]);

  const visibleTickets = isDemo
    ? tickets.filter(t => !demoArchived.some(a => a.id === t.id))
    : tickets.filter(t => !t.archived_at);

  const groups = groupTicketsByLane(visibleTickets, ticketStates, laneOverrides);

  const refreshTickets = async () => {
    if (globalMode) {
      await syncGlobalBoardTickets();
      return;
    }
    if (isDemo || !projectId) return;
    const t = await listTickets(projectId);
    setTickets(t);
  };

  const handleDrop = async (lane, e) => {
    e.preventDefault();
    const ticketId = e.dataTransfer.getData('text/ticket-id');
    if (!ticketId) return;
    if (lane !== 'dev_complete') return;

    const ticket = visibleTickets.find(t => t.id === ticketId);
    const effectiveProjectId = projectId || ticket?.project_id;
    setLaneOverride(ticketId, 'dev_complete', effectiveProjectId);
    if (isDemo) return;

    if (!effectiveProjectId) return;

    try {
      await updateTicketLane(effectiveProjectId, ticketId, 'dev_complete');
      await refreshTickets();
    } catch (err) {
      window.alert(err.response?.data?.detail || err.message || 'Failed to move ticket');
    }
  };

  const handleRunDemo = (ticketId, workflow) => {
    if (demoRunning[ticketId]) return;
    setDemoRunning(prev => ({ ...prev, [ticketId]: true }));
    runDemoTicket(ticketId, workflow, (event) => {
      handleWsEvent(event);
      if (event.type === 'ticket_done' || event.type === 'error') {
        setDemoRunning(prev => ({ ...prev, [ticketId]: false }));
      }
    });
  };

  return (
    <div className="swim-board-wrap">
      <OllamaPullModal
        open={!!pullRequest}
        info={pullRequest}
        ticketLabel={pullRequest?.pendingRun?.ticketLabel}
        onClose={() => setPullRequest(null)}
        onReady={handlePullReady}
      />
      <div className="swim-board-header">
        <div className="swim-board-header-copy">
          <span className="section-label">{globalMode ? 'ALL JIRA TICKETS' : 'TICKET BOARD'}</span>
          {!isDemo && visibleTickets.length > 0 && (
            <span className="swim-board-total">{visibleTickets.length} active ticket{visibleTickets.length === 1 ? '' : 's'}</span>
          )}
        </div>
        <button type="button" className="btn-outline swim-archived-link" onClick={() => navigate('/archived')}>
          Archived tickets
        </button>
      </div>
      <div className="swim-board">
        {BOARD_LANES.map(lane => (
          <div
            key={lane.id}
            className={`swim-lane swim-lane-${lane.id}`}
            onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }}
            onDrop={e => handleDrop(lane.id, e)}
          >
            <div className="swim-lane-header" style={{ borderColor: lane.color }}>
              <span className="swim-lane-title" style={{ color: lane.color }}>{lane.label}</span>
              <span className="swim-lane-count">{groups[lane.id].length}</span>
            </div>
            <div className="swim-lane-body">
              {lane.id === 'todo' && addProjectId && (
                <AddTicketForm projectId={addProjectId} isDemo={isDemo} onAdded={refreshTickets} />
              )}
              {groups[lane.id].map(t => (
                <SwimCard
                  key={t.id}
                  ticket={t}
                  lane={lane.id}
                  projectId={projectId}
                  globalMode={globalMode}
                  isDemo={isDemo}
                  onOpen={onTicketPress}
                  onRunDemo={handleRunDemo}
                  runningDemo={!!demoRunning[t.id]}
                  onModelMissing={handleModelMissing}
                />
              ))}
              {!groups[lane.id].length && lane.id !== 'todo' && (
                <div className="swim-lane-empty">Drop tickets here</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
