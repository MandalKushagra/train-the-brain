"""AI Pipeline Integration — orchestrates Screen Config + Golden Manifest generation.

Accepts screenshots and an optional GitHub repo URL, invokes the Vision AI
Extractor per screenshot, fetches code context via GitHub MCP, generates
ScreenConfigs, and produces a golden Simulation Manifest.

All save/load operations go through the storage abstraction interface.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

from agents.github_code_fetcher import GitHubCodeFetcher
from agents.vision_extractor import VisionExtractorAgent
from models.schemas import (
    CodeContext,
    GoldenManifestMetadata,
    ManifestStep,
    ScreenConfig,
    SimulationManifest,
)
from storage.storage_interface import StorageInterface

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline I/O models
# ---------------------------------------------------------------------------


class PipelineInput(BaseModel):
    """Input to the simulation pipeline."""

    workflow_id: str
    workflow_name: str
    screenshot_paths: list[str]
    github_repo_url: Optional[str] = None
    file_patterns: Optional[list[str]] = None
    screen_ordering: Optional[list[str]] = None  # ordered screen names


class FailedScreenshot(BaseModel):
    """Record of a screenshot that failed extraction."""

    path: str
    error: str


class PipelineOutput(BaseModel):
    """Output from the simulation pipeline."""

    screen_configs: list[ScreenConfig]
    manifest: Optional[SimulationManifest] = None  # None if already existed
    failed_screenshots: list[FailedScreenshot]
    warnings: list[str]


# ---------------------------------------------------------------------------
# Helper: find first interactive element in a ScreenConfig
# ---------------------------------------------------------------------------

_INTERACTIVE_TYPES = {"button", "input", "dropdown", "checkbox", "scan_input", "tab"}


def _find_first_interactive_element(config: ScreenConfig) -> Optional[str]:
    """Return the component_id of the first interactive element, or None."""
    for elem in config.elements:
        if elem.type in _INTERACTIVE_TYPES:
            return elem.component_id
        # Check children
        for child in elem.children:
            if child.type in _INTERACTIVE_TYPES:
                return child.component_id
    # Fallback: return the first element's component_id if any exist
    if config.elements:
        return config.elements[0].component_id
    return None


# ---------------------------------------------------------------------------
# Helper: order screen configs for manifest step generation
# ---------------------------------------------------------------------------


def _order_screen_configs(
    configs: list[ScreenConfig],
    screen_ordering: Optional[list[str]],
) -> list[ScreenConfig]:
    """Order screen configs by admin-provided ordering or alphabetically by name.

    If *screen_ordering* is provided, configs whose ``screen_name`` matches
    an entry (case-insensitive) are placed first in that order; unmatched
    configs are appended alphabetically.
    """
    if not screen_ordering:
        return sorted(configs, key=lambda c: c.screen_name.lower())

    ordering_lower = [name.lower() for name in screen_ordering]
    by_name: dict[str, ScreenConfig] = {c.screen_name.lower(): c for c in configs}

    ordered: list[ScreenConfig] = []
    used: set[str] = set()
    for name in ordering_lower:
        if name in by_name and name not in used:
            ordered.append(by_name[name])
            used.add(name)

    # Append remaining configs alphabetically
    for cfg in sorted(configs, key=lambda c: c.screen_name.lower()):
        if cfg.screen_name.lower() not in used:
            ordered.append(cfg)

    return ordered


# ---------------------------------------------------------------------------
# Helper: generate manifest steps from ordered screen configs
# ---------------------------------------------------------------------------


def _generate_manifest_steps(
    ordered_configs: list[ScreenConfig],
) -> list[ManifestStep]:
    """Create one ManifestStep per ScreenConfig.

    Each step gets:
    - step_id: sequential starting at 1
    - screen_id / screen: from the config
    - title / instruction: placeholder text for admin to customise
    - expected_action: default TAP
    - target_component_id: first interactive element in the config
    """
    steps: list[ManifestStep] = []
    for idx, config in enumerate(ordered_configs, start=1):
        target_id = _find_first_interactive_element(config) or ""
        steps.append(
            ManifestStep(
                step_id=idx,
                screen_id=config.screen_id,
                screen=config.screen_name,
                title=f"Step {idx}: {config.screen_name}",
                instruction=f"Tap the highlighted element on the {config.screen_name} screen.",
                expected_action="TAP",
                on_wrong_action="That's not the right element. Try again.",
                target_component_id=target_id,
            )
        )
    return steps


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------


class SimulationPipeline:
    """Orchestrates Screen Config extraction and golden Manifest generation.

    Usage::

        pipeline = SimulationPipeline(storage=my_storage)
        output = await pipeline.run(pipeline_input)
    """

    def __init__(
        self,
        storage: StorageInterface,
        vision_extractor: Optional[VisionExtractorAgent] = None,
        github_fetcher: Optional[GitHubCodeFetcher] = None,
    ) -> None:
        self._storage = storage
        self._vision = vision_extractor or VisionExtractorAgent()
        self._github = github_fetcher or GitHubCodeFetcher(
            github_token=os.environ.get("GITHUB_TOKEN")
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, inp: PipelineInput) -> PipelineOutput:
        """Execute the full pipeline.

        1. Fetch code context via GitHub MCP (if repo URL provided).
        2. For each screenshot, call VisionExtractorAgent.extract().
        3. Save each ScreenConfig via storage abstraction.
        4. If no golden manifest exists, generate and save one.
        5. If golden manifest already exists, skip and add a warning.
        """
        warnings: list[str] = []
        failed_screenshots: list[FailedScreenshot] = []
        screen_configs: list[ScreenConfig] = []

        # --- Step 1: Fetch code context (optional) ---
        code_context: Optional[CodeContext] = None
        if inp.github_repo_url:
            try:
                code_context = await self._github.fetch(
                    inp.github_repo_url, inp.file_patterns
                )
                if not code_context.fetched_files:
                    warnings.append(
                        f"No files fetched from {inp.github_repo_url}. "
                        "Proceeding with screenshot-only extraction."
                    )
            except Exception as exc:
                logger.warning("GitHub fetch failed: %s", exc)
                warnings.append(
                    f"Failed to fetch code from GitHub: {exc}. "
                    "Proceeding with screenshot-only extraction."
                )

        # --- Step 2: Extract ScreenConfigs from all screenshots in parallel (max 3 concurrent) ---
        async def _extract_one(path: str, semaphore: asyncio.Semaphore):
            async with semaphore:
                try:
                    return ("ok", path, await self._vision.extract(path, code_context))
                except Exception as exc:
                    logger.error("Extraction failed for %s: %s", path, exc)
                    return ("fail", path, str(exc))

        sem = asyncio.Semaphore(3)  # max 3 concurrent LLM calls
        results = await asyncio.gather(
            *[_extract_one(p, sem) for p in inp.screenshot_paths]
        )
        for status, path, data in results:
            if status == "ok":
                screen_configs.append(data)
            else:
                failed_screenshots.append(FailedScreenshot(path=path, error=data))

        # --- Step 3: Save each ScreenConfig via storage ---
        for config in screen_configs:
            try:
                self._storage.save_screen_config(inp.workflow_id, config)
            except Exception as exc:
                logger.error(
                    "Failed to save screen config %s: %s",
                    config.screen_id,
                    exc,
                )
                warnings.append(
                    f"Failed to save screen config '{config.screen_id}': {exc}"
                )

        # --- Step 4: Golden manifest generation ---
        manifest: Optional[SimulationManifest] = None

        if self._storage.manifest_exists(inp.workflow_id):
            warnings.append(
                "A golden manifest already exists for this workflow. "
                "Skipping manifest generation. Please manually integrate "
                "new screen configs into the existing manifest."
            )
        elif screen_configs:
            manifest = self._build_manifest(inp, screen_configs)
            try:
                self._storage.save_manifest(inp.workflow_id, manifest)
            except Exception as exc:
                logger.error("Failed to save manifest: %s", exc)
                warnings.append(f"Failed to save golden manifest: {exc}")
                manifest = None

        if failed_screenshots:
            names = ", ".join(f.path for f in failed_screenshots)
            warnings.append(
                f"The following screenshots failed extraction and need "
                f"manual config authoring: {names}"
            )

        return PipelineOutput(
            screen_configs=screen_configs,
            manifest=manifest,
            failed_screenshots=failed_screenshots,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_manifest(
        self,
        inp: PipelineInput,
        configs: list[ScreenConfig],
    ) -> SimulationManifest:
        """Build a golden SimulationManifest from the extracted ScreenConfigs."""
        ordered = _order_screen_configs(configs, inp.screen_ordering)
        steps = _generate_manifest_steps(ordered)

        now = datetime.now(timezone.utc).isoformat()
        return SimulationManifest(
            workflow_id=inp.workflow_id,
            workflow_name=inp.workflow_name,
            steps=steps,
            screen_configs={c.screen_id: c for c in configs},
            quiz_breaks=[],
            golden_metadata=GoldenManifestMetadata(
                created_at=now,
                last_modified_at=now,
                generated_by="ai_pipeline",
                is_edited=False,
            ),
        )
