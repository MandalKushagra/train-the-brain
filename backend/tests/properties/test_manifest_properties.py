"""Property-based tests for Simulation Manifest (Python/Hypothesis).

Feature: simulation-optimization
"""

import asyncio
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from models.schemas import (
    ManifestStep,
    Position,
    ScreenConfig,
    ScreenConfigElement,
    SimulationManifest,
)
from agents.simulation_pipeline import (
    PipelineInput,
    SimulationPipeline,
    _generate_manifest_steps,
)
from storage.storage_interface import StorageInterface


# ── Strategies ────────────────────────────────────────────────

VALID_ELEMENT_TYPES = [
    "button", "input", "dropdown", "card", "tab",
    "text_label", "header", "navigation_bar", "icon",
    "checkbox", "scan_input",
]

VALID_ACTIONS = ["TAP", "TYPE", "SELECT", "SCAN", "VERIFY"]

position_strategy = st.builds(
    Position,
    x=st.floats(min_value=0, max_value=100, allow_nan=False),
    y=st.floats(min_value=0, max_value=100, allow_nan=False),
    width=st.floats(min_value=0, max_value=100, allow_nan=False),
    height=st.floats(min_value=0, max_value=100, allow_nan=False),
)

element_strategy = st.builds(
    ScreenConfigElement,
    component_id=st.text(
        alphabet=st.sampled_from(list("abcdefghijklmnopqrstuvwxyz0123456789_")),
        min_size=1, max_size=15,
    ),
    type=st.sampled_from(VALID_ELEMENT_TYPES),
    label=st.text(
        alphabet=st.sampled_from(list("abcdefghijklmnopqrstuvwxyz ")),
        min_size=1, max_size=20,
    ),
    position=position_strategy,
    needs_review=st.booleans(),
    children=st.just([]),
)


def make_screen_config(screen_id: str, elements: list[ScreenConfigElement]) -> ScreenConfig:
    """Helper to create a ScreenConfig with unique component IDs."""
    # Ensure unique component_ids by prefixing with screen_id
    for i, el in enumerate(elements):
        el.component_id = f"{screen_id}_comp_{i}"
    return ScreenConfig(
        screen_id=screen_id,
        screen_name=f"Screen {screen_id}",
        source="manual",
        elements=elements,
    )


@st.composite
def manifest_with_configs(draw: st.DrawFn) -> SimulationManifest:
    """Generate a valid SimulationManifest with matching screen_configs."""
    num_steps = draw(st.integers(min_value=1, max_value=4))
    screen_ids = [f"screen_{i}" for i in range(num_steps)]

    configs: dict[str, ScreenConfig] = {}
    steps: list[ManifestStep] = []

    for i, sid in enumerate(screen_ids):
        elements = draw(st.lists(element_strategy, min_size=1, max_size=3))
        config = make_screen_config(sid, elements)
        configs[sid] = config

        target_id = config.elements[0].component_id
        action = draw(st.sampled_from(VALID_ACTIONS))
        steps.append(
            ManifestStep(
                step_id=i + 1,
                screen_id=sid,
                screen=config.screen_name,
                title=f"Step {i + 1}",
                instruction=f"Do step {i + 1}",
                expected_action=action,
                on_wrong_action="Wrong!",
                target_component_id=target_id,
            )
        )

    workflow_id = draw(
        st.text(
            alphabet=st.sampled_from(list("abcdefghijklmnopqrstuvwxyz0123456789")),
            min_size=1, max_size=10,
        )
    )

    return SimulationManifest(
        workflow_id=workflow_id,
        workflow_name=f"Workflow {workflow_id}",
        steps=steps,
        screen_configs=configs,
        quiz_breaks=[],
    )


# ── Property Tests ────────────────────────────────────────────


class TestManifestProperties:
    """Property 17 & 18: Pipeline referential integrity and resilience."""

    # Feature: simulation-optimization, Property 17: Pipeline referential integrity
    @settings(max_examples=100)
    @given(manifest=manifest_with_configs())
    def test_property_17_referential_integrity(
        self, manifest: SimulationManifest
    ) -> None:
        """Every step's target_component_id references a valid element in its screen's config.

        Validates: Requirements 9.3
        """
        for step in manifest.steps:
            # Step's screen_id must exist in screen_configs
            assert step.screen_id in manifest.screen_configs, (
                f"Step {step.step_id} references screen_id '{step.screen_id}' "
                f"not found in screen_configs"
            )

            config = manifest.screen_configs[step.screen_id]

            # Collect all component_ids (including nested children)
            all_ids: set[str] = set()

            def collect_ids(elements: list[ScreenConfigElement]) -> None:
                for el in elements:
                    all_ids.add(el.component_id)
                    if el.children:
                        collect_ids(el.children)

            collect_ids(config.elements)

            assert step.target_component_id in all_ids, (
                f"Step {step.step_id} references target_component_id "
                f"'{step.target_component_id}' not found in screen "
                f"'{step.screen_id}' elements: {all_ids}"
            )

    # Feature: simulation-optimization, Property 18: Pipeline resilience
    @settings(max_examples=100)
    @given(
        num_screenshots=st.integers(min_value=2, max_value=5),
        failure_indices=st.lists(
            st.integers(min_value=0, max_value=4),
            min_size=0, max_size=3,
        ),
    )
    def test_property_18_pipeline_resilience(
        self, num_screenshots: int, failure_indices: list[int]
    ) -> None:
        """Batch extraction with random failures produces partial results.

        Validates: Requirements 9.4
        """
        # Clamp failure indices to valid range
        failure_set = {i % num_screenshots for i in failure_indices}
        assume(len(failure_set) < num_screenshots)  # at least one success

        screenshot_paths = [f"screen_{i}.png" for i in range(num_screenshots)]

        # Build mock vision extractor that fails on specified indices
        configs = []
        side_effects = []
        for i in range(num_screenshots):
            if i in failure_set:
                side_effects.append(RuntimeError(f"Extraction failed for screen_{i}"))
            else:
                config = ScreenConfig(
                    screen_id=f"screen_{i}",
                    screen_name=f"Screen {i}",
                    source="vision_ai",
                    elements=[
                        ScreenConfigElement(
                            component_id=f"screen_{i}_btn",
                            type="button",
                            label="Submit",
                            position=Position(x=10, y=80, width=80, height=8),
                        )
                    ],
                )
                configs.append(config)
                side_effects.append(config)

        vision = AsyncMock()
        vision.extract = AsyncMock(side_effect=side_effects)

        storage = MagicMock(spec=StorageInterface)
        storage.manifest_exists.return_value = False
        storage.save_screen_config.return_value = None
        storage.save_manifest.return_value = None

        github = AsyncMock()
        github.fetch = AsyncMock(return_value=None)

        pipeline = SimulationPipeline(
            storage=storage, vision_extractor=vision, github_fetcher=github
        )

        inp = PipelineInput(
            workflow_id="wf_test",
            workflow_name="Test",
            screenshot_paths=screenshot_paths,
        )

        output = asyncio.get_event_loop().run_until_complete(pipeline.run(inp))

        expected_successes = num_screenshots - len(failure_set)
        expected_failures = len(failure_set)

        # Successful configs should be produced
        assert len(output.screen_configs) == expected_successes, (
            f"Expected {expected_successes} configs, got {len(output.screen_configs)}"
        )

        # Failed screenshots should be recorded
        assert len(output.failed_screenshots) == expected_failures, (
            f"Expected {expected_failures} failures, got {len(output.failed_screenshots)}"
        )

        # Pipeline should not abort — manifest should be generated from successes
        if expected_successes > 0:
            assert output.manifest is not None
