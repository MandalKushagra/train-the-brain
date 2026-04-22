"""Training routes — operator-facing endpoints (no auth, link-based access)."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models.db_models import TrainingAssignment, TrainingCompletion, StepMetric

router = APIRouter(tags=["training"])


class StepMetricReq(BaseModel):
    step_id: int
    wrong_attempts: int = 0
    hints_used: int = 0
    show_me_used: bool = False
    skipped: bool = False
    time_on_step_seconds: int = 0


class CompleteTrainingReq(BaseModel):
    quiz_score: int
    total_questions: int
    time_taken_seconds: int
    total_hints_used: int = 0
    total_skips: int = 0
    step_metrics: list[StepMetricReq] = []
    pass_threshold: float = 0.6


@router.get("/t/{link_token}")
def resolve_training_link(link_token: str, db: Session = Depends(get_db)):
    """Operator opens training link → get manifest + assignment info."""
    assignment = db.query(TrainingAssignment).filter(
        TrainingAssignment.link_token == link_token
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Invalid or expired training link")

    sim = assignment.simulation
    operator = assignment.operator

    # If already completed, return completion summary
    if assignment.status == "completed" and assignment.completion:
        return {
            "status": "completed",
            "assignment_id": assignment.id,
            "operator_id": operator.operator_id,
            "operator_name": operator.name,
            "simulation_name": sim.workflow_name,
            "quiz_score": assignment.completion.quiz_score,
            "total_questions": assignment.completion.total_questions,
            "passed": assignment.completion.passed,
            "time_taken_seconds": assignment.completion.time_taken_seconds,
            "completed_at": assignment.completed_at.isoformat() if assignment.completed_at else None,
        }

    return {
        "status": assignment.status,
        "assignment_id": assignment.id,
        "operator_id": operator.operator_id,
        "operator_name": operator.name,
        "simulation_id": sim.id,
        "simulation_name": sim.workflow_name,
        "manifest": sim.manifest_json,
        "assessment": sim.assessment_json,
    }


@router.post("/t/{link_token}/start")
def start_training(link_token: str, db: Session = Depends(get_db)):
    """Mark training as in_progress when operator begins."""
    assignment = db.query(TrainingAssignment).filter(
        TrainingAssignment.link_token == link_token
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Invalid training link")
    if assignment.status == "completed":
        raise HTTPException(status_code=400, detail="Training already completed")

    assignment.status = "in_progress"
    assignment.started_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "in_progress", "assignment_id": assignment.id}


@router.post("/t/{link_token}/complete")
def complete_training(link_token: str, req: CompleteTrainingReq, db: Session = Depends(get_db)):
    """Record training completion with quiz score and step metrics."""
    assignment = db.query(TrainingAssignment).filter(
        TrainingAssignment.link_token == link_token
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Invalid training link")
    if assignment.status == "completed":
        raise HTTPException(status_code=400, detail="Training already completed")

    now = datetime.now(timezone.utc)
    passed = (req.quiz_score / req.total_questions >= req.pass_threshold) if req.total_questions > 0 else False

    completion = TrainingCompletion(
        assignment_id=assignment.id,
        quiz_score=req.quiz_score,
        total_questions=req.total_questions,
        time_taken_seconds=req.time_taken_seconds,
        total_hints_used=req.total_hints_used,
        total_skips=req.total_skips,
        passed=passed,
    )
    db.add(completion)
    db.flush()

    # Save step-level metrics
    for sm in req.step_metrics:
        metric = StepMetric(
            completion_id=completion.id,
            step_id=sm.step_id,
            wrong_attempts=sm.wrong_attempts,
            hints_used=sm.hints_used,
            show_me_used=sm.show_me_used,
            skipped=sm.skipped,
            time_on_step_seconds=sm.time_on_step_seconds,
        )
        db.add(metric)

    assignment.status = "completed"
    assignment.completed_at = now
    db.commit()

    return {
        "status": "completed",
        "passed": passed,
        "quiz_score": req.quiz_score,
        "total_questions": req.total_questions,
        "time_taken_seconds": req.time_taken_seconds,
    }
