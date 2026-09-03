import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { PROVIDERS, groupModelsByTier, findModel } from '../utils/modelPicker';

function providerAvailable(key, providerChoices, models) {
  if (key === 'ollama') return true;
  return providerChoices?.providers?.[key]?.available
    ?? models?.providers?.[key]?.available
    ?? false;
}

export default function ModelCascadePicker({
  provider,
  selectedModel,
  providerChoices,
  models,
  tierLabels,
  onProviderChange,
  onModelChange,
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeTier, setActiveTier] = useState('frontier');
  const rootRef = useRef(null);

  const providerInfo = providerChoices?.providers?.[provider];
  const catalog = providerInfo?.models ?? [];
  const groups = useMemo(() => groupModelsByTier(catalog), [catalog]);
  const selected = findModel(catalog, selectedModel);

  useEffect(() => {
    const tier = groups.find(g => g.models.some(m => m.id === selectedModel))?.tier;
    if (tier) setActiveTier(tier);
  }, [selectedModel, groups]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onDoc = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [menuOpen]);

  useEffect(() => {
    setMenuOpen(false);
  }, [provider]);

  const activeGroup = groups.find(g => g.tier === activeTier) || groups[0];
  const activeModels = activeGroup?.models ?? [];

  const pickModel = (m) => {
    if (m.selectable === false) return;
    onModelChange(m.id);
    setMenuOpen(false);
  };

  return (
    <div className="cascade-picker" ref={rootRef}>
      <div className="cascade-picker-row">
        <label className="cascade-field">
          <span className="cascade-label">Provider</span>
          <div className="cascade-select-wrap">
            <select
              className="cascade-select"
              value={provider}
              onChange={e => onProviderChange(e.target.value)}
            >
              {PROVIDERS.map(p => {
                const ok = providerAvailable(p.key, providerChoices, models);
                return (
                  <option key={p.key} value={p.key} disabled={!ok}>
                    {p.label}{ok ? '' : ' (not configured)'}
                  </option>
                );
              })}
            </select>
            <ChevronDown size={14} className="cascade-chevron" aria-hidden />
          </div>
        </label>

        <label className="cascade-field cascade-field-grow cascade-model-field">
          <span className="cascade-label">Model</span>
          <div className="cascade-model-anchor">
            <button
              type="button"
              className={`cascade-trigger${menuOpen ? ' open' : ''}`}
              onClick={() => setMenuOpen(v => !v)}
              aria-expanded={menuOpen}
              aria-haspopup="menu"
            >
              <span className="cascade-trigger-main">
                <span className="cascade-trigger-name">{selected?.display || 'Select model…'}</span>
                {selected?.description && (
                  <span className="cascade-trigger-desc">{selected.description}</span>
                )}
              </span>
              <ChevronDown size={14} className="cascade-chevron" aria-hidden />
            </button>

            {menuOpen && (
              <div className="cascade-menu" role="menu">
              <div className="cascade-menu-tiers">
                {groups.map(({ tier }) => (
                  <button
                    key={tier}
                    type="button"
                    role="menuitem"
                    className={`cascade-tier${activeTier === tier ? ' active' : ''}`}
                    onMouseEnter={() => setActiveTier(tier)}
                    onFocus={() => setActiveTier(tier)}
                    onClick={() => setActiveTier(tier)}
                  >
                    <span>{tierLabels?.[tier] || tier}</span>
                    <ChevronRight size={14} aria-hidden />
                  </button>
                ))}
              </div>
              <div className="cascade-menu-models" role="group" aria-label={tierLabels?.[activeTier] || activeTier}>
                {activeModels.map(m => {
                  const selectable = m.selectable !== false;
                  const isSelected = selectedModel === m.id;
                  return (
                    <button
                      key={m.id}
                      type="button"
                      role="menuitemradio"
                      aria-checked={isSelected}
                      disabled={!selectable}
                      className={`cascade-model${isSelected ? ' selected' : ''}${!selectable ? ' disabled' : ''}`}
                      onClick={() => pickModel(m)}
                    >
                      <span className="cascade-model-name">{m.display}</span>
                      <span className="cascade-model-meta">
                        {m.installed && 'Installed · '}
                        {m.ram_hint && `${m.ram_hint.replace('~', '')} · `}
                        {m.description}
                      </span>
                      {!selectable && m.reason && (
                        <span className="cascade-model-policy">{m.reason}</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          </div>
        </label>
      </div>

      {provider === 'ollama' && providerInfo?.best_installed && (
        <div className="hint cascade-hint">
          Best installed: <code>{providerInfo.best_installed}</code>
        </div>
      )}
    </div>
  );
}
