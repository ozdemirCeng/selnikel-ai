"""
File Validation & Security Inspection Module
Validates file size (max 50 MB), SHA-256 fingerprinting, and magic-byte header inspection.
"""
import hashlib
from typing import Tuple

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# Standard file signatures (Magic Bytes)
MAGIC_SIGNATURES = {
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument",  # docx / xlsx / zip
    b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": "application/msword",      # legacy doc / xls
}

class FileValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_file_payload(content: bytes, filename: str) -> Tuple[str, str, int]:
    """
    Validates binary file payload against size limits and magic-byte headers.
    Returns: (sha256_hash, detected_mime_type, size_bytes)
    """
    size_bytes = len(content)
    if size_bytes == 0:
        raise FileValidationError("EMPTY_FILE", "Yüklenen dosya boş olamaz.")

    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise FileValidationError(
            "FILE_TOO_LARGE",
            f"Dosya boyutu 50 MB sınırını aşıyor ({size_bytes / (1024*1024):.2f} MB)."
        )

    # Calculate SHA-256 content hash
    sha256 = hashlib.sha256(content).hexdigest()

    # Magic byte check
    detected_mime = None
    for sig, mime in MAGIC_SIGNATURES.items():
        if content.startswith(sig):
            detected_mime = mime
            break

    # If not a known binary format, check if it's legitimate UTF-8 text (no null bytes)
    if not detected_mime:
        sample = content[:1024]
        # Real text files do not contain null bytes \x00
        if b"\x00" not in sample:
            try:
                sample.decode("utf-8")
                detected_mime = "text/plain"
            except UnicodeDecodeError:
                pass

    if not detected_mime:
        raise FileValidationError(
            "INVALID_MIME_TYPE",
            f"Desteklenmeyen veya bozuk dosya formatı. Başlık imzası tanınamadı ({filename})."
        )

    return sha256, detected_mime, size_bytes
