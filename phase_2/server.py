from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from pathlib import Path
import os
import uuid
import json
import asyncio
import requests
from datetime import datetime

# Import core logic from the original script
try:
    from batch_audit_processor import AsyncConcurrentProcessor, VideoTask
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from batch_audit_processor import AsyncConcurrentProcessor, VideoTask

app = FastAPI(title="AI Video Student Auditor API")

# Initialize the global processor
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", "2"))

if not GEMINI_API_KEY:
    print("⚠️  Warning: GEMINI_API_KEY environment variable not set!")

processor = AsyncConcurrentProcessor(api_key=GEMINI_API_KEY, max_concurrent=MAX_CONCURRENT)

# Data models
class AnalysisRequest(BaseModel):
    video_path: str # Can be local path or URL
    title: str
    persona: str
    callback_url: str = None

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
    
    video_input = req.video_path
    local_path = None
    
    # 1. Handle URL input: Download if it's a web link
    if video_input.startswith("http"):
        print(f"[*] Downloading video from URL: {video_input}")
        try:
            temp_dir = Path("temp_audit")
            temp_dir.mkdir(exist_ok=True)
            
            # Generate a unique filename to avoid collisions
            ext = os.path.splitext(video_input.split("?")[0])[1] or ".mp4"
            local_path = temp_dir / f"{job_id}{ext}"
            
            # Synchronous download (simplified for this task)
            with requests.get(video_input, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            print(f"[✓] Downloaded to: {local_path}")
            video_fs_path = local_path
        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = f"Download failed: {str(e)}"
            return
    else:
        # Local file path
        video_fs_path = Path(video_input)

    # 2. Start Analysis
    task = VideoTask(
        video_url="", 
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
    
    # 3. Cleanup local temp file if downloaded
    if local_path and local_path.exists():
        try:
            os.remove(local_path)
            print(f"[*] Cleaned up temp file: {local_path}")
        except:
            pass

    jobs[job_id]["end_time"] = datetime.now().isoformat()

@app.post("/analyze", response_model=AnalysisResponse)
async def create_analysis_job(req: AnalysisRequest, background_tasks: BackgroundTasks):
    """Trigger a new video analysis job"""
    # Validation
    if not req.video_path.startswith("http"):
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
