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
- Subscription plans, activation and renewal simulation
- Server-side entitlement checks before protected content access
- Learning catalogue with locked and included states
- Course search, category/access filters, and sorting
- A personal learning view for in-progress and completed courses
- Course guides explaining why a topic matters, its learning goals, and practical examples
- Twelve credited YouTube video recommendations with thumbnails, with four resources per curated topic
- Learner progress tracking
- Three module quizzes and a final assessment per course, with server-saved drafts, best grades, attempt history, feedback, and different question sets on retakes
- A curated learner catalogue limited to these three English courses; other resources stay hidden from students
- Educator content submission workflow
- Administrator content approval and rejection
- Payment records and audit events
- Responsive desktop and mobile interface
- Accessible mobile navigation, focus handling, and progress controls
- Password hashing and parameterised SQL queries

## Project structure

```text
EduStream/
  database/schema.sql     SQLite schema for Nimarta's database work
  assessment_content.py  Original module question banks (16 questions per module)
  assessments.py         Attempt lifecycle, question selection, gates and grading
  quizzes.py              Legacy practice questions, retained for existing records
  static/                 Website interface and brand assets
  tests/                  End-to-end API and assessment workflow tests
  server.py               Python web server and protected API
  START_EDUSTREAM.bat     Windows launcher
```

The SQLite schema is intentionally separated from the application so the database can later be reviewed or migrated to MySQL without redesigning the website interface.

## Course guides and external resources

Learners can select **Why learn this topic?** on a course card to read its guide. Guides and external YouTube recommendations are introductions; protected learning access still requires a valid subscription entitlement. Video links open in a new tab and credit the original creator. This project is not affiliated with those creators or with the reference site edustream.com.

Edit `static/course-guides.js` to maintain the topic introductions and verified video URLs. A resource outside the curated topics uses its own description and a clearly labelled YouTube topic search instead of assigning an unrelated video.

Each curated guide has one featured video and three related videos covering digital safety, SQL/database design, or web development/security. The page displays the actual resource count and credits the original creators. Thumbnail files are stored in `static/thumbnails/` so their previews can be served locally.

## Module quizzes and final assessments

Digital Safety Foundations, SQL Essentials, and Secure Web Application Design each have three module quizzes (8 questions each) and a final assessment (12 questions, four from each module). The final unlocks only after all three module quizzes have a passing grade of at least 80%. Passing all four assessments completes the course. Study progress remains a separate learner-maintained record; moving its slider to 100% does not award course completion.

The assessment hub shows module status, best grades, saved drafts, and the 20 most recent submitted attempts per assessment. Answers save to the server as learners work, and reopening an unfinished attempt resumes its saved questions and answers. Learners can navigate questions and review their answers before submission. Submissions are graded on the server and become read-only, with feedback and an unlimited option to start another attempt. Repeated submit requests return the same attempt result rather than create duplicate grades.

Each module has 16 original questions. A new module attempt selects eight questions that were not in that learner's immediately preceding submitted attempt for the same module. The final selects four per module while excluding questions from the previous final attempt. Question and answer-option order is shuffled and saved with the attempt. Questions may recur in later attempts; no claim is made that the finite bank is never repeated. Final questions revisit module content as a cumulative assessment. Existing unfinished attempts resume their same set.

Only the authenticated learner can read, save, or submit their attempts. Role, subscription and course visibility are checked for every request. Question keys and explanations are withheld until submission. Best grades determine completion, so a later unsuccessful retake does not remove an earlier pass. Estimated durations are guidance, not enforced timers. This prototype does not provide proctoring or certificates.

The module-and-assessment flow is inspired by [Coursera's assignment guidance](https://www.coursera.support/s/article/learner-000001563?language=en_US); EduStream's question content and assessment rules are its own. It is not a Coursera integration.

Each quiz requires an active subscription that includes its course. Starter includes Digital Safety and SQL Essentials; Secure Web requires Plus or Team.

Only these three selected courses (IDs 1–3) are eligible for the learner catalogue. They must be approved, have a nonempty quiz, and be marked English. All other resources, including Indonesian content, stay hidden from learners even after approval. The same restriction applies to direct content access, progress updates, and quiz requests. Existing records and educator/admin review access are preserved. Learner statistics count only visible courses.

The content form records English (`en`) or Bahasa Indonesia (`id`). Language is educator-supplied metadata, not automatic language detection. Existing curated English records receive `en` during the automatic schema migration. To expand the learner catalogue later, review `LEARNER_COURSE_IDS` in `server.py`, its eligibility checks, and the matching module banks in `assessment_content.py`.

Previous five-question practice results remain in `quiz_attempts` and their legacy API is retained for compatibility. They do not count as module passes. New drafts and grades are stored in `assessment_attempts`; existing learning and account records are preserved during startup migration.

After pulling a code update, restart the server so new API routes and database tables are loaded. Existing data is preserved because schema additions run automatically at startup; do not use `--reset` for a normal update.

Question references: [CISA password guidance](https://www.cisa.gov/sites/default/files/2024-09/Secure-Our-World-Passwords-Tip-Sheet.pdf), [NIST phishing guidance](https://www.nist.gov/itl/smallbusinesscyber/guidance-topic/phishing), and [Login.gov account authentication](https://www.login.gov/help/manage-your-account/add-or-change-your-authentication-method/). Privacy and role-access examples follow this project's acceptance checks.
