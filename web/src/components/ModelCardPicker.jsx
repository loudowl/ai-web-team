import { useMemo } from 'react';
import { groupModelsByTier, buildFallbackTooltip, getExtraLines } from '../utils/modelPicker';

function ModelOption({ model: m, selected, onSelect }) {
  const selectable = m.selectable !== false;
  const tooltip = m.tooltip || buildFallbackTooltip(m);
  const extraLines = getExtraLines(m, tooltip);
  const showExtra = extraLines.length > 0 || (tooltip.pull && !m.installed && selectable);

  return (
    <div className="model-option-wrap">
      <button
        type="button"
        disabled={!selectable}
        className={`model-option${selected ? ' selected' : ''}${!selectable ? ' disabled' : ''}${m.installed ? ' installed' : ''}${showExtra ? ' has-extra' : ''}`}
        onClick={() => selectable && onSelect(m.id)}
      >
        <div className="model-option-header">
          <span className="model-option-name">{m.display}</span>
          {m.installed && (
            <span className="model-option-tag">
              Installed{m.installed_size_gb ? ` · ${m.installed_size_gb} GB` : ''}
            </span>
          )}
          {!selectable && <span className="model-option-tag restricted">Restricted</span>}
          {m.ram_hint && selectable && (
            <span className="model-option-tag subtle">{m.ram_hint.replace('~', '').replace(' RAM', '')}</span>
          )}
        </div>
        <div className="model-option-desc">{m.description}</div>
        {showExtra && (
          <div className="model-option-extra" aria-hidden="true">
            {extraLines.length > 0 && (
              <ul className="model-option-extra-lines">
                {extraLines.map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            )}
            {tooltip.pull && !m.installed && selectable && (
              <code className="model-option-pull">{tooltip.pull}</code>
            )}
          </div>
        )}
      </button>
    </div>
  );
}

export default function ModelCardPicker({ provider, choices, tierLabels, selectedModel, onSelectModel }) {
  const providerInfo = choices?.providers?.[provider];
  const models = providerInfo?.models ?? [];
  const groups = useMemo(() => groupModelsByTier(models), [models]);

  if (!providerInfo) return null;

  return (
    <div className="model-picker">
      {groups.map(({ tier, models: tierModels }) => (
        <div key={tier} className="model-tier">
          <div className="model-tier-label">{tierLabels?.[tier] || tier}</div>
          <div className="model-options">
            {tierModels.map(m => (
              <ModelOption
                key={m.id}
                model={m}
                selected={selectedModel === m.id}
                onSelect={onSelectModel}
              />
            ))}
          </div>
        </div>
      ))}
      {provider === 'ollama' && providerInfo.best_installed && (
        <div className="hint">
          Best installed locally: <code>{providerInfo.best_installed}</code>
        </div>
      )}
    </div>
  );
}
