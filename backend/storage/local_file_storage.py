"""Local file-based storage implementation.

Stores JSON files on disk organised as:
    {base_dir}/{workflow_id}/screen_configs/{screen_id}.json
    {base_dir}/{workflow_id}/manifest.json
"""

import json
import os
from pathlib import Path

from pydantic import ValidationError

from models.schemas import ScreenConfig, SimulationManifest
from storage.storage_interface import StorageInterface, NotFoundError, ParseError


class LocalFileStorage(StorageInterface):
    """Stores Screen Configs and Manifests as JSON files on the local filesystem."""

    def __init__(self, base_dir: str = "./data") -> None:
        self.base_dir = Path(base_dir)

    # ── helpers ──────────────────────────────────────────────

    def _configs_dir(self, workflow_id: str) -> Path:
        return self.base_dir / workflow_id / "screen_configs"

    def _config_path(self, workflow_id: str, screen_id: str) -> Path:
        return self._configs_dir(workflow_id) / f"{screen_id}.json"

    def _manifest_path(self, workflow_id: str) -> Path:
        return self.base_dir / workflow_id / "manifest.json"

    # ── Screen Config operations ─────────────────────────────

    def save_screen_config(self, workflow_id: str, config: ScreenConfig) -> None:
        path = self._config_path(workflow_id, config.screen_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(config.model_dump_json(indent=2), encoding="utf-8")

    def load_screen_config(self, workflow_id: str, screen_id: str) -> ScreenConfig:
        path = self._config_path(workflow_id, screen_id)
        if not path.exists():
            raise NotFoundError(
                f"Screen config not found: workflow={workflow_id}, screen={screen_id}"
            )

        raw = path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ParseError(
                f"Failed to parse screen config JSON: workflow={workflow_id}, "
                f"screen={screen_id}"
            ) from exc

        try:
            return ScreenConfig.model_validate(data)
        except ValidationError as exc:
            raise ParseError(
                f"Invalid screen config: {exc}"
            ) from exc

    def list_screen_configs(self, workflow_id: str) -> list[ScreenConfig]:
        configs_dir = self._configs_dir(workflow_id)
        if not configs_dir.exists():
            return []

        configs: list[ScreenConfig] = []
        for file_path in sorted(configs_dir.glob("*.json")):
            screen_id = file_path.stem
            try:
                configs.append(self.load_screen_config(workflow_id, screen_id))
            except (NotFoundError, ParseError):
                # skip corrupt / invalid files
                continue
        return configs

    def delete_screen_config(self, workflow_id: str, screen_id: str) -> None:
        path = self._config_path(workflow_id, screen_id)
        if not path.exists():
            raise NotFoundError(
                f"Screen config not found: workflow={workflow_id}, screen={screen_id}"
            )
        os.remove(path)

    # ── Manifest operations ──────────────────────────────────

    def save_manifest(self, workflow_id: str, manifest: SimulationManifest) -> None:
        path = self._manifest_path(workflow_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    def load_manifest(self, workflow_id: str) -> SimulationManifest:
        path = self._manifest_path(workflow_id)
        if not path.exists():
            raise NotFoundError(f"Manifest not found: workflow={workflow_id}")

        raw = path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ParseError(
                f"Failed to parse manifest JSON: workflow={workflow_id}"
            ) from exc

        try:
            return SimulationManifest.model_validate(data)
        except ValidationError as exc:
            raise ParseError(f"Invalid manifest: {exc}") from exc

    def manifest_exists(self, workflow_id: str) -> bool:
        return self._manifest_path(workflow_id).exists()
