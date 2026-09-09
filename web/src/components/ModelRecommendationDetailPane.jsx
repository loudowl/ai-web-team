import { useEffect, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import {
  explainModelRecommendation,
  parseCreatorQuestions,
  truncateDescription,
} from '../utils/ticketAssessment';

export default function ModelRecommendationDetailPane({ ticket }) {
  const [descriptionExpanded, setDescriptionExpanded] = useState(false);

  useEffect(() => {
    setDescriptionExpanded(false);
  }, [ticket?.id]);

  if (!ticket) {
    return (
      <div className="model-rec-detail-empty">
        <div className="empty-icon">←</div>
        <div className="empty-title">Select a ticket</div>
        <div className="empty-text">Choose a ticket from the list to review its model recommendation.</div>
      </div>
    );
  }

  const recommendation = explainModelRecommendation(ticket);
  const creatorQuestions = parseCreatorQuestions(ticket);
  const description = truncateDescription(ticket.description);
  const showDescription = description.preview || description.full;

  return (
    <div className="model-rec-detail-inner">
      <header className="model-rec-detail-header">
        {ticket.jira_url && (
          <a
            className="ticket-modal-jira-link"
            href={ticket.jira_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            <ExternalLink size={14} />
            {ticket.ticket_key ? `Open ${ticket.ticket_key} in Jira` : 'Open ticket in Jira'}
          </a>
        )}
        <h2 className="model-rec-detail-title">
          {ticket.ticket_key || ticket.id}
          {' — '}
          {ticket.title}
        </h2>
        <div className="model-rec-detail-chips">
          <span className="ticket-modal-model-chip">{recommendation.summary}</span>
          {recommendation.tier && (
            <span className="model-rec-detail-tier">{recommendation.tier}</span>
          )}
          {recommendation.score != null && !Number.isNaN(Number(recommendation.score)) && (
            <span className="model-rec-detail-score">Score {Number(recommendation.score).toFixed(1)}</span>
          )}
        </div>
      </header>

      <section className="ticket-modal-assessment model-rec-detail-section">
        <div className="section-label">MODEL RECOMMENDATION</div>
        <div className="ticket-modal-assessment-reason">
          {recommendation.paragraphs.map((paragraph, index) => (
            <p key={index}>{paragraph}</p>
          ))}
          <p className="ticket-modal-assessment-note">
            Based on title, description, acceptance criteria, labels, and complexity rubric at ingest time.
          </p>
        </div>
      </section>

      {creatorQuestions.length > 0 && (
        <section className="ticket-modal-assessment model-rec-detail-section">
          <div className="section-label">QUESTIONS FOR THE TICKET CREATOR</div>
          <ul className="ticket-modal-questions-list">
            {creatorQuestions.map(q => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </section>
      )}

      {showDescription && (
        <section className="model-rec-detail-section model-rec-description-section">
          <div className="section-label">DESCRIPTION</div>
          <p className="model-rec-description-body">
            {descriptionExpanded && description.isTruncated
              ? description.full
              : description.preview}
          </p>
          {description.isTruncated && (
            <button
              type="button"
              className="model-rec-description-toggle"
              onClick={() => setDescriptionExpanded(v => !v)}
            >
              {descriptionExpanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </section>
      )}
    </div>
  );
}
