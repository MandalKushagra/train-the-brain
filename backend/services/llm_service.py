"""LLM Service — calls Gemini via Bifrost (OpenAI-compatible proxy).

Bifrost endpoint: https://bifrost.delhivery.com/v1/chat/completions
Model: gemini/gemini-2.5-flash
Auth: Bearer token (BIFROST_API_KEY)
"""
import json
import httpx
from config import BIFROST_API_KEY, BIFROST_BASE_URL, BIFROST_MODEL, SECURITY_GUARDRAILS

_TIMEOUT = 120  # seconds — LLM calls can be slow


def _call_bifrost(messages: list[dict], temperature: float = 0.3) -> str:
    """Call Bifrost chat completions endpoint."""
    url = f"{BIFROST_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {BIFROST_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": BIFROST_MODEL,
        "messages": messages,
        "temperature": temperature,
    }

    resp = httpx.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def call_llm(prompt: str, system_context: str = "") -> str:
    """Call LLM with security guardrails baked in."""
    messages = [
        {"role": "system", "content": f"{SECURITY_GUARDRAILS}\n\n{system_context}"},
        {"role": "user", "content": prompt},
    ]
    return _call_bifrost(messages)


def call_llm_json(prompt: str, system_context: str = "") -> dict:
    """Call LLM and parse the response as JSON."""
    json_instruction = (
        "\n\nIMPORTANT: Return ONLY valid JSON. "
        "No markdown, no ```json blocks, no explanation. Just the JSON object."
    )
    messages = [
        {"role": "system", "content": f"{SECURITY_GUARDRAILS}\n\n{system_context}"},
        {"role": "user", "content": prompt + json_instruction},
    ]
    text = _call_bifrost(messages)
    text = text.strip()

    # Strip markdown code fences if the model adds them
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    return json.loads(text)
