"""Educator file attachments for learning items (Student 2: publication integrity).

Controls, in brief:
- One attachment per learning item, uploaded by the item's own educator (or an
  admin) only while the item is pending. Once approved or rejected the file is
  frozen, so what the admin reviewed is what learners download.
- Allowed types: PDF, PNG and plain UTF-8 text. The extension must match the
  file's actual signature (magic bytes), so an HTML or executable file renamed
  to .pdf is rejected. Size limit is MAX_BYTES.
- Files are stored under a random server-chosen name. The uploaded name is
  kept only as cleaned display metadata and never used as a path.
- Downloads are always sent as attachments with a fixed content type, nosniff
  and a sandbox CSP, so a file is never rendered as a page on this site.
- Every upload records a SHA-256 hash, and the caller writes audit events for
  accepted and rejected uploads.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
import unicodedata
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

MAX_BYTES = 5 * 1024 * 1024
ALLOWED = {
    "pdf": "application/pdf",
    "png": "image/png",
    "txt": "text/plain; charset=utf-8",
}
_SAFE_NAME = re.compile(r"[^A-Za-z0-9 ._()-]+")


class UploadError(Exception):
    def __init__(self, message: str, status: int = 400, reason: str = "invalid"):
        super().__init__(message)
        self.status = status
        self.reason = reason


def clean_filename(raw: str) -> str:
    """Return a display-only file name: no folders, no control or odd characters."""
    name = PureWindowsPath(PurePosixPath(raw or "").name).name
    name = unicodedata.normalize("NFKC", name)
    name = _SAFE_NAME.sub("_", name).strip(" .")
    name = re.sub(r"_+", "_", name)
    if len(name) > 100:
        stem, dot, ext = name.rpartition(".")
        name = (stem[: 100 - len(ext) - 1] + "." + ext) if dot and len(ext) <= 5 else name[:100]
    return name


def detect_type(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if b"\x00" in data:
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    # Plain text only: no markup that a browser would treat as a document.
    if re.search(r"<\s*(!doctype|html|script|svg|iframe|object|embed)\b", text, re.IGNORECASE):
        return None
    return "txt"


def validate(raw_name: str, data: bytes) -> tuple[str, str]:
    """Check a file and return (clean display name, extension)."""
    name = clean_filename(raw_name)
    if not name or "." not in name:
        raise UploadError("Give the file a name ending in .pdf, .png or .txt.", reason="missing_name")
    extension = name.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED:
        raise UploadError("Only PDF, PNG and plain text (.txt) files can be uploaded.", 415, "extension")
    if not data:
        raise UploadError("The file is empty.", reason="empty")
    if len(data) > MAX_BYTES:
        raise UploadError("Files must be 5 MB or smaller.", 413, "too_large")
    detected = detect_type(data)
    if detected != extension:
        raise UploadError(
            f"The file content does not match a .{extension} file. Rename or export it in the correct format.",
            415,
            "signature_mismatch",
        )
    return name, extension


def store(connection: sqlite3.Connection, upload_root: Path, item: sqlite3.Row, user: dict,
          raw_name: str, data: bytes) -> dict:
    if user["role"] != "admin" and item["created_by"] != user["id"]:
        raise UploadError("You can only attach files to your own learning items.", 403, "not_owner")
    if item["status"] != "pending":
        raise UploadError("Files can only be changed while an item is pending review.", 409, "not_pending")
    name, extension = validate(raw_name, data)
    upload_root.mkdir(parents=True, exist_ok=True)
    stored_name = f"{secrets.token_hex(16)}.{extension}"
    (upload_root / stored_name).write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    previous = connection.execute(
        "SELECT stored_name FROM content_files WHERE learning_item_id = ?", (item["id"],)
    ).fetchone()
    connection.execute(
        """
        INSERT INTO content_files
            (learning_item_id, stored_name, original_name, file_type, size_bytes, sha256, uploaded_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(learning_item_id) DO UPDATE SET
            stored_name = excluded.stored_name, original_name = excluded.original_name,
            file_type = excluded.file_type, size_bytes = excluded.size_bytes, sha256 = excluded.sha256,
            uploaded_by = excluded.uploaded_by, created_at = excluded.created_at
        """,
        (item["id"], stored_name, name, extension, len(data), digest, user["id"],
         datetime.now(UTC).replace(microsecond=0).isoformat()),
    )
    if previous:
        (upload_root / previous["stored_name"]).unlink(missing_ok=True)
    return {"name": name, "type": extension, "size_bytes": len(data), "sha256": digest, "replaced": bool(previous)}


def file_record(connection: sqlite3.Connection, item_id: int) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM content_files WHERE learning_item_id = ?", (item_id,)).fetchone()


def public_info(record: sqlite3.Row | None) -> dict | None:
    if not record:
        return None
    return {"name": record["original_name"], "type": record["file_type"], "size_bytes": record["size_bytes"], "sha256": record["sha256"]}


def download_headers(record: sqlite3.Row) -> dict[str, str]:
    ascii_name = record["original_name"].encode("ascii", "replace").decode().replace('"', "_")
    return {
        "Content-Type": ALLOWED[record["file_type"]],
        "Content-Disposition": f'attachment; filename="{ascii_name}"',
        "Content-Security-Policy": "sandbox; default-src 'none'",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
    }
