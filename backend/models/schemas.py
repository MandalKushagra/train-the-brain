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


# --- Screen Config Models (Simulation Optimization) ---


class Position(BaseModel):
    x: float  # percentage 0-100
    y: float  # percentage 0-100
    width: float  # percentage 0-100
    height: float  # percentage 0-100


class ScreenConfigElement(BaseModel):
    component_id: str
    type: str  # button, input, dropdown, card, tab, text_label, header, navigation_bar, icon, checkbox, scan_input
    label: str
    position: Position
    needs_review: bool = False
    children: list["ScreenConfigElement"] = []


class ScreenConfigMetadata(BaseModel):
    source_screenshot_path: Optional[str] = None
    extraction_confidence: Optional[float] = None


class ScreenConfig(BaseModel):
    screen_id: str
    screen_name: str
    source: str  # "vision_ai" or "manual"
    elements: list[ScreenConfigElement]
    metadata: Optional[ScreenConfigMetadata] = None


# --- Simulation Manifest Models (Simulation Optimization) ---


class ManifestStep(BaseModel):
    step_id: int
    screen_id: str
    screen: str
    title: str
    instruction: str
    tip: Optional[str] = None
    expected_action: str  # TAP, TYPE, SELECT, SCAN, VERIFY
    expected_value: Optional[str] = None  # required for TYPE, SELECT, SCAN
    on_wrong_action: str
    target_component_id: str
    # Legacy fallback fields (legacy manifests only)
    screenshot: Optional[str] = None
    tap_target: Optional[dict] = None  # {x, y, width, height}


class GoldenManifestMetadata(BaseModel):
    created_at: str  # ISO timestamp
    last_modified_at: str  # ISO timestamp
    generated_by: str = "ai_pipeline"
    is_edited: bool = False


class SimulationManifest(BaseModel):
    workflow_id: str
    workflow_name: str
    steps: list[ManifestStep]
    screen_configs: dict[str, ScreenConfig]  # keyed by screen_id
    quiz_breaks: list[dict]
    golden_metadata: Optional[GoldenManifestMetadata] = None


class CodeContext(BaseModel):
    """Code context fetched from GitHub repos via GitHub MCP."""
    components: list[dict]  # component definitions
    screen_layouts: list[dict]  # screen layout info
    design_tokens: dict  # colors, spacing, typography
    repo_url: str
    fetched_files: list[str]  # paths of fetched files
