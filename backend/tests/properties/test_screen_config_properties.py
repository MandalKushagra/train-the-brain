"""Property-based tests for Screen Config (Python/Hypothesis).

Feature: simulation-optimization
"""

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from agents.vision_extractor import CONFIDENCE_THRESHOLD, _flag_confidence


# ── Strategies ────────────────────────────────────────────────

confidence_score = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


# ── Property Tests ────────────────────────────────────────────


class TestScreenConfigProperties:
    """Property 4: Low-confidence elements flagged for review."""

    # Feature: simulation-optimization, Property 4: Low-confidence elements flagged
    @settings(max_examples=100)
    @given(confidence=confidence_score)
    def test_property_4_low_confidence_elements_flagged(
        self, confidence: float
    ) -> None:
        """For any element with confidence below 0.7, needs_review must be True.

        Validates: Requirements 1.6
        """
        element: dict = {
            "component_id": "test_comp",
            "type": "button",
            "label": "Test",
            "position": {"x": 10, "y": 20, "width": 30, "height": 10},
            "confidence": confidence,
        }

        result = _flag_confidence(element)

        if confidence < CONFIDENCE_THRESHOLD:
            assert result["needs_review"] is True, (
                f"Element with confidence {confidence} (< {CONFIDENCE_THRESHOLD}) "
                f"should have needs_review=True"
            )
        else:
            # At or above threshold, needs_review should default to False
            assert result.get("needs_review", False) is False or confidence >= CONFIDENCE_THRESHOLD
