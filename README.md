# EduStream

EduStream is a secure subscription-based learning platform prototype for BIS3006. It demonstrates learner entitlements, protected content access, educator publishing, administrator approval, progress tracking, billing records and audit events.

## Run the prototype

Python 3.11 or newer is required. The application uses only Python's standard library, so no package installation is needed.

```powershell
python server.py --port 8765
```

Open `http://127.0.0.1:8765` in a browser. Existing database records are kept between runs. Use `--reset` only when you intentionally want to replace the local prototype data with the sample dataset.

You can also double-click `START_EDUSTREAM.bat` on Windows.

## Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Learner | `learner@edustream.local` | `Learn123!` |
| Educator | `educator@edustream.local` | `Teach123!` |
| Administrator | `admin@edustream.local` | `Admin123!` |

These credentials are for a local prototype only.

## Implemented features

- Role-based login for learners, educators and administrators
- Subscription plans, activation and renewal simulation with a confirmation step; renewals and plan changes add 30 days after the current end date, so paid days are kept
- Server-side entitlement checks before protected content access
- Learning catalogue with locked and included states
- Course search, category/access filters, and sorting
- A personal learning view for in-progress and completed courses
- Course guides explaining why a topic matters, its learning goals, and practical examples
- Twelve credited YouTube video recommendations with synthetic generated thumbnails, with four resources per curated topic
- Learner progress tracking
- Three module quizzes and a final assessment per course, with server-saved drafts, best grades, attempt history, feedback, and different question sets on retakes
- A curated learner catalogue limited to these three English courses; other resources stay hidden from students
- Learner feedback on each course, with administrator moderation
- Educator content submission workflow
- Administrator content approval and rejection
- Validated educator course file attachments (PDF, PNG or text), frozen once reviewed
- Payment records and audit events
- Administrator backup and restore with signed, integrity-checked backups and a seeded tampered-backup scenario
- Responsive desktop and mobile interface
- Accessible mobile navigation, focus handling, and progress controls
- Password hashing and parameterised SQL queries
- Sign-in throttling: 5 failed attempts per account per client (20 per client overall) in 15 minutes returns HTTP 429 with `Retry-After`
- Sessions stored in SQLite (as SHA-256 token digests), so sign-ins survive a server restart
- Learner self-registration (learner role only), a My profile page for every role, and password change that ends other sessions
- Audit events with an outcome (success, failure or denied) and a correlation ID that matches the response's `X-Request-ID` header; failed and throttled sign-ins, logout and wrong-role requests are recorded
- Cross-site request protection: POSTs must be JSON (or the file upload type) and any `Origin` header must match the site
- A simulated payment method that can decline, so a failed payment can be demonstrated without real card data
- Administrator takedown of published items with a required reason, and review decisions recorded with before and after status
- An administrator Operations view with an analytics summary and open issues, plus `operations.py seed-problem` to plant a reproducible problem

### Running beyond your own machine

The session cookie gets the `Secure` flag automatically when `--host` is anything other than a loopback address (for example `--host 0.0.0.0`). Browsers only send Secure cookies over HTTPS, so serve the site through a TLS proxy in that case. Override with `--secure-cookies on|off` or the `EDUSTREAM_SECURE_COOKIES` environment variable, for example `--secure-cookies off` for a plain-HTTP demo on a classroom network.

The sign-in page shows one-click Learner, Educator and Admin buttons. The demo passwords are served by `/api/session` only while these are on, not written into the page. Turn them off for any public deployment with `--demo-logins off` or `EDUSTREAM_DEMO_LOGINS=off`.

State-changing requests must be same-origin JSON: the server refuses a POST whose `Origin` or `Sec-Fetch-Site` shows another site, or whose `Content-Type` is not `application/json` (file uploads use `application/octet-stream` with the `X-File-Name` header). This backs up the `SameSite=Lax` session cookie. If you put the site behind a proxy that rewrites the `Host` header, forward the original host.

## Project structure

```text
EduStream/
  database/schema.sql     SQLite schema for Nimarta's database work
  assessment_content.py  Original module question banks (16 questions per module)
  accounts.py            Registration and profile validation (T1)
  assessments.py         Attempt lifecycle, question selection, gates and grading
  backups.py             Signed SQLite backups, integrity checks, restore and the seeded fault (T4)
  docs/                  Evidence traces (requirement, threat, control, test, result)
  operations.py          Operations summary, open issues and seeded problems (T4)
  quizzes.py              Legacy practice questions, retained for existing records
  static/                 Website interface and brand assets
  tests/                  End-to-end API and assessment workflow tests
  server.py               Python web server and protected API
  START_EDUSTREAM.bat     Windows launcher
```

The SQLite schema is intentionally separated from the application so the database can later be reviewed or migrated to MySQL without redesigning the website interface.

## Learner feedback

Learners can leave feedback in the lesson window of any course their plan includes. Other learners see the comment with the author's first name and initial only.

- Comments are stored as plain text and always displayed as text, so typed markup such as `<script>` shows literally and never runs. Text is kept rather than stripped because the Secure Web course invites learners to discuss code.
- Comments must be 2 to 500 characters. Control and invisible formatting characters are removed. Each learner can post up to 5 comments every 10 minutes.
- A learner can edit or delete only their own comments. Requests for another learner's comment return 404.
- Administrators can hide or restore any comment under **Learner feedback**. Hidden comments disappear for learners, stay in the moderation list with who hid them and when, and can no longer be edited or deleted by their author.
- Posting, editing, deleting, moderation, denied access and rate limiting are audit events. Events record ids only, never the comment text.

Tests are in `tests/test_feedback.py`, named `T3_FB_01` to `T3_FB_09` for the test register.

## Course guides and external resources

Learners can select **Why learn this topic?** on a course card to read its guide. Guides and external YouTube recommendations are introductions; protected learning access still requires a valid subscription entitlement. Video links open in a new tab and credit the original creator. This project is not affiliated with those creators or with the reference site edustream.com.

Edit `static/course-guides.js` to maintain the topic introductions and verified video URLs. A resource outside the curated topics uses its own description and a clearly labelled YouTube topic search instead of assigning an unrelated video.

Each curated guide has one featured video and three related videos covering digital safety, SQL/database design, or web development/security. The page displays the actual resource count and credits the original creators. Preview images in `static/thumbnails/` are synthetic SVG cards generated by `tools/generate_thumbnails.py`; no third-party thumbnails are stored, in line with the synthetic-content requirement.

## Educator course files

Educators can attach one course file to a learning item in Content Studio. Use your own or synthetic material only.

- Allowed types are PDF, PNG and plain UTF-8 text, up to 5 MB. The extension must match the file's actual content, so an HTML page or program renamed to `.pdf` is rejected, and `.txt` files containing HTML or script markup are rejected.
- Files are stored in `data/uploads/` under a random name chosen by the server. The uploaded name is cleaned and kept only for display, so it can never choose a folder or overwrite another file.
- A file can be attached or replaced only by the item's educator (or an administrator) and only while the item is pending. Once the item is approved or rejected the file is frozen, so learners download exactly what the administrator reviewed.
- Administrators can download the file from the approval queue. Learners can download it only when the item is approved, visible and included in their plan.
- Downloads are always sent as attachments with a fixed content type, `nosniff` and a sandbox content security policy. Each file's SHA-256 hash is stored and checked on every download.
- Accepted, rejected (with the reason), denied, downloaded and tampered files are audit events.

Tests are in `tests/test_uploads.py`, named `T2_UP_01` to `T2_UP_08` for the test register. Back up `data/uploads/` together with `data/edustream.db`.

## Accounts and profiles (T1)

New visitors can create a learner account from the sign-in screen. Educator and administrator accounts are never created this way: any `role` sent with the form is ignored.

- Passwords must be 10 to 128 characters, not on a short common-password list and not built from the email address. They are stored as salted PBKDF2 hashes.
- At most 5 accounts can be created from one client address per hour.
- Each account can view and edit only its own name; educators can also add a bio of up to 400 characters. Email and role cannot be changed through the profile.
- Changing a password needs the current password and signs the account out of every other session.
- A duplicate email is refused with HTTP 409. This tells the visitor that the email is registered, which is a known residual risk accepted for the prototype.

Tests: `tests/test_accounts.py`, `T1_AC_01` to `T1_AC_08`.

## Audit trail, cross-site checks and operations (T1, T2, T4)

Every response carries an `X-Request-ID` header. A caller may supply its own ID (8 to 64 letters, digits, `-` or `_`), which is handy for tracing an integration test; otherwise the server generates one. Each audit event stores that ID as `correlation_id` together with an `outcome` of `success`, `failure` or `denied`. Failed sign-ins store a pseudonymous account label (`acct-` plus 12 hex characters of a SHA-256 of the email), never the address or the password.

**Audit reports** lets an administrator filter by event type, outcome or correlation ID, and select a request ID on any event to see everything that request did.

POST requests must use `Content-Type: application/json` (the file upload uses `application/octet-stream`), and an `Origin` header, when the browser sends one, must match the site. Anything else returns 403 and a `request_blocked` event. Together with `SameSite=Lax` cookies this stops another site from submitting forms on a signed-in user's behalf.

When confirming a plan, the learner picks a fictitious test card. The declining card records a failed payment and a `payment_failed` event and leaves the current plan unchanged. No card details are ever accepted.

Administrators can take down any published item from the approval queue. A reason of 5 to 300 characters is required and stored in the `content_taken_down` event; learners lose access straight away.

**Operations** shows active subscriptions per plan, payments in the last 30 days, denied requests in the last 7 days, course engagement, and open issues: failed payments with no later success, 5 or more denied requests from one account in 24 hours, published items with markup or links, failed backup checks or file integrity checks, and submissions waiting more than a week. Each issue links to its audit events.

To plant a reproducible problem for the T4 demo (synthetic data only):

```powershell
python operations.py seed-problem --kind payment   # declined renewal for the demo learner
python operations.py seed-problem --kind access    # burst of denied requests from the demo learner
python operations.py seed-problem --kind content   # published item hiding a script tag and an off-site link
```

Then sign in as the administrator, open **Operations**, follow **View related events**, fix the cause (renew with the approving card, review the account, or take the item down), and press **Refresh** to see the issue clear. Each seeding writes a `problem_seeded` audit event.

Tests: `tests/test_audit_trail.py` (`T4_AU_01` to `T4_AU_07`, `T1_CS_01` to `T1_CS_02`) and `tests/test_operations.py` (`T1_PAY_01` to `T1_PAY_02`, `T2_TD_01`, `T4_OP_01` to `T4_OP_05`).

## Module quizzes and final assessments

Digital Safety Foundations, SQL Essentials, and Secure Web Application Design each have three module quizzes (8 questions each) and a final assessment (12 questions, four from each module). The final unlocks only after all three module quizzes have a passing grade of at least 80%. Passing all four assessments completes the course. Study progress remains a separate learner-maintained record; moving its slider to 100% does not award course completion.

The assessment hub shows module status, best grades, saved drafts, and the 20 most recent submitted attempts per assessment. Answers save to the server as learners work, and reopening an unfinished attempt resumes its saved questions and answers. Learners can navigate questions and review their answers before submission. Submissions are graded on the server and become read-only, with feedback and an unlimited option to start another attempt. Repeated submit requests return the same attempt result rather than create duplicate grades.

Each module has 16 original questions. A new module attempt selects eight questions that were not in that learner's immediately preceding submitted attempt for the same module. The final selects four per module while excluding questions from the previous final attempt. Question and answer-option order is shuffled and saved with the attempt. Questions may recur in later attempts; no claim is made that the finite bank is never repeated. Final questions revisit module content as a cumulative assessment. Existing unfinished attempts resume their same set.

Only the authenticated learner can read, save, or submit their attempts. Role, subscription and course visibility are checked for every request. Question keys and explanations are withheld until submission. Best grades determine completion, so a later unsuccessful retake does not remove an earlier pass. Estimated durations are guidance, not enforced timers. This prototype does not provide proctoring or certificates.

The module-and-assessment flow is inspired by [Coursera's assignment guidance](https://www.coursera.support/s/article/learner-000001563?language=en_US); EduStream's question content and assessment rules are its own. It is not a Coursera integration.

Each quiz requires an active subscription that includes its course. Starter includes Digital Safety and SQL Essentials; Secure Web requires Plus. The Team plan is hidden: it is not listed or sold, but existing Team records and their course access are kept.

The learner catalogue is not a fixed list of IDs. A learning item is shown to learners when it is approved, is not marked Indonesian (`id`), and has both a nonempty practice quiz in `quizzes.py` and module banks in `assessment_content.py`. Pending, rejected, Indonesian and quiz-less items stay hidden, even after approval. Listing an item does not grant access: opening it, updating progress and taking its quizzes all still require an active subscription whose plan has a `plan_entitlements` row for that item. When an admin approves an item it is added to the Plus and Team plans. Existing records and educator/admin review access are preserved. Learner statistics count only visible courses.

To add a course to the learner catalogue, approve it and add its quiz and module banks keyed by its learning item ID.

The content form records English (`en`) or Bahasa Indonesia (`id`). Language is educator-supplied metadata, not automatic language detection. Existing curated English records receive `en` during the automatic schema migration.

Previous five-question practice results remain in `quiz_attempts` and their legacy API is retained for compatibility. They do not count as module passes. New drafts and grades are stored in `assessment_attempts`; existing learning and account records are preserved during startup migration.

After pulling a code update, restart the server so new API routes and database tables are loaded. Existing data is preserved because schema additions run automatically at startup; do not use `--reset` for a normal update.

Question references: [CISA password guidance](https://www.cisa.gov/sites/default/files/2024-09/Secure-Our-World-Passwords-Tip-Sheet.pdf), [NIST phishing guidance](https://www.nist.gov/itl/smallbusinesscyber/guidance-topic/phishing), and [Login.gov account authentication](https://www.login.gov/help/manage-your-account/add-or-change-your-authentication-method/). Privacy and role-access examples follow this project's acceptance checks.

## Backup and recovery (T4)

Administrators open **Backup & recovery** to create a backup, verify it, or restore it. Each backup is a consistent SQLite copy in `data/backups/` with a manifest signed by HMAC-SHA256 (key in `data/backup.key`). Before a restore the server checks the signature, the SHA-256 digest and size, SQLite's integrity check, the required tables and that an active administrator exists. If any check fails the restore is refused and audited. A good restore first takes a safety backup, keeps audit events recorded after the backup, and signs everyone out.

Seeded problem for the demo: `python backups.py seed-fault --kind tamper` creates a backup in which the synthetic learner has been promoted to admin and the checksum recomputed. The signature check catches it. Other commands: `python backups.py create`, `list`, `verify <name>`. The evidence trace is in `docs/T4_backup_restore.md`.
