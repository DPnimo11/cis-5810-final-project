/* eslint-disable react/prop-types */
const FIELD_LABELS = {
  mass: { label: "Mass (kg)", min: 0.1, max: 500, step: 0.1 },
  bounciness: { label: "Bounciness", min: 0, max: 0.95, step: 0.05 },
  friction: { label: "Friction", min: 0, max: 1, step: 0.05 },
};

function PropertiesPanel({ properties, disabled, onChange, onSave }) {
  const objectOrder = [
    { key: "objectA", label: "Object A" },
    { key: "objectB", label: "Object B" },
  ];

  return (
    <div
      id="properties-panel-root"
      className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-xl backdrop-blur"
    >
      <div
        id="properties-panel-header"
        className="mb-4 flex flex-wrap items-center justify-between gap-4"
      >
        <div id="properties-panel-title">
          <p className="text-xs uppercase tracking-widest text-brand-400">Step 2</p>
          <h2 className="text-2xl font-semibold text-white">Physics Properties</h2>
          <p className="text-sm text-white/70">
            Review Gemini estimates and fine-tune before simulating.
          </p>
        </div>
        <button
          id="properties-panel-save-button"
          type="button"
          onClick={onSave}
          disabled={disabled}
          className="rounded-full bg-brand-500 px-5 py-2 font-semibold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-white/30"
        >
          Save adjustments
        </button>
      </div>

      <div
        id="properties-panel-grid"
        className="grid gap-4 md:grid-cols-2"
      >
        {objectOrder.map(({ key, label }) => {
          const obj = properties[key] || {};
          return (
            <div
              key={key}
              id={`properties-card-${key}`}
              className="rounded-xl border border-white/10 bg-slate-900/60 p-4"
            >
              <div id={`properties-card-${key}-title`} className="mb-4">
                <p className="text-sm font-semibold text-white">{label}</p>
                <p className="text-xs text-white/60">Facing: {obj.facing}</p>
              </div>

              {Object.entries(FIELD_LABELS).map(([field, meta]) => (
                <div
                  key={field}
                  id={`properties-card-${key}-${field}`}
                  className="mb-3"
                >
                  <label
                    htmlFor={`${key}-${field}`}
                    className="block text-xs uppercase tracking-wide text-white/70"
                  >
                    {meta.label}
                  </label>
                  <input
                    id={`${key}-${field}`}
                    type="number"
                    min={meta.min}
                    max={meta.max}
                    step={meta.step}
                    value={obj[field] ?? ""}
                    disabled={disabled}
                    onChange={(event) =>
                      onChange(key, field, parseFloat(event.target.value))
                    }
                    className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900/80 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
                  />
                </div>
              ))}

              <div id={`properties-card-${key}-facing`} className="mb-2">
                <label
                  htmlFor={`${key}-facing`}
                  className="block text-xs uppercase tracking-wide text-white/70"
                >
                  Facing Direction
                </label>
                <select
                  id={`${key}-facing`}
                  value={obj.facing || "front"}
                  disabled={disabled}
                  onChange={(event) => onChange(key, "facing", event.target.value)}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-slate-900/80 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
                >
                  <option value="front">Front</option>
                  <option value="left">Left</option>
                  <option value="right">Right</option>
                </select>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default PropertiesPanel;

