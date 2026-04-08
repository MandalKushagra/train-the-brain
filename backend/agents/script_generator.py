"""Agent 3 — Script & Overlay Generation.
Takes WorkflowGraph from Agent 2.
Outputs VideoScriptManifest with narration, overlay text, highlight coords per step.
This output feeds BOTH the video generator AND the web simulator.
"""
from services.llm_service import call_llm_json
from models.schemas import WorkflowGraph, VideoScriptManifest

SYSTEM_CONTEXT = """You are a training script writer agent.
Your job is to create clear, simple training instructions for warehouse operators.
Write like you're explaining to someone who has never used this app before.
Keep language simple — these are blue-collar workers, not engineers.
Narration should sound natural when read aloud (it will be used for TTS).
Instructions on screen should be SHORT — max 10 words."""


def run(workflow: WorkflowGraph, workflow_name: str = "Training Flow") -> VideoScriptManifest:
    """Run the script generator agent."""
    prompt = f"""Create a training script for each step of this workflow.

## Workflow:
{workflow.model_dump_json(indent=2)}

For each step, generate:
- title: short title (3-5 words)
- instruction: what to show on screen overlay (max 10 words)
- narration: what a trainer would say out loud (1-2 sentences, simple language)
- highlight_element: element id to highlight
- expected_action: TAP, TYPE, SCAN, SELECT, or VERIFY
- on_wrong_action: what to show if user does the wrong thing

Return JSON:
{{
  "workflow_id": "auto_generated_id",
  "workflow_name": "{workflow_name}",
  "target_users": ["fc_operators"],
  "language": "en",
  "steps": [
    {{
      "step_id": 1,
      "screen": "screen_id",
      "title": "Short Title",
      "instruction": "Tap the search box",
      "narration": "First, tap on the search box to find your product.",
      "highlight_element": "element_id",
      "expected_action": "TAP",
      "on_wrong_action": "Please tap the search box at the top of the screen."
    }}
  ],
  "error_scenarios": [
    {{"trigger": "what_causes_it", "message": "error message"}}
  ]
}}
"""
    result = call_llm_json(prompt, SYSTEM_CONTEXT)
    return VideoScriptManifest(**result)
