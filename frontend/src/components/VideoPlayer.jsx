/* eslint-disable react/prop-types */
function VideoPlayer({ videoUrl, jobId, isGenerating }) {
  return (
    <div
      id="video-panel"
      className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-lg backdrop-blur"
    >
      <div
        id="video-panel-header"
        className="mb-4 flex flex-wrap items-center justify-between gap-4"
      >
        <div id="video-panel-title">
          <p className="text-xs uppercase tracking-widest text-brand-400">Step 4</p>
          <h2 className="text-2xl font-semibold text-white">Simulation Output</h2>
          <p className="text-sm text-white/70">
            Preview and download the rendered collision clip.
          </p>
        </div>
        <div id="video-panel-meta" className="text-right">
          <p className="text-xs text-white/60">Job ID</p>
          <p className="font-mono text-sm text-white">{jobId || "—"}</p>
        </div>
      </div>

      {videoUrl ? (
        <div id="video-panel-player" className="rounded-xl border border-white/10 bg-black/60 p-4">
          <video
            id="simulation-video"
            key={videoUrl}
            src={videoUrl}
            controls
            className="h-64 w-full rounded-lg bg-black"
          />
          <a
            id="video-download-link"
            href={videoUrl}
            download={`collision-${jobId || "demo"}.mp4`}
            className="mt-4 inline-flex rounded-full bg-brand-500 px-6 py-2 font-semibold text-white transition hover:bg-brand-600"
          >
            Download video
          </a>
        </div>
      ) : (
        <div
          id="video-panel-placeholder"
          className="rounded-xl border border-dashed border-white/10 p-6 text-center text-white/70"
        >
          {isGenerating
            ? "Rendering in Blender... this can take up to a minute."
            : "Start a simulation to see the rendered clip here."}
        </div>
      )}
    </div>
  );
}

export default VideoPlayer;

