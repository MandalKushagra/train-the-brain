"""Utility for generating signed training link tokens."""
import hashlib
import time
from itsdangerous import URLSafeSerializer
from config import ADMIN_KEY

# Use admin key as signing secret (good enough for hackathon)
_serializer = URLSafeSerializer(ADMIN_KEY or "train-the-brain-secret")


def generate_link_token(simulation_id: str, operator_id: str) -> str:
    """Generate a unique signed token encoding simulation + operator."""
    data = {
        "sim": simulation_id,
        "op": operator_id,
        "ts": str(time.time()),
    }
    return _serializer.dumps(data)


def decode_link_token(token: str) -> dict | None:
    """Decode a training link token. Returns None if invalid."""
    try:
        return _serializer.loads(token)
    except Exception:
        return None
