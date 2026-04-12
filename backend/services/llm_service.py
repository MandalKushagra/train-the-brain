"""LLM Service — uses Bifrost (Delhivery AI Gateway) or direct Gemini API."""
import json
from config import (
    BIFROST_VIRTUAL_KEY, BIFROST_BASE_URL,
    GEMINI_API_KEY, GEMINI_MODEL, SECURITY_GUARDRAILS
)


if BIFROST_VIRTUAL_KEY:
    # Use Bifrost via OpenAI-compatible endpoint (most reliable)
    import openai
    oai_client = openai.OpenAI(
        base_url="https://bifrost.delhivery.com/openai",
        api_key="dummy-key",
        default_headers={"x-bf-vk": BIFROST_VIRTUAL_KEY}
    )
    USE_BIFROST = True
    print("🔗 Using Bifrost AI Gateway (OpenAI-compatible)")
else:
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)
    USE_BIFROST = False
    print("🔗 Using direct Gemini API (personal key)")


def call_llm(prompt: str, system_context: str = "") -> str:
    """Call LLM with security guardrails baked in."""
    full_prompt = f"{SECURITY_GUARDRAILS}\n\n{system_context}\n\n{prompt}"

    if USE_BIFROST:
        response = oai_client.chat.completions.create(
            model=f"gemini/{GEMINI_MODEL}",
            messages=[{"role": "user", "content": full_prompt}],
        )
        return response.choices[0].message.content
    else:
        response = client.models.generate_content(model=GEMINI_MODEL, contents=full_prompt)
        return response.text


def call_llm_json(prompt: str, system_context: str = "") -> dict:
    """Call LLM and parse the response as JSON."""
    full_prompt = (
        f"{SECURITY_GUARDRAILS}\n\n{system_context}\n\n{prompt}\n\n"
        "IMPORTANT: Return ONLY valid JSON. No markdown, no ```json blocks, no explanation. Just the JSON object."
    )

    if USE_BIFROST:
        response = oai_client.chat.completions.create(
            model=f"gemini/{GEMINI_MODEL}",
            messages=[{"role": "user", "content": full_prompt}],
        )
        text = response.choices[0].message.content.strip()
    else:
        response = client.models.generate_content(model=GEMINI_MODEL, contents=full_prompt)
        text = response.text.strip()

    # Strip markdown code fences if LLM adds them
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()
    return json.loads(text)
