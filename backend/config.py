import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class AppConfig:
    triposr_path: Path
    blender_exec: str
    gemini_api_key: str
    jobs_root: Path
    prompt_temperature: float = 0.2


def load_config() -> AppConfig:
    """
    Load configuration from environment variables (or .env file).
    Raises ValueError when required values are missing.
    """
    load_dotenv()

    root_dir = Path(__file__).resolve().parents[1]

    triposr_path = os.getenv("TRIPOSR_PATH")
    blender_exec = os.getenv("BLENDER_EXEC")
    api_key = os.getenv("GEMINI_API_KEY")
    jobs_root = os.getenv("JOBS_ROOT", root_dir / "jobs")

    missing = []
    if not triposr_path:
        missing.append("TRIPOSR_PATH")
    if not blender_exec:
        missing.append("BLENDER_EXEC")
    if not api_key:
        missing.append("GEMINI_API_KEY")

    if missing:
        joined = ", ".join(missing)
        raise ValueError(
            f"Missing required environment variables: {joined}. "
            "Create a .env file or export them prior to running the server."
        )

    return AppConfig(
        triposr_path=Path(triposr_path).expanduser().resolve(),
        blender_exec=blender_exec,
        gemini_api_key=api_key,
        jobs_root=Path(jobs_root).expanduser().resolve(),
    )

