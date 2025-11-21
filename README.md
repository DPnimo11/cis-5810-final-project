# cis-5810-final-project

Local-first web demo for our CIS 5810 final project. Two images are uploaded, Gemini estimates physics properties, TripoSR creates meshes, and Blender renders a collision video that can be streamed/downloaded from the browser.

## Stack

- **Python / Flask** backend with job queue + progress tracking
- **React + Vite + Tailwind** single-page UI
- **TripoSR** (local run) for mesh generation
- **Blender 4.2** (headless) for physics/rendering
- **Google Gemini** API for property estimation

## Prerequisites

- Python 3.10+
- Node.js 18+
- Blender 4.2 installed locally
- TripoSR repo cloned locally (keep note of its absolute path)
- Gemini API key (free tier works)

## Setup

1. Install Python dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   ```

2. Install frontend dependencies (first run only):

   ```bash
   cd frontend
   npm install
   cd ..
   ```

3. Configure environment variables:

   ```bash
   cp .env.example .env
   # edit .env to point to your TRIPOSR_PATH, BLENDER_EXEC, GEMINI_API_KEY, JOBS_ROOT
   ```

   - `TRIPOSR_PATH` → absolute path to the TripoSR repo
   - `BLENDER_EXEC` → absolute path to Blender binary (e.g., `/Applications/Blender.app/Contents/MacOS/Blender`)
   - `GEMINI_API_KEY` → API key from Google AI Studio
   - `JOBS_ROOT` → absolute path where uploads/renders are stored (`/path/to/project/jobs`)

## Running locally

The `start.sh` helper launches both backend and frontend (backend first, frontend in the foreground). It also installs frontend dependencies automatically if needed.

```bash
./start.sh
```

- Backend: http://localhost:5000
- Frontend dev server: http://localhost:5173 (uses `VITE_API_URL` env if you want to point elsewhere)

If you prefer manual control:

```bash
# Terminal 1
cd backend
python app.py

# Terminal 2
cd frontend
VITE_API_URL=http://localhost:5000 npm run dev
```

## API overview

| Method | Endpoint              | Purpose                              |
| ------ | --------------------- | ------------------------------------ |
| POST   | `/api/upload`         | Upload two images, returns `jobId`   |
| POST   | `/api/analyze`        | Run Gemini analysis                  |
| POST   | `/api/properties`     | Persist edited physics properties    |
| POST   | `/api/generate`       | Start TripoSR + Blender pipeline     |
| GET    | `/api/status/<jobId>` | Poll stage + percent progress        |
| GET    | `/api/video/<jobId>`  | Stream/download rendered MP4         |

Job folders (`jobs/<id>`) store uploads, meshes, and the final video (`output_collision.mp4`).

## Frontend workflow

1. Drag/drop or browse for two object images.
2. Click **Upload & Analyze** → backend saves files and calls Gemini.
3. Fine-tune mass, friction, bounciness, facing direction from the properties panel.
4. Click **Generate Simulation** to kick off TripoSR + Blender.
5. Watch the progress tracker advance; once complete the MP4 plays inline and can be downloaded.

## Notes

- All processing runs locally; ensure Blender and TripoSR are installed.
- The backend expects Blender to run headless; if it pops a window, disable GPU in Blender preferences or use the command line flag to force background.
- Jobs can be cleaned by deleting the `jobs/` directory (ignored via `.gitignore`). 