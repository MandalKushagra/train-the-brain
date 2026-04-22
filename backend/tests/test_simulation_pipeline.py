"""Tests for the SimulationPipeline orchestrator.

Covers:
- Pipeline orchestration (screenshot extraction + manifest generation)
- Screen-to-step mapping (ordering)
- Golden manifest generation with component ID references
- Golden manifest protection (skip if exists)
- Batch resilience (continue on individual failures)
- All operations use storage abstraction
"""

import asyncio
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.simulation_pipeline import (
    FailedScreenshot,
    PipelineInput,
    PipelineOutput,
    SimulationPipeline,
    _find_first_interactive_element,
    _generate_manifest_steps,
    _order_screen_configs,
)
from models.schemas import (
    CodeContext,
    Position,
    ScreenConfig,
    ScreenConfigElement,
    ScreenConfigMetadata,
    SimulationManifest,
)
from storage.storage_interface import StorageInterface


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    screen_id: str,
    screen_name: str,
    elements: Optional[list[ScreenConfigElement]] = None,
) -> ScreenConfig:
    """Create a minimal ScreenConfig for testing."""
    if elements is None:
        elements = [
            ScreenConfigElement(
                component_id=f"{screen_id}_btn",
                type="button",
                label="Submit",
                position=Position(x=10, y=80, width=80, height=8),
            ),
        ]
    return ScreenConfig(
        screen_id=screen_id,
        screen_name=screen_name,
        source="vision_ai",
        elements=elements,
    )


def _make_mock_storage(manifest_exists: bool = False) -> MagicMock:
    """Create a mock StorageInterface."""
    storage = MagicMock(spec=StorageInterface)
    storage.manifest_exists.return_value = manifest_exists
    storage.save_screen_config.return_value = None
    storage.save_manifest.return_value = None
    return storage


def _make_mock_vision(configs: list[ScreenConfig]) -> AsyncMock:
    """Create a mock VisionExtractorAgent that returns configs in order."""
    vision = AsyncMock()
    vision.extract = AsyncMock(side_effect=configs)
    return vision


def _make_mock_github(context: Optional[CodeContext] = None) -> AsyncMock:
    """Create a mock GitHubCodeFetcher."""
    github = AsyncMock()
    if context is None:
        context = CodeContext(
            components=[{"name": "SubmitButton"}],
            screen_layouts=[],
            design_tokens={},
            repo_url="https://github.com/test/repo",
            fetched_files=["src/components/SubmitButton.tsx"],
        )
    github.fetch = AsyncMock(return_value=context)
    return github


# ---------------------------------------------------------------------------
# Unit tests: helper functions
# ---------------------------------------------------------------------------


class TestFindFirstInteractiveElement:
    def test_returns_first_button(self):
        config = _make_config("s1", "Screen 1")
        assert _find_first_interactive_element(config) == "s1_btn"

    def test_returns_first_interactive_child(self):
        config = _make_config(
            "s1",
            "Screen 1",
            elements=[
                ScreenConfigElement(
                    component_id="card1",
                    type="card",
                    label="Card",
                    position=Position(x=0, y=0, width=100, height=50),
                    children=[
                        ScreenConfigElement(
                            component_id="inner_input",
                            type="input",
                            label="Name",
                            position=Position(x=5, y=5, width=90, height=10),
                        ),
                    ],
                ),
            ],
        )
        assert _find_first_interactive_element(config) == "inner_input"

    def test_returns_first_element_when_no_interactive(self):
        config = _make_config(
            "s1",
            "Screen 1",
            elements=[
                ScreenConfigElement(
                    component_id="label1",
                    type="text_label",
                    label="Hello",
                    position=Position(x=0, y=0, width=50, height=10),
                ),
            ],
        )
        assert _find_first_interactive_element(config) == "label1"

    def test_returns_none_for_empty_elements(self):
        config = _make_config("s1", "Screen 1", elements=[])
        assert _find_first_interactive_element(config) is None


class TestOrderScreenConfigs:
    def test_alphabetical_when_no_ordering(self):
        configs = [
            _make_config("c", "Charlie"),
            _make_config("a", "Alpha"),
            _make_config("b", "Bravo"),
        ]
        ordered = _order_screen_configs(configs, None)
        assert [c.screen_name for c in ordered] == ["Alpha", "Bravo", "Charlie"]

    def test_admin_ordering_respected(self):
        configs = [
            _make_config("c", "Charlie"),
            _make_config("a", "Alpha"),
            _make_config("b", "Bravo"),
        ]
        ordered = _order_screen_configs(configs, ["Bravo", "Charlie", "Alpha"])
        assert [c.screen_name for c in ordered] == ["Bravo", "Charlie", "Alpha"]

    def test_partial_ordering_appends_remaining(self):
        configs = [
            _make_config("c", "Charlie"),
            _make_config("a", "Alpha"),
            _make_config("b", "Bravo"),
        ]
        ordered = _order_screen_configs(configs, ["Charlie"])
        assert ordered[0].screen_name == "Charlie"
        # Remaining sorted alphabetically
        assert [c.screen_name for c in ordered[1:]] == ["Alpha", "Bravo"]

    def test_case_insensitive_matching(self):
        configs = [_make_config("a", "Alpha"), _make_config("b", "Bravo")]
        ordered = _order_screen_configs(configs, ["bravo", "alpha"])
        assert [c.screen_name for c in ordered] == ["Bravo", "Alpha"]


class TestGenerateManifestSteps:
    def test_creates_one_step_per_config(self):
        configs = [_make_config("s1", "Login"), _make_config("s2", "Dashboard")]
        steps = _generate_manifest_steps(configs)
        assert len(steps) == 2

    def test_step_ids_are_sequential(self):
        configs = [_make_config("s1", "A"), _make_config("s2", "B")]
        steps = _generate_manifest_steps(configs)
        assert [s.step_id for s in steps] == [1, 2]

    def test_step_references_screen_config(self):
        configs = [_make_config("login_screen", "Login Screen")]
        steps = _generate_manifest_steps(configs)
        assert steps[0].screen_id == "login_screen"
        assert steps[0].screen == "Login Screen"

    def test_step_has_target_component_id(self):
        configs = [_make_config("s1", "Screen 1")]
        steps = _generate_manifest_steps(configs)
        assert steps[0].target_component_id == "s1_btn"

    def test_default_action_is_tap(self):
        configs = [_make_config("s1", "Screen 1")]
        steps = _generate_manifest_steps(configs)
        assert steps[0].expected_action == "TAP"


# ---------------------------------------------------------------------------
# Integration tests: full pipeline
# ---------------------------------------------------------------------------


class TestSimulationPipelineRun:
    """Tests for the full pipeline.run() method."""

    @pytest.fixture
    def pipeline_input(self) -> PipelineInput:
        return PipelineInput(
            workflow_id="wf_001",
            workflow_name="Test Workflow",
            screenshot_paths=["screen1.png", "screen2.png"],
            github_repo_url="https://github.com/test/repo",
        )

    @pytest.mark.asyncio
    async def test_full_pipeline_success(self, pipeline_input):
        """Pipeline extracts configs, saves them, and generates manifest."""
        configs = [
            _make_config("login", "Login"),
            _make_config("dashboard", "Dashboard"),
        ]
        storage = _make_mock_storage(manifest_exists=False)
        vision = _make_mock_vision(configs)
        github = _make_mock_github()

        pipeline = SimulationPipeline(
            storage=storage, vision_extractor=vision, github_fetcher=github
        )
        output = await pipeline.run(pipeline_input)

        assert len(output.screen_configs) == 2
        assert output.manifest is not None
        assert len(output.manifest.steps) == 2
        assert output.failed_screenshots == []
        # Verify storage was called
        assert storage.save_screen_config.call_count == 2
        assert storage.save_manifest.call_count == 1

    @pytest.mark.asyncio
    async def test_github_context_passed_to_vision(self, pipeline_input):
        """Vision extractor receives the code context from GitHub."""
        config = _make_config("s1", "Screen 1")
        storage = _make_mock_storage()
        vision = _make_mock_vision([config, config])
        github = _make_mock_github()

        pipeline = SimulationPipeline(
            storage=storage, vision_extractor=vision, github_fetcher=github
        )
        await pipeline.run(pipeline_input)

        # Vision extract should have been called with code_context
        for call in vision.extract.call_args_list:
            assert call.args[1] is not None  # code_context arg

    @pytest.mark.asyncio
    async def test_manifest_protection_skips_if_exists(self, pipeline_input):
        """If manifest already exists, skip generation and warn."""
        config = _make_config("s1", "Screen 1")
        storage = _make_mock_storage(manifest_exists=True)
        vision = _make_mock_vision([config, config])

        pipeline = SimulationPipeline(
            storage=storage, vision_extractor=vision, github_fetcher=_make_mock_github()
        )
        output = await pipeline.run(pipeline_input)

        assert output.manifest is None
        assert storage.save_manifest.call_count == 0
        assert any("already exists" in w for w in output.warnings)

    @pytest.mark.asyncio
    async def test_batch_resilience_on_extraction_failure(self, pipeline_input):
        """If one screenshot fails, continue with the rest."""
        good_config = _make_config("s1", "Screen 1")
        vision = AsyncMock()
        vision.extract = AsyncMock(
            side_effect=[good_config, RuntimeError("LLM timeout")]
        )
        storage = _make_mock_storage()

        pipeline = SimulationPipeline(
            storage=storage, vision_extractor=vision, github_fetcher=_make_mock_github()
        )
        output = await pipeline.run(pipeline_input)

        assert len(output.screen_configs) == 1
        assert len(output.failed_screenshots) == 1
        assert output.failed_screenshots[0].path == "screen2.png"
        assert "LLM timeout" in output.failed_screenshots[0].error
        # Manifest should still be generated from the successful config
        assert output.manifest is not None
        assert len(output.manifest.steps) == 1

    @pytest.mark.asyncio
    async def test_no_github_url_proceeds_without_context(self):
        """Pipeline works without a GitHub repo URL."""
        inp = PipelineInput(
            workflow_id="wf_002",
            workflow_name="No GitHub",
            screenshot_paths=["screen.png"],
        )
        config = _make_config("s1", "Screen 1")
        storage = _make_mock_storage()
        vision = _make_mock_vision([config])

        pipeline = SimulationPipeline(
            storage=storage, vision_extractor=vision, github_fetcher=_make_mock_github()
        )
        output = await pipeline.run(inp)

        assert len(output.screen_configs) == 1
        # Vision should have been called with code_context=None
        vision.extract.assert_called_once_with("screen.png", None)

    @pytest.mark.asyncio
    async def test_manifest_has_golden_metadata(self, pipeline_input):
        """Generated manifest includes golden metadata."""
        config = _make_config("s1", "Screen 1")
        storage = _make_mock_storage()
        vision = _make_mock_vision([config, config])

        pipeline = SimulationPipeline(
            storage=storage, vision_extractor=vision, github_fetcher=_make_mock_github()
        )
        output = await pipeline.run(pipeline_input)

        assert output.manifest is not None
        meta = output.manifest.golden_metadata
        assert meta is not None
        assert meta.generated_by == "ai_pipeline"
        assert meta.is_edited is False

    @pytest.mark.asyncio
    async def test_manifest_screen_configs_keyed_by_id(self, pipeline_input):
        """Manifest screen_configs dict is keyed by screen_id."""
        configs = [
            _make_config("login", "Login"),
            _make_config("dashboard", "Dashboard"),
        ]
        storage = _make_mock_storage()
        vision = _make_mock_vision(configs)

        pipeline = SimulationPipeline(
            storage=storage, vision_extractor=vision, github_fetcher=_make_mock_github()
        )
        output = await pipeline.run(pipeline_input)

        assert output.manifest is not None
        assert "login" in output.manifest.screen_configs
        assert "dashboard" in output.manifest.screen_configs

    @pytest.mark.asyncio
    async def test_screen_ordering_applied(self):
        """Admin-provided screen ordering is respected in manifest steps."""
        inp = PipelineInput(
            workflow_id="wf_003",
            workflow_name="Ordered",
            screenshot_paths=["a.png", "b.png"],
            screen_ordering=["Bravo", "Alpha"],
        )
        configs = [_make_config("a", "Alpha"), _make_config("b", "Bravo")]
        storage = _make_mock_storage()
        vision = _make_mock_vision(configs)

        pipeline = SimulationPipeline(
            storage=storage, vision_extractor=vision, github_fetcher=_make_mock_github()
        )
        output = await pipeline.run(inp)

        assert output.manifest is not None
        assert output.manifest.steps[0].screen == "Bravo"
        assert output.manifest.steps[1].screen == "Alpha"

    @pytest.mark.asyncio
    async def test_github_fetch_failure_adds_warning(self, pipeline_input):
        """If GitHub fetch fails, pipeline continues with a warning."""
        config = _make_config("s1", "Screen 1")
        storage = _make_mock_storage()
        vision = _make_mock_vision([config, config])
        github = AsyncMock()
        github.fetch = AsyncMock(side_effect=RuntimeError("Network error"))

        pipeline = SimulationPipeline(
            storage=storage, vision_extractor=vision, github_fetcher=github
        )
        output = await pipeline.run(pipeline_input)

        assert len(output.screen_configs) == 2
        assert any("Failed to fetch code from GitHub" in w for w in output.warnings)

    @pytest.mark.asyncio
    async def test_all_extractions_fail_no_manifest(self, pipeline_input):
        """If all screenshots fail, no manifest is generated."""
        vision = AsyncMock()
        vision.extract = AsyncMock(side_effect=RuntimeError("fail"))
        storage = _make_mock_storage()

        pipeline = SimulationPipeline(
            storage=storage, vision_extractor=vision, github_fetcher=_make_mock_github()
        )
        output = await pipeline.run(pipeline_input)

        assert len(output.screen_configs) == 0
        assert len(output.failed_screenshots) == 2
        assert output.manifest is None
        assert storage.save_manifest.call_count == 0

    @pytest.mark.asyncio
    async def test_storage_save_failure_adds_warning(self, pipeline_input):
        """If storage save fails for a config, pipeline continues with a warning."""
        configs = [
            _make_config("login", "Login"),
            _make_config("dashboard", "Dashboard"),
        ]
        storage = _make_mock_storage()
        storage.save_screen_config.side_effect = [
            None,
            RuntimeError("Disk full"),
        ]
        vision = _make_mock_vision(configs)

        pipeline = SimulationPipeline(
            storage=storage, vision_extractor=vision, github_fetcher=_make_mock_github()
        )
        output = await pipeline.run(pipeline_input)

        assert len(output.screen_configs) == 2
        assert any("Failed to save screen config" in w for w in output.warnings)

    @pytest.mark.asyncio
    async def test_manifest_steps_reference_valid_component_ids(self, pipeline_input):
        """Each manifest step's target_component_id should reference a real element."""
        configs = [
            _make_config("login", "Login"),
            _make_config("dashboard", "Dashboard"),
        ]
        storage = _make_mock_storage()
        vision = _make_mock_vision(configs)

        pipeline = SimulationPipeline(
            storage=storage, vision_extractor=vision, github_fetcher=_make_mock_github()
        )
        output = await pipeline.run(pipeline_input)

        assert output.manifest is not None
        for step in output.manifest.steps:
            config = output.manifest.screen_configs[step.screen_id]
            all_ids = {el.component_id for el in config.elements}
            assert step.target_component_id in all_ids or step.target_component_id == ""

    @pytest.mark.asyncio
    async def test_empty_screenshots_list(self):
        """Pipeline with no screenshots produces no configs and no manifest."""
        inp = PipelineInput(
            workflow_id="wf_empty",
            workflow_name="Empty",
            screenshot_paths=[],
        )
        storage = _make_mock_storage()
        pipeline = SimulationPipeline(
            storage=storage,
            vision_extractor=AsyncMock(),
            github_fetcher=_make_mock_github(),
        )
        output = await pipeline.run(inp)

        assert len(output.screen_configs) == 0
        assert output.manifest is None
        assert len(output.failed_screenshots) == 0
