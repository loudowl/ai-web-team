import { useMemo, useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { groupPreAssessedBySize } from '../utils/boardLanes';
import { formatModelAssignment } from '../utils/modelPicker';

function ModelRecRow({ ticket, selected, onSelect }) {
  const assignment = formatModelAssignment(
    ticket.assigned_provider || ticket.project_provider,
    ticket.assigned_model || ticket.project_model,
  );

  return (
    <button
      type="button"
      className={`model-rec-row${selected ? ' selected' : ''}`}
      onClick={() => onSelect(ticket.id)}
    >
      <div className="model-rec-row-top">
        <span className="model-rec-row-key">{ticket.ticket_key || ticket.id}</span>
        {ticket.jira_priority && (
          <span className="model-rec-row-priority">{ticket.jira_priority}</span>
        )}
      </div>
      <div className="model-rec-row-title">{ticket.title}</div>
      <div className="model-rec-row-meta">
        {ticket.complexity_tier && (
          <span className="model-rec-row-tier">{ticket.complexity_tier}</span>
        )}
        <span className="model-rec-row-model">{assignment.summary}</span>
      </div>
      {ticket.project_name && (
        <div className="model-rec-row-batch">{ticket.project_name}</div>
      )}
    </button>
  );
}

export default function ModelRecommendationList({ tickets, selectedId, onSelect }) {
  const sizeGroups = useMemo(() => groupPreAssessedBySize(tickets), [tickets]);
  const [collapsedSizeGroups, setCollapsedSizeGroups] = useState({});

  const toggleSizeGroup = (size) => {
    setCollapsedSizeGroups(prev => ({ ...prev, [size]: !prev[size] }));
  };

  if (!tickets.length) {
    return (
      <div className="model-rec-empty">
        <div className="empty-icon">🧠</div>
        <div className="empty-title">No tickets yet</div>
        <div className="empty-text">Sync Jira tickets to see model recommendations here.</div>
      </div>
    );
  }

  return (
    <div className="model-rec-list-inner">
      {sizeGroups.map(group => {
        const expanded = !collapsedSizeGroups[group.size];
        return (
          <div key={group.size} className="swim-preassessed-size-group">
            <button
              type="button"
              className="swim-preassessed-size-toggle"
              onClick={() => toggleSizeGroup(group.size)}
              aria-expanded={expanded}
            >
              <ChevronRight size={14} className={`swim-size-chevron${expanded ? ' expanded' : ''}`} />
              <span className="swim-preassessed-size-label">{group.label}</span>
              <span className="swim-preassessed-size-count">{group.tickets.length}</span>
            </button>
            {expanded && (
              <div className="model-rec-size-rows">
                {group.tickets.map(ticket => (
                  <ModelRecRow
                    key={ticket.id}
                    ticket={ticket}
                    selected={selectedId === ticket.id}
                    onSelect={onSelect}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
