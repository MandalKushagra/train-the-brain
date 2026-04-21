"""Pydantic models for data flowing between agents."""
from pydantic import BaseModel
from typing import Any, Optional


class UIElement(BaseModel):
    id: str
    type: str  # button, input, dropdown, card, tab, text
    label: str
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None


class Screen(BaseModel):
    id: str
    name: str
    source: str  # figma, code, prd, or combination
    elements: list[UIElement]
    screenshot_path: Optional[str] = None


class NavigationRule(BaseModel):
    from_screen: str
    to_screen: str
    trigger: str  # element id or action that causes navigation


class ValidationRule(BaseModel):
    screen: str
    rule: str


class ErrorScenario(BaseModel):
    trigger: str
    message: str
    screen: Optional[str] = None


# --- Agent 1 Output ---
class UnifiedContent(BaseModel):
    screens: list[Screen]
    navigation: list[NavigationRule]
    validation_rules: list[ValidationRule]
    error_scenarios: list[ErrorScenario]


# --- Agent 2 Output ---
class WorkflowStep(BaseModel):
    step_id: int
    screen: str
    action: str  # TAP, TYPE, SCAN, SELECT, VERIFY
    target: Optional[Any] = None  # element id or object
    description: str = ""  # what happens at this step


class Branch(BaseModel):
    at_step: int
    condition: str
    insert_step: Optional[Any] = None
    check: Optional[str] = None


class WorkflowGraph(BaseModel):
    steps: list[WorkflowStep]
    branches: list[Branch]
    error_scenarios: list[ErrorScenario]


# --- Agent 3 Output ---
class StepScript(BaseModel):
    step_id: int
    screen: str
    title: str
    instruction: str  # short text shown on screen overlay
    narration: str  # longer text for TTS voiceover
    highlight_element: str  # element id to highlight
    highlight_coords: Optional[dict] = None  # {x, y, w, h} on screenshot
    expected_action: str
    on_wrong_action: str
    screenshot_path: Optional[str] = None


class VideoScriptManifest(BaseModel):
    workflow_id: str
    workflow_name: str
    target_users: list[str]
    language: str
    steps: list[StepScript]
    error_scenarios: list[ErrorScenario]


# --- Agent 4 Output ---
class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    correct: int  # index of correct option


class Assessment(BaseModel):
    questions: list[QuizQuestion]
    pass_threshold: float = 0.6


# --- Final combined output ---
class TrainingPackage(BaseModel):
    manifest: VideoScriptManifest
    assessment: Assessment
    video_path: Optional[str] = None
