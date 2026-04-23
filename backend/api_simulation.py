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


@router.post("/generate")
async def generate_simulation(
    workflow_name: str = Form(...),
    github_repo_urls: str = Form("[]"),
    file_patterns: str = Form(""),
    screenshots: list[UploadFile] = File(...),
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

    # Parse GitHub repo URLs (JSON array from frontend)
    try:
        repo_urls = json.loads(github_repo_urls)
        if not isinstance(repo_urls, list):
            repo_urls = []
    except json.JSONDecodeError:
        repo_urls = []
    # Use first repo URL for pipeline (pipeline fetches from multiple via loop)
    primary_repo_url = repo_urls[0] if repo_urls else None

    # Build pipeline input
    inp = PipelineInput(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        screenshot_paths=screenshot_paths,
        github_repo_url=primary_repo_url,
        file_patterns=patterns,
    )

    # Run the pipeline
    pipeline = SimulationPipeline(storage=storage)
    try:
        output = await pipeline.run(inp)
    except Exception as e:
        logger.exception("Pipeline failed")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "workflow_id": workflow_id},
        )

    # Build response
    manifest_data = output.manifest.model_dump() if output.manifest else None
    configs_data = [c.model_dump() for c in output.screen_configs]

    return {
        "status": "ok",
        "workflow_id": workflow_id,
        "manifest": manifest_data,
        "screen_configs": configs_data,
        "failed_screenshots": [f.model_dump() for f in output.failed_screenshots],
        "warnings": output.warnings,
    }


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
    """List all workflow IDs that have generated manifests."""
    data_path = Path(DATA_DIR)
    if not data_path.exists():
        return {"workflows": []}

    workflows = []
    for d in sorted(data_path.iterdir()):
        if d.is_dir() and (d / "manifest.json").exists():
            manifest = json.loads((d / "manifest.json").read_text())
            workflows.append({
                "workflow_id": d.name,
                "workflow_name": manifest.get("workflow_name", d.name),
            })
    return {"workflows": workflows}
