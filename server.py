"""
FastAPI backend server for the AI CV Screener application.
Provides REST API endpoints for the frontend to interact with the pipeline.
"""
import os
import sys
import json
import uuid
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import run_pipeline, build_pipeline
from state.shared_state import MASState

# ─────────────────────────────────────────────
# FastAPI App Setup
# ─────────────────────────────────────────────

app = FastAPI(
    title="AI CV Screener API",
    description="REST API for the AI CV Screener Multi-Agent System",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Directories
# ─────────────────────────────────────────────

UPLOAD_DIR = Path("data/uploads")
CV_DIR = Path("data/cvs")
OUTPUT_DIR = Path("outputs")

# Create directories if they don't exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CV_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# ─────────────────────────────────────────────
# In-memory state for pipeline runs
# ─────────────────────────────────────────────

pipeline_runs: dict[str, dict] = {}

# ─────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────

class JobDescriptionInput(BaseModel):
    job_id: Optional[str] = None
    title: str
    required_skills: list[str]
    preferred_skills: list[str] = []
    min_experience_years: float
    education_requirement: str
    description: str


class PipelineRequest(BaseModel):
    job_description: JobDescriptionInput


class PipelineResponse(BaseModel):
    run_id: str
    status: str
    message: str


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    progress: str
    result: Optional[dict] = None
    error: Optional[str] = None


# ─────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────

def generate_job_id() -> str:
    """Generate a unique job ID."""
    return f"job_{uuid.uuid4().hex[:8]}"


def save_job_description(job_data: JobDescriptionInput) -> str:
    """Save job description to JSON file and return path."""
    if not job_data.job_id:
        job_data.job_id = generate_job_id()
    
    job_path = UPLOAD_DIR / f"job_{job_data.job_id}.json"
    job_dict = job_data.model_dump()
    
    with open(job_path, "w", encoding="utf-8") as f:
        json.dump(job_dict, f, indent=4)
    
    return str(job_path)


def run_pipeline_async(run_id: str, job_path: str, cv_path: str):
    """Run the pipeline in a blocking manner (for async tasks)."""
    try:
        pipeline_runs[run_id]["status"] = "processing"
        pipeline_runs[run_id]["progress"] = "Initializing pipeline..."
        
        # Build and run pipeline
        app_pipeline = build_pipeline()
        
        # Load job description
        with open(job_path, "r", encoding="utf-8") as f:
            job_description = json.load(f)
        
        initial_state: MASState = {
            "job_description_path": job_path,
            "cv_folder_path": str(cv_path),
            "job_description": job_description,
            "candidate_profiles": [],
            "match_results": [],
            "ranked_candidates": [],
            "executive_summary": None,
            "report_path": None,
            "logs": [],
            "errors": [],
        }
        
        # Run pipeline with progress updates
        pipeline_runs[run_id]["progress"] = "Agent 1: Parsing CVs..."
        
        # Custom streaming by running agents one by one
        state = initial_state
        
        # Agent 1: Parser
        from agents.parser_agent import run_document_parser
        state = run_document_parser(state)
        pipeline_runs[run_id]["candidate_profiles"] = state.get("candidate_profiles", [])
        pipeline_runs[run_id]["progress"] = f"Agent 1: Parsed {len(state.get('candidate_profiles', []))} CVs"
        
        # Agent 2: Job Matcher
        from agents.job_matcher_agent import run_job_matcher_agent
        state = run_job_matcher_agent(state)
        pipeline_runs[run_id]["match_results"] = state.get("match_results", [])
        pipeline_runs[run_id]["progress"] = f"Agent 2: Scored {len(state.get('match_results', []))} candidates"
        
        # Agent 3: Ranker
        from agents.ranker_agent import run_candidate_ranker
        state = run_candidate_ranker(state)
        pipeline_runs[run_id]["ranked_candidates"] = state.get("ranked_candidates", [])
        pipeline_runs[run_id]["executive_summary"] = state.get("executive_summary")
        pipeline_runs[run_id]["progress"] = f"Agent 3: Ranked {len(state.get('ranked_candidates', []))} candidates"
        
        # Agent 4: Report Generator
        from agents.report_generator import run_report_generator
        state = run_report_generator(state)
        pipeline_runs[run_id]["report_path"] = state.get("report_path")
        pipeline_runs[run_id]["progress"] = "Agent 4: Report generated"
        
        pipeline_runs[run_id]["status"] = "completed"
        pipeline_runs[run_id]["result"] = {
            "job_description": state.get("job_description"),
            "candidate_profiles": state.get("candidate_profiles", []),
            "match_results": state.get("match_results", []),
            "ranked_candidates": state.get("ranked_candidates", []),
            "executive_summary": state.get("executive_summary"),
            "report_path": state.get("report_path"),
            "logs": state.get("logs", []),
            "errors": state.get("errors", []),
        }
        
    except Exception as e:
        pipeline_runs[run_id]["status"] = "failed"
        pipeline_runs[run_id]["error"] = str(e)
        pipeline_runs[run_id]["progress"] = f"Error: {str(e)}"


# ─────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────

@app.get("/")
async def root():
    """Redirect to the frontend."""
    return FileResponse("frontend/index.html")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/upload-cv", status_code=201)
async def upload_cv(file: UploadFile = File(...)):
    """
    Upload a CV file (PDF or DOCX).
    Files are stored in data/uploads/ directory.
    """
    allowed_extensions = {".pdf", ".docx", ".txt"}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Also copy to CV directory for pipeline processing
    cv_file_path = CV_DIR / unique_filename
    with open(file_path, "rb") as src:
        with open(cv_file_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
    
    return {
        "filename": unique_filename,
        "original_name": file.filename,
        "size": file_path.stat().st_size,
        "path": str(file_path)
    }


@app.post("/api/upload-cvs/batch", status_code=201)
async def upload_cvs_batch(files: list[UploadFile] = File(...)):
    """
    Upload multiple CV files at once.
    """
    uploaded_files = []
    allowed_extensions = {".pdf", ".docx", ".txt"}
    
    for file in files:
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            continue
        
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename
        cv_file_path = CV_DIR / unique_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        with open(file_path, "rb") as src:
            with open(cv_file_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
        
        uploaded_files.append({
            "filename": unique_filename,
            "original_name": file.filename,
            "size": file_path.stat().st_size,
        })
    
    return {
        "uploaded": len(uploaded_files),
        "files": uploaded_files
    }


@app.post("/api/job-description", status_code=201)
async def create_job_description(job: JobDescriptionInput):
    """
    Create and save a job description.
    """
    job_path = save_job_description(job)
    
    return {
        "job_id": job.job_id,
        "title": job.title,
        "path": job_path,
        "message": "Job description saved successfully"
    }


@app.get("/api/job-description/{job_id}")
async def get_job_description(job_id: str):
    """
    Retrieve a job description by ID.
    If job_id is 'default', loads from data/job_description.json.
    """
    # Check for default job description
    if job_id == "default":
        default_path = Path("data/job_description.json")
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                return json.load(f)
    
    # Check in uploads directory
    job_path = UPLOAD_DIR / f"job_{job_id}.json"
    
    if not job_path.exists():
        # If not found, try loading default as fallback
        default_path = Path("data/job_description.json")
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail="Job description not found")
    
    with open(job_path, "r", encoding="utf-8") as f:
        job_data = json.load(f)
    
    return job_data


@app.post("/api/run-pipeline")
async def run_pipeline_endpoint(
    background_tasks: BackgroundTasks,
    job_id: Optional[str] = None,
    clear_cvs: bool = True
):
    """
    Run the CV screening pipeline.
    Uses the job description from data/job_description.json or uploads/.
    Processes all CVs in data/cvs/ directory.
    
    Returns a run_id to check status.
    """
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    
    # Determine job description path
    if job_id:
        job_path = UPLOAD_DIR / f"job_{job_id}.json"
        if not job_path.exists():
            raise HTTPException(status_code=404, detail=f"Job description '{job_id}' not found")
    else:
        # Use default job description
        job_path = Path("data/job_description.json")
        if not job_path.exists():
            raise HTTPException(status_code=404, detail="Default job description not found")
    
    # Clear CV directory if requested
    if clear_cvs and CV_DIR.exists():
        for f in CV_DIR.iterdir():
            if f.is_file():
                f.unlink()
        
        # Copy uploaded files to CV directory
        if UPLOAD_DIR.exists():
            for f in UPLOAD_DIR.iterdir():
                if f.is_file() and f.suffix.lower() in {".pdf", ".docx", ".txt"}:
                    if not f.name.startswith("job_"):  # Skip job description files
                        shutil.copy2(f, CV_DIR / f.name)
    
    # Initialize run state
    pipeline_runs[run_id] = {
        "status": "queued",
        "progress": "Preparing pipeline...",
        "job_id": job_id or "default",
        "started_at": datetime.now().isoformat(),
        "candidate_profiles": [],
        "match_results": [],
        "ranked_candidates": [],
        "executive_summary": None,
        "report_path": None,
        "result": None,
        "error": None,
    }
    
    # Run pipeline in background
    background_tasks.add_task(
        run_pipeline_async,
        run_id,
        str(job_path),
        str(CV_DIR)
    )
    
    return {
        "run_id": run_id,
        "status": "queued",
        "message": "Pipeline started. Use run_id to check status."
    }


@app.get("/api/run-status/{run_id}")
async def get_run_status(run_id: str):
    """
    Get the status of a pipeline run.
    """
    if run_id not in pipeline_runs:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run_data = pipeline_runs[run_id]
    
    return {
        "run_id": run_id,
        "status": run_data["status"],
        "progress": run_data["progress"],
        "result": run_data["result"],
        "error": run_data["error"],
    }


@app.get("/api/runs")
async def list_runs():
    """
    List all pipeline runs.
    """
    runs = []
    for run_id, data in pipeline_runs.items():
        runs.append({
            "run_id": run_id,
            "status": data["status"],
            "progress": data["progress"],
            "started_at": data.get("started_at"),
            "job_id": data.get("job_id"),
        })
    
    return {"runs": runs}


@app.get("/api/report/{run_id}")
async def get_report(run_id: str):
    """
    Get the generated HTML report for a completed run.
    """
    if run_id not in pipeline_runs:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run_data = pipeline_runs[run_id]
    
    if run_data["status"] != "completed" or not run_data.get("report_path"):
        raise HTTPException(status_code=400, detail="Report not available")
    
    report_path = Path(run_data["report_path"])
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(
        str(report_path),
        media_type="text/html",
        headers={"Content-Disposition": f"inline; filename=report_{run_id}.html"}
    )


@app.get("/api/candidates/{run_id}")
async def get_candidates(run_id: str):
    """
    Get ranked candidates for a completed run.
    """
    if run_id not in pipeline_runs:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run_data = pipeline_runs[run_id]
    
    if run_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Run not completed")
    
    return {
        "job_description": run_data.get("result", {}).get("job_description"),
        "executive_summary": run_data.get("executive_summary"),
        "ranked_candidates": run_data.get("ranked_candidates", []),
        "total": len(run_data.get("ranked_candidates", [])),
        "shortlisted": sum(1 for c in run_data.get("ranked_candidates", []) if c.get("status") == "Shortlisted"),
        "rejected": sum(1 for c in run_data.get("ranked_candidates", []) if c.get("status") == "Rejected"),
    }


@app.delete("/api/clear-uploads")
async def clear_uploads():
    """
    Clear all uploaded files.
    """
    cleared = 0
    
    # Clear uploads directory (except job descriptions)
    if UPLOAD_DIR.exists():
        for f in UPLOAD_DIR.iterdir():
            if f.is_file() and not f.name.startswith("job_"):
                f.unlink()
                cleared += 1
    
    # Clear CV directory
    if CV_DIR.exists():
        for f in CV_DIR.iterdir():
            if f.is_file():
                f.unlink()
                cleared += 1
    
    return {"message": f"Cleared {cleared} files"}


# ─────────────────────────────────────────────
# Frontend Routes
# ─────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard."""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/report-viewer")
async def report_viewer():
    """Serve the report viewer page."""
    with open("frontend/report.html", "r", encoding="utf-8") as f:
        return f.read()


# ─────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
