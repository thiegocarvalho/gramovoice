import os
import sys
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
from typing import Dict, Any, Optional

from tts_engine import TTSEngine, AVAILABLE_VOICES
from utils import load_settings

def start_api() -> None:
    """Initializes and runs the FastAPI server for GramoVoice."""
    app = FastAPI(title="GramoVoice API")
    settings = load_settings()
    engine = TTSEngine(
        max_chars=settings.get("max_chars", 300),
        default_language=settings.get("language", "pt-br")
    )

    tasks: Dict[str, Dict[str, Any]] = {}
    voice_list = list(AVAILABLE_VOICES.keys())

    @app.get("/")
    async def get_metadata() -> Dict[str, Any]:
        """Provides metadata about the running API server."""
        return {
            "title": "GramoVoice",
            "status": "online",
            "available_voices": voice_list,
            "engine_info": {
                "model": "Kokoro ONNX v1.0",
                "device": engine.device.upper(),
                "max_chars_per_chunk": engine.max_chars,
                "default_language": engine.default_language
            }
        }

    class SynthesisRequest(BaseModel):
        text: str
        project_name: str
        voice: str = "Dora (Feminino)"
        speed: float = 1.0
        language: str = "pt-br"
        chunk_size: int = 300
        webhook_url: Optional[str] = None

    @app.post("/synthesize")
    async def synthesize(req: SynthesisRequest, background_tasks: BackgroundTasks) -> Dict[str, str]:
        """Queues a synthesis task in the background."""
        if not req.text.strip():
            raise HTTPException(status_code=400, detail="Text is required")

        task_id = str(uuid.uuid4())
        output_dir = os.path.join(os.getcwd(), "out")
        os.makedirs(output_dir, exist_ok=True)

        basename = os.path.basename(req.project_name)
        filename = f"{basename}.wav" if not (basename.endswith(".mp3") or basename.endswith(".wav")) else basename
        target_path = os.path.join(output_dir, filename)
        tasks[task_id] = {"status": "processing", "file": filename}

        def run_background_synthesis(tid, r, path):
            engine.max_chars = r.chunk_size
            success = engine.synthesize(
                text=r.text,
                output_path=path,
                speed=r.speed,
                speaker_wav=r.voice,
                language=r.language
            )
            tasks[tid]["status"] = "completed" if success else "failed"

            if r.webhook_url:
                try:
                    import httpx
                    httpx.post(r.webhook_url, json={"task_id": tid, "status": tasks[tid]["status"], "file": r.project_name, "path": path})
                except: pass

        background_tasks.add_task(run_background_synthesis, task_id, req, target_path)
        return {"status": "queued", "task_id": task_id}

    @app.get("/status/{task_id}")
    async def get_status(task_id: str):
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        return tasks[task_id]

    print("Starting GramoVoice API Server...", file=sys.stderr)
    uvicorn.run(app, host="0.0.0.0", port=8000)
