"""Administrator backup, verification and restore for the EduStream SQLite database.

Student 4 (T4: administration, audit and recovery). See docs/T4_backup_restore.md
for the requirement -> threat -> control -> test -> result trace.

Each backup is two files in ``<data>/backups``:

* ``edustream-<UTC time>-<random>.db``: a consistent copy taken with SQLite's
  online backup API, so it is safe while the server is running.
* the same name with ``.json``: a manifest holding the copy's SHA-256 digest,
  size, table row counts and the highest audit event id, signed with
  HMAC-SHA256.

The HMAC key lives in ``<data>/backup.key``, outside the backup folder and never
inside a backup. A person who edits a backup can recompute its SHA-256, but
cannot produce a valid signature without the key, so the edit is detected
(control C-T4-BR-02). A restore is refused unless every check passes.

The module uses only the standard library and makes no change to
database/schema.sql: backup metadata is kept in the manifest files and events
go to the existing audit_events table.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path

NAME_PATTERN = re.compile(r"edustream-\d{8}T\d{6}Z-[0-9a-f]{8}\.db")
MANIFEST_FORMAT = "edustream-backup/1"
MAX_BACKUPS = 20
# Tables a backup must contain to be a usable EduStream database.
REQUIRED_TABLES = frozenset(
    {"users", "plans", "subscriptions", "learning_items", "plan_entitlements",
     "progress", "payments", "audit_events", "assessment_attempts"}
)
# Serialises backup, restore and pruning so two admins cannot interleave them.
_LOCK = threading.Lock()


class BackupError(Exception):
    """A backup could not be used. ``problems`` lists each failed check."""

    def __init__(self, message: str, problems: list[str] | None = None):
        super().__init__(message)
        self.problems = problems or [message]


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def backup_dir(db_path: Path) -> Path:
    return Path(db_path).parent / "backups"


def key_path(db_path: Path) -> Path:
    return Path(db_path).parent / "backup.key"


def _signing_key(db_path: Path) -> bytes:
    path = key_path(db_path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        # O_EXCL: if two processes race, only one key is ever written.
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "w", encoding="ascii") as handle:
                handle.write(secrets.token_hex(32))
    key = bytes.fromhex(path.read_text(encoding="ascii").strip())
    if len(key) < 32:
        raise BackupError("The backup signing key is invalid.")
    return key


def _canonical(manifest: dict) -> bytes:
    unsigned = {k: v for k, v in manifest.items() if k != "hmac"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sign(db_path: Path, manifest: dict) -> str:
    return hmac.new(_signing_key(db_path), _canonical(manifest), hashlib.sha256).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _open_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def _inspect(path: Path) -> dict:
    """Open a database copy read-only and describe it. Raises sqlite3.DatabaseError if unreadable."""
    connection = _open_readonly(path)
    try:
        integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
        tables = sorted(
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        )
        counts = {}
        for table in tables:
            if table in REQUIRED_TABLES:
                counts[table] = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        max_audit = 0
        admins = 0
        if "audit_events" in tables:
            max_audit = connection.execute("SELECT COALESCE(MAX(id), 0) FROM audit_events").fetchone()[0]
        if "users" in tables:
            admins = connection.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
            ).fetchone()[0]
        return {"integrity": integrity, "tables": tables, "row_counts": counts,
                "max_audit_id": max_audit, "active_admins": admins}
    finally:
        connection.close()


def _paths_for(db_path: Path, name: str) -> tuple[Path, Path]:
    # C-T4-BR-01: only names this module generates are accepted, so a request
    # cannot point a restore at ../edustream.db or any other file.
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise BackupError("Backup name is not valid.", ["T4_C01 name is not a generated backup name"])
    folder = backup_dir(db_path)
    return folder / name, folder / (name[:-3] + ".json")


def exists(db_path: Path, name: str) -> bool:
    """True if ``name`` is a valid backup name and its file or manifest is present."""
    try:
        file_path, manifest_path = _paths_for(Path(db_path), name)
    except BackupError:
        return False
    return file_path.is_file() or manifest_path.is_file()


def create_backup(db_path: Path, created_by: str, label: str = "manual") -> dict:
    """Copy the live database, check the copy, write a signed manifest and return it."""
    db_path = Path(db_path)
    with _LOCK:
        return _create_backup_locked(db_path, created_by, label)


def _create_backup_locked(db_path: Path, created_by: str, label: str) -> dict:
    folder = backup_dir(db_path)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = _now()
    name = f"edustream-{stamp.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(4)}.db"
    target, manifest_path = _paths_for(db_path, name)
    partial = target.with_suffix(".partial")
    source = sqlite3.connect(db_path, timeout=10)
    dest = sqlite3.connect(partial)
    try:
        source.backup(dest)
    finally:
        dest.close()
        source.close()
    try:
        facts = _inspect(partial)
        if facts["integrity"] != ["ok"]:
            raise BackupError("The new backup failed SQLite's integrity check.")
        os.replace(partial, target)
    finally:
        partial.unlink(missing_ok=True)
    manifest = {
        "format": MANIFEST_FORMAT,
        "file": name,
        "label": str(label)[:40],
        "created_at": stamp.isoformat(),
        "created_by": str(created_by)[:120],
        "size": target.stat().st_size,
        "sha256": _sha256(target),
        "tables": facts["tables"],
        "row_counts": facts["row_counts"],
        "max_audit_id": facts["max_audit_id"],
    }
    manifest["hmac"] = _sign(db_path, manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    _prune(db_path)
    return manifest


def _prune(db_path: Path) -> None:
    # C-T4-BR-08: keep a bounded number of copies so backups cannot fill the disk.
    names = sorted(p.name for p in backup_dir(db_path).glob("edustream-*.db") if NAME_PATTERN.fullmatch(p.name))
    for name in names[:-MAX_BACKUPS]:
        file_path, manifest_path = _paths_for(db_path, name)
        file_path.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)


def _check(db_path: Path, file_path: Path, manifest_path: Path, name: str) -> tuple[dict | None, list[str]]:
    """Run every integrity check against ``file_path``. Returns (manifest, problems)."""
    problems: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError
    except FileNotFoundError:
        return None, ["T4_C02 manifest is missing"]
    except (ValueError, UnicodeDecodeError):
        return None, ["T4_C02 manifest is not valid JSON"]

    signature = manifest.get("hmac")
    if not isinstance(signature, str) or not hmac.compare_digest(signature, _sign(db_path, manifest)):
        problems.append("T4_C02 manifest signature does not match (manifest or backup was altered)")
    if manifest.get("format") != MANIFEST_FORMAT or manifest.get("file") != name:
        problems.append("T4_C02 manifest does not describe this backup file")

    if not file_path.is_file():
        problems.append("T4_C03 backup file is missing")
        return manifest, problems
    if file_path.stat().st_size != manifest.get("size"):
        problems.append("T4_C03 file size differs from the manifest")
    if _sha256(file_path) != manifest.get("sha256"):
        problems.append("T4_C03 SHA-256 digest differs from the manifest")

    try:
        facts = _inspect(file_path)
    except sqlite3.DatabaseError as exc:
        problems.append(f"T4_C04 file is not a readable SQLite database ({exc})")
        return manifest, problems
    if facts["integrity"] != ["ok"]:
        problems.append("T4_C04 SQLite integrity check failed: " + "; ".join(facts["integrity"][:3]))
    missing = sorted(REQUIRED_TABLES - set(facts["tables"]))
    if missing:
        problems.append("T4_C05 required tables are missing: " + ", ".join(missing))
    if facts["active_admins"] < 1:
        problems.append("T4_C05 backup has no active administrator, so restoring it would lock admins out")
    return manifest, problems


def verify_backup(db_path: Path, name: str) -> dict:
    """Check a stored backup. Returns {"name", "ok", "problems", "manifest"}."""
    file_path, manifest_path = _paths_for(Path(db_path), name)
    manifest, problems = _check(Path(db_path), file_path, manifest_path, name)
    return {"name": name, "ok": not problems, "problems": problems, "manifest": manifest}


def list_backups(db_path: Path) -> list[dict]:
    folder = backup_dir(Path(db_path))
    if not folder.is_dir():
        return []
    names = sorted(
        {p.name for p in folder.glob("edustream-*.db") if NAME_PATTERN.fullmatch(p.name)}
        | {p.stem + ".db" for p in folder.glob("edustream-*.json") if NAME_PATTERN.fullmatch(p.stem + ".db")},
        reverse=True,
    )
    result = []
    for name in names:
        check = verify_backup(db_path, name)
        manifest = check["manifest"] or {}
        result.append({
            "name": name,
            "label": manifest.get("label", ""),
            "created_at": manifest.get("created_at"),
            "created_by": manifest.get("created_by", ""),
            "size": manifest.get("size"),
            "row_counts": manifest.get("row_counts", {}),
            "ok": check["ok"],
            "problems": check["problems"],
        })
    return result


def restore_backup(db_path: Path, name: str, actor: str) -> dict:
    """Verify and restore a backup over the live database.

    Returns {"restored": manifest, "safety_backup": manifest, "carried_audit": int}.
    Raises BackupError (with ``problems``) and leaves the live database untouched
    if any check fails.
    """
    db_path = Path(db_path)
    with _LOCK:
        file_path, manifest_path = _paths_for(db_path, name)
        # C-T4-BR-06: verify and restore from the same private copy, so the file
        # cannot be swapped between the check and the restore.
        fd, staged_name = tempfile.mkstemp(prefix=".restore-", suffix=".db", dir=backup_dir(db_path))
        staged = Path(staged_name)
        try:
            with os.fdopen(fd, "wb") as out:
                if file_path.is_file():
                    with open(file_path, "rb") as src:
                        for chunk in iter(lambda: src.read(1 << 16), b""):
                            out.write(chunk)
            manifest, problems = _check(db_path, staged, manifest_path, name)
            if problems:
                raise BackupError("Backup failed its integrity checks and was not restored.", problems)

            # C-T4-BR-05: a safety copy of the current state is taken first, so a
            # restore can itself be undone.
            safety = _create_backup_locked(db_path, actor, "pre-restore")

            live = sqlite3.connect(db_path, timeout=10)
            try:
                carried = [
                    tuple(row) for row in live.execute(
                        "SELECT user_id, event_type, details, created_at FROM audit_events WHERE id > ? ORDER BY id",
                        (manifest["max_audit_id"],),
                    )
                ]
                backup_db = _open_readonly(staged)
                try:
                    backup_db.backup(live)
                finally:
                    backup_db.close()
                # C-T4-BR-07: audit events recorded after the backup was taken are
                # copied forward, so a restore cannot be used to erase the trail.
                live.execute("PRAGMA foreign_keys = ON")
                known = {row[0] for row in live.execute("SELECT id FROM users")}
                live.executemany(
                    "INSERT INTO audit_events (user_id, event_type, details, created_at) VALUES (?, ?, ?, ?)",
                    [(uid if uid in known else None, etype, details, created) for uid, etype, details, created in carried],
                )
                live.commit()
            finally:
                live.close()
            return {"restored": manifest, "safety_backup": safety, "carried_audit": len(carried)}
        finally:
            staged.unlink(missing_ok=True)


# --- Seeded fault scenario (evidence for T4) -------------------------------

FAULT_KINDS = ("tamper", "corrupt", "unsigned")


def seed_fault(db_path: Path, kind: str = "tamper") -> dict:
    """Create a backup, then deliberately damage it. Returns the damaged backup's manifest.

    * tamper: promote the synthetic learner account to admin inside the copy and
      recompute the SHA-256 and size in the manifest, as a careful attacker
      would. Only the HMAC signature still exposes the change.
    * corrupt: overwrite 4 KB in the middle of the file, as disk damage would.
    * unsigned: replace the manifest with a self-made one with no valid signature.
    """
    if kind not in FAULT_KINDS:
        raise ValueError(f"kind must be one of {', '.join(FAULT_KINDS)}")
    db_path = Path(db_path)
    manifest = create_backup(db_path, "Seeded fault scenario", f"seeded-{kind}")
    file_path, manifest_path = _paths_for(db_path, manifest["file"])
    if kind == "tamper":
        connection = sqlite3.connect(file_path)
        try:
            connection.execute("UPDATE users SET role = 'admin' WHERE email = 'learner@edustream.local'")
            connection.commit()
        finally:
            connection.close()
        manifest["size"] = file_path.stat().st_size
        manifest["sha256"] = _sha256(file_path)
    elif kind == "corrupt":
        size = file_path.stat().st_size
        with open(file_path, "r+b") as handle:
            handle.seek(max(0, size // 2 - 2048))
            handle.write(b"\x00\xff" * 2048)
    else:
        manifest["hmac"] = hashlib.sha256(_canonical(manifest)).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def _record(db_path: Path, event_type: str, details: str) -> None:
    connection = sqlite3.connect(db_path, timeout=10)
    try:
        connection.execute(
            "INSERT INTO audit_events (user_id, event_type, details, created_at) VALUES (NULL, ?, ?, ?)",
            (event_type, details[:500], _now().isoformat()),
        )
        connection.commit()
    finally:
        connection.close()


def main() -> None:
    default_db = Path(__file__).resolve().parent / "data" / "edustream.db"
    parser = argparse.ArgumentParser(description="EduStream backup tools (prototype, synthetic data only)")
    parser.add_argument("--db", type=Path, default=default_db, help="Database file (default: data/edustream.db)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("create", help="Take a signed backup")
    sub.add_parser("list", help="List backups and their check results")
    verify = sub.add_parser("verify", help="Check one backup")
    verify.add_argument("name")
    fault = sub.add_parser("seed-fault", help="Create a deliberately damaged backup for the T4 demo")
    fault.add_argument("--kind", choices=FAULT_KINDS, default="tamper")
    args = parser.parse_args()

    if not args.db.exists():
        parser.error(f"{args.db} does not exist. Start the server once to create it.")
    if args.command == "create":
        manifest = create_backup(args.db, "Command line", "manual")
        _record(args.db, "backup_created", f"outcome=success backup={manifest['file']} by=command line")
        print(manifest["file"])
    elif args.command == "list":
        for entry in list_backups(args.db):
            print(("OK      " if entry["ok"] else "FAILED  ") + entry["name"] + "  " + entry["label"])
            for problem in entry["problems"]:
                print("        - " + problem)
    elif args.command == "verify":
        try:
            result = verify_backup(args.db, args.name)
        except BackupError as exc:
            parser.error(str(exc))
        print("OK" if result["ok"] else "FAILED")
        for problem in result["problems"]:
            print(" - " + problem)
        raise SystemExit(0 if result["ok"] else 1)
    else:
        manifest = seed_fault(args.db, args.kind)
        _record(args.db, "backup_fault_seeded", f"outcome=seeded kind={args.kind} backup={manifest['file']}")
        print(f"Seeded a {args.kind} fault in {manifest['file']}")
        print("Sign in as the administrator, open Backup & recovery, and try to restore it.")


if __name__ == "__main__":
    main()
