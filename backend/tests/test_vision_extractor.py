"""Unit tests for VisionExtractorAgent.

Tests use mocked LLM responses to verify ScreenConfig output structure,
artifact filtering, confidence flagging, and error handling.
"""

import os
import tempfile
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from agents.vision_extractor import (
    VisionExtractorAgent,
    _flag_confidence,
    _is_artifact,
    _parse_elements,
    CONFIDENCE_THRESHOLD,
)
from models.schemas import CodeContext


# ── Helpers ───────────────────────────────────────────────────


def _create_temp_image() -> str:
    """Create a minimal temporary PNG file for testing."""
    # Minimal 1x1 PNG
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
        b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    fd, path = tempfile.mkstemp(suffix=".png")
    os.write(fd, png_bytes)
    os.close(fd)
    return path


MOCK_LLM_RESPONSE = {
    "screen_name": "Login Screen",
    "elements": [
        {
            "component_id": "btn_login",
            "type": "button",
            "label": "Login",
            "position": {"x": 10, "y": 80, "width": 80, "height": 8},
            "confidence": 0.95,
            "children": [],
        },
        {
            "component_id": "input_user",
            "type": "input",
            "label": "Username",
            "position": {"x": 10, "y": 30, "width": 80, "height": 8},
            "confidence": 0.88,
            "children": [],
        },
    ],
    "overall_confidence": 0.91,
}


# ── Unit Tests: Helper Functions ──────────────────────────────


class TestIsArtifact:
    def test_snackbar_is_artifact(self):
        assert _is_artifact({"label": "Error snackbar", "type": "text"})

    def test_debug_overlay_is_artifact(self):
        assert _is_artifact({"label": "Debug overlay", "type": "overlay"})

    def test_notification_bar_is_artifact(self):
        assert _is_artifact({"label": "Notification bar", "type": "bar"})

    def test_normal_button_is_not_artifact(self):
        assert not _is_artifact({"label": "Submit", "type": "button"})

    def test_normal_input_is_not_artifact(self):
        assert not _is_artifact({"label": "Username", "type": "input"})


class TestFlagConfidence:
    def test_low_confidence_flagged(self):
        elem = {"confidence": 0.5}
        result = _flag_confidence(elem)
        assert result["needs_review"] is True

    def test_high_confidence_not_flagged(self):
        elem = {"confidence": 0.9}
        result = _flag_confidence(elem)
        assert result.get("needs_review", False) is False

    def test_threshold_boundary(self):
        elem = {"confidence": CONFIDENCE_THRESHOLD}
        result = _flag_confidence(elem)
        assert result.get("needs_review", False) is False

    def test_just_below_threshold(self):
        elem = {"confidence": CONFIDENCE_THRESHOLD - 0.01}
        result = _flag_confidence(elem)
        assert result["needs_review"] is True


class TestParseElements:
    def test_parses_basic_elements(self):
        raw = [
            {
                "component_id": "btn1",
                "type": "button",
                "label": "Click",
                "position": {"x": 10, "y": 20, "width": 30, "height": 10},
                "confidence": 0.9,
            }
        ]
        parsed = _parse_elements(raw)
        assert len(parsed) == 1
        assert parsed[0].component_id == "btn1"
        assert parsed[0].type == "button"

    def test_filters_artifacts(self):
        raw = [
            {
                "component_id": "btn1",
                "type": "button",
                "label": "Submit",
                "position": {"x": 10, "y": 20, "width": 30, "height": 10},
                "confidence": 0.9,
            },
            {
                "component_id": "snack1",
                "type": "text",
                "label": "Error snackbar message",
                "position": {"x": 0, "y": 90, "width": 100, "height": 10},
                "confidence": 0.8,
            },
        ]
        parsed = _parse_elements(raw)
        assert len(parsed) == 1
        assert parsed[0].component_id == "btn1"

    def test_parses_nested_children(self):
        raw = [
            {
                "component_id": "card1",
                "type": "card",
                "label": "Order Card",
                "position": {"x": 5, "y": 10, "width": 90, "height": 40},
                "confidence": 0.85,
                "children": [
                    {
                        "component_id": "label1",
                        "type": "text_label",
                        "label": "Order #123",
                        "position": {"x": 5, "y": 5, "width": 50, "height": 10},
                        "confidence": 0.9,
                    }
                ],
            }
        ]
        parsed = _parse_elements(raw)
        assert len(parsed) == 1
        assert len(parsed[0].children) == 1
        assert parsed[0].children[0].component_id == "label1"


# ── Integration Tests: VisionExtractorAgent ───────────────────


class TestVisionExtractorAgent:
    @pytest.mark.asyncio
    async def test_extract_produces_valid_screen_config(self):
        """Mock the LLM call and verify the output ScreenConfig structure."""
        image_path = _create_temp_image()
        try:
            agent = VisionExtractorAgent()

            # Mock the internal LLM call
            agent._ensure_llm = MagicMock()
            agent._llm_ready = True
            agent._guardrails = ""
            agent._call_vision_llm = AsyncMock(return_value=MOCK_LLM_RESPONSE)

            config = await agent.extract(image_path)

            assert config.screen_id  # non-empty
            assert config.screen_name == "Login Screen"
            assert config.source == "vision_ai"
            assert len(config.elements) == 2
            assert config.elements[0].component_id == "btn_login"
            assert config.elements[1].component_id == "input_user"
            assert config.metadata is not None
            assert config.metadata.source_screenshot_path == image_path
            assert config.metadata.extraction_confidence == 0.91
        finally:
            os.unlink(image_path)

    @pytest.mark.asyncio
    async def test_extract_raises_on_missing_image(self):
        agent = VisionExtractorAgent()
        with pytest.raises(FileNotFoundError):
            await agent.extract("/nonexistent/path.png")

    @pytest.mark.asyncio
    async def test_extract_filters_artifacts_from_response(self):
        """Artifacts in the LLM response should be filtered out."""
        image_path = _create_temp_image()
        try:
            response_with_artifacts = {
                "screen_name": "Test",
                "elements": [
                    {
                        "component_id": "btn1",
                        "type": "button",
                        "label": "Submit",
                        "position": {"x": 10, "y": 80, "width": 80, "height": 8},
                        "confidence": 0.9,
                    },
                    {
                        "component_id": "toast1",
                        "type": "text",
                        "label": "Debug overlay info",
                        "position": {"x": 0, "y": 0, "width": 100, "height": 5},
                        "confidence": 0.7,
                    },
                ],
                "overall_confidence": 0.8,
            }

            agent = VisionExtractorAgent()
            agent._ensure_llm = MagicMock()
            agent._llm_ready = True
            agent._guardrails = ""
            agent._call_vision_llm = AsyncMock(return_value=response_with_artifacts)

            config = await agent.extract(image_path)
            # The debug overlay should be filtered out
            assert len(config.elements) == 1
            assert config.elements[0].component_id == "btn1"
        finally:
            os.unlink(image_path)

    @pytest.mark.asyncio
    async def test_extract_with_code_context(self):
        """Code context should be accepted without errors."""
        image_path = _create_temp_image()
        try:
            code_context = CodeContext(
                components=[{"name": "LoginButton"}],
                screen_layouts=[],
                design_tokens={"colors": {"primary": "#1565C0"}},
                repo_url="https://github.com/test/repo",
                fetched_files=["src/components/LoginButton.tsx"],
            )

            agent = VisionExtractorAgent()
            agent._ensure_llm = MagicMock()
            agent._llm_ready = True
            agent._guardrails = ""
            agent._call_vision_llm = AsyncMock(return_value=MOCK_LLM_RESPONSE)

            config = await agent.extract(image_path, code_context)
            assert config.source == "vision_ai"
            assert len(config.elements) == 2
        finally:
            os.unlink(image_path)
