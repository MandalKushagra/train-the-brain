"""Training API — assign users, generate unique links, track progress.

Endpoints:
  POST   /training/{job_id}/assign       PM assigns users → unique links
  GET    /training/link/{token}          User opens their unique link → gets manifest + starts tracking
  POST   /training/link/{token}/step     User completes a step
  POST   /training/link/{token}/wrong    User makes a wrong attempt
  POST   /training/link/{token}/complete User finishes training + quiz
  GET    /training/{job_id}/progress     PM views all user progress for a job
  GET    /training/{job_id}/stats        PM views aggregate stats
  GET    /training/{job_id}/step-analytics  PM views step-level analytics
"""
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import db_service
from services import storage_service as store

router = APIRouter(prefix="/training", tags=["training"])


# ── Request / Response models ───────────────────────────────────


class UserAssignment(BaseModel):
    user_name: str
    user_email: Optional[str] = None
    user_id: Optional[str] = None


class AssignRequest(BaseModel):
    users: list[UserAssignment]
    assigned_by: Optional[str] = None


class AssignedUser(BaseModel):
    user_name: str
    token: str
    training_url: str
    status: str


class AssignResponse(BaseModel):
    job_id: str
    workflow_name: str
    assigned: list[AssignedUser]


class TrainingSession(BaseModel):
    token: str
    user_name: str
    workflow_name: str
    status: str
    current_step: int
    total_steps: int
    manifest: Optional[dict] = None
    assessment: Optional[dict] = None


class StepCompleteRequest(BaseModel):
    step_id: int
    time_spent_sec: float = 0


class QuizCompleteRequest(BaseModel):
    quiz_score: float
    quiz_passed: bool
    quiz_answers: list


class UserProgress(BaseModel):
    token: str
    user_name: str
    user_email: Optional[str] = None
    status: str
    current_step: int
    total_steps: int
    progress_pct: float
    quiz_score: Optional[float] = None
    quiz_passed: Optional[bool] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class JobStats(BaseModel):
    job_id: str
    total_assigned: int
    completed: int
    in_progress: int
    pending: int
    completion_rate: float
    avg_quiz_score: Optional[float] = None
    quiz_pass_rate: Optional[float] = None


class StepAnalytics(BaseModel):
    step_id: int
    users_reached: int
    users_completed: int
    drop_off_rate: float
    total_attempts: int
    avg_time_sec: Optional[float] = None


# ── PM: Assign users to a training ─────────────────────────────


@router.post("/{job_id}/assign", response_model=AssignResponse)
async def assign_users(job_id: str, req: AssignRequest):
    """PM assigns one or more users to a completed training job.
    Each user gets a unique token that becomes their training link.
    """
    job = db_service.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] != "completed":
        raise HTTPException(409, f"Job is '{job['status']}'. Can only assign users to completed jobs.")

    # Get total steps from manifest
    total_steps = 0
    if job["manifest_s3_key"]:
        manifest = store.download_json(job["manifest_s3_key"])
        total_steps = len(manifest.get("steps", []))

    assigned = []
    for user in req.users:
        token = uuid.uuid4().hex[:10]
        db_service.create_assignment(
            assignment_id=token,
            job_id=job_id,
            user_name=user.user_name,
            total_steps=total_steps,
            user_email=user.user_email,
            user_id=user.user_id,
            assigned_by=req.assigned_by,
        )
        assigned.append(AssignedUser(
            user_name=user.user_name,
            token=token,
            training_url=f"/training/link/{token}",
            status="pending",
        ))

    return AssignResponse(
        job_id=job_id,
        workflow_name=job["workflow_name"],
        assigned=assigned,
    )


# ── User: Open training link ───────────────────────────────────


@router.get("/link/{token}", response_model=TrainingSession)
async def open_training_link(token: str):
    """User opens their unique training link.
    Returns the manifest + assessment so the simulator can render.
    Marks training as in_progress on first open.
    """
    assignment = db_service.get_assignment(token)
    if not assignment:
        raise HTTPException(404, "Training link not found or expired")

    job = db_service.get_job(assignment["job_id"])
    if not job:
        raise HTTPException(404, "Training job not found")

    # Mark as started on first open
    if assignment["status"] == "pending":
        db_service.start_training(token)

    # Fetch manifest + assessment from S3
    manifest = None
    assessment = None
    if job["manifest_s3_key"]:
        manifest = store.download_json(job["manifest_s3_key"])
    if job["assessment_s3_key"]:
        assessment = store.download_json(job["assessment_s3_key"])

    return TrainingSession(
        token=token,
        user_name=assignment["user_name"],
        workflow_name=job["workflow_name"],
        status="in_progress" if assignment["status"] == "pending" else assignment["status"],
        current_step=assignment["current_step"],
        total_steps=assignment["total_steps"],
        manifest=manifest,
        assessment=assessment,
    )


# ── User: Step progress ────────────────────────────────────────


@router.post("/link/{token}/step")
async def complete_step(token: str, req: StepCompleteRequest):
    """User completes a step in the simulator."""
    assignment = db_service.get_assignment(token)
    if not assignment:
        raise HTTPException(404, "Training link not found")
    if assignment["status"] == "completed":
        raise HTTPException(409, "Training already completed")

    next_step = req.step_id + 1
    db_service.update_step_progress(token, req.step_id, next_step)

    return {
        "status": "ok",
        "step_completed": req.step_id,
        "current_step": next_step,
        "total_steps": assignment["total_steps"],
    }


@router.post("/link/{token}/wrong")
async def record_wrong(token: str, req: StepCompleteRequest):
    """User made a wrong attempt on a step."""
    assignment = db_service.get_assignment(token)
    if not assignment:
        raise HTTPException(404, "Training link not found")

    db_service.record_wrong_attempt(token, req.step_id)
    return {"status": "ok", "step_id": req.step_id, "message": "Wrong attempt recorded"}


# ── User: Complete training + quiz ──────────────────────────────


@router.post("/link/{token}/complete")
async def complete_training(token: str, req: QuizCompleteRequest):
    """User finishes the training and submits quiz answers."""
    assignment = db_service.get_assignment(token)
    if not assignment:
        raise HTTPException(404, "Training link not found")
    if assignment["status"] == "completed":
        raise HTTPException(409, "Training already completed")

    db_service.complete_training(
        token,
        quiz_score=req.quiz_score,
        quiz_passed=req.quiz_passed,
        quiz_answers=req.quiz_answers,
    )

    return {
        "status": "completed",
        "quiz_score": req.quiz_score,
        "quiz_passed": req.quiz_passed,
        "message": "Training completed. Well done!" if req.quiz_passed else "Training completed. Quiz not passed — retake recommended.",
    }


# ── PM: View progress ──────────────────────────────────────────


@router.get("/{job_id}/progress", response_model=list[UserProgress])
async def get_progress(job_id: str):
    """PM views progress of all assigned users for a training job."""
    assignments = db_service.list_assignments_for_job(job_id)
    if not assignments:
        raise HTTPException(404, "No assignments found for this job")

    return [
        UserProgress(
            token=a["id"],
            user_name=a["user_name"],
            user_email=a["user_email"],
            status=a["status"],
            current_step=a["current_step"],
            total_steps=a["total_steps"],
            progress_pct=round((a["current_step"] / a["total_steps"] * 100) if a["total_steps"] > 0 else 0, 1),
            quiz_score=a["quiz_score"],
            quiz_passed=bool(a["quiz_passed"]) if a["quiz_passed"] is not None else None,
            started_at=a["started_at"],
            completed_at=a["completed_at"],
        )
        for a in assignments
    ]


@router.get("/{job_id}/stats", response_model=JobStats)
async def get_stats(job_id: str):
    """PM views aggregate stats for a training job."""
    stats = db_service.get_job_stats(job_id)
    if not stats or stats["total_assigned"] == 0:
        raise HTTPException(404, "No assignments found")

    total = stats["total_assigned"]
    completed = stats["completed"] or 0
    passed = stats["quiz_passed_count"] or 0

    return JobStats(
        job_id=job_id,
        total_assigned=total,
        completed=completed,
        in_progress=stats["in_progress"] or 0,
        pending=stats["pending"] or 0,
        completion_rate=round(completed / total * 100, 1) if total > 0 else 0,
        avg_quiz_score=round(stats["avg_quiz_score"], 2) if stats["avg_quiz_score"] else None,
        quiz_pass_rate=round(passed / completed * 100, 1) if completed > 0 else None,
    )


@router.get("/{job_id}/step-analytics", response_model=list[StepAnalytics])
async def get_step_analytics(job_id: str):
    """PM views step-level analytics — which steps users struggle with."""
    steps = db_service.get_step_analytics(job_id)
    if not steps:
        return []

    return [
        StepAnalytics(
            step_id=s["step_id"],
            users_reached=s["users_reached"],
            users_completed=s["users_completed"],
            drop_off_rate=round(
                (1 - s["users_completed"] / s["users_reached"]) * 100, 1
            ) if s["users_reached"] > 0 else 0,
            total_attempts=s["total_attempts"],
            avg_time_sec=round(s["avg_time_sec"], 1) if s["avg_time_sec"] else None,
        )
        for s in steps
    ]
