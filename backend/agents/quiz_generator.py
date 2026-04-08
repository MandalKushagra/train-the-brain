"""Agent 4 — Quiz/Assessment Generation.
Takes WorkflowGraph from Agent 2.
Outputs quiz questions grounded in the workflow steps.
Runs in PARALLEL with Agent 3.
"""
from services.llm_service import call_llm_json
from models.schemas import WorkflowGraph, Assessment

SYSTEM_CONTEXT = """You are a training assessment agent.
Create multiple-choice questions that test whether a warehouse operator
understood the workflow they just learned. Questions must be:
- Grounded in the actual workflow steps (no made-up info)
- Simple language (blue-collar audience)
- 4 options each, only 1 correct
- Mix of: sequence questions, error handling, branching logic"""


def run(workflow: WorkflowGraph) -> Assessment:
    """Run the quiz generator agent."""
    prompt = f"""Based on this workflow, create 5 multiple-choice quiz questions.

## Workflow:
{workflow.model_dump_json(indent=2)}

Return JSON:
{{
  "questions": [
    {{
      "question": "What is the first step in the flow?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct": 0
    }}
  ],
  "pass_threshold": 0.6
}}

Make questions test UNDERSTANDING, not memorization.
Include at least 1 question about error scenarios.
Include at least 1 question about branching/conditional logic.
"""
    result = call_llm_json(prompt, SYSTEM_CONTEXT)
    return Assessment(**result)
