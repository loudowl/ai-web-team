import { useEffect, useState } from 'react';
import { useProjectStore } from '../store/projectStore';
import TicketProgressCard from './TicketProgressCard';

export default function TicketProgressGrid({ onTicketPress }) {
  const { tickets, ticketStates } = useProjectStore();
  const [, tick] = useState(0);

  useEffect(() => {
    const active = tickets.some(t => {
      const ts = ticketStates[t.id];
      return ts?.active || ts?.status === 'running';
    });
    if (!active) return undefined;
    const id = setInterval(() => tick(n => n + 1), 1000);
    return () => clearInterval(id);
  }, [tickets, ticketStates]);

  if (!tickets.length) {
    return <div className="empty-italic" style={{ padding: 16 }}>No tickets.</div>;
  }

  return (
    <div className="ticket-progress-grid">
      {tickets.map(t => (
        <button
          key={t.id}
          type="button"
          className="ticket-progress-grid-item"
          onClick={() => onTicketPress?.(t.id)}
        >
          <TicketProgressCard ticket={t} compact={tickets.length > 3} />
        </button>
      ))}
    </div>
  );
}
