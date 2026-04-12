"""LLM Service — uses Bifrost (Delhivery AI Gateway) or direct Gemini API."""
import json
from google import genai
from config import (
    BIFROST_VIRTUAL_KEY, BIFROST_BASE_URL,
    GEMINI_API_KEY, GEMINI_MODEL, SECURITY_GUARDRAILS
)


# Use Bifrost if virtual key is set, otherwise fall back to direct Gemini
if BIFROST_VIRTUAL_KEY:
    client = genai.Client(
        api_key="dummy-key",
        http_options={
            'base_url': BIFROST_BASE_URL,
            'headers': {'x-bf-vk': BIFROST_VIRTUAL_KEY}
        }
    )
    print("🔗 Using Bifrost AI Gateway")
else:
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("🔗 Using direct Gemini API (personal key)")


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
