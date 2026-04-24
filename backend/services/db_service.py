"""SQLite job tracker — lightweight metadata store.

SQLite stores job metadata (status, timestamps, S3 keys).
The actual large payloads (manifest, assessment) live in S3.
This keeps the DB small and fast.
"""
import os
import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "train_the_brain.db")

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
    return _local.conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            workflow_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            -- S3 keys for inputs
            prd_s3_key TEXT,
            code_s3_key TEXT,
            figma_s3_key TEXT,
            screenshots_s3_keys TEXT,  -- JSON array of keys
            -- S3 keys for outputs
            manifest_s3_key TEXT,
            assessment_s3_key TEXT,
            -- Error info
            error_message TEXT,
            -- Extra metadata
            figma_url TEXT,
            input_metadata TEXT  -- JSON blob for any extra info
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);

        -- ── Training assignments ───────────────────────────────
        -- Each row = one user assigned to one training (job).
        -- The unique token IS the shareable link.
        CREATE TABLE IF NOT EXISTS training_assignments (
            id TEXT PRIMARY KEY,              -- unique token (used in the link)
            job_id TEXT NOT NULL,             -- which pipeline job (manifest) this is for
            user_name TEXT NOT NULL,          -- operator name / display name
            user_email TEXT,                  -- optional email
            user_id TEXT,                     -- optional external employee ID
            status TEXT NOT NULL DEFAULT 'pending',  -- pending | in_progress | completed
            current_step INTEGER DEFAULT 0,  -- which step the user is currently on
            total_steps INTEGER DEFAULT 0,   -- total steps in the manifest (cached)
            quiz_score REAL,                 -- final quiz score (0.0 - 1.0)
            quiz_passed INTEGER,             -- 1 = passed, 0 = failed, NULL = not taken
            quiz_answers TEXT,               -- JSON array of user's answers
            started_at TEXT,                 -- when user first opened the link
            completed_at TEXT,               -- when user finished the training
            assigned_at TEXT NOT NULL,        -- when PM created this assignment
            assigned_by TEXT,                -- PM who assigned it
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_assignments_job ON training_assignments(job_id);
        CREATE INDEX IF NOT EXISTS idx_assignments_status ON training_assignments(status);
        CREATE INDEX IF NOT EXISTS idx_assignments_user ON training_assignments(user_name);

        -- ── Step-level progress tracking ───────────────────────
        -- One row per step the user has interacted with.
        -- Enables "40% got stuck on Step 3" analytics.
        CREATE TABLE IF NOT EXISTS step_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id TEXT NOT NULL,
            step_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',  -- pending | completed | skipped | wrong_attempt
            attempts INTEGER DEFAULT 0,       -- how many tries on this step
            time_spent_sec REAL DEFAULT 0,    -- seconds spent on this step
            completed_at TEXT,
            FOREIGN KEY (assignment_id) REFERENCES training_assignments(id),
            UNIQUE(assignment_id, step_id)
        );

        CREATE INDEX IF NOT EXISTS idx_step_progress_assignment ON step_progress(assignment_id);
    """)
    conn.commit()


def create_job(
    job_id: str,
    workflow_name: str,
    prd_s3_key: Optional[str] = None,
    code_s3_key: Optional[str] = None,
    figma_s3_key: Optional[str] = None,
    figma_url: Optional[str] = None,
    screenshots_s3_keys: Optional[list[str]] = None,
) -> dict:
    """Insert a new job record."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    conn.execute(
        """INSERT INTO jobs
           (id, workflow_name, status, created_at, updated_at,
            prd_s3_key, code_s3_key, figma_s3_key, figma_url, screenshots_s3_keys)
           VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?)""",
        (
            job_id, workflow_name, now, now,
            prd_s3_key, code_s3_key, figma_s3_key, figma_url,
            json.dumps(screenshots_s3_keys) if screenshots_s3_keys else None,
        ),
    )
    conn.commit()
    return get_job(job_id)


def update_job_status(job_id: str, status: str, **kwargs):
    """Update job status and optional fields (manifest_s3_key, error_message, etc.)."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    sets = ["status = ?", "updated_at = ?"]
    vals = [status, now]
    for col in ("manifest_s3_key", "assessment_s3_key", "error_message"):
        if col in kwargs and kwargs[col] is not None:
            sets.append(f"{col} = ?")
            vals.append(kwargs[col])
    vals.append(job_id)
    conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", vals)
    conn.commit()


def get_job(job_id: str) -> Optional[dict]:
    """Fetch a job by ID."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    return dict(row)


def list_jobs(status: Optional[str] = None, limit: int = 50) -> list[dict]:
    """List recent jobs, optionally filtered by status."""
    conn = _get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Training Assignment CRUD ────────────────────────────────────


def create_assignment(
    assignment_id: str,
    job_id: str,
    user_name: str,
    total_steps: int,
    user_email: Optional[str] = None,
    user_id: Optional[str] = None,
    assigned_by: Optional[str] = None,
) -> dict:
    """Create a training assignment. The assignment_id becomes the unique link token."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    conn.execute(
        """INSERT INTO training_assignments
           (id, job_id, user_name, user_email, user_id, status,
            current_step, total_steps, assigned_at, assigned_by)
           VALUES (?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?)""",
        (assignment_id, job_id, user_name, user_email, user_id, total_steps, now, assigned_by),
    )
    conn.commit()
    return get_assignment(assignment_id)


def get_assignment(assignment_id: str) -> Optional[dict]:
    """Fetch an assignment by its unique token."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM training_assignments WHERE id = ?", (assignment_id,)).fetchone()
    return dict(row) if row else None


def list_assignments_for_job(job_id: str) -> list[dict]:
    """List all assignments for a given training job."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM training_assignments WHERE job_id = ? ORDER BY assigned_at DESC",
        (job_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def start_training(assignment_id: str):
    """Mark training as in_progress when user first opens the link."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    conn.execute(
        """UPDATE training_assignments
           SET status = 'in_progress', started_at = COALESCE(started_at, ?)
           WHERE id = ? AND status IN ('pending', 'in_progress')""",
        (now, assignment_id),
    )
    conn.commit()


def update_step_progress(assignment_id: str, step_id: int, current_step: int):
    """Record that a user completed a step and advance their position."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    # Upsert step_progress
    conn.execute(
        """INSERT INTO step_progress (assignment_id, step_id, status, attempts, completed_at)
           VALUES (?, ?, 'completed', 1, ?)
           ON CONFLICT(assignment_id, step_id)
           DO UPDATE SET status = 'completed', attempts = attempts + 1, completed_at = ?""",
        (assignment_id, step_id, now, now),
    )
    # Update current position
    conn.execute(
        "UPDATE training_assignments SET current_step = ? WHERE id = ?",
        (current_step, assignment_id),
    )
    conn.commit()


def record_wrong_attempt(assignment_id: str, step_id: int):
    """Record a wrong attempt on a step (for analytics)."""
    conn = _get_conn()
    conn.execute(
        """INSERT INTO step_progress (assignment_id, step_id, status, attempts)
           VALUES (?, ?, 'wrong_attempt', 1)
           ON CONFLICT(assignment_id, step_id)
           DO UPDATE SET attempts = attempts + 1""",
        (assignment_id, step_id),
    )
    conn.commit()


def complete_training(assignment_id: str, quiz_score: float, quiz_passed: bool, quiz_answers: list):
    """Mark training as completed with quiz results."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    conn.execute(
        """UPDATE training_assignments
           SET status = 'completed', completed_at = ?,
               quiz_score = ?, quiz_passed = ?, quiz_answers = ?
           WHERE id = ?""",
        (now, quiz_score, 1 if quiz_passed else 0, json.dumps(quiz_answers), assignment_id),
    )
    conn.commit()


def get_step_progress(assignment_id: str) -> list[dict]:
    """Get all step-level progress for an assignment."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM step_progress WHERE assignment_id = ? ORDER BY step_id",
        (assignment_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Dashboard / Analytics queries ───────────────────────────────


def get_job_stats(job_id: str) -> dict:
    """Get aggregate stats for a training job (for PM dashboard)."""
    conn = _get_conn()
    row = conn.execute(
        """SELECT
             COUNT(*) as total_assigned,
             SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
             SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
             SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
             AVG(CASE WHEN quiz_score IS NOT NULL THEN quiz_score END) as avg_quiz_score,
             SUM(CASE WHEN quiz_passed = 1 THEN 1 ELSE 0 END) as quiz_passed_count
           FROM training_assignments WHERE job_id = ?""",
        (job_id,),
    ).fetchone()
    return dict(row) if row else {}


def get_step_analytics(job_id: str) -> list[dict]:
    """Get step-level analytics across all users for a job (e.g., '40% stuck on Step 3')."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT
             sp.step_id,
             COUNT(DISTINCT sp.assignment_id) as users_reached,
             SUM(CASE WHEN sp.status = 'completed' THEN 1 ELSE 0 END) as users_completed,
             SUM(sp.attempts) as total_attempts,
             AVG(sp.time_spent_sec) as avg_time_sec
           FROM step_progress sp
           JOIN training_assignments ta ON sp.assignment_id = ta.id
           WHERE ta.job_id = ?
           GROUP BY sp.step_id
           ORDER BY sp.step_id""",
        (job_id,),
    ).fetchall()
    return [dict(r) for r in rows]
