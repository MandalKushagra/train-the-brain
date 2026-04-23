"""Abstract storage interface for Screen Configs and Simulation Manifests.

Local implementation now; a teammate will implement the remote backend
(S3, REST API) behind the same interface later.
"""

from abc import ABC, abstractmethod

from models.schemas import ScreenConfig, SimulationManifest


class NotFoundError(Exception):
    """Raised when a requested resource is not found in storage."""


class ParseError(Exception):
    """Raised when stored data cannot be parsed or fails validation."""


class StorageInterface(ABC):
    """Abstract storage interface.

    All pipeline components, the Config Editor, and the runtime simulator
    should depend on this interface — never on direct file system or S3 calls.
    """

    @abstractmethod
    def save_screen_config(self, workflow_id: str, config: ScreenConfig) -> None:
        """Persist a ScreenConfig for the given workflow."""
        ...

    @abstractmethod
    def load_screen_config(self, workflow_id: str, screen_id: str) -> ScreenConfig:
        """Load and validate a ScreenConfig. Raises NotFoundError / ParseError."""
        ...

    @abstractmethod
    def list_screen_configs(self, workflow_id: str) -> list[ScreenConfig]:
        """List all ScreenConfigs for a workflow."""
        ...

    @abstractmethod
    def delete_screen_config(self, workflow_id: str, screen_id: str) -> None:
        """Delete a ScreenConfig. Raises NotFoundError if not found."""
        ...

    @abstractmethod
    def save_manifest(self, workflow_id: str, manifest: SimulationManifest) -> None:
        """Persist a SimulationManifest for the given workflow."""
        ...

    @abstractmethod
    def load_manifest(self, workflow_id: str) -> SimulationManifest:
        """Load and validate a SimulationManifest. Raises NotFoundError / ParseError."""
        ...

    @abstractmethod
    def manifest_exists(self, workflow_id: str) -> bool:
        """Check whether a manifest exists for the given workflow."""
        ...
