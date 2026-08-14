"""Private document storage (Prompt 11).

Files are written under ``settings.document_storage_dir`` with a random,
non-guessable key. The ``file_ref`` is the *private* storage key — it is never
exposed as a URL by any API; retrieval is authenticated and owner-scoped via
the documents router. Uploads are validated for extension, size and (when
enabled) a SHA-256 checksum recorded at write time.

No third-party SDK is required; the default backend is local disk which also
works on the dev/test SQLite stack. Swap to GCS/S3 by replacing this module
(see docs/architecture/17-extensibility.md).
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import ValidationError_


class DocumentStorageError(ValidationError_):
    code = "DOCUMENT_STORAGE"

    def __init__(self, message: str = "Could not store the document.") -> None:
        super().__init__(message)


class DocumentStorage:
    """Local-disk private storage. Keyed by opaque refs, never by user input."""

    _EXTENSION_RE = re.compile(r"^[a-z0-9]{1,10}$")
    _SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")

    def __init__(self, root: str | None = None, *, max_size_bytes: int | None = None) -> None:
        settings = get_settings()
        self.root = Path(root or settings.document_storage_dir)
        self.max_size_bytes = max_size_bytes or settings.document_max_size_bytes
        self.accepted_formats = [
            fmt.strip().lower()
            for fmt in settings.document_accepted_formats.split(",")
            if fmt.strip()
        ]

    # -- Paths -----------------------------------------------------------------

    def _base_dir(self) -> Path:
        if not self.root.exists():
            self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def _ref_for(self, file_ref: str) -> Path:
        """Resolve a stored ref into a path, blocking traversal attempts."""
        resolved = (self._base_dir() / file_ref).resolve()
        base = self._base_dir().resolve()
        if not str(resolved).startswith(str(base)):
            raise DocumentStorageError("Invalid storage reference.")
        return resolved

    # -- Validation ------------------------------------------------------------

    def validate_extension(self, extension: str) -> str:
        """Return the lower-cased, allowed extension or raise 422."""
        ext = extension.strip().lstrip(".").lower()
        if not self._EXTENSION_RE.match(ext) or ext not in self.accepted_formats:
            raise ValidationError_(
                f"Unsupported file type '{ext}'. Allowed: {', '.join(self.accepted_formats)}.",
                code="DOCUMENT_UNSUPPORTED_FORMAT",
            )
        return ext

    def validate_size(self, size_bytes: int) -> None:
        if size_bytes <= 0:
            raise ValidationError_("Empty file.", code="DOCUMENT_EMPTY_FILE")
        if size_bytes > self.max_size_bytes:
            raise ValidationError_(
                "File too large. Maximum upload size is "
                f"{self.max_size_bytes // (1024 * 1024)} MB.",
                code="DOCUMENT_TOO_LARGE",
            )

    def extension_from_name(self, file_name: str) -> str:
        suffix = Path(file_name or "").suffix
        if suffix:
            return suffix[1:]
        # No suffix: sniff from the allowed list is not reliable — reject.
        raise ValidationError_(
            "File must have an allowed extension (pdf, jpg, jpeg, png).",
            code="DOCUMENT_NO_EXTENSION",
        )

    # -- Write / read / delete ---------------------------------------------------

    async def save(self, data: bytes, *, extension: str) -> tuple[str, str]:
        """Write ``data`` to private storage.

        Returns ``(file_ref, sha256_hex)``. The ref is opaque and random; the
        extension is appended purely for tooling/debugging and is not trusted.
        """
        ext = self.validate_extension(extension)
        self.validate_size(len(data))
        ref = f"{secrets.token_hex(16)}.{ext}"
        path = self._base_dir() / ref
        path.write_bytes(data)
        checksum = hashlib.sha256(data).hexdigest()
        return ref, checksum

    async def read(self, file_ref: str) -> bytes:
        try:
            return self._ref_for(file_ref).read_bytes()
        except FileNotFoundError as exc:  # noqa: PERF203
            raise DocumentStorageError("Document file is missing.") from exc

    async def delete(self, file_ref: str) -> None:
        try:
            path = self._ref_for(file_ref)
            if path.exists():
                os.remove(path)
        except OSError as exc:  # noqa: BLE001 — best-effort cleanup
            raise DocumentStorageError("Could not remove the document file.") from exc


__all__ = ["DocumentStorage", "DocumentStorageError"]
