import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import ImageUpload from "./components/ImageUpload.jsx";
import PropertiesPanel from "./components/PropertiesPanel.jsx";
import ProgressTracker from "./components/ProgressTracker.jsx";
import VideoPlayer from "./components/VideoPlayer.jsx";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

const BASE_PROPERTIES = {
  objectA: { mass: 1, bounciness: 0.5, friction: 0.5, facing: "front" },
  objectB: { mass: 1, bounciness: 0.5, friction: 0.5, facing: "front" },
};

const createDefaultProperties = () => ({
  objectA: { ...BASE_PROPERTIES.objectA },
  objectB: { ...BASE_PROPERTIES.objectB },
});

function App() {
  const [files, setFiles] = useState({ objectA: null, objectB: null });
  const [previews, setPreviews] = useState({ objectA: null, objectB: null });
  const [job, setJob] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [properties, setProperties] = useState(() => createDefaultProperties());
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [polling, setPolling] = useState(false);
  const [videoUrl, setVideoUrl] = useState(null);
  const [error, setError] = useState(null);
  const [statusMessage, setStatusMessage] = useState("Upload two objects to begin.");

  const canUpload = files.objectA && files.objectB && !isAnalyzing && !isGenerating;

  useEffect(() => {
    return () => {
      Object.values(previews).forEach((url) => url && URL.revokeObjectURL(url));
    };
  }, [previews]);

  useEffect(() => {
    if (!polling || !jobId) return undefined;

    const fetchStatus = async () => {
      try {
        const { data } = await axios.get(`${API_BASE_URL}/api/status/${jobId}`);
        setJob(data.job);

        if (data.job.status === "complete" && data.job.hasVideo) {
          setVideoUrl(`${API_BASE_URL}/api/video/${jobId}?t=${Date.now()}`);
          setStatusMessage("Render complete!");
          setIsGenerating(false);
          setPolling(false);
        } else if (data.job.status === "error") {
          setError(data.job.error || "Processing failed.");
          setIsGenerating(false);
          setPolling(false);
        }
      } catch (statusError) {
        console.error(statusError);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 2500);
    return () => clearInterval(interval);
  }, [polling, jobId]);

  const handleFileSelect = (objectKey, file) => {
    setError(null);
    setVideoUrl(null);
    setJob(null);
    setJobId(null);
    setProperties(createDefaultProperties());
    setFiles((prev) => ({ ...prev, [objectKey]: file }));
    setPreviews((prev) => {
      if (prev[objectKey]) URL.revokeObjectURL(prev[objectKey]);
      return { ...prev, [objectKey]: URL.createObjectURL(file) };
    });
  };

  const handleUploadAndAnalyze = async () => {
    if (!canUpload) return;
    try {
      setError(null);
      setStatusMessage("Uploading images...");
      const formData = new FormData();
      formData.append("objectA", files.objectA);
      formData.append("objectB", files.objectB);

      const { data } = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setJob(data.job);
      setJobId(data.job.id);

      setIsAnalyzing(true);
      setStatusMessage("Analyzing physics properties with Gemini...");
      const analysis = await axios.post(`${API_BASE_URL}/api/analyze`, {
        jobId: data.job.id,
      });
      setProperties(analysis.data.properties);
      setJob(analysis.data.job);
      setIsAnalyzing(false);
      setStatusMessage("Properties ready. Adjust if needed.");
    } catch (uploadError) {
      console.error(uploadError);
      setError(uploadError.response?.data?.error || uploadError.message);
      setIsAnalyzing(false);
    }
  };

  const handlePropertyChange = (objectKey, field, value) => {
    setProperties((prev) => ({
      ...prev,
      [objectKey]: {
        ...prev[objectKey],
        [field]: value,
      },
    }));
  };

  const handleSaveProperties = async () => {
    if (!jobId) return;
    try {
      await axios.post(`${API_BASE_URL}/api/properties`, {
        jobId,
        properties,
      });
      setStatusMessage("Properties saved.");
    } catch (saveError) {
      console.error(saveError);
      setError(saveError.response?.data?.error || saveError.message);
    }
  };

  const handleGenerate = async () => {
    if (!jobId) {
      setError("Upload and analyze objects first.");
      return;
    }

    try {
      setError(null);
      setStatusMessage("Starting mesh generation...");
      setIsGenerating(true);
      await axios.post(`${API_BASE_URL}/api/properties`, {
        jobId,
        properties,
      });
      await axios.post(`${API_BASE_URL}/api/generate`, { jobId });
      setPolling(true);
    } catch (genError) {
      console.error(genError);
      setError(genError.response?.data?.error || genError.message);
      setIsGenerating(false);
    }
  };

  const stages = useMemo(() => job?.stages || {}, [job]);

  return (
    <div id="app-root" className="relative min-h-screen bg-slate-950 text-white">
      <div
        id="app-background"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.35),_transparent_55%)]"
      />
      <div id="app-overlay" className="relative z-10">
        <header id="app-header" className="mx-auto max-w-6xl px-6 py-10">
          <div
            id="app-hero"
            className="rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900/80 via-slate-900/40 to-brand-700/20 p-10 shadow-2xl"
          >
            <p className="text-sm uppercase tracking-[0.4em] text-brand-200">
              CIS 5810 · Final Project
            </p>
            <h1 className="mt-4 text-4xl font-bold text-white md:text-5xl">
              3D Physics Collision Sandbox
            </h1>
            <p className="mt-3 max-w-2xl text-lg text-white/80">
              Upload two objects, let Gemini guess their physics, tweak settings, and
              watch Blender render the impact — all from your browser.
            </p>
            <div
              id="status-banner"
              className="mt-6 rounded-2xl bg-black/30 p-4 text-sm text-white/80"
            >
              {statusMessage}
            </div>
            {error && (
              <div
                id="error-banner"
                className="mt-3 rounded-2xl bg-red-500/20 p-4 text-sm text-red-200"
              >
                {error}
              </div>
            )}
          </div>
        </header>

        <main id="app-main" className="mx-auto max-w-6xl space-y-10 px-6 pb-16">
          <div
            id="upload-section"
            className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-xl backdrop-blur"
          >
            <div
              id="upload-section-header"
              className="mb-6 flex flex-wrap items-center justify-between gap-4"
            >
              <div id="upload-section-title">
                <p className="text-xs uppercase tracking-widest text-brand-400">
                  Step 1
                </p>
                <h2 className="text-2xl font-semibold text-white">Upload Objects</h2>
                <p className="text-sm text-white/70">
                  PNG or JPG up to ~5MB works best. Background removal happens
                  automatically.
                </p>
              </div>
              <button
                id="upload-section-button"
                type="button"
                onClick={handleUploadAndAnalyze}
                disabled={!canUpload}
                className="rounded-full bg-brand-500 px-6 py-3 font-semibold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-white/20"
              >
                {isAnalyzing ? "Analyzing..." : "Upload & Analyze"}
              </button>
            </div>

            <div
              id="upload-section-grid"
              className="grid gap-6 md:grid-cols-2"
            >
              <ImageUpload
                objectKey="objectA"
                label="Object A (moves left to right)"
                file={files.objectA}
                preview={previews.objectA}
                onFileSelect={handleFileSelect}
              />
              <ImageUpload
                objectKey="objectB"
                label="Object B (moves right to left)"
                file={files.objectB}
                preview={previews.objectB}
                onFileSelect={handleFileSelect}
              />
            </div>
          </div>

          <PropertiesPanel
            properties={properties}
            disabled={!jobId || isAnalyzing}
            onChange={handlePropertyChange}
            onSave={handleSaveProperties}
          />

          <div
            id="generation-controls"
            className="rounded-2xl border border-white/10 bg-white/5 p-6 text-center shadow-lg backdrop-blur"
          >
            <p className="text-sm text-white/70">
              Ready to see the collision? This step runs TripoSR + Blender locally.
            </p>
            <button
              id="generate-button"
              type="button"
              onClick={handleGenerate}
              disabled={!jobId || isGenerating}
              className="mt-4 rounded-full bg-emerald-500 px-8 py-3 font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-white/20"
            >
              {isGenerating ? "Generating..." : "Generate Simulation"}
            </button>
          </div>

          <ProgressTracker stages={stages} progress={job?.progress || 0} />

          <VideoPlayer videoUrl={videoUrl} jobId={jobId} isGenerating={isGenerating} />
        </main>
      </div>
    </div>
  );
}

export default App;

