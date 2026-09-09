import { useEffect, useMemo, useRef, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import ModelRecommendationList from '../components/ModelRecommendationList';
import ModelRecommendationDetailPane from '../components/ModelRecommendationDetailPane';
import { connectWS, listProjects } from '../services/api';
import { useProjectStore } from '../store/projectStore';
import { useUiStore } from '../store/uiStore';

export default function ModelRecommendationPage() {
  const { syncGlobalBoardTickets, handleWsEvent, setWs, clearBoardRunState, tickets } = useProjectStore();
  const { setInterfaceMode } = useUiStore();
  const [selectedId, setSelectedId] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [meta, setMeta] = useState({ project_count: 0, ticket_count: 0 });
  const wsRefs = useRef([]);

  const visibleTickets = useMemo(
    () => tickets.filter(t => !t.archived_at),
    [tickets],
  );

  const selectedTicket = useMemo(
    () => visibleTickets.find(t => t.id === selectedId) || null,
    [visibleTickets, selectedId],
  );

  const load = async () => {
    const data = await syncGlobalBoardTickets();
    setMeta({
      project_count: data.project_count ?? 0,
      ticket_count: (data.tickets || []).length,
    });
    const projects = await listProjects().catch(() => []);
    return (projects || []).filter(p => p.mode === 'jira');
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

  useEffect(() => {
    if (selectedId && visibleTickets.some(t => t.id === selectedId)) return;
    setSelectedId(visibleTickets[0]?.id || null);
  }, [visibleTickets, selectedId]);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  return (
    <div className="screen minimal-project model-rec-page">
      <div className="navbar jira-board-navbar">
        <div className="nav-center jira-board-nav-center">
          <span className="nav-title">
            Model recommendation view
            <span className="model-rec-pre-assessed-tag"> (Pre Assessed)</span>
          </span>
          <span className="chip" style={{ fontSize: 9, color: '#bc8cff', borderColor: '#bc8cff' }}>
            ALL TICKETS
          </span>
        </div>
        <div className="nav-actions">
          <button type="button" className="icon-btn" onClick={onRefresh} title="Refresh tickets" disabled={refreshing}>
            <RefreshCw size={18} className={refreshing ? 'spin-icon' : ''} />
          </button>
        </div>
      </div>

      <div className="jira-banner">
        {meta.ticket_count > 0
          ? `${visibleTickets.length} active ticket${visibleTickets.length === 1 ? '' : 's'} grouped by recommended size. Select one to review model routing.`
          : 'All non-archived tickets appear here once Jira batches are synced.'}
      </div>

      <div className="model-rec-layout">
        <aside className="model-rec-list-panel">
          <ModelRecommendationList
            tickets={visibleTickets}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </aside>
        <main className="model-rec-detail-panel">
          <ModelRecommendationDetailPane ticket={selectedTicket} />
        </main>
      </div>
    </div>
  );
}
