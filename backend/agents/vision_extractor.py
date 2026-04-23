"""Vision AI Extractor — analyzes screenshots and extracts semantic UI layout.

Uses the project's LLM service (Bifrost / Gemini) with vision capabilities
to identify UI elements, their types, positions, hierarchy, and confidence.
Produces a ScreenConfig that the Config Editor and Component Renderer consume.
"""

import asyncio
import base64
import json
import logging
import os
import re
from typing import Optional

from models.schemas import (
    CodeContext,
    Position,
    ScreenConfig,
    ScreenConfigElement,
    ScreenConfigMetadata,
)

logger = logging.getLogger(__name__)

# Supported element types the LLM should classify into
ELEMENT_TYPE_TAXONOMY = [
    "button",
    "input",
    "dropdown",
    "card",
    "tab",
    "text_label",
    "header",
    "navigation_bar",
    "icon",
    "checkbox",
    "scan_input",
]

# Artifact labels/types to filter out after extraction
ARTIFACT_KEYWORDS = [
    "snackbar",
    "toast",
    "debug",
    "overlay",
    "notification bar",
    "notification_bar",
    "debug overlay",
    "debug_overlay",
    "error snackbar",
    "error_snackbar",
    "status bar",
    "status_bar",
]

# Confidence threshold — elements below this get needs_review=True
CONFIDENCE_THRESHOLD = 0.7

# Maximum time allowed for a single extraction call (seconds)
EXTRACTION_TIMEOUT_SECONDS = 120


def _encode_image_base64(image_path: str) -> str:
    """Read an image file and return its base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _image_media_type(image_path: str) -> str:
    """Return the MIME type based on file extension."""
    ext = os.path.splitext(image_path)[1].lower()
    return {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(
        ext.lstrip("."), "image/png"
    )


def _is_artifact(element: dict) -> bool:
    """Check if an element looks like an irrelevant artifact.

    Matches against known artifact keywords in the element's label or type.
    """
    label = (element.get("label") or "").lower()
    etype = (element.get("type") or "").lower()
    combined = f"{label} {etype}"
    return any(kw in combined for kw in ARTIFACT_KEYWORDS)


def _flag_confidence(element: dict) -> dict:
    """Set needs_review=True if confidence is below the threshold."""
    confidence = element.get("confidence", 1.0)
    if confidence < CONFIDENCE_THRESHOLD:
        element["needs_review"] = True
    else:
        element.setdefault("needs_review", False)
    return element


def _parse_elements(raw_elements: list[dict]) -> list[ScreenConfigElement]:
    """Convert raw LLM element dicts into ScreenConfigElement models.

    Recursively handles children for hierarchical grouping.
    Filters artifacts and applies confidence flagging.
    """
    parsed: list[ScreenConfigElement] = []
    for elem in raw_elements:
        if _is_artifact(elem):
            continue

        elem = _flag_confidence(elem)

        pos_data = elem.get("position", {})
        position = Position(
            x=float(pos_data.get("x", 0)),
            y=float(pos_data.get("y", 0)),
            width=float(pos_data.get("width", 0)),
            height=float(pos_data.get("height", 0)),
        )

        # Recursively parse children (hierarchical grouping)
        raw_children = elem.get("children", [])
        children = _parse_elements(raw_children) if raw_children else []

        parsed.append(
            ScreenConfigElement(
                component_id=elem.get("component_id", ""),
                type=elem.get("type", "text_label"),
                label=elem.get("label", ""),
                position=position,
                needs_review=elem.get("needs_review", False),
                children=children,
            )
        )
    return parsed


class VisionExtractorAgent:
    """Analyzes screenshot images and extracts semantic UI layout.

    Uses code context from GitHub MCP to improve component identification.
    Returns a ScreenConfig with elements, hierarchy, and suggested component IDs.
    Marks low-confidence elements with needs_review=True.
    """

    def __init__(self) -> None:
        # Lazy-import LLM dependencies so the module can be imported without
        # side-effects (useful for testing).
        self._llm_ready = False

    def _ensure_llm(self) -> None:
        """Lazily initialise the LLM client on first use."""
        if self._llm_ready:
            return

        from config import (
            BIFROST_VIRTUAL_KEY,
            GEMINI_API_KEY,
            GEMINI_MODEL,
            SECURITY_GUARDRAILS,
        )

        self._model = GEMINI_MODEL
        self._guardrails = SECURITY_GUARDRAILS

        # Reuse the same client pattern from llm_service.py (proven to work)
        if BIFROST_VIRTUAL_KEY:
            import openai

            self._oai_client = openai.OpenAI(
                base_url="https://bifrost.delhivery.com/openai",
                api_key="dummy-key",
                default_headers={"x-bf-vk": BIFROST_VIRTUAL_KEY},
                timeout=300.0,
            )
            self._use_bifrost = True
        else:
            from google import genai

            self._genai_client = genai.Client(api_key=GEMINI_API_KEY)
            self._use_bifrost = False

        self._llm_ready = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def extract(
        self,
        image_path: str,
        code_context: Optional[CodeContext] = None,
    ) -> ScreenConfig:
        """Send image + code context to vision LLM, get structured layout back.

        Returns a ScreenConfig with elements, hierarchy, and suggested
        component IDs.  Marks low-confidence elements with needs_review=True.

        Raises:
            TimeoutError: If extraction exceeds 30 seconds.
            FileNotFoundError: If the image file does not exist.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        self._ensure_llm()

        try:
            return await asyncio.wait_for(
                self._do_extract(image_path, code_context),
                timeout=EXTRACTION_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.error(
                "Vision extraction timed out after %ds for %s",
                EXTRACTION_TIMEOUT_SECONDS,
                image_path,
            )
            raise TimeoutError(
                f"Vision extraction timed out after {EXTRACTION_TIMEOUT_SECONDS}s "
                f"for {image_path}. Mark this screen for manual authoring."
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _do_extract(
        self,
        image_path: str,
        code_context: Optional[CodeContext],
    ) -> ScreenConfig:
        """Core extraction logic — called within the timeout wrapper."""
        fname = os.path.basename(image_path)
        fsize = os.path.getsize(image_path) / 1024
        print(f"🔍 [{fname}] Starting vision extraction ({fsize:.0f} KB)...")
        
        prompt = self._build_prompt(image_path, code_context)
        print(f"🔍 [{fname}] Prompt built ({len(prompt)} chars). Encoding image...")
        
        image_b64 = _encode_image_base64(image_path)
        media_type = _image_media_type(image_path)
        print(f"🔍 [{fname}] Image encoded ({len(image_b64) // 1024} KB base64). Calling LLM...")
        
        import time
        start = time.time()
        raw_json = await self._call_vision_llm(prompt, image_b64, media_type)
        elapsed = time.time() - start
        print(f"✅ [{fname}] LLM responded in {elapsed:.1f}s. Parsing response...")
        
        config = self._parse_response(raw_json, image_path)
        print(f"✅ [{fname}] Extracted {len(config.elements)} elements from screen '{config.screen_name}'")
        return config

    def _build_prompt(
        self,
        image_path: str,
        code_context: Optional[CodeContext],
    ) -> str:
        """Build the vision extraction prompt with element type taxonomy.

        If code_context is available, include component definitions and
        design tokens to improve accuracy.
        """
        taxonomy_str = ", ".join(ELEMENT_TYPE_TAXONOMY)

        code_section = ""
        if code_context and code_context.components:
            comp_names = [c.get("name", "") for c in code_context.components]
            code_section += (
                "\n\n## Code Context (from the app's source code)\n"
                f"Known component names: {', '.join(comp_names)}\n"
            )
            if code_context.design_tokens:
                code_section += (
                    f"Design tokens: {json.dumps(code_context.design_tokens, default=str)[:1000]}\n"
                )
            code_section += (
                "Use these component names as component_id values where they "
                "match elements in the screenshot.\n"
            )

        return f"""{self._guardrails}

You are a UI layout extraction agent. Analyze the provided screenshot and
identify every visible UI element.

## Element Type Taxonomy
Classify each element into one of these types:
{taxonomy_str}

## Instructions
1. For EACH element, return:
   - component_id: a unique camelCase identifier (use known component names from code context if available)
   - type: one of the types listed above
   - label: the visible text or a descriptive label
   - position: bounding box as percentage of screen dimensions (x, y, width, height — each 0-100)
   - confidence: your confidence score for this classification (0.0 to 1.0)
   - children: nested child elements if this is a container (e.g., a card containing buttons)

2. EXCLUDE irrelevant artifacts: snackbars, toasts, debug overlays, notification bars, status bars.

3. Detect HIERARCHICAL grouping: if a card contains a label and a button, the card is the parent with children.

4. Return ONLY valid JSON matching this schema:
{{
  "screen_name": "descriptive screen name",
  "elements": [
    {{
      "component_id": "uniqueId",
      "type": "button",
      "label": "Submit",
      "position": {{ "x": 10, "y": 80, "width": 80, "height": 8 }},
      "confidence": 0.95,
      "children": []
    }}
  ],
  "overall_confidence": 0.85
}}
{code_section}
IMPORTANT: Return ONLY valid JSON. No markdown, no ```json blocks, no explanation."""

    def _filter_artifacts(
        self, elements: list[ScreenConfigElement]
    ) -> list[ScreenConfigElement]:
        """Remove elements identified as artifacts (snackbars, debug overlays, etc.).

        This is a second-pass filter on already-parsed elements, in case the
        LLM didn't fully exclude them.
        """
        filtered: list[ScreenConfigElement] = []
        for elem in elements:
            combined = f"{elem.label} {elem.type}".lower()
            if any(kw in combined for kw in ARTIFACT_KEYWORDS):
                continue
            # Recursively filter children
            if elem.children:
                elem.children = self._filter_artifacts(elem.children)
            filtered.append(elem)
        return filtered

    async def _call_vision_llm(
        self, prompt: str, image_b64: str, media_type: str
    ) -> dict:
        """Call the vision LLM with the image and prompt, return parsed JSON."""
        if self._use_bifrost:
            return await self._call_bifrost_vision(prompt, image_b64, media_type)
        else:
            return await self._call_gemini_vision(prompt, image_b64, media_type)

    async def _call_bifrost_vision(
        self, prompt: str, image_b64: str, media_type: str
    ) -> dict:
        """Call Bifrost (OpenAI-compatible) with vision message format."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_b64}"
                        },
                    },
                ],
            }
        ]

        print(f"   📡 Sending to Bifrost (model: gemini/{self._model}, payload: ~{len(image_b64)//1024}KB)...")
        # Synchronous call — same pattern as llm_service.py which works
        response = self._oai_client.chat.completions.create(
            model=f"gemini/{self._model}",
            messages=messages,
        )
        print(f"   📡 Bifrost responded. Parsing JSON...")
        text = response.choices[0].message.content.strip()
        return self._parse_json_text(text)

    async def _call_gemini_vision(
        self, prompt: str, image_b64: str, media_type: str
    ) -> dict:
        """Call Gemini directly with inline image data."""
        from google.genai import types

        image_part = types.Part.from_bytes(
            data=base64.b64decode(image_b64),
            mime_type=media_type,
        )

        response = self._genai_client.models.generate_content(
            model=self._model,
            contents=[prompt, image_part],
        )
        text = response.text.strip()
        return self._parse_json_text(text)

    @staticmethod
    def _parse_json_text(text: str) -> dict:
        """Strip markdown fences and parse JSON from LLM output."""
        # Remove ```json ... ``` wrappers
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        return json.loads(text)

    def _parse_response(self, raw: dict, image_path: str) -> ScreenConfig:
        """Convert raw LLM JSON response into a validated ScreenConfig."""
        screen_name = raw.get("screen_name", os.path.basename(image_path))
        overall_confidence = raw.get("overall_confidence")
        raw_elements = raw.get("elements", [])

        # Parse elements (filters artifacts + flags confidence during parsing)
        elements = _parse_elements(raw_elements)

        # Second-pass artifact filter on parsed elements
        elements = self._filter_artifacts(elements)

        # Build screen_id from screen_name
        screen_id = re.sub(r"[^a-z0-9]+", "_", screen_name.lower()).strip("_")

        return ScreenConfig(
            screen_id=screen_id,
            screen_name=screen_name,
            source="vision_ai",
            elements=elements,
            metadata=ScreenConfigMetadata(
                source_screenshot_path=image_path,
                extraction_confidence=overall_confidence,
            ),
        )
