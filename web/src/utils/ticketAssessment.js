import { formatModelAssignment } from './modelPicker';

const TIER_MODEL_HINTS = {
  trivial:
    'Trivial changes (short copy, CSS tweaks, typos) route to the lightest available model — usually local Ollama for speed and zero API cost.',
  simple:
    'Simple tickets stay on lightweight models that handle scoped edits without heavy planning overhead.',
  medium:
    'Medium complexity warrants a cloud model with stronger reasoning for multi-step implementation and moderate scope.',
  complex:
    'Complex tickets need a capable cloud model for architecture-aware changes, larger diffs, and careful planning.',
  critical:
    'Critical-tier work uses the strongest configured frontier model for reliability on high-impact changes.',
};

const PROVIDER_NOTES = {
  ollama: 'Local Ollama keeps this ticket off cloud APIs until you override the assignment.',
  anthropic: 'Anthropic was selected for strong code generation and reasoning on this complexity tier.',
  openai: 'OpenAI was selected for frontier capability on this complexity tier.',
  gemini: 'Gemini was selected based on your routing configuration for this tier.',
  cursor: 'Cursor Composer routing applies for this tier per your project settings.',
};

export function parseCreatorQuestions(ticket) {
  if (!ticket?.creator_questions_json) return [];
  try {
    const parsed = JSON.parse(ticket.creator_questions_json);
    return Array.isArray(parsed) ? parsed.filter(q => typeof q === 'string' && q.trim()) : [];
  } catch {
    return [];
  }
}

/** Human-readable model routing explanation from ticket assessment fields. */
export function explainModelRecommendation(ticket) {
  const provider = ticket?.assigned_provider || ticket?.project_provider;
  const model = ticket?.assigned_model || ticket?.project_model;
  const assignment = formatModelAssignment(provider, model);
  const tier = ticket?.complexity_tier || 'medium';
  const score = ticket?.complexity_score;

  const paragraphs = [
    `Recommended coding model: ${assignment.summary}.`,
    TIER_MODEL_HINTS[tier] || TIER_MODEL_HINTS.medium,
  ];

  if (score != null && !Number.isNaN(Number(score))) {
    paragraphs.push(
      `Complexity rubric score ${Number(score).toFixed(1)} → tier "${tier}" drives the default model mapping (not a separate LLM call).`,
    );
  } else if (tier) {
    paragraphs.push(`Complexity tier "${tier}" drives the default model mapping (not a separate LLM call).`);
  }

  if (provider && PROVIDER_NOTES[provider]) {
    paragraphs.push(PROVIDER_NOTES[provider]);
  }

  if (ticket?.recommended_t_shirt_size_reason) {
    paragraphs.push(`Sizing context: ${ticket.recommended_t_shirt_size_reason}`);
  }

  return {
    summary: assignment.summary,
    tier,
    score,
    paragraphs,
  };
}

export function truncateDescription(text, limit = 180) {
  const normalized = (text || '').replace(/\s+/g, ' ').trim();
  if (!normalized) return { preview: '', isTruncated: false };
  if (normalized.length <= limit) {
    return { preview: normalized, isTruncated: false };
  }
  return {
    preview: `${normalized.slice(0, limit).trimEnd()}…`,
    isTruncated: true,
    full: normalized,
  };
}
