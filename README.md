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
