import hashlib
import os
from pathlib import Path
from typing import Tuple
from app.core.config import settings
from app.core.logging import logger


class DocumentStorageManager:
    """Handles local raw document persistence and SHA-256 hash generation."""

    def __init__(self, base_dir: str = settings.STORAGE_DIR):
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    async def save_file(self, filename: str, content: bytes) -> Tuple[str, str, int]:
        """Save file bytes and return (file_hash, file_path, file_size_bytes)."""
        file_hash = self.compute_sha256(content)
        file_size = len(content)

        # Store using hash prefix to avoid collision
        safe_filename = f"{file_hash[:12]}_{filename}"
        dest_path = self.raw_dir / safe_filename

        with open(dest_path, "wb") as f:
            f.write(content)

        logger.info(f"Saved file {filename} as {safe_filename} ({file_size} bytes)")
        return file_hash, str(dest_path), file_size


storage_manager = DocumentStorageManager()
