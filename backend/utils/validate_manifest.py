"""Validation utility for SimulationManifest JSON objects."""

from typing import Any

VALID_ACTIONS = ["TAP", "TYPE", "SELECT", "SCAN", "VERIFY"]


def _validate_step(step: Any, path: str, errors: list[dict]) -> None:
    """Validate a single manifest step."""
    if not isinstance(step, dict):
        errors.append({"path": path, "message": "step must be an object"})
        return

    if not isinstance(step.get("step_id"), (int, float)):
        errors.append({"path": f"{path}.step_id", "message": "step_id is required and must be a number"})

    if not step.get("screen_id") or not isinstance(step.get("screen_id"), str):
        errors.append({"path": f"{path}.screen_id", "message": "screen_id is required and must be a string"})

    if not step.get("title") or not isinstance(step.get("title"), str):
        errors.append({"path": f"{path}.title", "message": "title is required and must be a string"})

    if not step.get("instruction") or not isinstance(step.get("instruction"), str):
        errors.append({"path": f"{path}.instruction", "message": "instruction is required and must be a string"})

    action = step.get("expected_action")
    if not action or not isinstance(action, str):
        errors.append({"path": f"{path}.expected_action", "message": "expected_action is required and must be a string"})
    elif action not in VALID_ACTIONS:
        errors.append({"path": f"{path}.expected_action", "message": f"expected_action must be one of: {', '.join(VALID_ACTIONS)}"})

    if not step.get("on_wrong_action") or not isinstance(step.get("on_wrong_action"), str):
        errors.append({"path": f"{path}.on_wrong_action", "message": "on_wrong_action is required and must be a string"})

    if not step.get("target_component_id") or not isinstance(step.get("target_component_id"), str):
        errors.append({"path": f"{path}.target_component_id", "message": "target_component_id is required and must be a string"})


def validate_manifest(manifest: Any) -> dict:
    """Validate a SimulationManifest JSON object.

    Returns:
        dict with 'valid' (bool) and 'errors' (list of {path, message}).
    """
    errors: list[dict] = []

    if not isinstance(manifest, dict):
        return {"valid": False, "errors": [{"path": "", "message": "manifest must be an object"}]}

    if not manifest.get("workflow_id") or not isinstance(manifest.get("workflow_id"), str):
        errors.append({"path": "workflow_id", "message": "workflow_id is required and must be a string"})

    if not manifest.get("workflow_name") or not isinstance(manifest.get("workflow_name"), str):
        errors.append({"path": "workflow_name", "message": "workflow_name is required and must be a string"})

    steps = manifest.get("steps")
    if not isinstance(steps, list):
        errors.append({"path": "steps", "message": "steps is required and must be an array"})
    else:
        for i, step in enumerate(steps):
            _validate_step(step, f"steps[{i}]", errors)

    screen_configs = manifest.get("screen_configs")
    if not isinstance(screen_configs, dict):
        errors.append({"path": "screen_configs", "message": "screen_configs is required and must be an object"})

    quiz_breaks = manifest.get("quiz_breaks")
    if not isinstance(quiz_breaks, list):
        errors.append({"path": "quiz_breaks", "message": "quiz_breaks is required and must be an array"})

    return {"valid": len(errors) == 0, "errors": errors}
