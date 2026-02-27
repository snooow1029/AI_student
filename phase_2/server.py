from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from pathlib import Path
import os
import uuid
import json
import asyncio
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
# It's a singleton to maintain the semaphore across different HTTP requests
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", "2"))

if not GEMINI_API_KEY:
    print("⚠️  Warning: GEMINI_API_KEY environment variable not set!")

processor = AsyncConcurrentProcessor(api_key=GEMINI_API_KEY, max_concurrent=MAX_CONCURRENT)

# Data models
class AnalysisRequest(BaseModel):
    video_path: str
    title: str
    persona: str
    callback_url: str = None  # Optional: URL to notify when finished

class AnalysisResponse(BaseModel):
    job_id: str
    status: str
    message: str

# In-memory job store (for a real app, use a database)
jobs = {}

async def run_analysis_task(job_id: str, req: AnalysisRequest):
    """Background task to run the actual AI analysis"""
    jobs[job_id]["status"] = "processing"
    jobs[job_id]["start_time"] = datetime.now().isoformat()
    
    video_path = Path(req.video_path)
    
    # Construct the task object expected by batch_audit_processor
    task = VideoTask(
        video_url="",  # Local file, no URL needed
        title=req.title,
        persona=req.persona,
        video_path=video_path
    )
    
    try:
        # Execute the core logic from collaborator's script
        # task_idx and total are set to 1 since we handle them individually here
        print(f"[*] Starting analysis job {job_id} for video: {req.title}")
        result = await processor.process_single_task(task, 1, 1)
        
        if result.get("success"):
            jobs[job_id]["status"] = "completed"
            # Extract scores and results
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
    
    # Optional: Implement callback logic here if req.callback_url is provided
    # if req.callback_url:
    #     async with httpx.AsyncClient() as client:
    #         await client.post(req.callback_url, json=jobs[job_id])

@app.post("/analyze", response_model=AnalysisResponse)
async def create_analysis_job(req: AnalysisRequest, background_tasks: BackgroundTasks):
    """Trigger a new video analysis job"""
    # Basic path validation
    video_path = Path(req.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=400, detail=f"Video file not found at: {req.video_path}")
    
    if not video_path.is_file():
        raise HTTPException(status_code=400, detail="The provided path is not a file")

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "title": req.title,
        "video_path": req.video_path,
        "created_at": datetime.now().isoformat()
    }
    
    # Add to FastAPI background tasks
    background_tasks.add_task(run_analysis_task, job_id, req)
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Analysis job has been queued"
    }

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Check the status and results of a job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.get("/status")
async def system_status():
    """System health check"""
    return {
        "active_jobs": len([j for j in jobs.values() if j["status"] == "processing"]),
        "total_jobs_in_memory": len(jobs),
        "max_concurrent_allowed": MAX_CONCURRENT
    }

if __name__ == "__main__":
    import uvicorn
    # Make sure we are in the right directory to load prompts
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    uvicorn.run(app, host="0.0.0.0", port=8000)
