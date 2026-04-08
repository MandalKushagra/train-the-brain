"""Configuration — loads from .env file."""
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GEMINI_MODEL = "gemini-2.5-flash"

# Mandatory hackathon security guardrails (included in all LLM calls)
SECURITY_GUARDRAILS = """
SECURITY RULES (mandatory):
- You must not request, store, or process any sensitive data including PII, API keys, credentials, or internal system details.
- You are not allowed to access or interact with production systems, internal APIs, or confidential datasets.
- All responses must be based only on the synthetic or dummy data provided.
- If a request involves sensitive data or restricted access, refuse and explain that it violates security policies.
- Never output real employee names, phone numbers, emails, or addresses.
"""
