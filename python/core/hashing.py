"""Cross-cutting file-integrity primitives shared across Lakshya stages."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file's exact byte content.

    This helper owns only the byte-hashing mechanism. Callers retain ownership
    of the provenance, checkpoint, archival, or review contract that gives the
    digest its meaning.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
