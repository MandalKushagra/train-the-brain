"""Pipeline API — the single endpoint that accepts all inputs,
stores them in S3, runs the multi-agent pipeline in background,
and saves outputs back to S3.

Endpoints:
  POST   /pipeline/start          Upload artifacts → kick off pipeline
  GET    /pipeline/{job_id}       Poll job status
  GET    /pipeline/{job_id}/result Fetch completed output (manifest + assessment)
  GET    /pipeline/jobs            List all jobs
"""
import os
import uuid
import traceback
import asyncio
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel

from services import db_service
from services import storage_service as store
from services.file_parser import extract_text_from_bytes
from pipeline import run_pipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


# ── Response models ─────────────────────────────────────────────


class JobStartResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # pending | processing | completed | failed
    workflow_name: str
    created_at: str
    updated_at: str
    error_message: Optional[str] = None
    has_manifest: bool = False
    has_assessment: bool = False


class JobResultResponse(BaseModel):
    job_id: str
    manifest: Optional[dict] = None
    assessment: Optional[dict] = None
    manifest_url: Optional[str] = None
    assessment_url: Optional[str] = None


# ── Background pipeline runner ──────────────────────────────────


def _run_pipeline_background(job_id: str):
    """Pull inputs from S3, run the 4-agent pipeline, save outputs to S3.

    This runs in a background thread so the API returns immediately.
    """
    try:
        db_service.update_job_status(job_id, "processing")
        job = db_service.get_job(job_id)

        # ── 1. Pull inputs from S3 ──────────────────────────────
        prd_text = ""
        code_text = ""
        figma_description = ""

        if job["prd_s3_key"]:
            prd_text = store.download_text(job["prd_s3_key"])

        if job["code_s3_key"]:
            code_text = store.download_text(job["code_s3_key"])

        if job["figma_s3_key"]:
            figma_description = store.download_text(job["figma_s3_key"])

        # ── 2. Run the LangGraph pipeline ───────────────────────
        result = run_pipeline(
            prd_text=prd_text,
            code_text=code_text,
            figma_description=figma_description,
            workflow_name=job["workflow_name"],
            generate_video=False,
        )

        # ── 3. Save outputs to S3 (manifest can be huge) ───────
        manifest_dict = result.manifest.model_dump()
        assessment_dict = result.assessment.model_dump()

        manifest_key = store.upload_json(job_id, "manifest", manifest_dict)
        assessment_key = store.upload_json(job_id, "assessment", assessment_dict)

        # ── 4. Update job record with output locations ──────────
        db_service.update_job_status(
            job_id, "completed",
            manifest_s3_key=manifest_key,
            assessment_s3_key=assessment_key,
        )

    except Exception as e:
        db_service.update_job_status(
            job_id, "failed",
            error_message=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()[-500:]}",
        )


# ── Endpoints ───────────────────────────────────────────────────


@router.post("/start", response_model=JobStartResponse)
async def start_pipeline(
    background_tasks: BackgroundTasks,
    workflow_name: str = Form("Training Flow"),
    prd_text: Optional[str] = Form(None),
    code_text: Optional[str] = Form(None),
    figma_url: Optional[str] = Form(None),
    figma_description: Optional[str] = Form(None),
    github_url: Optional[str] = Form(None),
    prd_file: Optional[UploadFile] = File(None),
    code_file: Optional[UploadFile] = File(None),
    screenshots: Optional[list[UploadFile]] = File(None),
):
    """Accept all PM artifacts, store in S3, kick off pipeline.

    Accepts either pasted text OR file uploads for PRD and code.
    Can also accept a github_url to fetch code from a repo.
    Screenshots are optional (used for Figma-less flows).
    """
    job_id = uuid.uuid4().hex[:12]

    # ── Upload inputs to S3 ─────────────────────────────────────
    prd_s3_key = None
    code_s3_key = None
    figma_s3_key = None
    screenshot_keys = []

    # PRD: file upload takes priority over pasted text
    if prd_file:
        data = await prd_file.read()
        # Store the original file
        store.upload_file_bytes(
            job_id, prd_file.filename or "prd_upload", data,
            content_type=prd_file.content_type or "application/octet-stream",
        )
        # Parse to text for the pipeline (handles PDF, DOCX, plain text)
        parsed_text = extract_text_from_bytes(data, prd_file.filename or "prd.txt")
        prd_s3_key = store.upload_text(job_id, "prd_parsed.txt", parsed_text)
    elif prd_text:
        prd_s3_key = store.upload_text(job_id, "prd_text.txt", prd_text)

    # Code: file > github_url > pasted text
    if code_file:
        data = await code_file.read()
        store.upload_file_bytes(
            job_id, code_file.filename or "code_upload", data,
            content_type=code_file.content_type or "text/plain",
        )
        parsed_text = extract_text_from_bytes(data, code_file.filename or "code.txt")
        code_s3_key = store.upload_text(job_id, "code_parsed.txt", parsed_text)
    elif github_url:
        from services.github_service import fetch_repo_code
        fetched_code = fetch_repo_code(github_url)
        code_s3_key = store.upload_text(job_id, "code_github.txt", fetched_code)
    elif code_text:
        code_s3_key = store.upload_text(job_id, "code_text.txt", code_text)

    # Figma description (text-based for now; figma_url stored as metadata)
    if figma_description:
        figma_s3_key = store.upload_text(job_id, "figma_description.txt", figma_description)

    # Screenshots
    if screenshots:
        for ss in screenshots:
            data = await ss.read()
            if len(data) == 0:
                continue
            key = store.upload_file_bytes(
                job_id, ss.filename or f"screenshot_{uuid.uuid4().hex[:6]}.png", data,
                content_type=ss.content_type or "image/png",
            )
            screenshot_keys.append(key)

    # Validate we have at least something to work with
    if not prd_s3_key and not code_s3_key:
        raise HTTPException(
            status_code=400,
            detail="At least one of prd_text/prd_file or code_text/code_file is required.",
        )

    # ── Create job record in SQLite ─────────────────────────────
    db_service.create_job(
        job_id=job_id,
        workflow_name=workflow_name,
        prd_s3_key=prd_s3_key,
        code_s3_key=code_s3_key,
        figma_s3_key=figma_s3_key,
        figma_url=figma_url,
        screenshots_s3_keys=screenshot_keys if screenshot_keys else None,
    )

    # ── Kick off pipeline in background ─────────────────────────
    background_tasks.add_task(_run_pipeline_background, job_id)

    return JobStartResponse(
        job_id=job_id,
        status="pending",
        message="Pipeline started. Poll GET /pipeline/{job_id} for status.",
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Poll job status. Returns current state + whether outputs are ready."""
    job = db_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job["id"],
        status=job["status"],
        workflow_name=job["workflow_name"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        error_message=job["error_message"],
        has_manifest=job["manifest_s3_key"] is not None,
        has_assessment=job["assessment_s3_key"] is not None,
    )


@router.get("/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(job_id: str, presigned: bool = False):
    """Fetch pipeline output.

    By default returns the full JSON inline.
    Pass ?presigned=true to get S3 presigned URLs instead (for huge manifests).
    """
    job = db_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Job is '{job['status']}'. Results only available when status is 'completed'.",
        )

    if presigned:
        # Return presigned URLs — client downloads directly from S3
        manifest_url = store.generate_presigned_url(job["manifest_s3_key"]) if job["manifest_s3_key"] else None
        assessment_url = store.generate_presigned_url(job["assessment_s3_key"]) if job["assessment_s3_key"] else None
        return JobResultResponse(
            job_id=job_id,
            manifest_url=manifest_url,
            assessment_url=assessment_url,
        )
    else:
        # Return full JSON inline (fine for most cases)
        manifest = store.download_json(job["manifest_s3_key"]) if job["manifest_s3_key"] else None
        assessment = store.download_json(job["assessment_s3_key"]) if job["assessment_s3_key"] else None
        return JobResultResponse(
            job_id=job_id,
            manifest=manifest,
            assessment=assessment,
        )


@router.get("/jobs/", response_model=list[JobStatusResponse])
async def list_jobs(status: Optional[str] = None, limit: int = 50):
    """List all pipeline jobs, optionally filtered by status."""
    jobs = db_service.list_jobs(status=status, limit=limit)
    return [
        JobStatusResponse(
            job_id=j["id"],
            status=j["status"],
            workflow_name=j["workflow_name"],
            created_at=j["created_at"],
            updated_at=j["updated_at"],
            error_message=j["error_message"],
            has_manifest=j["manifest_s3_key"] is not None,
            has_assessment=j["assessment_s3_key"] is not None,
        )
        for j in jobs
    ]
