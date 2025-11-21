from __future__ import annotations

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import AppConfig, load_config
from physics_pipeline import ObjectProperties, PhysicsPipeline, PipelineError


def stage(status: str = "pending", message: str | None = None) -> Dict[str, str | None]:
    return {"status": status, "message": message}


def ensure_jobs_root(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


config: AppConfig = load_config()
pipeline = PhysicsPipeline(config)
ensure_jobs_root(config.jobs_root)

app = Flask(__name__)
CORS(app)

executor = ThreadPoolExecutor(max_workers=1)
jobs_lock = threading.Lock()
jobs: Dict[str, Dict] = {}


def save_job(job: Dict) -> None:
    job_dir = Path(job["dir"])
    job_dir.mkdir(parents=True, exist_ok=True)
    with open(job_dir / "job.json", "w", encoding="utf-8") as handle:
        json.dump(job, handle, indent=2)


def get_job(job_id: str) -> Dict:
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        raise KeyError(f"Job {job_id} not found")
    return job


def create_job(file_a, file_b) -> Dict:
    job_id = uuid.uuid4().hex
    job_dir = config.jobs_root / job_id
    uploads_dir = job_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    def save_file(field_name, file_storage):
        filename = secure_filename(file_storage.filename or f"{field_name}.png")
        if "." not in filename:
            filename = f"{field_name}.png"
        dest = uploads_dir / filename
        file_storage.save(dest)
        return dest

    path_a = save_file("objectA", file_a)
    path_b = save_file("objectB", file_b)

    job = {
        "id": job_id,
        "dir": str(job_dir),
        "status": "uploaded",
        "progress": 10,
        "stages": {
            "upload": stage("completed", "Images uploaded"),
            "analysis": stage(),
            "generation": stage(),
            "render": stage(),
        },
        "files": {
            "objectA": {"original": str(path_a), "clean": None, "model": None},
            "objectB": {"original": str(path_b), "clean": None, "model": None},
        },
        "properties": {"objectA": None, "objectB": None},
        "video_path": None,
        "error": None,
    }

    with jobs_lock:
        jobs[job_id] = job
    save_job(job)
    return job


def serialize_job(job: Dict) -> Dict:
    serialized = {
        k: v
        for k, v in job.items()
        if k
        not in {
            "dir",
            "files",
        }
    }
    serialized["hasVideo"] = bool(job.get("video_path"))
    return serialized


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/upload", methods=["POST"])
def upload():
    file_a = request.files.get("objectA")
    file_b = request.files.get("objectB")
    if not file_a or not file_b:
        return jsonify({"error": "Both objectA and objectB image files are required."}), 400

    job = create_job(file_a, file_b)
    return jsonify({"job": serialize_job(job)})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    job_id = data.get("jobId")
    if not job_id:
        return jsonify({"error": "jobId is required"}), 400

    try:
        job = get_job(job_id)
    except KeyError:
        return jsonify({"error": "Job not found"}), 404

    job["status"] = "analyzing"
    job["stages"]["analysis"] = stage("running", "Analyzing physics properties")
    save_job(job)

    try:
        objects = {
            "objectA": Path(job["files"]["objectA"]["original"]),
            "objectB": Path(job["files"]["objectB"]["original"]),
        }
        props = pipeline.analyze_objects(Path(job["dir"]), objects)

        job["properties"] = {
            key: vars(value) for key, value in props.items()
        }
        job["status"] = "analysis_complete"
        job["progress"] = 50
        job["stages"]["analysis"] = stage("completed", "AI properties detected")
        save_job(job)
        return jsonify({"job": serialize_job(job), "properties": job["properties"]})
    except PipelineError as exc:
        job["status"] = "error"
        job["error"] = str(exc)
        job["stages"]["analysis"] = stage("failed", str(exc))
        save_job(job)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/properties", methods=["POST"])
def update_properties():
    data = request.get_json(silent=True) or {}
    job_id = data.get("jobId")
    properties = data.get("properties")
    if not job_id or not isinstance(properties, dict):
        return jsonify({"error": "jobId and properties are required"}), 400

    try:
        job = get_job(job_id)
    except KeyError:
        return jsonify({"error": "Job not found"}), 404

    job["properties"] = properties
    save_job(job)
    return jsonify({"job": serialize_job(job)})


def schedule_generation(job_id: str) -> None:
    def background():
        try:
            job = get_job(job_id)
        except KeyError:
            return

        def progress(stage_key: str, message: str, percent: float) -> None:
            job["progress"] = percent
            if stage_key in job["stages"]:
                job["stages"][stage_key] = stage("running", message)
            save_job(job)

        job["status"] = "generating"
        job["stages"]["generation"] = stage("running", "Generating 3D meshes")
        job["stages"]["render"] = stage("pending")
        save_job(job)

        try:
            obj_files = {
                "objectA": job["files"]["objectA"],
                "objectB": job["files"]["objectB"],
            }
            props = {
                key: ObjectProperties(**value)
                for key, value in job["properties"].items()
                if value
            }
            if len(props) != 2:
                raise PipelineError("Physics properties missing for one or both objects.")

            video_path = pipeline.generate_collision(
                Path(job["dir"]),
                obj_files,
                props,
                progress,
            )

            job["video_path"] = str(video_path)
            job["status"] = "complete"
            job["progress"] = 100
            job["stages"]["generation"] = stage("completed", "3D meshes ready")
            job["stages"]["render"] = stage("completed", "Render finished")
            save_job(job)
        except PipelineError as exc:
            job["status"] = "error"
            job["error"] = str(exc)
            job["stages"]["generation"] = stage("failed", str(exc))
            job["stages"]["render"] = stage("failed", str(exc))
            save_job(job)

    executor.submit(background)


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    job_id = data.get("jobId")
    if not job_id:
        return jsonify({"error": "jobId is required"}), 400

    try:
        job = get_job(job_id)
    except KeyError:
        return jsonify({"error": "Job not found"}), 404

    if job["status"] in {"generating", "rendering"}:
        return jsonify({"job": serialize_job(job)})

    schedule_generation(job_id)
    return jsonify({"message": "Generation started", "job": serialize_job(job)})


@app.route("/api/status/<job_id>", methods=["GET"])
def status(job_id: str):
    try:
        job = get_job(job_id)
    except KeyError:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"job": serialize_job(job)})


@app.route("/api/video/<job_id>", methods=["GET"])
def video(job_id: str):
    try:
        job = get_job(job_id)
    except KeyError:
        return jsonify({"error": "Job not found"}), 404

    video_path = job.get("video_path")
    if not video_path or not Path(video_path).exists():
        return jsonify({"error": "Video not ready"}), 404

    return send_file(video_path, mimetype="video/mp4")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

