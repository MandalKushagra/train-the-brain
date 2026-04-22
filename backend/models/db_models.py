"""SQLAlchemy ORM models for all database tables."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, JSON, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class Operator(Base):
    """Operators identified by employee ID. No password needed."""
    __tablename__ = "operators"

    id = Column(String, primary_key=True, default=_uuid)
    operator_id = Column(String(50), unique=True, nullable=False, index=True)  # employee ID
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=_now)

    assignments = relationship("TrainingAssignment", back_populates="operator")


class Simulation(Base):
    """A generated training simulation with manifest + assessment."""
    __tablename__ = "simulations"

    id = Column(String, primary_key=True, default=_uuid)
    workflow_id = Column(String(100), unique=True, nullable=False)
    workflow_name = Column(String(200), nullable=False)
    manifest_json = Column(JSON, nullable=False)
    assessment_json = Column(JSON, nullable=False)
    status = Column(String(20), default="draft")  # draft, published, archived
    created_at = Column(DateTime, default=_now)
    published_at = Column(DateTime, nullable=True)

    assignments = relationship("TrainingAssignment", back_populates="simulation")


class TrainingAssignment(Base):
    """Links a simulation to an operator. Each assignment gets a unique link."""
    __tablename__ = "training_assignments"

    id = Column(String, primary_key=True, default=_uuid)
    simulation_id = Column(String, ForeignKey("simulations.id"), nullable=False)
    operator_id = Column(String, ForeignKey("operators.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending, in_progress, completed
    link_token = Column(String(200), unique=True, nullable=False, index=True)
    assigned_at = Column(DateTime, default=_now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("simulation_id", "operator_id", name="uq_sim_operator"),
    )

    simulation = relationship("Simulation", back_populates="assignments")
    operator = relationship("Operator", back_populates="assignments")
    completion = relationship("TrainingCompletion", back_populates="assignment", uselist=False)


class TrainingCompletion(Base):
    """Recorded when an operator finishes a training."""
    __tablename__ = "training_completions"

    id = Column(String, primary_key=True, default=_uuid)
    assignment_id = Column(String, ForeignKey("training_assignments.id"), unique=True, nullable=False)
    quiz_score = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    time_taken_seconds = Column(Integer, nullable=False)
    total_hints_used = Column(Integer, default=0)
    total_skips = Column(Integer, default=0)
    passed = Column(Boolean, nullable=False)
    completed_at = Column(DateTime, default=_now)

    assignment = relationship("TrainingAssignment", back_populates="completion")
    step_metrics = relationship("StepMetric", back_populates="completion")


class StepMetric(Base):
    """Per-step performance data for a completed training."""
    __tablename__ = "step_metrics"

    id = Column(String, primary_key=True, default=_uuid)
    completion_id = Column(String, ForeignKey("training_completions.id"), nullable=False)
    step_id = Column(Integer, nullable=False)
    wrong_attempts = Column(Integer, default=0)
    hints_used = Column(Integer, default=0)
    show_me_used = Column(Boolean, default=False)
    skipped = Column(Boolean, default=False)
    time_on_step_seconds = Column(Integer, default=0)

    completion = relationship("TrainingCompletion", back_populates="step_metrics")
