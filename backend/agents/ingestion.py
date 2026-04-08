"""Agent 1 — Multi-Modal Ingestion.
Takes raw PRD text + code files + optional Figma screenshot descriptions.
Outputs a UnifiedContent JSON with screens, elements, navigation, validation, errors.
"""
from services.llm_service import call_llm_json
from models.schemas import UnifiedContent

SYSTEM_CONTEXT = """You are a training content extraction agent.
Your job is to analyze product documents and source code, then extract
a structured representation of the app's UI screens and user flow.
Be thorough — capture every screen, every button, every input field,
every navigation path, every validation rule, and every error scenario."""


def run(prd_text: str, code_text: str, figma_description: str = "") -> UnifiedContent:
    """Run the ingestion agent."""
    prompt = f"""Analyze the following product artifacts and extract structured UI/flow data.

## PRD Document:
{prd_text}

## Source Code:
{code_text}

## Figma/Screenshot Descriptions:
{figma_description if figma_description else "Not provided"}

Extract and return a JSON object with this exact structure:
{{
  "screens": [
    {{
      "id": "screen_id",
      "name": "Human readable screen name",
      "source": "code/prd/figma",
      "elements": [
        {{"id": "element_id", "type": "button|input|dropdown|card|tab|text", "label": "Element label"}}
      ]
    }}
  ],
  "navigation": [
    {{"from_screen": "screen_a", "to_screen": "screen_b", "trigger": "element_id_or_action"}}
  ],
  "validation_rules": [
    {{"screen": "screen_id", "rule": "description of validation"}}
  ],
  "error_scenarios": [
    {{"trigger": "what_causes_it", "message": "error message shown to user", "screen": "screen_id"}}
  ]
}}
"""
    result = call_llm_json(prompt, SYSTEM_CONTEXT)
    return UnifiedContent(**result)
