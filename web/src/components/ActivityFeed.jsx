import { useRef, useEffect, useState } from 'react';
import { useProjectStore } from '../store/projectStore';
import ThinkingIndicator from './ThinkingIndicator';

const SYSTEM_META = { label: 'System', icon: '⚙️', color: '#8b949e' };

function FeedItem({ message }) {
  const { AGENT_META } = useProjectStore();
  const meta = AGENT_META[message.agent] || SYSTEM_META;
  const isError = message.type === 'error';
  const isDone  = message.type === 'done';

  return (
    <div className={`feed-item${isError ? ' error' : ''}`}>
      <div className="avatar" style={{ background: meta.color + '22', borderColor: meta.color }}>
        <span className="avatar-icon">{meta.icon}</span>
      </div>
      <div className="bubble">
        <div className="bubble-header">
          <span className="agent-name" style={{ color: meta.color }}>{meta.label}</span>
          <span className="timestamp">
            {message.ts?.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        <div className={`message-text${isDone ? ' done' : ''}${isError ? ' error' : ''}`}>
          {message.text}
        </div>
      </div>
    </div>
  );
}

function StreamingOutput({ agentKey }) {
  const { agentStates, AGENT_META } = useProjectStore();
  const state = agentStates[agentKey];
  const meta  = AGENT_META[agentKey];

  if (state.status !== 'running' || !state.output) return null;

  const preview = state.output.slice(-300);

  return (
    <div className="streaming">
      <div className="streaming-dot" style={{ background: meta.color }} />
      <div className="streaming-bubble">
        <div className="agent-name" style={{ color: meta.color, marginBottom: 4 }}>
          {meta.icon} {meta.label} — streaming
        </div>
        <div className="streaming-text">{preview}</div>
        <div className="cursor" />
      </div>
    </div>
  );
}

export default function ActivityFeed() {
  const { feedMessages, activeAgent, agentStates, activeTicketId, ticketStates } = useProjectStore();
  const endRef = useRef(null);
  const [, tick] = useState(0);

  const streamingLen = activeAgent ? agentStates[activeAgent]?.output.length : 0;
  const activeTicket = activeTicketId ? ticketStates[activeTicketId] : null;

  useEffect(() => {
    if (!activeTicket?.thinkingSince) return undefined;
    const id = setInterval(() => tick(n => n + 1), 1000);
    return () => clearInterval(id);
  }, [activeTicket?.thinkingSince]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [feedMessages.length, streamingLen]);

  return (
    <div className="feed">
      <span className="section-label">ACTIVITY FEED</span>
      <div className="feed-list">
        {feedMessages.map(item => (
          <FeedItem key={String(item.id)} message={item} />
        ))}
        {activeTicketId && (activeTicket?.status === 'running' || activeTicket?.active) && (
          <ThinkingIndicator ticketId={activeTicketId} compact />
        )}
        {activeAgent ? <StreamingOutput agentKey={activeAgent} /> : null}
        <div ref={endRef} />
      </div>
    </div>
  );
}
