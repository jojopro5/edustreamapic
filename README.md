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
- A five-question Digital Safety practice quiz with clickable answers, saved scores, feedback, and retakes
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
  quizzes.py              Practice questions and server-side answer keys
  static/                 Website interface and brand assets
  tests/test_api.py       End-to-end API tests
  server.py               Python web server and protected API
  START_EDUSTREAM.bat     Windows launcher
```

The SQLite schema is intentionally separated from the application so the database can later be reviewed or migrated to MySQL without redesigning the website interface.

## Course guides and external resources

Learners can select **Why learn this topic?** on a course card to read its guide. Guides and external YouTube recommendations are introductions; protected learning access still requires a valid subscription entitlement. Video links open in a new tab and credit the original creator. This project is not affiliated with those creators or with the reference site edustream.com.

Edit `static/course-guides.js` to maintain the topic introductions and verified video URLs. A resource outside the curated topics uses its own description and a clearly labelled YouTube topic search instead of assigning an unrelated video.

Each curated guide has one featured video and three related videos covering digital safety, SQL/database design, or web development/security. The page displays the actual resource count and credits the original creators. Thumbnail files are stored in `static/thumbnails/` so their previews can be served locally.

## Practice quiz

Digital Safety Foundations includes a five-question practice quiz. Learners can open it from the dashboard, course card, course guide, or protected learning dialog. Entire answer rows are clickable, keyboard controls work, and students can change answers or retake the quiz after receiving feedback. Scores are graded on the server and saved to the signed-in learner's own account. A quiz result does not automatically change course progress.

SQL Essentials and Secure Web Application Design currently provide course guides, videos, and progress tracking but do not yet include interactive quizzes. The Digital Safety quiz requires an active subscription that includes the course.

After pulling a code update, restart the server so new API routes and database tables are loaded. Existing data is preserved because schema additions run automatically at startup; do not use `--reset` for a normal update.

Question references: [CISA password guidance](https://www.cisa.gov/sites/default/files/2024-09/Secure-Our-World-Passwords-Tip-Sheet.pdf), [NIST phishing guidance](https://www.nist.gov/itl/smallbusinesscyber/guidance-topic/phishing), and [Login.gov account authentication](https://www.login.gov/help/manage-your-account/add-or-change-your-authentication-method/). Privacy and role-access examples follow this project's acceptance checks.
