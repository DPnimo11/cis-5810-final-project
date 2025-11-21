/* eslint-disable react/prop-types */
const STAGE_ORDER = [
  { key: "upload", label: "Upload" },
  { key: "analysis", label: "Analysis" },
  { key: "generation", label: "3D Models" },
  { key: "render", label: "Render" },
];

function ProgressTracker({ stages = {}, progress = 0 }) {
  return (
    <div
      id="progress-panel"
      className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-lg backdrop-blur"
    >
      <div
        id="progress-panel-header"
        className="mb-4 flex flex-wrap items-end justify-between gap-4"
      >
        <div id="progress-panel-title">
          <p className="text-xs uppercase tracking-widest text-brand-400">Step 3</p>
          <h2 className="text-2xl font-semibold text-white">Pipeline Progress</h2>
          <p className="text-sm text-white/70">
            Generation & rendering stages update automatically.
          </p>
        </div>
        <div id="progress-panel-meter" className="text-right">
          <p className="text-sm text-white/70">Overall progress</p>
          <p className="text-3xl font-bold text-white">{Math.round(progress)}%</p>
        </div>
      </div>

      <div
        id="progress-panel-grid"
        className="grid gap-3 md:grid-cols-4"
      >
        {STAGE_ORDER.map(({ key, label }) => {
          const stageData = stages[key] || {};
          const status = stageData.status || "pending";
          const message = stageData.message || "Waiting to start";
          const isDone = status === "completed";
          const isRunning = status === "running";

          return (
            <div
              key={key}
              id={`progress-card-${key}`}
              className={`rounded-xl border p-4 ${
                isDone
                  ? "border-emerald-400/60 bg-emerald-500/10"
                  : isRunning
                    ? "border-brand-500/60 bg-brand-500/10"
                    : "border-white/10 bg-slate-900/60"
              }`}
            >
              <div id={`progress-card-${key}-header`} className="mb-2">
                <p className="text-sm font-semibold text-white">{label}</p>
                <p className="text-xs uppercase tracking-wide text-white/60">
                  {status}
                </p>
              </div>
              <div id={`progress-card-${key}-message`} className="text-xs text-white/80">
                {message}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ProgressTracker;

