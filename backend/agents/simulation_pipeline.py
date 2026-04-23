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
from agents.figma_fetcher import FigmaFetcher
from agents.vision_extractor import VisionExtractorAgent
from models.schemas import (
    CodeContext,
    GoldenManifestMetadata,
    ManifestStep,
    Position,
    ScreenConfig,
    ScreenConfigElement,
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
    github_repo_url: Optional[str] = None  # legacy single repo
    github_repos: Optional[list[dict]] = None  # [{url, branch}] — multiple repos
    file_patterns: Optional[list[str]] = None
    screen_ordering: Optional[list[str]] = None
    prd_text: Optional[str] = None
    figma_urls: Optional[list[str]] = None


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
        self._figma = FigmaFetcher()

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
        print(f"\n{'='*60}")
        print(f"🚀 SIMULATION PIPELINE STARTED")
        print(f"   Workflow: {inp.workflow_name} ({inp.workflow_id})")
        print(f"   Screenshots: {len(inp.screenshot_paths)}")
        print(f"   GitHub URL: {inp.github_repo_url or 'none'}")
        print(f"{'='*60}\n")

        warnings: list[str] = []
        failed_screenshots: list[FailedScreenshot] = []
        screen_configs: list[ScreenConfig] = []

        # --- Step 1: Fetch code context from all GitHub repos ---
        code_context: Optional[CodeContext] = None
        repos = inp.github_repos or ([{"url": inp.github_repo_url, "branch": "main"}] if inp.github_repo_url else [])
        
        if repos:
            print(f"📦 Step 1: Fetching code from {len(repos)} GitHub repo(s)...")
            all_components = []
            all_layouts = []
            all_tokens = {}
            all_files = []
            
            for repo_entry in repos:
                repo_url = repo_entry.get("url", "") if isinstance(repo_entry, dict) else repo_entry
                branch = repo_entry.get("branch", "main") if isinstance(repo_entry, dict) else "main"
                if not repo_url:
                    continue
                print(f"   📦 Fetching {repo_url} (branch: {branch})...")
                try:
                    ctx = await self._github.fetch(repo_url, inp.file_patterns, branch=branch)
                    all_components.extend(ctx.components)
                    all_layouts.extend(ctx.screen_layouts)
                    all_tokens.update(ctx.design_tokens)
                    all_files.extend(ctx.fetched_files)
                    print(f"      ✅ Fetched {len(ctx.fetched_files)} files")
                except Exception as exc:
                    print(f"      ❌ Failed: {exc}")
                    warnings.append(f"Failed to fetch code from {repo_url}: {exc}")
            
            if all_files:
                code_context = CodeContext(
                    components=all_components,
                    screen_layouts=all_layouts,
                    design_tokens=all_tokens,
                    repo_url=repos[0].get("url", "") if isinstance(repos[0], dict) else repos[0],
                    fetched_files=all_files,
                )
                print(f"   📊 Total: {len(all_files)} files, {len(all_components)} components, {len(all_layouts)} layouts")
            else:
                print(f"   ⚠️ No files fetched from any repo")

        # --- Step 1b: Fetch Figma design data (if URLs provided) ---
        figma_data = []
        if inp.figma_urls:
            print(f"\n📐 Step 1b: Fetching design data from {len(inp.figma_urls)} Figma file(s)...")
            for figma_url in inp.figma_urls:
                if not figma_url.strip():
                    continue
                print(f"   📐 Fetching {figma_url}...")
                try:
                    result = await self._figma.fetch(figma_url)
                    figma_data.append(result)
                    if result.get("frames"):
                        print(f"      ✅ Got {len(result['frames'])} frames, {len(result.get('components', []))} components")
                        if result.get("images"):
                            rendered = sum(1 for v in result["images"].values() if v)
                            print(f"      📸 {rendered} frame images rendered")
                        for f in result["frames"][:10]:
                            children_count = len(f.get("children", []))
                            print(f"         - {f['name']} ({f.get('type', '?')}, {children_count} children)")
                            # Print grandchildren too
                            for child in f.get("children", [])[:15]:
                                gc_count = len(child.get("children", []))
                                print(f"            - {child['name']} ({child.get('type', '?')}, {gc_count} children)")
                    elif result.get("error"):
                        print(f"      ❌ {result['error']}")
                except Exception as exc:
                    print(f"      ❌ Figma fetch failed: {exc}")
                    warnings.append(f"Failed to fetch Figma data from {figma_url}: {exc}")

        # --- Step 2: Extract ScreenConfigs from all screenshots in parallel (max 3 concurrent) ---
        print(f"\n🔍 Step 2: Extracting screen configs from {len(inp.screenshot_paths)} screenshots (max 3 parallel)...")
        
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

        print(f"\n📊 Extraction results: {len(screen_configs)} succeeded, {len(failed_screenshots)} failed")

        # --- Step 2b: If no screenshots but PRD text available, generate configs from text ---
        if not screen_configs and inp.prd_text:
            print(f"\n📝 Step 2b: No screenshots — generating screen configs from PRD + code context via text LLM...")
            try:
                text_configs = self._generate_configs_from_text(inp.prd_text, code_context)
                screen_configs.extend(text_configs)
                print(f"   ✅ Generated {len(text_configs)} screen configs from text")
            except Exception as exc:
                print(f"   ❌ Text generation failed: {exc}")
                logger.error("Text-based config generation failed: %s", exc)
                warnings.append(f"Text-based screen config generation failed: {exc}")

        # --- Step 3: Save each ScreenConfig via storage ---
        print(f"\n💾 Step 3: Saving screen configs...")
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
        print(f"\n📋 Step 4: Golden manifest generation...")
        manifest: Optional[SimulationManifest] = None

        if self._storage.manifest_exists(inp.workflow_id):
            warnings.append(
                "A golden manifest already exists for this workflow. "
                "Skipping manifest generation. Please manually integrate "
                "new screen configs into the existing manifest."
            )
        elif screen_configs:
            manifest = self._build_manifest(inp, screen_configs)
            print(f"   ✅ Golden manifest generated: {len(manifest.steps)} steps")
            print(f"\n📄 GOLDEN MANIFEST:")
            print(f"   workflow_id: {manifest.workflow_id}")
            print(f"   workflow_name: {manifest.workflow_name}")
            print(f"   screens: {list(manifest.screen_configs.keys())}")
            for s in manifest.steps:
                print(f"   Step {s.step_id}: [{s.expected_action}] {s.screen} → {s.target_component_id} | {s.instruction[:60]}")
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

        print(f"\n{'='*60}")
        print(f"✅ PIPELINE COMPLETE — {len(screen_configs)} configs, {len(failed_screenshots)} failures")
        print(f"{'='*60}\n")

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

    def _generate_configs_from_text(
        self,
        prd_text: str,
        code_context: Optional[CodeContext],
    ) -> list[ScreenConfig]:
        """Generate ScreenConfigs from PRD text + code context using text-only LLM call."""
        from services.llm_service import call_llm_json

        code_section = ""
        if code_context and code_context.screen_layouts:
            layouts = [sl.get("file", "") for sl in code_context.screen_layouts[:5]]
            code_section = f"\n\nKnown screen files from codebase: {', '.join(layouts)}"
        if code_context and code_context.design_tokens:
            code_section += f"\nDesign tokens: {str(code_context.design_tokens)[:500]}"

        prompt = f"""Based on this PRD/workflow description, generate Screen Configs for a training simulation.

## PRD:
{prd_text}
{code_section}

For each screen in the workflow, generate a ScreenConfig with UI elements.

Element types: button, input, dropdown, card, tab, text_label, header, navigation_bar, icon, checkbox, scan_input

Return JSON:
{{
  "screens": [
    {{
      "screen_id": "unique_snake_case_id",
      "screen_name": "Human Readable Name",
      "elements": [
        {{
          "component_id": "unique_camel_case_id",
          "type": "button",
          "label": "Visible Text",
          "position": {{ "x": 10, "y": 80, "width": 80, "height": 8 }},
          "children": []
        }}
      ]
    }}
  ]
}}

Position values are percentages (0-100) of screen dimensions.
Include realistic UI elements: headers, input fields, buttons, labels, navigation bars.
Generate 3-8 screens based on the workflow complexity."""

        print(f"   Calling text LLM for screen generation...")
        result = call_llm_json(prompt, "You are a UI layout generation agent for mobile app training simulations.")

        configs: list[ScreenConfig] = []
        for screen_data in result.get("screens", []):
            elements = []
            for el in screen_data.get("elements", []):
                pos = el.get("position", {})
                elements.append(ScreenConfigElement(
                    component_id=el.get("component_id", ""),
                    type=el.get("type", "text_label"),
                    label=el.get("label", ""),
                    position=Position(
                        x=float(pos.get("x", 0)),
                        y=float(pos.get("y", 0)),
                        width=float(pos.get("width", 0)),
                        height=float(pos.get("height", 0)),
                    ),
                    children=[],
                ))
            configs.append(ScreenConfig(
                screen_id=screen_data.get("screen_id", ""),
                screen_name=screen_data.get("screen_name", ""),
                source="vision_ai",
                elements=elements,
            ))
        return configs

