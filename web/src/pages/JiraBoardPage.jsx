import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import TicketSwimBoard from '../components/TicketSwimBoard';
import BoardMemoryMeter from '../components/BoardMemoryMeter';
import TicketModal from '../components/TicketModal';
import { connectWS, listProjects } from '../services/api';
import { useProjectStore } from '../store/projectStore';
import { useUiStore } from '../store/uiStore';

export default function JiraBoardPage() {
  const navigate = useNavigate();
  const { syncGlobalBoardTickets, handleWsEvent, setWs, clearBoardRunState, tickets } = useProjectStore();
  const { setInterfaceMode } = useUiStore();
  const [modalTicketId, setModalTicketId] = useState(null);
  const [defaultProjectId, setDefaultProjectId] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [meta, setMeta] = useState({ project_count: 0, ticket_count: 0 });
  const wsRefs = useRef([]);

  const load = async () => {
    const data = await syncGlobalBoardTickets();
    setMeta({
      project_count: data.project_count ?? 0,
      ticket_count: (data.tickets || []).length,
    });
    const projects = await listProjects().catch(() => []);
    const jiraProjects = (projects || []).filter(p => p.mode === 'jira');
    setDefaultProjectId(jiraProjects[0]?.id || null);
    return jiraProjects;
  };

  useEffect(() => {
    clearBoardRunState();
    setInterfaceMode('minimal');

    let mounted = true;

    load().then(jiraProjects => {
      if (!mounted) return;
      wsRefs.current.forEach(ws => ws.close());
      wsRefs.current = jiraProjects.map(project => {
        const ws = connectWS(
          project.id,
          handleWsEvent,
          () => { if (mounted) syncGlobalBoardTickets(); },
        );
        return ws;
      });
      setWs(wsRefs.current[0] || null);
    });

    const poll = window.setInterval(() => {
      syncGlobalBoardTickets();
    }, 15000);

    return () => {
      mounted = false;
      window.clearInterval(poll);
      wsRefs.current.forEach(ws => ws.close());
      wsRefs.current = [];
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const hasTickets = tickets.filter(t => !t.archived_at).length > 0;

  return (
    <div className="screen minimal-project">
      <div className="navbar jira-board-navbar">
        <div className="nav-center jira-board-nav-center">
          <span className="nav-title">Jira board</span>
          <span className="chip" style={{ fontSize: 9, color: '#58a6ff', borderColor: '#58a6ff' }}>ALL TICKETS</span>
        </div>
        <div className="nav-actions">
          <button type="button" className="icon-btn" onClick={onRefresh} title="Refresh board" disabled={refreshing}>
            <RefreshCw size={18} className={refreshing ? 'spin-icon' : ''} />
          </button>
        </div>
      </div>

      <div className="jira-banner">
        {meta.ticket_count > 0
          ? `${meta.ticket_count} active ticket${meta.ticket_count === 1 ? '' : 's'} across ${meta.project_count} batch${meta.project_count === 1 ? '' : 'es'}.`
          : 'All non-archived tickets from every Jira batch appear here.'}
      </div>

      {hasTickets && (
        <BoardMemoryMeter projectId={defaultProjectId} />
      )}

      {!defaultProjectId && !hasTickets ? (
        <div className="empty jira-board-empty">
          <div className="empty-icon">📋</div>
          <div className="empty-title">No Jira board yet</div>
          <div className="empty-text">
            Create a ticket batch first, then all active tickets will show up here.
          </div>
          <button type="button" className="btn-outline" onClick={() => navigate('/batch')}>
            New ticket batch
          </button>
        </div>
      ) : (
        <div className="content swim-board-scroll minimal-ticket-scroll">
          <TicketSwimBoard
            globalMode
            defaultProjectId={defaultProjectId}
            onTicketPress={setModalTicketId}
          />
        </div>
      )}

      {modalTicketId && (
        <TicketModal ticketId={modalTicketId} onClose={() => setModalTicketId(null)} />
      )}
    </div>
  );
}
