"""
Ingestion Worker & File Validator.
Validates file binary magic bytes, MIME types, file sizes, and executes job steps.
"""
import hashlib
import io
from typing import BinaryIO, Optional
from pydantic import BaseModel

class FileValidationResult(BaseModel):
    is_valid: bool
    mime_type: Optional[str] = None
    file_size_bytes: int = 0
    sha256_hash: Optional[str] = None
    error_message: Optional[str] = None


class FileValidator:
    """Validates file magic bytes and size limits (max 50 MB)."""
    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

    MAGIC_BYTES = {
        b"%PDF": "application/pdf",
        b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        b"\xd0\xcf\x11\xe0": "application/msword",
    }

    @classmethod
    def validate_file(cls, stream: BinaryIO, filename: str) -> FileValidationResult:
        stream.seek(0, io.SEEK_END)
        size = stream.tell()
        stream.seek(0)

        if size == 0:
            return FileValidationResult(
                is_valid=False,
                file_size_bytes=0,
                error_message="Yüklenen dosya boştur (0 byte).",
            )

        if size > cls.MAX_FILE_SIZE_BYTES:
            return FileValidationResult(
                is_valid=False,
                file_size_bytes=size,
                error_message=f"Dosya boyutu sınırı aşıldı ({size / (1024*1024):.1f} MB > 50 MB).",
            )

        header = stream.read(16)
        stream.seek(0)

        # Detect MIME type from magic bytes
        detected_mime = None
        for magic, mime in cls.MAGIC_BYTES.items():
            if header.startswith(magic):
                detected_mime = mime
                break

        if not detected_mime:
            if filename.lower().endswith(".txt"):
                detected_mime = "text/plain"
            else:
                return FileValidationResult(
                    is_valid=False,
                    file_size_bytes=size,
                    error_message=f"Geçersiz veya desteklenmeyen dosya formatı: {filename}",
                )

        # Compute SHA-256
        sha256 = hashlib.sha256()
        while chunk := stream.read(65536):
            sha256.update(chunk)
        stream.seek(0)

        return FileValidationResult(
            is_valid=True,
            mime_type=detected_mime,
            file_size_bytes=size,
            sha256_hash=sha256.hexdigest(),
        )
