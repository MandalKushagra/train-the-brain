"""FastAPI endpoints for the new Simulation Optimization pipeline.

Adds to the existing api.py — import and mount this router there.
Run: uvicorn api:app --reload --port 8000
"""
import asyncio
import json
import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from agents.simulation_pipeline import PipelineInput, SimulationPipeline
from storage.local_file_storage import LocalFileStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sim", tags=["simulation-optimization"])

# Local storage for generated configs/manifests
DATA_DIR = os.environ.get("SIM_DATA_DIR", "./sim_data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
storage = LocalFileStorage(base_dir=DATA_DIR)

# In-memory job status tracker
job_status: dict[str, dict] = {}  # workflow_id -> {status, workflow_name, created_at, error, ...}


@router.post("/generate")
async def generate_simulation(
    workflow_name: str = Form(...),
    prd_text: str = Form(""),
    github_repo_urls: str = Form("[]"),
    figma_urls: str = Form("[]"),
    file_patterns: str = Form(""),
    screenshots: list[UploadFile] = File(default=[]),
):
    """Accept admin form data, run the simulation pipeline, return the golden manifest.

    Form fields:
    - workflow_name: Name for this training workflow
    - github_repo_url: Optional GitHub repo URL for code context
    - file_patterns: Optional comma-separated glob patterns (e.g. src/components/**,src/screens/**)
    - screenshots: One or more PNG/JPG screenshot files
    """
    workflow_id = f"wf_{uuid.uuid4().hex[:8]}"

    # Save uploaded screenshots to disk
    upload_dir = Path(UPLOAD_DIR) / workflow_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    screenshot_paths: list[str] = []
    for f in screenshots:
        dest = upload_dir / f.filename
        with open(dest, "wb") as out:
            content = await f.read()
            out.write(content)
        screenshot_paths.append(str(dest))

    # Parse file patterns
    patterns = [p.strip() for p in file_patterns.split(",") if p.strip()] or None

    # Parse GitHub repo URLs (JSON array from frontend — now with branch info)
    try:
        repo_entries = json.loads(github_repo_urls)
        if not isinstance(repo_entries, list):
            repo_entries = []
    except json.JSONDecodeError:
        repo_entries = []

    # Parse Figma URLs
    try:
        figma_url_list = json.loads(figma_urls)
        if not isinstance(figma_url_list, list):
            figma_url_list = []
    except json.JSONDecodeError:
        figma_url_list = []

    # Build pipeline input with all repos
    inp = PipelineInput(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        screenshot_paths=screenshot_paths,
        github_repos=repo_entries or None,
        file_patterns=patterns,
        prd_text=prd_text or None,
        figma_urls=figma_url_list or None,
    )

    # Track job status
    from datetime import datetime, timezone
    job_status[workflow_id] = {
        "status": "processing",
        "workflow_name": workflow_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "screenshots": len(screenshot_paths),
        "error": None,
    }

    # Run pipeline in background
    import asyncio

    async def _run_pipeline():
        try:
            pipeline = SimulationPipeline(storage=storage)
            output = await pipeline.run(inp)
            job_status[workflow_id]["status"] = "done" if output.manifest else "failed"
            job_status[workflow_id]["configs"] = len(output.screen_configs)
            job_status[workflow_id]["steps"] = len(output.manifest.steps) if output.manifest else 0
            job_status[workflow_id]["failed_screenshots"] = [f.model_dump() for f in output.failed_screenshots]
            job_status[workflow_id]["warnings"] = output.warnings
        except Exception as e:
            logger.exception("Pipeline failed")
            job_status[workflow_id]["status"] = "failed"
            job_status[workflow_id]["error"] = str(e)

    asyncio.create_task(_run_pipeline())

    return {
        "status": "accepted",
        "workflow_id": workflow_id,
        "message": "Pipeline started. Check /sim/status/{workflow_id} for progress.",
    }


@router.get("/status/{workflow_id}")
def get_status(workflow_id: str):
    """Get the processing status of a workflow."""
    if workflow_id in job_status:
        return job_status[workflow_id]
    # Check if manifest exists on disk (from previous runs)
    try:
        manifest = storage.load_manifest(workflow_id)
        return {
            "status": "done",
            "workflow_name": manifest.workflow_name,
            "steps": len(manifest.steps),
            "configs": len(manifest.screen_configs),
        }
    except Exception:
        return JSONResponse(status_code=404, content={"error": "Workflow not found"})


@router.get("/manifest/{workflow_id}")
def get_manifest(workflow_id: str):
    """Fetch a generated golden manifest by workflow ID."""
    try:
        manifest = storage.load_manifest(workflow_id)
        return manifest.model_dump()
    except Exception as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


@router.get("/workflows")
def list_workflows():
    """List all workflow IDs that have generated manifests or are in progress."""
    data_path = Path(DATA_DIR)
    workflows = []
    
    # Add in-progress jobs
    seen_ids = set()
    for wf_id, status in job_status.items():
        seen_ids.add(wf_id)
        workflows.append({
            "workflow_id": wf_id,
            "workflow_name": status.get("workflow_name", wf_id),
            "status": status.get("status", "unknown"),
            "created_at": status.get("created_at", ""),
            "steps": status.get("steps", 0),
            "configs": status.get("configs", 0),
            "error": status.get("error"),
        })
    
    # Add completed ones from disk
    if data_path.exists():
        for d in sorted(data_path.iterdir()):
            if d.is_dir() and d.name not in seen_ids and (d / "manifest.json").exists():
                try:
                    manifest = json.loads((d / "manifest.json").read_text())
                    workflows.append({
                        "workflow_id": d.name,
                        "workflow_name": manifest.get("workflow_name", d.name),
                        "status": "done",
                        "steps": len(manifest.get("steps", [])),
                        "configs": len(manifest.get("screen_configs", {})),
                    })
                except Exception:
                    pass
    
    return {"workflows": workflows}
