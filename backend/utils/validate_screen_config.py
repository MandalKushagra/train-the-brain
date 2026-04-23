"""Validation utility for ScreenConfig JSON objects."""

from typing import Any

VALID_ELEMENT_TYPES = [
    "button", "input", "dropdown", "card", "tab",
    "text_label", "header", "navigation_bar", "icon", "checkbox", "scan_input",
]

VALID_SOURCES = ["vision_ai", "manual"]


def _validate_element(element: Any, path: str, errors: list[dict]) -> None:
    """Validate a single ScreenConfig element and its children recursively."""
    if not isinstance(element, dict):
        errors.append({"path": path, "message": "element must be an object"})
        return

    if not element.get("component_id") or not isinstance(element.get("component_id"), str):
        errors.append({"path": f"{path}.component_id", "message": "component_id is required and must be a string"})

    el_type = element.get("type")
    if not el_type or not isinstance(el_type, str):
        errors.append({"path": f"{path}.type", "message": "type is required and must be a string"})
    elif el_type not in VALID_ELEMENT_TYPES:
        errors.append({"path": f"{path}.type", "message": f"type must be one of: {', '.join(VALID_ELEMENT_TYPES)}"})

    pos = element.get("position")
    if not isinstance(pos, dict):
        errors.append({"path": f"{path}.position", "message": "position is required and must be an object"})
    else:
        for field in ("x", "y", "width", "height"):
            val = pos.get(field)
            if not isinstance(val, (int, float)) or val < 0 or val > 100:
                errors.append({
                    "path": f"{path}.position.{field}",
                    "message": f"{field} is required and must be a number between 0 and 100",
                })

    children = element.get("children")
    if isinstance(children, list):
        for i, child in enumerate(children):
            _validate_element(child, f"{path}.children[{i}]", errors)


def validate_screen_config(config: Any) -> dict:
    """Validate a ScreenConfig JSON object.

    Returns:
        dict with 'valid' (bool) and 'errors' (list of {path, message}).
    """
    errors: list[dict] = []

    if not isinstance(config, dict):
        return {"valid": False, "errors": [{"path": "", "message": "config must be an object"}]}

    if not config.get("screen_id") or not isinstance(config.get("screen_id"), str):
        errors.append({"path": "screen_id", "message": "screen_id is required and must be a string"})

    if not config.get("screen_name") or not isinstance(config.get("screen_name"), str):
        errors.append({"path": "screen_name", "message": "screen_name is required and must be a string"})

    source = config.get("source")
    if source not in VALID_SOURCES:
        errors.append({"path": "source", "message": 'source is required and must be "vision_ai" or "manual"'})

    elements = config.get("elements")
    if not isinstance(elements, list):
        errors.append({"path": "elements", "message": "elements is required and must be an array"})
    else:
        for i, el in enumerate(elements):
            _validate_element(el, f"elements[{i}]", errors)

    return {"valid": len(errors) == 0, "errors": errors}
