export const PROVIDERS = [
  { key: 'openai',    label: 'OpenAI',    icon: '🤖', desc: 'Cloud — best quality' },
  { key: 'anthropic', label: 'Anthropic', icon: '🧠', desc: 'Cloud — strong reasoning' },
  { key: 'ollama',    label: 'Ollama',    icon: '🦙', desc: 'Local — recommended for Jira mode' },
];

export const TIER_ORDER = ['frontier', 'recent', 'coding', 'excluded'];

export function groupModelsByTier(models = []) {
  const groups = {};
  for (const m of models) {
    const tier = m.tier || 'other';
    if (!groups[tier]) groups[tier] = [];
    groups[tier].push(m);
  }
  return TIER_ORDER.filter(t => groups[t]?.length).map(t => ({ tier: t, models: groups[t] }));
}

export function buildFallbackTooltip(m) {
  const lines = [m.description].filter(Boolean);
  if (m.reason) lines.push(`Policy: ${m.reason}`);
  return { lines, pull: null };
}

export function getExtraLines(m, tooltip) {
  const desc = (m.description || '').trim();
  return (tooltip.lines || []).filter(line => {
    const t = (line || '').trim();
    return t && t !== desc;
  });
}

export function findModel(models, id) {
  return (models || []).find(m => m.id === id);
}

export function formatModelAssignment(provider, model, catalogModels = []) {
  const providerInfo = PROVIDERS.find(p => p.key === provider);
  const providerLabel = providerInfo?.label || provider || 'Unknown';
  const catalogMatch = findModel(catalogModels, model)
    || findModel(catalogModels, `${model}:latest`)
    || findModel(catalogModels, model?.split(':')[0]);
  const rawModel = (model || 'unset').replace(/:latest$/i, '').split('/').pop();
  const modelLabel = catalogMatch?.display
    || (rawModel.charAt(0).toUpperCase() + rawModel.slice(1));
  return {
    providerLabel,
    modelLabel,
    summary: `${modelLabel} · ${providerLabel}`,
  };
}

export function workflowLabel(workflowId) {
  const labels = {
    simple: 'Simple fix',
    fix: 'Fix',
    full_cycle: 'Full cycle',
  };
  return labels[workflowId] || workflowId || '';
}
