"""S3 Service — handles all artifact storage.

Upload strategy:
  - Input artifacts (PDFs, code files, screenshots) → s3://{bucket}/jobs/{job_id}/inputs/
  - Pipeline outputs (manifest JSON, assessment JSON) → s3://{bucket}/jobs/{job_id}/outputs/
  - Large outputs are stored in S3, only metadata in SQLite.

Uses boto3 with standard AWS credential chain (.env, IAM role, etc.)
"""
import os
import json
import uuid
import boto3
from botocore.exceptions import ClientError
from typing import Optional

S3_BUCKET = os.getenv("S3_BUCKET", "train-the-brain-artifacts")
S3_REGION = os.getenv("AWS_REGION", "ap-south-1")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            region_name=S3_REGION,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
    return _client


def _ensure_bucket():
    """Create bucket if it doesn't exist (for dev/hackathon convenience)."""
    client = _get_client()
    try:
        client.head_bucket(Bucket=S3_BUCKET)
    except ClientError:
        try:
            client.create_bucket(
                Bucket=S3_BUCKET,
                CreateBucketConfiguration={"LocationConstraint": S3_REGION},
            )
        except ClientError:
            pass  # bucket may already exist in another account — proceed anyway


# ── Upload helpers ──────────────────────────────────────────────


def upload_file_bytes(job_id: str, filename: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload raw bytes to S3. Returns the S3 key."""
    _ensure_bucket()
    key = f"jobs/{job_id}/inputs/{filename}"
    _get_client().put_object(Bucket=S3_BUCKET, Key=key, Body=data, ContentType=content_type)
    return key


def upload_json(job_id: str, name: str, payload: dict) -> str:
    """Upload a JSON dict to S3 outputs folder. Returns the S3 key."""
    _ensure_bucket()
    key = f"jobs/{job_id}/outputs/{name}.json"
    body = json.dumps(payload, indent=2, default=str)
    _get_client().put_object(
        Bucket=S3_BUCKET, Key=key, Body=body.encode(), ContentType="application/json"
    )
    return key


def upload_text(job_id: str, filename: str, text: str) -> str:
    """Upload plain text (PRD paste, code paste) to S3 inputs."""
    _ensure_bucket()
    key = f"jobs/{job_id}/inputs/{filename}"
    _get_client().put_object(
        Bucket=S3_BUCKET, Key=key, Body=text.encode(), ContentType="text/plain"
    )
    return key


# ── Download helpers ────────────────────────────────────────────


def download_text(key: str) -> str:
    """Download a text/JSON object from S3."""
    resp = _get_client().get_object(Bucket=S3_BUCKET, Key=key)
    return resp["Body"].read().decode()


def download_json(key: str) -> dict:
    """Download and parse a JSON object from S3."""
    text = download_text(key)
    return json.loads(text)


def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for downloading an S3 object."""
    return _get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )


# ── Listing ─────────────────────────────────────────────────────


def list_job_inputs(job_id: str) -> list[str]:
    """List all input artifact keys for a job."""
    prefix = f"jobs/{job_id}/inputs/"
    resp = _get_client().list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
    return [obj["Key"] for obj in resp.get("Contents", [])]
