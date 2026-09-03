import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { listArchivedTickets } from '../services/api';
import { useBoardStore } from '../store/boardStore';

export default function ArchivedTicketsPage() {
  const navigate = useNavigate();
  const { demoArchived, restoreDemoTicket, clearDemoArchived } = useBoardStore();
  const [archived, setArchived] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listArchivedTickets()
      .then(rows => setArchived(rows || []))
      .catch(() => setArchived([]))
      .finally(() => setLoading(false));
  }, []);

  const allArchived = [
    ...demoArchived.map(t => ({ ...t, _demo: true })),
    ...archived.filter(t => !demoArchived.some(d => d.id === t.id)),
  ];

  return (
    <div className="screen">
      <div className="navbar">
        <button type="button" className="icon-btn" onClick={() => navigate(-1)}>
          <ChevronLeft size={24} color="#58a6ff" />
        </button>
        <span className="nav-title">Archived tickets</span>
        <span className="spacer-40" />
      </div>

      <div className="content">
        {demoArchived.length > 0 && (
          <button type="button" className="btn-outline" style={{ marginBottom: 12 }} onClick={clearDemoArchived}>
            Clear demo archived
          </button>
        )}

        {loading && !allArchived.length ? (
          <div className="hint">Loading…</div>
        ) : !allArchived.length ? (
          <div className="empty-italic">No archived tickets yet.</div>
        ) : (
          <div className="archived-list">
            {allArchived.map(t => (
              <div key={t.id} className="archived-row card">
                <div>
                  <div className="swim-card-key">{t.ticket_key || t.id}</div>
                  <div className="swim-card-title">{t.title}</div>
                  <div className="meta-text">
                    Archived {t.archived_at ? new Date(t.archived_at).toLocaleString() : '—'}
                    {t._demo ? ' · demo' : ''}
                  </div>
                </div>
                {t._demo && (
                  <button type="button" className="btn-outline" onClick={() => restoreDemoTicket(t.id)}>
                    Restore
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
