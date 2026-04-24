"""Storage Service — abstracts S3 vs local filesystem.

In local/dev mode (USE_LOCAL_STORAGE=true or no AWS creds), stores files
on disk under ./storage/. In production, uses S3.

All other code calls this module instead of s3_service directly.
"""
import os
import json
from typing import Optional

USE_LOCAL = os.getenv("USE_LOCAL_STORAGE", "true").lower() == "true"
LOCAL_STORAGE_DIR = os.getenv("LOCAL_STORAGE_DIR", "storage")


def _local_path(key: str) -> str:
    path = os.path.join(LOCAL_STORAGE_DIR, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


# ── Upload ──────────────────────────────────────────────────────


def upload_file_bytes(job_id: str, filename: str, data: bytes, content_type: str = "") -> str:
    key = f"jobs/{job_id}/inputs/{filename}"
    if USE_LOCAL:
        with open(_local_path(key), "wb") as f:
            f.write(data)
        return key
    from services import s3_service
    return s3_service.upload_file_bytes(job_id, filename, data, content_type)


def upload_json(job_id: str, name: str, payload: dict) -> str:
    key = f"jobs/{job_id}/outputs/{name}.json"
    if USE_LOCAL:
        with open(_local_path(key), "w") as f:
            json.dump(payload, f, indent=2, default=str)
        return key
    from services import s3_service
    return s3_service.upload_json(job_id, name, payload)


def upload_text(job_id: str, filename: str, text: str) -> str:
    key = f"jobs/{job_id}/inputs/{filename}"
    if USE_LOCAL:
        with open(_local_path(key), "w") as f:
            f.write(text)
        return key
    from services import s3_service
    return s3_service.upload_text(job_id, filename, text)


# ── Download ────────────────────────────────────────────────────


def download_text(key: str) -> str:
    if USE_LOCAL:
        with open(_local_path(key), "r") as f:
            return f.read()
    from services import s3_service
    return s3_service.download_text(key)


def download_json(key: str) -> dict:
    if USE_LOCAL:
        with open(_local_path(key), "r") as f:
            return json.load(f)
    from services import s3_service
    return s3_service.download_json(key)


def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    if USE_LOCAL:
        return f"/local-storage/{key}"
    from services import s3_service
    return s3_service.generate_presigned_url(key, expires_in)


def list_job_inputs(job_id: str) -> list[str]:
    if USE_LOCAL:
        prefix = os.path.join(LOCAL_STORAGE_DIR, "jobs", job_id, "inputs")
        if not os.path.exists(prefix):
            return []
        keys = []
        for f in os.listdir(prefix):
            keys.append(f"jobs/{job_id}/inputs/{f}")
        return keys
    from services import s3_service
    return s3_service.list_job_inputs(job_id)
