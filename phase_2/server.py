from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import os
import uuid
import asyncio
import hashlib
import urllib.request
from datetime import datetime

# Import core logic from the original script
try:
    from batch_audit_processor import AsyncConcurrentProcessor, VideoTask, TEMP_DOWNLOAD_DIR
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from batch_audit_processor import AsyncConcurrentProcessor, VideoTask, TEMP_DOWNLOAD_DIR


def is_video_url(s: str) -> bool:
    """Check if input is an HTTP/HTTPS URL (vs local file path)."""
    s = (s or "").strip()
    return s.startswith("http://") or s.startswith("https://")


async def download_http_video(url: str) -> Path:
    """Download video from HTTP/HTTPS URL to temp directory. Returns local Path."""
    print(f"   Downloading: {url[:80]}...")
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    ext = ".mp4"  # default; could parse from URL if needed
    out_path = TEMP_DOWNLOAD_DIR / f"{url_hash}{ext}"
    if out_path.exists():
        return out_path
    TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def _download():
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0",
            "Referer": url.rsplit("/", 1)[0] + "/",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            with open(out_path, "wb") as f:
                f.write(resp.read())

    await asyncio.to_thread(_download)
    if not out_path.exists():
        raise RuntimeError(f"Download failed: {url}")
    return out_path

app = FastAPI(title="AI Video Student Auditor API")

# Initialize the global processor
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", "2"))

if not GEMINI_API_KEY:
    print("⚠️  Warning: GEMINI_API_KEY environment variable not set!")

processor = AsyncConcurrentProcessor(api_key=GEMINI_API_KEY, max_concurrent=MAX_CONCURRENT)

# Data models
class AnalysisRequest(BaseModel):
    video_path: str  # Local file path OR HTTP/HTTPS URL
    title: str
    persona: str
    callback_url: Optional[str] = None

class AnalysisResponse(BaseModel):
    job_id: str
    status: str
    message: str

# In-memory job store
jobs = {}

async def run_analysis_task(job_id: str, req: AnalysisRequest):
    """Background task to run the actual AI analysis"""
    jobs[job_id]["status"] = "processing"
    jobs[job_id]["start_time"] = datetime.now().isoformat()
    print(f"[*] Job {job_id} started: {req.title}")

    try:
        if is_video_url(req.video_path):
            print(f"[*] Job {job_id} downloading from URL...")
            video_fs_path = await download_http_video(req.video_path)
            print(f"[*] Job {job_id} download complete: {video_fs_path.name}")
        else:
            video_fs_path = Path(req.video_path).resolve()
            if not video_fs_path.exists():
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["error"] = f"Local file not found: {video_fs_path}"
                return
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        print(f"[✗] Job {job_id} failed (download/prep): {e}")
        return

    # Start Analysis
    task = VideoTask(
        video_url=req.video_path if is_video_url(req.video_path) else "",
        title=req.title,
        persona=req.persona,
        video_path=video_fs_path
    )
    
    try:
        print(f"[*] Starting analysis job {job_id} for video: {req.title}")
        result = await processor.process_single_task(task, 1, 1)
        
        if result.get("success"):
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = {
                "scores": result.get("scores"),
                "agent1_analysis": result.get("agent1_result"),
                "agent2_report": result.get("agent2_result"),
                "agent3_simulation": result.get("agent3_result")
            }
            print(f"[✓] Job {job_id} completed successfully")
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = result.get("error", "Unknown error")
            print(f"[✗] Job {job_id} failed: {jobs[job_id]['error']}")
            
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        print(f"[✗] Job {job_id} crashed: {e}")

    jobs[job_id]["end_time"] = datetime.now().isoformat()

@app.post("/analyze", response_model=AnalysisResponse)
async def create_analysis_job(req: AnalysisRequest, background_tasks: BackgroundTasks):
    """Trigger a new video analysis job. video_path can be a local file path or HTTP/HTTPS URL."""
    if not is_video_url(req.video_path):
        video_path = Path(req.video_path)
        if not video_path.exists():
            raise HTTPException(status_code=400, detail=f"Local file not found: {req.video_path}")

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "title": req.title,
        "video_path": req.video_path,
        "created_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(run_analysis_task, job_id, req)
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Analysis job has been queued"
    }

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.get("/status")
async def system_status():
    return {
        "active_jobs": len([j for j in jobs.values() if j["status"] == "processing"]),
        "total_jobs_in_memory": len(jobs),
        "max_concurrent_allowed": MAX_CONCURRENT
    }

if __name__ == "__main__":
    import uvicorn
    file_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(file_dir)
    uvicorn.run(app, host="0.0.0.0", port=8000)
