"""LLM Service — wraps Gemini Pro via google.genai (new SDK). Swap-able if you need to change provider later."""
import json
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL, SECURITY_GUARDRAILS


client = genai.Client(api_key=GEMINI_API_KEY)


def call_llm(prompt: str, system_context: str = "") -> str:
    """Call Gemini with security guardrails baked in."""
    full_prompt = f"{SECURITY_GUARDRAILS}\n\n{system_context}\n\n{prompt}"
    response = client.models.generate_content(model=GEMINI_MODEL, contents=full_prompt)
    return response.text


def call_llm_json(prompt: str, system_context: str = "") -> dict:
    """Call Gemini and parse the response as JSON."""
    full_prompt = (
        f"{SECURITY_GUARDRAILS}\n\n{system_context}\n\n{prompt}\n\n"
        "IMPORTANT: Return ONLY valid JSON. No markdown, no ```json blocks, no explanation. Just the JSON object."
    )
    response = client.models.generate_content(model=GEMINI_MODEL, contents=full_prompt)
    text = response.text.strip()
    # Strip markdown code fences if Gemini adds them
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()
    return json.loads(text)
