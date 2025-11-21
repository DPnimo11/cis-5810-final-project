from __future__ import annotations

import base64
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Literal, Mapping

import requests
from rembg import remove

from config import AppConfig


class PipelineError(RuntimeError):
    """Raised when any stage of the processing pipeline fails."""


ObjectKey = Literal["objectA", "objectB"]


@dataclass
class ObjectProperties:
    mass: float
    bounciness: float
    friction: float
    facing: str

    @classmethod
    def from_raw(cls, data: Mapping) -> "ObjectProperties":
        return cls(
            mass=float(data.get("mass", 1.0)),
            bounciness=float(data.get("bounciness", 0.5)),
            friction=float(data.get("friction", 0.5)),
            facing=str(data.get("facing", "front")),
        )


ProgressCallback = Callable[[str, str, float], None]


class PhysicsPipeline:
    """
    Wraps Gemini analysis, TripoSR mesh generation, and Blender rendering.
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.blender_script = Path(__file__).resolve().parents[1] / "final_blender.py"
        if not self.blender_script.exists():
            raise PipelineError(
                f"Blender script not found at {self.blender_script}. "
                "Ensure final_blender.py exists in the project root."
            )

    @staticmethod
    def _emit(
        callback: ProgressCallback | None, stage: str, message: str, percent: float
    ) -> None:
        if callback:
            callback(stage, message, percent)

    def analyze_objects(
        self,
        job_dir: Path,
        objects: Dict[ObjectKey, Path],
        on_progress: ProgressCallback | None = None,
    ) -> Dict[ObjectKey, ObjectProperties]:
        job_dir.mkdir(parents=True, exist_ok=True)
        results: Dict[ObjectKey, ObjectProperties] = {}

        for idx, (key, image_path) in enumerate(objects.items()):
            image_path = Path(image_path)
            if not image_path.exists():
                raise PipelineError(f"{key} image not found at {image_path}")

            message = f"Analyzing {image_path.name}"
            percent = 20 + (idx * 10)
            self._emit(on_progress, "analysis", message, percent)
            analysis = self._get_physics_gemini_rest(image_path)
            results[key] = ObjectProperties.from_raw(analysis)

        self._emit(on_progress, "analysis", "Analysis complete", 50)
        return results

    def generate_collision(
        self,
        job_dir: Path,
        objects: Dict[ObjectKey, Dict[str, str | None]],
        properties: Dict[ObjectKey, ObjectProperties],
        on_progress: ProgressCallback | None = None,
    ) -> Path:
        job_dir = Path(job_dir)
        job_dir.mkdir(parents=True, exist_ok=True)

        mesh_paths: Dict[ObjectKey, Path] = {}

        for index, key in enumerate(["objectA", "objectB"]):
            obj_info = objects[key]
            original_path = Path(obj_info["original"])
            if not original_path.exists():
                raise PipelineError(f"{key} original image missing at {original_path}")

            obj_dir = job_dir / key
            obj_dir.mkdir(exist_ok=True)
            clean_path = obj_dir / "clean.png"
            mesh_dir = obj_dir / "mesh"

            self._emit(on_progress, "generation", f"Cleaning {key}", 55 + (index * 5))
            cleaned = self._clean_background(original_path, clean_path)
            obj_info["clean"] = str(cleaned)

            self._emit(on_progress, "generation", f"Generating mesh for {key}", 65 + (index * 10))
            mesh = self._generate_3d_model(cleaned, mesh_dir)
            obj_info["model"] = str(mesh)
            mesh_paths[key] = mesh

        self._emit(on_progress, "render", "Running Blender simulation", 90)
        video_path = job_dir / "output_collision.mp4"
        self._run_blender(mesh_paths, properties, video_path, cwd=job_dir)
        self._emit(on_progress, "render", "Render complete", 100)
        return video_path

    # --- Helper functions adopted from the original CLI script ---

    def _clean_background(self, input_path: Path, output_path: Path) -> Path:
        try:
            with open(input_path, "rb") as input_file:
                input_data = input_file.read()
            output_data = remove(input_data)
            with open(output_path, "wb") as handle:
                handle.write(output_data)
            return output_path
        except Exception as exc:
            raise PipelineError(f"Background removal failed for {input_path}: {exc}") from exc

    def _get_physics_gemini_rest(self, image_path: Path) -> Dict:
        with open(image_path, "rb") as handle:
            b64_data = base64.b64encode(handle.read()).decode("utf-8")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-2.5-flash:generateContent"
            f"?key={self.config.gemini_api_key}"
        )

        prompt_text = """
        Look at this object. Estimate its physics properties and visual orientation.
        Return ONLY a raw JSON object (no markdown) with these keys:
        "mass": number (kg),
        "bounciness": number (0.0 to 0.95),
        "friction": number (0.0 to 1.0),
        "facing": string (one of: "left", "right", "front").

        Note: If the object is facing the left side of the image, return "left".
        If it faces the right side, return "right".
        """

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt_text},
                        {"inline_data": {"mime_type": "image/png", "data": b64_data}},
                    ]
                }
            ]
        }

        try:
            response = requests.post(
                url, json=payload, headers={"Content-Type": "application/json"}, timeout=120
            )
            response.raise_for_status()
            result = response.json()
            text_content = result["candidates"][0]["content"]["parts"][0]["text"]
            clean_json = (
                text_content.replace("```json", "").replace("```", "").strip()
            )
            return json.loads(clean_json)
        except Exception as exc:
            print(f"[!] Gemini API issue ({exc}); using fallback defaults.")
            return {"mass": 1.0, "bounciness": 0.5, "friction": 0.5, "facing": "front"}

    def _generate_3d_model(self, image_path: Path, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [
                    "python",
                    "run.py",
                    str(image_path),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=self.config.triposr_path,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise PipelineError(f"TripoSR failed: {exc}") from exc

        expected_mesh = output_dir / "0" / "mesh.obj"
        if not expected_mesh.exists():
            raise PipelineError(f"Mesh not found at {expected_mesh}")
        return expected_mesh

    def _run_blender(
        self,
        meshes: Dict[ObjectKey, Path],
        properties: Dict[ObjectKey, ObjectProperties],
        output_path: Path,
        cwd: Path | None = None,
    ) -> None:
        args = [
            str(meshes["objectA"]),
            str(properties["objectA"].mass),
            str(properties["objectA"].bounciness),
            str(properties["objectA"].friction),
            str(properties["objectA"].facing),
            str(meshes["objectB"]),
            str(properties["objectB"].mass),
            str(properties["objectB"].bounciness),
            str(properties["objectB"].friction),
            str(properties["objectB"].facing),
        ]
        try:
            subprocess.run(
                [
                    self.config.blender_exec,
                    "--background",
                    "--python",
                    str(self.blender_script),
                    "--",
                    *args,
                ],
                cwd=str(cwd or output_path.parent),
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise PipelineError(f"Blender render failed: {exc}") from exc

        if not output_path.exists():
            raise PipelineError(f"Expected render output at {output_path} but file not found.")

