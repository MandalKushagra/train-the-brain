"""FastAPI backend — serves the pipeline via HTTP.
Run: uvicorn api:app --reload --port 8000

Endpoints:
  Legacy:
    POST /generate          — mock pipeline (kept for backward compat)
    GET  /manifest/{id}     — mock manifest
    GET  /assessment/{id}   — mock assessment

  New (real pipeline + S3 + background jobs):
    POST /pipeline/start          — upload artifacts, kick off pipeline
    GET  /pipeline/{job_id}       — poll job status
    GET  /pipeline/{job_id}/result — fetch completed output
    GET  /pipeline/jobs/           — list all jobs

Test the new pipeline with curl:
  curl -X POST http://localhost:8000/pipeline/start \
    -F 'workflow_name=FTG Flow' \
    -F 'prd_text=...' \
    -F 'code_text=...'
"""
import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from services import db_service
from pipeline_api import router as pipeline_router
from training_api import router as training_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB on startup."""
    db_service.init_db()
    yield


app = FastAPI(title="Train the Brain API", version="0.2.0", lifespan=lifespan)

# CORS — allow the React frontend to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the new pipeline router
app.include_router(pipeline_router)

# Mount the training assignment + tracking router
app.include_router(training_router)

# --- Request/Response models ---

class GenerateRequest(BaseModel):
    prd_text: str
    code_text: str
    figma_description: str = ""
    workflow_name: str = "Training Flow"
    generate_video: bool = False


class GenerateResponse(BaseModel):
    status: str
    manifest: dict
    assessment: dict
    video_path: Optional[str] = None


# --- Mock manifest (used until Gemini key is ready) ---

MOCK_MANIFEST = {
    "workflow_id": "ftg_revamped_flow_v1",
    "workflow_name": "FTG - Dimension & Weight Capture (Revamped)",
    "target_users": ["fc_operators"],
    "language": "en",
    "steps": [
        {
            "step_id": 1, "screen": "sku_search", "title": "Search for Product",
            "instruction": "Type SKU or scan barcode",
            "narration": "First, type the SKU or scan the barcode to find your product.",
            "highlight_element": "ftg_diamention_capture_input_field",
            "expected_action": "TYPE", "on_wrong_action": "Please use the search box at the top."
        },
        {
            "step_id": 2, "screen": "sku_search", "title": "Select Product",
            "instruction": "Tap the correct product",
            "narration": "Now tap on the correct product from the search results.",
            "highlight_element": "product_card",
            "expected_action": "TAP", "on_wrong_action": "Tap on a product card from the list."
        },
        {
            "step_id": 3, "screen": "packaging_options", "title": "Choose Packaging",
            "instruction": "Select packaging type",
            "narration": "Select how this product is packaged. Choose Ships In Own Box for single items.",
            "highlight_element": "option_siob",
            "expected_action": "TAP", "on_wrong_action": "Please select one of the three packaging options."
        },
        {
            "step_id": 4, "screen": "packaging_options", "title": "Proceed",
            "instruction": "Tap Next",
            "narration": "Good. Now tap Next to continue to product identifiers.",
            "highlight_element": "btn_next",
            "expected_action": "TAP", "on_wrong_action": "Tap the Next button at the bottom."
        },
        {
            "step_id": 5, "screen": "product_identifiers", "title": "Select Category",
            "instruction": "Choose product category",
            "narration": "Select the product category from the dropdown.",
            "highlight_element": "spinner_product_category",
            "expected_action": "TAP", "on_wrong_action": "Tap the product category dropdown."
        },
        {
            "step_id": 6, "screen": "product_identifiers", "title": "Continue",
            "instruction": "Tap Next",
            "narration": "Tap Next to go to dimension capture.",
            "highlight_element": "btn_next_identifiers",
            "expected_action": "TAP", "on_wrong_action": "Tap the Next button."
        },
        {
            "step_id": 7, "screen": "dimension_weight", "title": "V-Measure Mode",
            "instruction": "Place product on machine",
            "narration": "V-Measure is selected by default. Place the product on the machine and scan the barcode shown on screen.",
            "highlight_element": "tab_vmeasure",
            "expected_action": "SCAN", "on_wrong_action": "Place product on V-Measure machine first."
        },
        {
            "step_id": 8, "screen": "dimension_weight", "title": "Verify Dimensions",
            "instruction": "Check L, W, H and Weight",
            "narration": "Check the captured dimensions and weight. If they look wrong, tap Recapture.",
            "highlight_element": "layout_vmeasure_calculated",
            "expected_action": "VERIFY", "on_wrong_action": "Review the dimension values shown."
        },
        {
            "step_id": 9, "screen": "dimension_weight", "title": "Save",
            "instruction": "Tap Save Dimensions",
            "narration": "Everything looks good. Tap Save Dimensions to complete FTG.",
            "highlight_element": "btn_save_dimensions",
            "expected_action": "TAP", "on_wrong_action": "Tap the Save Dimensions button."
        }
    ],
    "error_scenarios": [
        {"trigger": "vmeasure_exceeds_limits", "message": "This SKU/Box is outside the V-Measure limit"},
        {"trigger": "no_manual_permission", "message": "You do not have permission to use Manual mode"},
        {"trigger": "machine_not_configured", "message": "This machine is not configured. Contact IT team."}
    ]
}

MOCK_ASSESSMENT = {
    "questions": [
        {
            "question": "What is the first thing you do in the FTG flow?",
            "options": ["Select packaging", "Scan barcode or type SKU", "Enter dimensions", "Save"],
            "correct": 1
        },
        {
            "question": "When you select Ships In Own Case Box (SIOCB), what extra field appears?",
            "options": ["Weight", "Items Per Box", "Product Image", "Barcode"],
            "correct": 1
        },
        {
            "question": "Who can use Manual mode for entering dimensions?",
            "options": ["Anyone", "Only users with UMS permission", "Only managers", "Only IT team"],
            "correct": 1
        },
        {
            "question": "What happens if V-Measure dimensions exceed machine limits?",
            "options": ["Data saves anyway", "Error shown, must use manual or different machine", "App restarts", "Nothing"],
            "correct": 1
        },
        {
            "question": "How often does V-Measure poll for dimension data?",
            "options": ["Every 1 second", "Every 2 seconds", "Every 5 seconds", "Only once"],
            "correct": 1
        }
    ],
    "pass_threshold": 0.6
}


# --- Routes ---

@app.get("/")
def health():
    return {"status": "ok", "service": "train-the-brain"}


@app.post("/generate", response_model=GenerateResponse)
def generate_training(req: GenerateRequest):
    """Generate training content from PRD + code.
    Currently returns mock data. Will use real pipeline once Gemini key is ready.
    """
    # TODO: Replace with real pipeline call once API key is available:
    # from pipeline import run_pipeline
    # result = run_pipeline(req.prd_text, req.code_text, req.figma_description, req.workflow_name, generate_video=req.generate_video)
    # return GenerateResponse(status="ok", manifest=result.manifest.model_dump(), assessment=result.assessment.model_dump(), video_path=result.video_path)

    return GenerateResponse(
        status="ok",
        manifest=MOCK_MANIFEST,
        assessment=MOCK_ASSESSMENT,
        video_path=None,
    )


@app.get("/manifest/{workflow_id}")
def get_manifest(workflow_id: str):
    """Fetch a saved manifest by ID. Currently returns mock."""
    if workflow_id == "ftg_revamped_flow_v1":
        return MOCK_MANIFEST
    raise HTTPException(status_code=404, detail="Manifest not found")


@app.get("/assessment/{workflow_id}")
def get_assessment(workflow_id: str):
    """Fetch quiz for a workflow. Currently returns mock."""
    if workflow_id == "ftg_revamped_flow_v1":
        return MOCK_ASSESSMENT
    raise HTTPException(status_code=404, detail="Assessment not found")


@app.get("/video/{workflow_id}")
def get_video(workflow_id: str):
    """Serve generated video file."""
    video_path = f"output/{workflow_id}.mp4"
    if os.path.exists(video_path):
        return FileResponse(video_path, media_type="video/mp4")
    raise HTTPException(status_code=404, detail="Video not found")
