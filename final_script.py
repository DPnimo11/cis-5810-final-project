from pathlib import Path

from backend.config import load_config
from backend.physics_pipeline import PhysicsPipeline


def main():
    """
    Convenience CLI wrapper that keeps the original sample workflow working.
    """
    config = load_config()
    pipeline = PhysicsPipeline(config)

    job_dir = Path.cwd() / "cli_job"
    objects = {
        "objectA": Path("captured.jpeg").resolve(),
        "objectB": Path("horse.png").resolve(),
    }

    print("\n[>] Gemini: Estimating physics properties...")
    properties = pipeline.analyze_objects(job_dir, objects)

    job_files = {
        "objectA": {"original": str(objects["objectA"]), "clean": None, "model": None},
        "objectB": {"original": str(objects["objectB"]), "clean": None, "model": None},
    }

    print("\n[>] Blender: Generating collision video...")
    video_path = pipeline.generate_collision(job_dir, job_files, properties)
    print(f"\n[Done] Check video at {video_path}")


if __name__ == "__main__":
    main()