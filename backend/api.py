"""FastAPI backend — serves the AI pipeline + admin panel + training links.
Run: uvicorn api:app --reload --port 8000
"""
import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from pipeline import run_pipeline
from database import init_db
from routes.admin import router as admin_router
from routes.training import router as training_router

app = FastAPI(title="Train the Brain API", version="0.3.0")

# Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin_router)
app.include_router(training_router)


@app.on_event("startup")
def on_startup():
    init_db()


# --- Legacy endpoints (kept for backward compat) ---

# In-memory store for generated manifests (legacy)
store: dict[str, dict] = {}


class GenerateRequest(BaseModel):
    prd_text: str
    code_text: str
    figma_description: str = ""
    workflow_name: str = "Training Flow"


class GenerateResponse(BaseModel):
    status: str
    workflow_id: str
    manifest: dict
    assessment: dict


@app.get("/")
def health():
    return {"status": "ok", "service": "train-the-brain", "version": "0.3.0"}


@app.post("/generate", response_model=GenerateResponse)
def generate_training(req: GenerateRequest):
    """Run the real AI pipeline: PRD + code → manifest + quiz."""
    result = run_pipeline(
        prd_text=req.prd_text,
        code_text=req.code_text,
        figma_description=req.figma_description,
        workflow_name=req.workflow_name,
        generate_video=False,
    )
    manifest_data = result.manifest.model_dump()
    assessment_data = result.assessment.model_dump()
    workflow_id = manifest_data.get("workflow_id", "generated")

    store[workflow_id] = {
        "manifest": manifest_data,
        "assessment": assessment_data,
    }

    return GenerateResponse(
        status="ok",
        workflow_id=workflow_id,
        manifest=manifest_data,
        assessment=assessment_data,
    )


@app.get("/training/{workflow_id}")
def get_training(workflow_id: str):
    """Fetch a generated manifest + assessment by ID (legacy in-memory)."""
    if workflow_id in store:
        return store[workflow_id]
    raise HTTPException(status_code=404, detail="Training not found. Generate one first via POST /generate.")


@app.post("/generate-with-defaults")
def generate_with_defaults():
    """Quick endpoint: runs pipeline with built-in FTG test data."""
    prd_path = "test_data/ftg_prd.txt"
    code_path = "test_data/ftg_code.txt"

    with open(prd_path, "r") as f:
        prd_text = f.read()
    with open(code_path, "r") as f:
        code_text = f.read()

    result = run_pipeline(
        prd_text=prd_text,
        code_text=code_text,
        workflow_name="FTG Dimension Capture (Revamped)",
        generate_video=False,
    )
    manifest_data = result.manifest.model_dump()
    assessment_data = result.assessment.model_dump()
    workflow_id = manifest_data.get("workflow_id", "ftg_default")

    store[workflow_id] = {
        "manifest": manifest_data,
        "assessment": assessment_data,
    }

    return {
        "status": "ok",
        "workflow_id": workflow_id,
        "manifest": manifest_data,
        "assessment": assessment_data,
    }
