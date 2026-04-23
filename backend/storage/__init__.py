"""Storage abstraction layer.

Local implementation now, remote implementation by teammate later.
"""

from storage.storage_interface import (
    StorageInterface,
    NotFoundError,
    ParseError,
)
from storage.local_file_storage import LocalFileStorage

__all__ = [
    "StorageInterface",
    "LocalFileStorage",
    "NotFoundError",
    "ParseError",
]
