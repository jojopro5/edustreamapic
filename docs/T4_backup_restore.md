# T4 evidence: backup, integrity checks and restore

Student 4 (administration, audit and recovery). Synthetic demo data only: every
account and record comes from `server.seed_database`. No schema change was
needed: backup metadata lives in signed manifest files and events go to the
existing `audit_events` table.

## Requirements

| ID | Requirement |
| --- | --- |
| R-T4-BR-01 | An administrator can take a backup of the live database without stopping the site. |
| R-T4-BR-02 | A backup is checked for tampering and damage before it can be restored. |
| R-T4-BR-03 | A damaged or altered backup is refused, and the refusal is audited. |
| R-T4-BR-04 | A good backup can be restored, and the restore itself can be undone. |
| R-T4-BR-05 | Backup, verify, refuse and restore actions leave an audit trail that a restore cannot erase. |
| R-T4-BR-06 | Only administrators can list, create, verify or restore backups. |

## Threats

| ID | Threat |
| --- | --- |
| TH-T4-BR-01 | An insider edits a backup (for example promotes their account to admin) and recomputes its checksum, hoping it gets restored. |
| TH-T4-BR-02 | Disk damage or a partial copy corrupts a backup file. |
| TH-T4-BR-03 | A request names a file outside the backup folder (path traversal) to overwrite the live database. |
| TH-T4-BR-04 | A non-admin account uses the backup API. |
| TH-T4-BR-05 | A restore is used to wipe audit events that record wrongdoing. |
| TH-T4-BR-06 | Sessions from before the restore stay valid against restored accounts and roles. |
| TH-T4-BR-07 | A file is swapped between verification and restore. |
| TH-T4-BR-08 | A restore locks every administrator out, or a mistaken restore cannot be reversed. |
| TH-T4-BR-09 | Unlimited backups fill the disk. |

## Controls

Problem messages shown to the admin start with the check code (T4_C01 to T4_C05).

| ID | Control | Where |
| --- | --- | --- |
| C-T4-BR-01 (T4_C01) | Only generated names `edustream-<UTC>-<8 hex>.db` are accepted; anything else is 404. | `backups._paths_for` |
| C-T4-BR-02 (T4_C02) | Manifest signed with HMAC-SHA256; the key is in `data/backup.key`, outside the backup folder and never inside a backup. | `backups._sign`, `_check` |
| C-T4-BR-03 (T4_C03) | File size and SHA-256 must match the manifest. | `backups._check` |
| C-T4-BR-04 (T4_C04) | File must open read-only as SQLite and pass `PRAGMA integrity_check`. | `backups._inspect` |
| C-T4-BR-05 (T4_C05) | Required tables present and at least one active admin; a pre-restore safety backup is always taken. | `backups._check`, `restore_backup` |
| C-T4-BR-06 | Verify and restore run on the same private staged copy. | `backups.restore_backup` |
| C-T4-BR-07 | Audit events newer than the backup are copied forward after a restore; every action is logged with `outcome=` and a `ref=`. | `backups.restore_backup`, `server._restore_backup` |
| C-T4-BR-08 | At most 20 backups are kept. | `backups._prune` |
| C-T4-BR-09 | Restore needs the backup name typed as confirmation, ends every session and clears the admin's cookie. | `server._restore_backup` |
| C-T4-BR-10 | All backup endpoints require the admin role. | `server.do_GET`, `do_POST` |

## Seeded fault scenario

`python backups.py seed-fault --kind tamper` makes a backup, promotes the
synthetic learner `learner@edustream.local` to admin inside the copy, and
recomputes the manifest's SHA-256 and size. Only the HMAC signature can catch
it. `--kind corrupt` overwrites 4 KB of the file; `--kind unsigned` replaces
the signature with a plain hash. The CLI records a `backup_fault_seeded`
audit event so the demo is transparent.

Demo: run the command, sign in as the administrator, open **Backup & recovery**,
press **Verify** then **Restore…** on the `seeded-tamper` row. The restore is
refused, the learner keeps the learner role, and **Audit reports** shows
`backup_verify_failed` and `backup_restore_refused`.

## Trace and results

Run `python -m unittest tests.test_backups`. Result on 2026-11-26: 14 of 14 passed (41 of 41 for the full suite).

| Requirement | Threat | Control | Test | Result |
| --- | --- | --- | --- | --- |
| R-T4-BR-01 | TH-T4-BR-02 | C-T4-BR-02, 04 | T4_BR_01 signed backup created and listed | Pass |
| R-T4-BR-06 | TH-T4-BR-04 | C-T4-BR-10 | T4_BR_02 learner, educator and anonymous refused | Pass |
| R-T4-BR-03 | TH-T4-BR-03 | C-T4-BR-01 | T4_BR_03 traversal and unknown names 404 | Pass |
| R-T4-BR-03, 05 | TH-T4-BR-01 | C-T4-BR-02, 07 | T4_BR_04 seeded tamper detected by signature, restore refused, audited | Pass |
| R-T4-BR-03 | TH-T4-BR-02 | C-T4-BR-03 | T4_BR_05 corrupted file refused | Pass |
| R-T4-BR-03 | TH-T4-BR-01 | C-T4-BR-02 | T4_BR_06 forged unsigned manifest refused | Pass |
| R-T4-BR-03 | TH-T4-BR-02 | C-T4-BR-02, 03 | T4_BR_07 missing manifest or file refused | Pass |
| R-T4-BR-04, 05 | TH-T4-BR-05, 06 | C-T4-BR-05, 07, 09 | T4_BR_08 restore recovers data, keeps later audit events, ends sessions | Pass |
| R-T4-BR-04 | TH-T4-BR-08 | C-T4-BR-09 | T4_BR_09 restore needs typed confirmation | Pass |
| R-T4-BR-02 | TH-T4-BR-08 | C-T4-BR-05 | T4_BR_10 backup with no active admin refused | Pass |
| R-T4-BR-04 | TH-T4-BR-08 | C-T4-BR-05 | T4_BR_11 safety backup undoes a restore | Pass |
| R-T4-BR-01 | TH-T4-BR-09 | C-T4-BR-08 | T4_BR_12 old backups pruned | Pass |
| R-T4-BR-02 | TH-T4-BR-07 | C-T4-BR-03, 06 | T4_BR_13 swapped file caught at restore | Pass |
| R-T4-BR-01, 04 | TH-T4-BR-06 | C-T4-BR-09 | T4_BR_14 backup and restore while the server runs | Pass |

## Limits (prototype)

- The signing key sits on the same machine as the backups. In production it would be in a secrets store, and backups would be copied off-site and encrypted.
- Backups are not encrypted; they hold password hashes, so `data/` stays out of git (`.gitignore`).
- A restore replaces the whole database; there is no per-table restore.
