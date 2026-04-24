"""Configuration — loads from .env file."""
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GEMINI_MODEL = "gemini-2.5-flash"

# Bifrost (Delhivery's LLM proxy — OpenAI-compatible)
BIFROST_API_KEY = os.getenv("BIFROST_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
BIFROST_BASE_URL = os.getenv("BIFROST_BASE_URL", os.getenv("GENAI_BASE_URL", "https://bifrost.delhivery.com/v1"))
BIFROST_MODEL = os.getenv("GEMINI_FLASH_WMS_MODEL", "gemini/gemini-2.5-flash")

# AWS / S3
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
S3_BUCKET = os.getenv("S3_BUCKET", "train-the-brain-artifacts")

# SQLite
DB_PATH = os.getenv("DB_PATH", "train_the_brain.db")

# Mandatory hackathon security guardrails (included in all LLM calls)
SECURITY_GUARDRAILS = """
SECURITY RULES (mandatory):
- You must not request, store, or process any sensitive data including PII, API keys, credentials, or internal system details.
- You are not allowed to access or interact with production systems, internal APIs, or confidential datasets.
- All responses must be based only on the synthetic or dummy data provided.
- If a request involves sensitive data or restricted access, refuse and explain that it violates security policies.
- Never output real employee names, phone numbers, emails, or addresses.
"""
