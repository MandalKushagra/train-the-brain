"""Admin routes — simulation management, assignment, operator search."""
import os
import shutil
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import pdfplumber
from database import get_db
from models.db_models import Simulation, Operator, TrainingAssignment, TrainingCompletion, StepMetric
from config import ADMIN_KEY
from link_utils import generate_link_token
from pipeline import run_pipeline

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Auth dependency ---
def require_admin(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")


# --- Request/Response schemas ---
class CreateSimulationReq(BaseModel):
    workflow_id: str
    workflow_name: str
    manifest_json: dict
    assessment_json: dict


class PublishReq(BaseModel):
    pass


class AssignReq(BaseModel):
    simulation_id: str
    operator_ids: list[str]  # employee IDs
    operator_names: dict[str, str] = {}  # optional: {operator_id: name}


class OperatorSummary(BaseModel):
    operator_id: str
    name: str
    assignment_id: str
    simulation_name: str
    status: str
    assigned_at: str
    completed_at: Optional[str] = None
    quiz_score: Optional[int] = None
    total_questions: Optional[int] = None
    passed: Optional[bool] = None
    time_taken_seconds: Optional[int] = None
    training_link: str


# --- Simulation CRUD ---

@router.get("/simulations", dependencies=[Depends(require_admin)])
def list_simulations(db: Session = Depends(get_db)):
    sims = db.query(Simulation).order_by(Simulation.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "workflow_id": s.workflow_id,
            "workflow_name": s.workflow_name,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "published_at": s.published_at.isoformat() if s.published_at else None,
            "assignment_count": len(s.assignments),
        }
        for s in sims
    ]


@router.post("/simulations", dependencies=[Depends(require_admin)])
def create_simulation(req: CreateSimulationReq, db: Session = Depends(get_db)):
    existing = db.query(Simulation).filter(Simulation.workflow_id == req.workflow_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Simulation with workflow_id '{req.workflow_id}' already exists")
    sim = Simulation(
        workflow_id=req.workflow_id,
        workflow_name=req.workflow_name,
        manifest_json=req.manifest_json,
        assessment_json=req.assessment_json,
        status="draft",
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)
    return {"id": sim.id, "workflow_id": sim.workflow_id, "status": sim.status}


@router.get("/simulations/{sim_id}", dependencies=[Depends(require_admin)])
def get_simulation(sim_id: str, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {
        "id": sim.id,
        "workflow_id": sim.workflow_id,
        "workflow_name": sim.workflow_name,
        "manifest_json": sim.manifest_json,
        "assessment_json": sim.assessment_json,
        "status": sim.status,
        "created_at": sim.created_at.isoformat() if sim.created_at else None,
        "published_at": sim.published_at.isoformat() if sim.published_at else None,
    }


@router.put("/simulations/{sim_id}", dependencies=[Depends(require_admin)])
def update_simulation(sim_id: str, req: CreateSimulationReq, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    sim.workflow_name = req.workflow_name
    sim.manifest_json = req.manifest_json
    sim.assessment_json = req.assessment_json
    db.commit()
    return {"id": sim.id, "status": "updated"}


@router.post("/simulations/{sim_id}/publish", dependencies=[Depends(require_admin)])
def publish_simulation(sim_id: str, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    sim.status = "published"
    sim.published_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": sim.id, "status": "published"}


# --- Assignment ---

@router.post("/assign", dependencies=[Depends(require_admin)])
def assign_training(req: AssignReq, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == req.simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if sim.status != "published":
        raise HTTPException(status_code=400, detail="Simulation must be published before assigning")

    results = []
    for emp_id in req.operator_ids:
        # Get or create operator
        op = db.query(Operator).filter(Operator.operator_id == emp_id).first()
        if not op:
            name = req.operator_names.get(emp_id, emp_id)
            op = Operator(operator_id=emp_id, name=name)
            db.add(op)
            db.flush()

        # Check if already assigned
        existing = db.query(TrainingAssignment).filter(
            TrainingAssignment.simulation_id == sim.id,
            TrainingAssignment.operator_id == op.id,
        ).first()
        if existing:
            results.append({
                "operator_id": emp_id,
                "status": "already_assigned",
                "training_link": f"/t/{existing.link_token}",
            })
            continue

        token = generate_link_token(sim.id, op.id)
        assignment = TrainingAssignment(
            simulation_id=sim.id,
            operator_id=op.id,
            link_token=token,
        )
        db.add(assignment)
        db.flush()
        results.append({
            "operator_id": emp_id,
            "status": "assigned",
            "assignment_id": assignment.id,
            "training_link": f"/t/{token}",
        })

    db.commit()
    return {"simulation_id": sim.id, "assignments": results}


@router.get("/assignments", dependencies=[Depends(require_admin)])
def list_assignments(simulation_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(TrainingAssignment)
    if simulation_id:
        q = q.filter(TrainingAssignment.simulation_id == simulation_id)
    assignments = q.order_by(TrainingAssignment.assigned_at.desc()).all()
    return [_assignment_to_dict(a) for a in assignments]


# --- Operator Search ---

@router.get("/operators/search", dependencies=[Depends(require_admin)])
def search_operator(operator_id: str, db: Session = Depends(get_db)):
    op = db.query(Operator).filter(Operator.operator_id == operator_id).first()
    if not op:
        raise HTTPException(status_code=404, detail=f"Operator '{operator_id}' not found")

    assignments = db.query(TrainingAssignment).filter(
        TrainingAssignment.operator_id == op.id
    ).order_by(TrainingAssignment.assigned_at.desc()).all()

    pending = []
    completed = []
    for a in assignments:
        entry = _assignment_to_dict(a)
        if a.status == "completed":
            completed.append(entry)
        else:
            pending.append(entry)

    return {
        "operator_id": op.operator_id,
        "name": op.name,
        "pending_trainings": pending,
        "completed_trainings": completed,
        "total_assigned": len(assignments),
        "total_completed": len(completed),
        "total_pending": len(pending),
    }


# --- Dashboard stats ---

@router.get("/dashboard/overview", dependencies=[Depends(require_admin)])
def dashboard_overview(db: Session = Depends(get_db)):
    total_sims = db.query(Simulation).filter(Simulation.status == "published").count()
    total_operators = db.query(Operator).count()
    total_assignments = db.query(TrainingAssignment).count()
    total_completed = db.query(TrainingAssignment).filter(TrainingAssignment.status == "completed").count()
    total_pending = db.query(TrainingAssignment).filter(TrainingAssignment.status != "completed").count()

    completions = db.query(TrainingCompletion).all()
    avg_score = 0.0
    failed_count = 0
    if completions:
        scores = [c.quiz_score / c.total_questions * 100 for c in completions if c.total_questions > 0]
        avg_score = sum(scores) / len(scores) if scores else 0
        failed_count = sum(1 for c in completions if not c.passed)

    return {
        "total_simulations": total_sims,
        "total_operators": total_operators,
        "total_assignments": total_assignments,
        "total_completed": total_completed,
        "total_pending": total_pending,
        "completion_rate": round(total_completed / total_assignments * 100, 1) if total_assignments > 0 else 0,
        "average_quiz_score": round(avg_score, 1),
        "failed_operators": failed_count,
    }


@router.get("/dashboard/simulation/{sim_id}", dependencies=[Depends(require_admin)])
def dashboard_simulation(sim_id: str, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    assignments = db.query(TrainingAssignment).filter(TrainingAssignment.simulation_id == sim_id).all()
    completed_assignments = [a for a in assignments if a.status == "completed"]

    # Step-level aggregation
    step_stats = {}
    for a in completed_assignments:
        if a.completion:
            for sm in a.completion.step_metrics:
                if sm.step_id not in step_stats:
                    step_stats[sm.step_id] = {"wrong_attempts": 0, "hints_used": 0, "skips": 0, "count": 0}
                step_stats[sm.step_id]["wrong_attempts"] += sm.wrong_attempts
                step_stats[sm.step_id]["hints_used"] += sm.hints_used
                step_stats[sm.step_id]["skips"] += 1 if sm.skipped else 0
                step_stats[sm.step_id]["count"] += 1

    # Average per step
    for sid, stats in step_stats.items():
        n = stats["count"]
        stats["avg_wrong_attempts"] = round(stats["wrong_attempts"] / n, 1) if n else 0
        stats["avg_hints_used"] = round(stats["hints_used"] / n, 1) if n else 0
        stats["skip_rate"] = round(stats["skips"] / n * 100, 1) if n else 0

    return {
        "simulation_id": sim.id,
        "workflow_name": sim.workflow_name,
        "total_assigned": len(assignments),
        "total_completed": len(completed_assignments),
        "completion_rate": round(len(completed_assignments) / len(assignments) * 100, 1) if assignments else 0,
        "step_analytics": step_stats,
        "operators": [_assignment_to_dict(a) for a in assignments],
    }


def _assignment_to_dict(a: TrainingAssignment) -> dict:
    d = {
        "assignment_id": a.id,
        "operator_id": a.operator.operator_id if a.operator else None,
        "operator_name": a.operator.name if a.operator else None,
        "simulation_id": a.simulation_id,
        "simulation_name": a.simulation.workflow_name if a.simulation else None,
        "status": a.status,
        "training_link": f"/t/{a.link_token}",
        "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
        "started_at": a.started_at.isoformat() if a.started_at else None,
        "completed_at": a.completed_at.isoformat() if a.completed_at else None,
    }
    if a.completion:
        d["quiz_score"] = a.completion.quiz_score
        d["total_questions"] = a.completion.total_questions
        d["passed"] = a.completion.passed
        d["time_taken_seconds"] = a.completion.time_taken_seconds
        d["total_hints_used"] = a.completion.total_hints_used
        d["total_skips"] = a.completion.total_skips
    return d

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")


@router.post("/generate-from-upload", dependencies=[Depends(require_admin)])
async def generate_from_upload(
    workflow_name: str = Form(...),
    screenshots: list[UploadFile] = File(default=[]),
    prd_files: list[UploadFile] = File(default=[]),
    sop_files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    """Accept file uploads (PNGs for screens, PDFs for PRD/SOP), run the AI pipeline, and create a simulation."""
    job_id = str(uuid.uuid4())[:8]
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    screens_dir = os.path.join(job_dir, "screens")
    os.makedirs(screens_dir, exist_ok=True)

    try:
        # Save screenshot PNGs
        for f in screenshots:
            dest = os.path.join(screens_dir, f.filename or f"screen_{uuid.uuid4()[:6]}.png")
            with open(dest, "wb") as out:
                out.write(await f.read())

        # Extract text from PRD PDFs
        prd_text = ""
        for f in prd_files:
            tmp = os.path.join(job_dir, f.filename or "prd.pdf")
            with open(tmp, "wb") as out:
                out.write(await f.read())
            with pdfplumber.open(tmp) as pdf:
                for page in pdf.pages:
                    prd_text += (page.extract_text() or "") + "\n"

        # Extract text from SOP PDFs
        sop_text = ""
        for f in sop_files:
            tmp = os.path.join(job_dir, f.filename or "sop.pdf")
            with open(tmp, "wb") as out:
                out.write(await f.read())
            with pdfplumber.open(tmp) as pdf:
                for page in pdf.pages:
                    sop_text += (page.extract_text() or "") + "\n"

        # Build figma description from screenshot filenames
        screen_files = sorted(os.listdir(screens_dir))
        figma_desc = f"Screenshots uploaded: {', '.join(screen_files)}" if screen_files else ""

        # Combine PRD + SOP as code_text (SOP serves as process documentation)
        combined_code = sop_text.strip() if sop_text.strip() else "No SOP provided."

        if not prd_text.strip():
            raise HTTPException(status_code=400, detail="At least one PRD PDF is required.")

        # Run the AI pipeline
        result = run_pipeline(
            prd_text=prd_text,
            code_text=combined_code,
            figma_description=figma_desc,
            workflow_name=workflow_name,
            screenshots_dir=screens_dir,
            generate_video=False,
        )

        manifest_data = result.manifest.model_dump()
        assessment_data = result.assessment.model_dump()
        wf_id = manifest_data.get("workflow_id", f"upload_{job_id}")

        # Create simulation in DB
        existing = db.query(Simulation).filter(Simulation.workflow_id == wf_id).first()
        if existing:
            wf_id = f"{wf_id}_{job_id}"

        sim = Simulation(
            workflow_id=wf_id,
            workflow_name=workflow_name,
            manifest_json=manifest_data,
            assessment_json=assessment_data,
            status="draft",
        )
        db.add(sim)
        db.commit()
        db.refresh(sim)

        return {
            "status": "ok",
            "simulation_id": sim.id,
            "workflow_id": wf_id,
            "workflow_name": workflow_name,
            "steps_generated": len(manifest_data.get("steps", [])),
            "questions_generated": len(assessment_data.get("questions", [])),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")
    finally:
        # Clean up uploaded files
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir, ignore_errors=True)

