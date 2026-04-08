"""Agent 2 — Workflow Extraction.
Takes UnifiedContent from Agent 1.
Outputs an ordered WorkflowGraph with steps, branches, and error scenarios.
"""
from services.llm_service import call_llm_json
from models.schemas import UnifiedContent, WorkflowGraph

SYSTEM_CONTEXT = """You are a workflow analysis agent.
Your job is to take structured UI data and determine the exact step-by-step
user journey. Think like a user — what do they do first? What next?
Identify the happy path, then the branches and error states.
Order steps logically. Be precise about which element the user interacts with."""


def run(content: UnifiedContent) -> WorkflowGraph:
    """Run the workflow extraction agent."""
    prompt = f"""Given this structured app data, determine the step-by-step user workflow.

## App Data:
{content.model_dump_json(indent=2)}

Return a JSON object with this exact structure:
{{
  "steps": [
    {{
      "step_id": 1,
      "screen": "screen_id",
      "action": "TAP|TYPE|SCAN|SELECT|VERIFY",
      "target": "element_id",
      "description": "what the user does at this step"
    }}
  ],
  "branches": [
    {{
      "at_step": 3,
      "condition": "what triggers the branch",
      "insert_step": "optional extra step description",
      "check": "optional permission or validation check"
    }}
  ],
  "error_scenarios": [
    {{
      "trigger": "what causes it",
      "message": "error message",
      "screen": "screen_id"
    }}
  ]
}}

Order steps in the sequence a user would naturally follow.
Include ALL meaningful interactions — don't skip steps.
"""
    result = call_llm_json(prompt, SYSTEM_CONTEXT)
    return WorkflowGraph(**result)
