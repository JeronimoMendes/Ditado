import os
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from providers import DeepgramProvider, TranscriptResult, TranscriptionProvider

app = FastAPI()

jobs: dict[str, dict] = {}

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def get_provider() -> TranscriptionProvider:
    name = os.environ.get("TRANSCRIPTION_PROVIDER", "deepgram")
    if name == "deepgram":
        return DeepgramProvider()
    raise ValueError(f"Unknown transcription provider: {name}")


provider = get_provider()


async def process_transcription(job_id: str, audio_data: bytes, filename: str) -> None:
    jobs[job_id]["status"] = "processing"
    try:
        result = await provider.transcribe(audio_data, filename)
        jobs[job_id]["status"] = "done"
        jobs[job_id]["result"] = result
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


@app.post("/api/transcribe")
async def transcribe(file: UploadFile, background_tasks: BackgroundTasks) -> dict:
    audio_data = await file.read()
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending"}
    background_tasks.add_task(process_transcription, job_id, audio_data, file.filename or "audio")
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
async def status(job_id: str) -> dict:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    resp = {"job_id": job_id, "status": job["status"]}
    if job["status"] == "error":
        resp["error"] = job.get("error", "Unknown error")
    return resp


@app.get("/api/result/{job_id}")
async def result(job_id: str) -> dict:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    if job["status"] != "done":
        raise HTTPException(status_code=400, detail=f"Job status: {job['status']}")
    tr: TranscriptResult = job["result"]
    return {"job_id": job_id, "utterances": [asdict(u) for u in tr.utterances]}


def format_timestamp(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


@app.get("/api/result/{job_id}/download")
async def download(job_id: str) -> PlainTextResponse:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    if job["status"] != "done":
        raise HTTPException(status_code=400, detail=f"Job status: {job['status']}")
    tr: TranscriptResult = job["result"]
    lines = [
        f"[{format_timestamp(u.start)}] Speaker {u.speaker + 1}: {u.text}"
        for u in tr.utterances
    ]
    text = "\n".join(lines)
    return PlainTextResponse(
        text,
        headers={"Content-Disposition": f"attachment; filename=transcript-{job_id[:8]}.txt"},
    )


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
