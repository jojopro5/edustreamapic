"""Original EduStream module questions; grading keys remain on the server.

Each course has three sixteen-question banks. Module attempts select eight;
final exams select four from each bank. The larger banks support genuinely
different questions on the next attempt. All questions are original material.
"""


def _question(question_id, prompt, choices, correct, explanation):
    return {
        "id": question_id,
        "prompt": prompt,
        "options": [
            {"id": option_id, "text": text}
            for option_id, text in zip("abcd", choices, strict=True)
        ],
        "correct_option_id": correct,
        "explanation": explanation,
    }


COURSE_ASSESSMENTS = {
    1: {
        "title": "Digital Safety Foundations",
        "modules": [
            {
                "id": "module-1",
                "title": "Protecting accounts and devices",
                "description": "Choose safer passwords, use additional sign-in protection, and secure the devices you study on.",
                "estimated_minutes": 12,
                "questions": [
                    _question("m1q1", "A learner needs a password for a new study account. Which approach offers the strongest protection against password reuse?", [
                        "Use the same password as the learner's email account.",
                        "Use a long, unique password stored in a trusted password manager.",
                        "Use the learner's name and birth year on every study website.",
                        "Ask every member of the project team to share one password.",
                    ], "b", "A unique password prevents a breach of one service from immediately exposing other accounts that reuse that password. A password manager helps manage different long passwords."),
                    _question("m1q2", "What extra protection does multi-factor authentication provide when a password is stolen?", [
                        "It gives every signed-in user permission to manage other accounts.",
                        "It makes the password visible only to classmates.",
                        "It requires another independent verification factor for sign-in.",
                        "It guarantees that every message the learner receives is genuine.",
                    ], "c", "An additional verification factor can prevent a stolen password alone from being enough to sign in. It does not remove the need to recognise suspicious messages."),
                    _question("m1q3", "Your phone shows an unexpected request to approve a sign-in that you did not start. What should you do first?", [
                        "Deny the request and check your account through its known website or app.",
                        "Approve it so the repeated prompts stop.",
                        "Send the approval code to the person who requested it.",
                        "Approve it if it arrives outside class hours.",
                    ], "a", "An unexpected approval request can indicate someone is attempting to use your account. Deny it and investigate through a trusted route rather than approving an unknown sign-in."),
                    _question("m1q4", "A service provides recovery codes for use when your second-factor device is unavailable. Where should you keep them?", [
                        "In a public project repository so they cannot be lost.",
                        "In a group chat where everyone can retrieve them.",
                        "On a screenshot posted beside your student profile.",
                        "In a secure location you can access if you lose the device.",
                    ], "d", "Recovery codes can grant access to an account. Keep them private and available through a secure recovery route, rather than publishing or sharing them."),
                    _question("m1q5", "You finish using EduStream on a shared library computer. Which action best protects the account from the next user?", [
                        "Minimise the browser window.",
                        "Sign out and avoid leaving saved credentials on the computer.",
                        "Leave the learner dashboard open but turn off the monitor.",
                        "Close only the course video while keeping the account signed in.",
                    ], "b", "Signing out ends access through the active session. Saved credentials on a shared device can still expose an account, so they should not be left there."),
                    _question("m1q6", "A different website reports that your password was exposed, and you reused that password for your email account. What is the most appropriate response?", [
                        "Wait until someone changes the email account before acting.",
                        "Change the exposed password only on the reporting website.",
                        "Replace it with different strong passwords on every account where it was reused.",
                        "Post the old password online to warn others.",
                    ], "c", "Attackers may try exposed credentials on other services. Replace reused passwords, secure the affected accounts, and review available account activity and sign-in protection."),
                    _question("m1q7", "Why should learners install security updates from their device's trusted update mechanism?", [
                        "Updates can fix vulnerabilities that attackers might exploit.",
                        "Updates remove the need for passwords on all websites.",
                        "Every update automatically makes all downloaded files safe.",
                        "Updates give websites permission to collect unlimited personal data.",
                    ], "a", "Security updates can correct known weaknesses in software. They complement safer account and browsing habits rather than replacing them."),
                    _question("m1q8", "What is an important responsibility when using a password manager?", [
                        "Use a short master password because the stored passwords are long.",
                        "Share the manager's unlock credentials with the whole class.",
                        "Export all saved passwords into an unprotected public document.",
                        "Protect the manager with a strong unlock credential and available additional sign-in protection.",
                    ], "d", "A password manager protects many account credentials. Its own access and recovery settings therefore need careful protection."),
                ],
            },
            {
                "id": "module-2",
                "title": "Recognising online threats",
                "description": "Evaluate messages, links, downloads, and urgent requests before trusting them with an account or device.",
                "estimated_minutes": 12,
                "questions": [
                    _question("m2q1", "An email says your course access expires in ten minutes unless you sign in through an unfamiliar link. What is the safest way to check the claim?", [
                        "Enter the password quickly because the message is urgent.",
                        "Reply with the password and ask the sender to check it.",
                        "Open the platform using its known address and check the account there.",
                        "Forward the message to everyone and ask them to try the link.",
                    ], "c", "Urgency and an unfamiliar sign-in link are reasons to verify independently. Opening the known service address avoids relying on the message's supplied link."),
                    _question("m2q2", "Your platform's known host is learning.example. Which address uses that exact host, rather than putting its name inside another host?", [
                        "https://learning.example/courses",
                        "https://learning.example.attacker.test/courses",
                        "https://learning-example.test/courses",
                        "https://attacker.test/learning.example",
                    ], "a", "In these examples, the host is the domain after https:// and before the next slash. The other addresses use different hosts even though their text resembles or includes the expected name."),
                    _question("m2q3", "A website uses HTTPS and displays a padlock. What can you conclude from that alone?", [
                        "Every claim on the website is trustworthy.",
                        "The website is definitely owned by your university.",
                        "Any file offered by the website is safe to run.",
                        "The connection to that website is encrypted, but its identity and requests still need checking.",
                    ], "d", "HTTPS protects the connection to the host. A misleading or malicious site can also use HTTPS, so encryption alone does not establish that a site is the one you intended to visit."),
                    _question("m2q4", "A poster has a QR code labelled 'Student account verification'. Scanning it opens a login page you do not recognise. What should you do?", [
                        "Enter your login because QR codes cannot be changed.",
                        "Check the destination and verify the request through an official channel before entering credentials.",
                        "Use a classmate's account first to see whether it works.",
                        "Grant the page every requested permission to complete verification.",
                    ], "b", "A QR code is another way of supplying a destination. Treat an unexpected login destination like an unfamiliar link and verify it before sharing account information."),
                    _question("m2q5", "A message that appears to come from a classmate contains an unexpected attachment and asks you to enable macros. What is the safest response?", [
                        "Enable macros because the displayed sender name is familiar.",
                        "Forward the attachment to other learners before opening it.",
                        "Verify with the classmate through a separate trusted channel before opening or enabling anything.",
                        "Disable the computer's security controls so the file opens correctly.",
                    ], "c", "Familiar sender names can be impersonated, and accounts can be compromised. Unexpected attachments and requests to enable active content should be checked independently."),
                    _question("m2q6", "Someone claiming to be IT support contacts you unexpectedly and asks for your password and one-time sign-in code. Which response is appropriate?", [
                        "Do not share them; contact support using its established contact details.",
                        "Share the code but keep the password private.",
                        "Share both if the caller knows your name.",
                        "Send them through a different chat app to make the request safe.",
                    ], "a", "Passwords and sign-in codes can grant account access. Verify unexpected support requests using a known contact route rather than trusting the caller's identity claim."),
                    _question("m2q7", "A video page says you must install an unknown browser extension before watching a lesson. What should you check before installing it?", [
                        "Only whether its icon matches the course's colour.",
                        "Whether a comment says it is popular.",
                        "Whether disabling browser warnings makes installation faster.",
                        "Whether the lesson provider really requires it, its trusted source, and the permissions it requests.",
                    ], "d", "Browser extensions may receive significant access to browsing data. An unexpected installation request should be verified with the provider and assessed for source and permissions."),
                    _question("m2q8", "You entered your password into a page and then realised the address was suspicious. What is the best next step?", [
                        "Keep using the page until it confirms whether the password worked.",
                        "Use the real service to secure the account, change the exposed password, and report the suspicious page.",
                        "Assume no harm occurred because the page displayed an error.",
                        "Send the suspicious page your recovery codes to recover access.",
                    ], "b", "A fake page can capture information even when it displays an error. Respond through the real service, review account security and active sessions where available, and report the incident."),
                ],
            },
            {
                "id": "module-3",
                "title": "Privacy and responsible learning",
                "description": "Protect learner information, make careful sharing decisions, and respond responsibly when something goes wrong.",
                "estimated_minutes": 12,
                "questions": [
                    _question("m3q1", "A study group needs names and university email addresses to organise meetings. Which collection approach best follows data minimisation?", [
                        "Collect only the information needed for organising the meetings.",
                        "Also collect passport numbers in case they become useful later.",
                        "Request every member's account password to verify identity.",
                        "Download all available profile information before deciding what is needed.",
                    ], "a", "Data minimisation means limiting collection to the information necessary for the stated purpose. Collecting extra sensitive information creates avoidable privacy exposure."),
                    _question("m3q2", "You share a project document containing classmates' names. Which sharing setting is the most appropriate when only your team needs it?", [
                        "Allow anyone with the link to edit and repost it publicly.",
                        "Make it searchable by everyone on the internet.",
                        "Restrict access to the intended team members with only the permissions they need.",
                        "Remove the document title while leaving public access enabled.",
                    ], "c", "Restricting the audience and editing rights limits unnecessary exposure. A less descriptive title does not change who can open the document."),
                    _question("m3q3", "A learner can view courses, while an administrator can approve new content. Which principle supports this difference?", [
                        "Every account should have the same permissions.",
                        "Users should receive only the permissions needed for their role.",
                        "Anyone who knows a protected URL should be allowed to use it.",
                        "Older accounts should automatically become administrators.",
                    ], "b", "Least privilege limits permissions to what a person needs. Viewing learning material does not require the authority to approve or administer it."),
                    _question("m3q4", "Changing a course address unexpectedly reveals another learner's private progress. What should you do?", [
                        "Change the learner's progress to test how much access you have.",
                        "Download every other learner's record as proof.",
                        "Share the address in the class chat so everyone can try it.",
                        "Stop accessing the information and report the issue through an appropriate private channel.",
                    ], "d", "Limit further exposure and report the access-control issue responsibly. Access to an unintended record does not give permission to modify, collect, or publish it."),
                    _question("m3q5", "You want to include a dashboard screenshot in a public project presentation. What should you do if it contains real student names and email addresses?", [
                        "Use demonstration data or remove personal details that are not needed for the presentation.",
                        "Assume public sharing is acceptable because it is a school project.",
                        "Crop the page heading but leave every personal record visible.",
                        "Increase the image resolution so the details are easier to read.",
                    ], "a", "A presentation can demonstrate functionality without exposing real learner records. Demonstration data or appropriate removal of unnecessary personal information reduces that exposure."),
                    _question("m3q6", "Which backup practice best helps a student recover important project work after a device fails?", [
                        "Keep the only copy in the same folder under another filename.",
                        "Copy the project once and never check the copy again.",
                        "Keep regular backups separate from the working copy and check that they can be restored.",
                        "Publish private credentials with the project to make recovery easier.",
                    ], "c", "A separate, recoverable backup reduces the risk of losing every copy in one failure. Checking restoration helps establish that the backup is usable."),
                    _question("m3q7", "Which information is useful for investigating a denied course-access attempt without unnecessarily exposing secrets?", [
                        "The learner's plain-text password and recovery codes.",
                        "The account identifier, requested item, outcome, and time.",
                        "A full copy of all private messages in the learner's account.",
                        "Every session token used by the learner that month.",
                    ], "b", "An audit record needs enough context to understand an event. Passwords, recovery codes, and session tokens are secrets and should not be copied into routine logs."),
                    _question("m3q8", "Your group finishes a project that used a temporary shared folder of learner information. What should guide how long that information remains available?", [
                        "Keep it publicly available forever because storage is inexpensive.",
                        "Let any teammate copy it into unrelated projects.",
                        "Hide the folder name but leave the public sharing link active.",
                        "Review the agreed purpose and retention requirements, then remove unnecessary access and data appropriately.",
                    ], "d", "Information should not remain broadly accessible simply because a project has ended. Review retention needs and remove access or copies that are no longer justified."),
                ],
            },
        ],
    },
    2: {
        "title": "SQL Essentials",
        "modules": [
            {
                "id": "module-1",
                "title": "Tables, keys, and relationships",
                "description": "Model learner, course, and subscription data with clear keys and useful integrity constraints.",
                "estimated_minutes": 15,
                "questions": [
                    _question("m1q1", "In a relational database, what does a row in a learners table normally represent?", [
                        "Every learner's email address combined into one value.",
                        "The rules for every table in the database.",
                        "One learner record with values for the table's columns.",
                        "A command that automatically deletes inactive learners.",
                    ], "c", "A table groups records of a particular kind. Each row holds one record, and columns describe its attributes, such as learner ID and email address."),
                    _question("m1q2", "What is the main purpose of a primary key such as learners.id?", [
                        "Uniquely identify each learner row.",
                        "Automatically sort every query by the learner's name.",
                        "Allow several rows to use the same identifying value.",
                        "Prevent the application from reading the table.",
                    ], "a", "A primary key provides a unique identity for a row. Related records can use that identity without depending on names, which may change or be duplicated."),
                    _question("m1q3", "A subscriptions table has learner_id referencing learners.id. What does this foreign key relationship describe?", [
                        "The subscriptions table must contain every learner's full name.",
                        "The two tables must have exactly the same number of rows.",
                        "Every subscription creates a new database automatically.",
                        "Each referenced learner_id identifies a related learner record.",
                    ], "d", "The foreign key links a subscription to its learner. An enforced foreign key also helps prevent references to learner records that do not exist."),
                    _question("m1q4", "One learner may have several subscription records over time, and each subscription belongs to one learner. What relationship is this?", [
                        "One-to-one from learners to subscriptions.",
                        "One-to-many from learners to subscriptions.",
                        "A relationship that cannot be represented in SQL.",
                        "Many-to-many with no way to identify a subscription owner.",
                    ], "b", "The same learner ID can appear in multiple subscription records. Each subscription row still points to one learner, giving a one-to-many relationship."),
                    _question("m1q5", "A course can belong to several plans, and each plan can include several courses. Which design represents this relationship clearly?", [
                        "A plan_courses table containing a plan_id and course_id for each allowed pairing.",
                        "A single courses column containing all plan names as comma-separated text.",
                        "A separate database for every learner who buys a plan.",
                        "Remove course IDs and rely on the display order of course cards.",
                    ], "a", "A junction table models a many-to-many relationship as individual pairings. A key on the pair can also prevent duplicate plan-course entries."),
                    _question("m1q6", "What database constraint can prevent two learner accounts from using the same required email address?", [
                        "ORDER BY email on every SELECT query.",
                        "A larger maximum length for the email column.",
                        "A UNIQUE constraint together with NOT NULL on the email column.",
                        "A comment reminding users not to reuse addresses.",
                    ], "c", "UNIQUE prevents duplicate stored email values, while NOT NULL requires a value. Sorting or comments do not enforce these data rules."),
                    _question("m1q7", "A learner has not completed a course, so completed_at has no date yet. Which value appropriately represents that missing date?", [
                        "The text 'completed' regardless of the learner's progress.",
                        "NULL, when the column allows a missing value.",
                        "The learner's email address.",
                        "A randomly chosen date from a completed course.",
                    ], "b", "NULL represents the absence of a value. It is different from inventing a completion date or storing unrelated text in the field."),
                    _question("m1q8", "Why store a learner's email once in learners and refer to learner_id from progress records?", [
                        "It makes foreign keys unnecessary in every other table.",
                        "It ensures emails can never be changed.",
                        "It automatically authorises every learner to edit every record.",
                        "It reduces duplicated learner details and inconsistent updates.",
                    ], "d", "Separating learner details from course progress avoids repeating the same email in many rows. Updating the learner record can then keep related views consistent through the ID relationship."),
                ],
            },
            {
                "id": "module-2",
                "title": "Querying and combining records",
                "description": "Use filtering, sorting, joins, and aggregates to answer practical questions about a learning platform.",
                "estimated_minutes": 15,
                "questions": [
                    _question("m2q1", "Which query returns only the titles of approved courses?", [
                        "SELECT title FROM courses;",
                        "SELECT title FROM courses WHERE status = 'approved';",
                        "DELETE FROM courses WHERE status = 'approved';",
                        "SELECT status FROM courses ORDER BY title;",
                    ], "b", "SELECT title chooses the output column, and WHERE filters rows to the approved status. Without WHERE, titles from other statuses would also be returned."),
                    _question("m2q2", "Which condition selects courses in the Data category that take no more than 60 minutes?", [
                        "WHERE category = 'Data' OR duration_minutes <= 60",
                        "WHERE category = 'Data' AND duration_minutes > 60",
                        "WHERE duration_minutes = 'Data'",
                        "WHERE category = 'Data' AND duration_minutes <= 60",
                    ], "d", "AND requires both conditions to hold. OR would also include courses outside Data when their duration is short enough."),
                    _question("m2q3", "You want the most recently created courses first. Which clause provides that ordering?", [
                        "ORDER BY created_at DESC",
                        "ORDER BY created_at ASC",
                        "WHERE created_at IS NOT NULL",
                        "GROUP BY category",
                    ], "a", "Descending order places later date-time values before earlier ones. A WHERE condition filters rows but does not determine their order."),
                    _question("m2q4", "How can a query combine subscriptions with their matching learner names?", [
                        "Join subscriptions.id to learners.full_name.",
                        "Read only subscriptions and assume learner names are stored there.",
                        "INNER JOIN learners ON subscriptions.learner_id = learners.id.",
                        "Use ORDER BY on subscriptions without reading learners.",
                    ], "c", "The stored learner_id points to the learner's primary key. Joining on that relationship associates each subscription with the correct learner details."),
                    _question("m2q5", "A report must include every learner, including learners with no subscription. Which starting join is appropriate?", [
                        "learners INNER JOIN subscriptions ON learners.id = subscriptions.learner_id",
                        "learners LEFT JOIN subscriptions ON learners.id = subscriptions.learner_id",
                        "subscriptions INNER JOIN learners ON subscriptions.id = learners.id",
                        "Read subscriptions alone and assume it contains every learner.",
                    ], "b", "A LEFT JOIN preserves rows from the left-hand learners table even when no matching subscription exists. Subscription columns are NULL for those unmatched rows."),
                    _question("m2q6", "Which condition finds progress records that have no completion date?", [
                        "WHERE completed_at = NULL",
                        "WHERE completed_at = 'NULL'",
                        "WHERE completed_at IS NOT NULL",
                        "WHERE completed_at IS NULL",
                    ], "d", "IS NULL tests for a missing value. The text 'NULL' is a string, and ordinary equality with NULL does not perform a missing-value test."),
                    _question("m2q7", "A report needs the number of courses in each category. Which query expresses this?", [
                        "SELECT category, COUNT(*) FROM courses GROUP BY category;",
                        "SELECT category, COUNT(*) FROM courses ORDER BY title;",
                        "SELECT category FROM courses WHERE COUNT(*) > 0;",
                        "SELECT COUNT(category) FROM courses WHERE category = NULL;",
                    ], "a", "GROUP BY creates a group for each category, and COUNT(*) counts rows in each group. Ordering alone does not produce separate category counts."),
                    _question("m2q8", "A learner can have several subscription rows. Which expression counts different learners represented in that table?", [
                        "COUNT(*)",
                        "SUM(learner_id)",
                        "COUNT(DISTINCT learner_id)",
                        "MAX(learner_id)",
                    ], "c", "DISTINCT removes repeated learner IDs before counting them. COUNT(*) counts subscription rows, which can be more than the number of learners."),
                ],
            },
            {
                "id": "module-3",
                "title": "Safe updates and reliable data",
                "description": "Apply precise updates, bound parameters, transactions, and validation to protect the records behind a website.",
                "estimated_minutes": 15,
                "questions": [
                    _question("m3q1", "A learner types a course title into a search form. How should the application pass that value to its SQL query?", [
                        "Concatenate the raw input into the SQL command text.",
                        "Trust the value because it came from the application's own form.",
                        "Give the learner database administrator permissions.",
                        "Use a parameterized query and provide the value separately.",
                    ], "d", "Bound values are treated as data instead of being inserted into SQL command text. This prevents input from adding SQL instructions to that value position."),
                    _question("m3q2", "Which condition most precisely limits a progress update to one authenticated learner and one course?", [
                        "WHERE course_id = ?",
                        "WHERE learner_id = ? AND course_id = ?",
                        "WHERE progress_percent < 100",
                        "No WHERE clause is necessary if the new progress value is valid.",
                    ], "b", "Both identifiers are needed to target one learner-course record. The learner ID must come from the trusted authenticated identity rather than an unverified user-supplied owner ID."),
                    _question("m3q3", "What happens when UPDATE progress SET progress_percent = 100 is executed without a WHERE clause?", [
                        "It sets progress_percent to 100 for every row in the table.",
                        "It changes only the first learner shown on the website.",
                        "It changes only records owned by the database connection's website user.",
                        "It automatically asks which course should be updated.",
                    ], "a", "Without WHERE, the update applies to all rows. A database connection does not automatically infer the website learner's intended record."),
                    _question("m3q4", "Activating a subscription requires creating both a subscription row and a payment record. What does wrapping the two writes in one transaction help achieve?", [
                        "It makes every future payment succeed.",
                        "It removes the need to validate the selected plan.",
                        "Both writes can commit together, or both can be rolled back if the operation fails.",
                        "It publishes both records to every learner.",
                    ], "c", "A transaction allows related writes to succeed as one unit or be rolled back together. It does not replace payment validation or access-control checks."),
                    _question("m3q5", "A database transaction encounters an error after its first change but before the remaining changes finish. What does ROLLBACK do?", [
                        "Commits the successful first change and ignores the others.",
                        "Deletes every table in the database.",
                        "Repeats every command until no error is possible.",
                        "Discards the uncommitted changes made in that transaction.",
                    ], "d", "ROLLBACK undoes the uncommitted work in the transaction. It helps avoid leaving only part of a related operation applied."),
                    _question("m3q6", "Which constraint can reject an invalid progress value such as 140 at the database level?", [
                        "ORDER BY progress_percent",
                        "CHECK (progress_percent BETWEEN 0 AND 100)",
                        "A longer column name describing the allowed values.",
                        "SELECT progress_percent FROM progress",
                    ], "b", "A CHECK constraint enforces a condition when data is written. Application validation remains useful for clearer user feedback, while the constraint protects stored data."),
                    _question("m3q7", "A report groups courses by category and should include only categories with at least three courses. Which clause filters the grouped counts?", [
                        "HAVING COUNT(*) >= 3",
                        "WHERE COUNT(*) >= 3",
                        "ORDER BY COUNT(*) = 3",
                        "LIMIT category >= 3",
                    ], "a", "HAVING filters groups using aggregate results. WHERE filters individual rows before grouping and is not the place for this grouped COUNT condition."),
                    _question("m3q8", "Before deleting expired test subscriptions, which approach best reduces the risk of deleting unintended records?", [
                        "Delete every subscription and recreate the active ones from memory.",
                        "Use DELETE without a WHERE clause to avoid complicated conditions.",
                        "Check the target rows using the same filter, then perform the precise deletion with appropriate transaction and recovery safeguards.",
                        "Rename the subscriptions table before running any DELETE statement.",
                    ], "c", "Reviewing the selected rows helps validate the filter before deletion. A precise condition and suitable transaction or recovery approach reduce the impact of a mistake."),
                ],
            },
        ],
    },
    3: {
        "title": "Secure Web Application Design",
        "modules": [
            {
                "id": "module-1",
                "title": "Identity, permissions, and sessions",
                "description": "Distinguish identity from permissions and enforce account, record, and session boundaries on the server.",
                "estimated_minutes": 15,
                "questions": [
                    _question("m1q1", "Which statement correctly distinguishes authentication from authorisation?", [
                        "Authentication checks identity; authorisation checks permission to perform a particular action.",
                        "Authentication chooses a page layout; authorisation chooses its colours.",
                        "Once authentication succeeds, every protected action should be permitted.",
                        "Both checks can be replaced by keeping administrator URLs secret.",
                    ], "a", "Knowing who a user is does not establish what that user may do. A signed-in learner still needs permission for each protected action or record."),
                    _question("m1q2", "A learner changes a request's owner ID to update someone else's progress. What must the server do?", [
                        "Allow it if the requested progress value is between 0 and 100.",
                        "Trust the supplied owner ID because the request came from the website.",
                        "Check access to that record using the authenticated identity and reject the unauthorised update.",
                        "Allow it whenever the learner has an active subscription.",
                    ], "c", "Record ownership and permission must be checked on the server. A valid progress value or subscription does not authorise changes to another learner's data."),
                    _question("m1q3", "The interface hides the Approve content button from learners. What else is required?", [
                        "Make the administrator button a different colour.",
                        "Verify the authorised role on the server whenever an approval request arrives.",
                        "Place the approval URL in a less visible part of the page.",
                        "Trust all approval requests because learners cannot see the button.",
                    ], "b", "Users can send requests without using the displayed interface. Server-side role checks enforce the permission even when a client bypasses a hidden button."),
                    _question("m1q4", "How should a production website store passwords for later verification?", [
                        "As plain text so the administrator can recover them.",
                        "Encoded with Base64 so they appear unreadable at first glance.",
                        "In a publicly downloadable JavaScript file.",
                        "As salted password hashes using a suitable password-hashing algorithm.",
                    ], "d", "Password verification should compare an appropriate password hash rather than store retrievable plain-text passwords. A salt helps distinguish hashes of the same password across accounts."),
                    _question("m1q5", "What does HttpOnly on a session cookie help prevent?", [
                        "Page JavaScript directly reading the cookie through document.cookie.",
                        "The server receiving the cookie with a request.",
                        "Every possible cross-site request without any other protection.",
                        "The session reaching its expiry time.",
                    ], "a", "HttpOnly restricts access from page JavaScript. It does not replace HTTPS, authorisation, or controls against unwanted cross-site requests."),
                    _question("m1q6", "What does the Secure attribute on a session cookie tell a browser to do?", [
                        "Give the session access to administrator features.",
                        "Keep the session valid forever.",
                        "Send the cookie only over secure connections such as HTTPS.",
                        "Hide all application source code from the user.",
                    ], "c", "The Secure attribute restricts transmission of the cookie to secure connections. It addresses transport exposure, not the user's permissions or session lifetime."),
                    _question("m1q7", "What should a secure sign-out process do with an active server-side session?", [
                        "Hide the dashboard but leave the session valid.",
                        "Invalidate the server-side session and clear the browser's session cookie.",
                        "Copy the token into a public log to record the sign-out.",
                        "Change the account role and leave the session running.",
                    ], "b", "Invalidating the server-side session prevents the token from continuing to authorise requests. Clearing the cookie removes the browser's copy used on later requests."),
                    _question("m1q8", "A protected endpoint cannot determine whether the user has the required permission. Which default is safest?", [
                        "Allow the action whenever the request contains a familiar course name.",
                        "Assume all signed-in users are administrators.",
                        "Retry the action with a different learner's permissions.",
                        "Deny the protected action until the required permission can be established.",
                    ], "d", "Failing closed avoids granting access because an authorisation check is missing or unsuccessful. Uncertainty about permission should not become permission."),
                ],
            },
            {
                "id": "module-2",
                "title": "Safe input and content publication",
                "description": "Validate requests, render user content safely, and keep unapproved or unsafe submissions out of learner views.",
                "estimated_minutes": 15,
                "questions": [
                    _question("m2q1", "A form limits duration to 5–600 minutes in browser JavaScript. Where must this rule also be checked?", [
                        "Only in the form's placeholder text.",
                        "Only after the resource has been published.",
                        "On the server before accepting each submitted value.",
                        "Nowhere else, because requests cannot bypass a browser form.",
                    ], "c", "Browser checks improve feedback but can be bypassed. The server must validate input before using it or storing it."),
                    _question("m2q2", "A learner comment contains '<script>alert(1)</script>'. How should a page display it when comments are intended to be plain text?", [
                        "Insert it as HTML so the browser can decide whether it is useful.",
                        "Render it as text using a safe text API or appropriate output encoding.",
                        "Run it only when the commenter has an active subscription.",
                        "Move it into a different HTML element without changing how it is interpreted.",
                    ], "b", "Rendering comments as text prevents their contents from becoming executable page markup. Moving untrusted HTML between elements does not remove that risk."),
                    _question("m2q3", "A course search endpoint uses a learner's input in an SQL query. Which design keeps input separate from SQL command text?", [
                        "Concatenate the input directly into a SELECT statement.",
                        "Remove spaces from the input and then concatenate it.",
                        "Allow raw SQL because only learners can use the search page.",
                        "Use bound parameters for the search value.",
                    ], "d", "Bound parameters treat a supplied search value as data. Formatting changes such as removing spaces are not a substitute for parameterization."),
                    _question("m2q4", "An educator uploads a file named lesson.pdf. Which approach best supports safe handling of the upload?", [
                        "Validate permitted file types, size, and actual content characteristics, and store it where it cannot execute as application code.",
                        "Trust any file whose name ends in .pdf.",
                        "Place every upload in an executable application directory.",
                        "Publish the file before checking it so learners can report problems.",
                    ], "a", "A filename alone does not establish a file's contents or safety. Validate the upload and use storage and delivery controls appropriate for untrusted files."),
                    _question("m2q5", "An educator changes a submitted JSON field from status='pending' to status='approved'. How should the publication endpoint respond?", [
                        "Accept the status because the educator created the content.",
                        "Allow the change if the title contains no special characters.",
                        "Enforce the approval workflow and role on the server, regardless of the submitted status.",
                        "Hide the status input in the next form but publish the current request.",
                    ], "c", "Client-supplied publication state is not proof of approval. The server must assign and enforce status according to the caller's role and the review workflow."),
                    _question("m2q6", "What should an API generally return to a learner when an unexpected database error occurs?", [
                        "The complete database password and connection string.",
                        "A useful, limited error message, while recording appropriate diagnostic details in protected server logs.",
                        "All table contents so the learner can troubleshoot the issue.",
                        "A successful response even though the requested operation failed.",
                    ], "b", "User-facing errors should explain failure without exposing internal secrets or records. Protected diagnostics can help developers investigate without publishing those details."),
                    _question("m2q7", "A server accepts a plan_code field. Only starter, plus, and team are valid. Which validation best matches this rule?", [
                        "Accept any value that contains at least one letter.",
                        "Accept any value that is not longer than the longest plan name.",
                        "Trust the value because the interface uses a dropdown.",
                        "Check that the submitted value is one of the supported plan codes.",
                    ], "d", "An allowlist directly represents the valid values. A client dropdown can be bypassed, and length checks alone do not establish that a plan exists."),
                    _question("m2q8", "A cookie-authenticated application receives a request to change a learner's subscription. Which approach helps defend against unwanted cross-site requests?", [
                        "Use appropriate anti-CSRF protections for state-changing requests, alongside authentication and authorisation.",
                        "Assume HttpOnly cookies alone stop every cross-site request.",
                        "Allow the change through a publicly embedded image URL.",
                        "Trust every request that includes the name of a valid plan.",
                    ], "a", "Browsers may attach cookies to requests, so a valid cookie does not by itself prove that the user intended a state change. Appropriate anti-CSRF measures complement access checks."),
                ],
            },
            {
                "id": "module-3",
                "title": "Reliable access and security checks",
                "description": "Test failure paths, protect sensitive configuration, and use careful logging and request handling to maintain secure behaviour.",
                "estimated_minutes": 15,
                "questions": [
                    _question("m3q1", "Which test most directly checks that learners cannot use an administrator approval endpoint?", [
                        "Verify that the learner sidebar uses a different colour.",
                        "Send an approval request while authenticated as a learner and confirm it is denied without changing content status.",
                        "Check only that an administrator can approve content.",
                        "Confirm that the learner's browser has JavaScript enabled.",
                    ], "b", "A negative permission test must exercise the protected endpoint and verify both the denial and the absence of an unintended change. A hidden button is not sufficient evidence."),
                    _question("m3q2", "A learner's subscription expires while an old course page is still open. What should happen on the next protected API request?", [
                        "The request should succeed forever because the page was opened earlier.",
                        "The browser should decide whether payment is required without asking the server.",
                        "The server should reactivate the subscription automatically.",
                        "The server should recheck current entitlement and deny access when it is no longer valid.",
                    ], "d", "Entitlements can change after a page loads. Checking the current permission at the protected endpoint prevents stale client state from extending access."),
                    _question("m3q3", "Where should a production application keep a private database credential?", [
                        "In protected server-side configuration that is not sent to the browser or committed as a public secret.",
                        "Inside a JavaScript bundle downloaded by every learner.",
                        "In an HTML comment on the login page.",
                        "In a publicly accessible screenshot of the settings page.",
                    ], "a", "Server credentials should remain in protected server-side configuration or a suitable secret store. Anything delivered to the browser must be treated as visible to its user."),
                    _question("m3q4", "Which audit entry best records a denied content request without including authentication secrets?", [
                        "The user's plain-text password and the requested title.",
                        "The session token and every cookie in the request.",
                        "The account identifier, requested content ID, denial outcome, and timestamp.",
                        "The private content itself and a complete copy of the user's profile.",
                    ], "c", "Useful audit context identifies the actor, target, outcome, and time. Recording passwords, session tokens, or unnecessary private content increases exposure without being required for this event."),
                    _question("m3q5", "An API returns a learner's private progress. What caching concern should the developer address?", [
                        "Private responses should be placed in a public cache for every user.",
                        "Shared caches must not serve one learner's private response to another; suitable cache controls such as no-store can prevent storage.",
                        "Changing the response's font makes shared caching safe.",
                        "Responses containing JSON cannot be cached by intermediaries.",
                    ], "b", "Personalised responses need cache handling that respects privacy. JSON is not inherently uncacheable, and an unsafe shared cache can expose another user's data."),
                    _question("m3q6", "A learner double-clicks Submit, sending the same quiz attempt twice. Which server behaviour avoids duplicate final results?", [
                        "Award twice as many marks because two requests arrived.",
                        "Trust a disabled browser button to prevent every duplicate request.",
                        "Create a new unrelated attempt for each request without checking the attempt ID.",
                        "Recognise the attempt and return its saved result if it has already been submitted.",
                    ], "d", "Idempotent handling makes repeated submission of the same attempt return the same final outcome. Server-side checks are needed because duplicate requests can occur even with careful interface controls."),
                    _question("m3q7", "A login endpoint receives many rapid failed password attempts. Which control can help slow automated guessing?", [
                        "Apply appropriate rate limits and monitoring to failed login activity.",
                        "Remove password verification during busy periods.",
                        "Display the correct password after several failed attempts.",
                        "Grant a longer-lived session to every failed attempt.",
                    ], "a", "Rate limiting can restrict how quickly repeated attempts are processed, and monitoring helps identify suspicious activity. These controls support, rather than replace, secure authentication."),
                    _question("m3q8", "What should a protected endpoint do when a session has expired?", [
                        "Trust the account name still displayed on the page.",
                        "Allow the request if the user can guess the original session token.",
                        "Reject the expired session and require the user to authenticate again before protected access.",
                        "Keep extending the session indefinitely without any validity check.",
                    ], "c", "The server must enforce session validity. An old interface or token does not make an expired session authorised to continue accessing protected resources."),
                ],
            },
        ],
    },
}


# Additional scenarios form the other half of each module's question bank.
# They are included in the same module before the assessment service imports it.
_ADDITIONAL_QUESTIONS = {
    1: {
        "module-1": [
            _question("m1q9", "You step away from your laptop in a classroom while a learner account is signed in. Which action protects the session from someone nearby?", [
                "Leave a note asking others not to touch the keyboard.",
                "Lock the device before leaving it unattended.",
                "Turn the screen brightness down while leaving it unlocked.",
                "Open a different browser tab over the dashboard.",
            ], "b", "A locked device requires the user to unlock it before continuing. Covering or minimising a signed-in page does not prevent another person from using the session."),
            _question("m1q10", "Why does the recovery email account for a learning platform need strong protection?", [
                "It determines the colours used in the course catalogue.",
                "It makes all websites automatically approve the learner's identity.",
                "Someone who controls it may be able to reset the learning account's password.",
                "It allows the learner to skip all subscription checks.",
            ], "c", "Recovery routes can be used to regain account access. Protecting the main password while leaving its recovery account weak leaves another route into the account."),
            _question("m1q11", "Your phone is lost while several study accounts are signed in. What is an appropriate account-security response from another trusted device?", [
                "Use available account controls to revoke the lost device's sessions and follow the provider's recovery steps.",
                "Post your passwords publicly so classmates can help locate the phone.",
                "Assume that changing the phone's wallpaper remotely will end every session.",
                "Wait for the finder to send instructions before protecting any account.",
            ], "a", "Revoking sessions can prevent continued account access from the lost device. Use trusted account and device recovery controls rather than relying on whoever finds the device."),
            _question("m1q12", "A simple calculator app asks to read all contacts and record audio. What is the most careful response?", [
                "Grant both permissions because installing an app means trusting every request.",
                "Grant permissions only when the app has an attractive icon.",
                "Disable the device's permission controls permanently.",
                "Question whether those permissions are needed and decline unnecessary access.",
            ], "d", "Permissions should match the task an app needs to perform. Access to contacts or audio is not automatically justified by an unrelated feature."),
            _question("m1q13", "What is a main benefit of encrypting a laptop's storage when the device is lost while powered off?", [
                "It guarantees that every website visited on the laptop was safe.",
                "It helps protect stored files from being read without the required unlock credentials.",
                "It prevents the owner from accidentally sharing a file after signing in.",
                "It eliminates the need for backups.",
            ], "b", "Storage encryption protects data at rest. It does not prevent every disclosure after a device is unlocked, and it does not replace backups."),
            _question("m1q14", "You receive a password-reset message for a request you did not make. Which response is appropriate?", [
                "Send the reset link to the person who says they requested it.",
                "Enter your current password into any page linked in the message.",
                "Do not share the reset link; check the account through the known service and review suspicious activity.",
                "Assume your password must already have changed simply because the email arrived.",
            ], "c", "A reset message alone does not prove a reset was completed. Its link may grant account control, so keep it private and check concerns through the real service."),
            _question("m1q15", "A sign-in process asks for a password and then a PIN that the user memorised. Why is that not necessarily multi-factor authentication?", [
                "Both checks can be the same type of factor: something the user knows.",
                "A PIN is always public information.",
                "Every process with two screens automatically uses two independent factors.",
                "Passwords cannot be combined with any other form of verification.",
            ], "a", "Multiple steps do not automatically mean multiple independent factors. Two memorised secrets are both knowledge factors."),
            _question("m1q16", "A classmate needs to borrow your laptop briefly. Which arrangement better separates their activity from your signed-in study accounts?", [
                "Give the classmate the password for your primary user account.",
                "Leave your browser profile signed in and ask them to avoid it.",
                "Save your recovery codes on the desktop for convenience.",
                "Use a separate guest or user account without access to your active sessions.",
            ], "d", "A separate account or appropriately restricted guest session helps separate another person's activity from your own files and signed-in services."),
        ],
        "module-2": [
            _question("m2q9", "A stranger uses your public course timetable and team members' names to make a request sound convincing. What does this demonstrate?", [
                "Knowing public details proves the stranger is authorised support staff.",
                "Personal details can be used to make social-engineering messages appear credible.",
                "A detailed message can never be fraudulent.",
                "Public information cannot be used in account attacks.",
            ], "b", "Attackers can combine available details to build a believable story. Familiar information is not proof that a request or sender is authorised."),
            _question("m2q10", "A downloaded file is named lecture-notes.pdf.exe. Why should you avoid treating it as an ordinary PDF just because 'pdf' appears in the name?", [
                "Every filename containing two dots is a harmless text file.",
                "Adding pdf anywhere in a filename prevents code execution.",
                "The name can disguise an executable; verify the actual file type and source before opening it.",
                "Renaming it to notes.pdf automatically removes any harmful behaviour.",
            ], "c", "A familiar-looking portion of a filename can be misleading. Renaming a file does not change its underlying content or make an untrusted executable safe."),
            _question("m2q11", "An unsolicited message contains a shortened URL whose destination is unclear. Which approach is safest when it requests account sign-in?", [
                "Use the known service address or another trusted route to verify the request before signing in.",
                "Trust the URL because short links always belong to the sender.",
                "Enter only half the password to test whether the page is genuine.",
                "Forward the link to the whole class to see who can sign in.",
            ], "a", "Shortening can hide the destination from the message text. An account request should be verified without relying on that concealed destination."),
            _question("m2q12", "An email's display name says 'University Help Desk'. What does that name establish on its own?", [
                "The university has verified every link in the message.",
                "The sender is entitled to receive your password.",
                "The message must come from the university's genuine email system.",
                "Very little about authenticity, because display names can be chosen or imitated.",
            ], "d", "A display name is not reliable proof of who sent a message. Check unexpected requests using the institution's trusted contact routes."),
            _question("m2q13", "Files on a university-managed laptop suddenly become unreadable and a message demands payment to unlock them. What is an appropriate immediate response?", [
                "Connect every backup drive immediately and open the same files there.",
                "Disconnect the affected device from networks and promptly contact the university's IT response channel.",
                "Forward the suspected program to classmates so they can reproduce the issue.",
                "Continue using the device normally until the next class.",
            ], "b", "Limiting network connectivity can help contain spread while responsible IT staff investigate. Avoid connecting additional storage or distributing suspicious files."),
            _question("m2q14", "You find an unlabelled USB drive outside a classroom. What should you do?", [
                "Plug it into a shared computer so any risk affects everyone equally.",
                "Disable antivirus before checking what is on it.",
                "Hand it to the appropriate lost-property or IT service instead of connecting it to your device.",
                "Open every file to identify the owner before reporting it.",
            ], "c", "Unknown removable media can expose a device to unsafe files or other attacks. Use an appropriate handling process rather than connecting it to a personal or shared machine."),
            _question("m2q15", "A search engine's first result is an advertisement that resembles your course platform. What should you verify before entering credentials?", [
                "That the destination is the platform's genuine address; placement in search results does not prove authenticity.",
                "Only that the result appears above all other results.",
                "Only that the advertisement uses the same colour as the platform.",
                "Nothing, because all paid advertisements are official support pages.",
            ], "a", "Search ranking or paid placement is not proof of ownership. Verify the host or use an established bookmark when signing in."),
            _question("m2q16", "A downloaded installer asks you to disable security software to finish installing a study tool. What is the most careful response?", [
                "Disable all protection permanently to avoid future interruptions.",
                "Install it on a classmate's device first without telling them.",
                "Assume the request is safe because the installer contains the word education.",
                "Stop and verify the tool and installation instructions through the publisher's trusted source or IT support.",
            ], "d", "An unexpected request to remove security protection deserves verification. A claimed purpose or familiar name does not establish that an installer is trustworthy."),
        ],
        "module-3": [
            _question("m3q9", "You lose a USB drive that contains a project file with real learner information. Which response is most responsible?", [
                "Wait several weeks in case the drive turns up.",
                "Hide the loss so the project group does not worry.",
                "Promptly report the loss through the appropriate project or institutional channel and explain what information may be affected.",
                "Post the complete learner file publicly so everyone knows what was lost.",
            ], "c", "Prompt reporting allows the responsible people to assess exposure and take appropriate steps. Reporting the incident does not require publishing the affected information."),
            _question("m3q10", "A teammate leaves the project, but a private shared folder still gives them editing access. What should the remaining team review?", [
                "Whether that access is still needed and remove it when it is no longer justified.",
                "Only the colour of the folder icon.",
                "How to give the former teammate access to unrelated folders too.",
                "Whether renaming the folder will automatically revoke permissions.",
            ], "a", "Access needs can change when roles change. Review the actual sharing permissions rather than assuming a renamed folder or an ended role removes access automatically."),
            _question("m3q11", "A photo intended for a public project page contains precise location metadata. What should you consider before uploading it?", [
                "Metadata cannot reveal anything if the photo looks harmless.",
                "Publish all metadata because it is not visible in the picture itself.",
                "Convert the filename to uppercase to remove location details.",
                "Remove location details that are unnecessary and could expose someone's private location.",
            ], "d", "Files can contain information beyond what appears on screen. Review unnecessary metadata before public sharing, particularly when it reveals a person's location."),
            _question("m3q12", "Why can publicly sharing a person's birth date, childhood school, and family details create an account-security risk?", [
                "Such details always function as an encrypted password.",
                "They may help someone guess weak recovery answers or build convincing impersonation messages.",
                "They automatically grant the poster administrator rights.",
                "Personal details cannot affect account security once a password exists.",
            ], "b", "Personal information may support impersonation or weak account-recovery checks. Consider the purpose and audience before making those details public."),
            _question("m3q13", "A classmate asks to use your learner account to access subscribed course material. What is the safer way to help?", [
                "Give them the password but keep your email address private.",
                "Send them your active session cookie instead of the password.",
                "Point them to the proper account and access process instead of sharing your credentials.",
                "Let them change your account's recovery email temporarily.",
            ], "c", "Sharing passwords or session tokens exposes account activity and personal information. Help through the platform's intended account and access arrangements."),
            _question("m3q14", "A profile form includes an optional phone-number field that is unrelated to the learner's task. What supports a more privacy-conscious decision?", [
                "Read the stated purpose and leave the optional information out if it is not needed or wanted.",
                "Provide every optional field because empty fields always break security.",
                "Enter another learner's number without permission.",
                "Publish the number in a course comment instead of the form.",
            ], "a", "Optional information should be considered in light of its purpose and the user's preference. An unnecessary field does not need to be filled with another person's information."),
            _question("m3q15", "Your team plans to make its project repository public. Which review best protects private project material?", [
                "Check only whether the logo has the right dimensions.",
                "Assume every file in the project folder is appropriate for public release.",
                "Upload real learner exports to make the demonstration more realistic.",
                "Review files and history for personal records, credentials, and private notes before publishing.",
            ], "d", "A repository can expose source history and supporting files as well as current code. Use suitable demonstration data and keep private records and secrets out of public releases."),
            _question("m3q16", "You need to report a bug that briefly displayed another learner's email address. What evidence-sharing approach best limits further exposure?", [
                "Post an unredacted recording on public social media.",
                "Send only necessary details through the designated private reporting channel, redacting unrelated personal information.",
                "Collect more learners' details to make the report larger.",
                "Share the affected account's password so staff can investigate faster.",
            ], "b", "A useful report describes the issue with enough evidence to investigate. Limit its audience and avoid collecting or distributing unnecessary personal information."),
        ],
    },
    2: {
        "module-1": [
            _question("m1q9", "The progress table should store at most one row for each learner-course pair. Which key directly enforces that rule?", [
                "A key on progress_percent alone.",
                "A key on course_id alone, allowing only one learner per course.",
                "A composite unique key or primary key on (learner_id, course_id).",
                "Sorting all rows by learner_id before displaying them.",
            ], "c", "The combination identifies one learner's progress in one course. Either ID alone would incorrectly restrict legitimate records for other learners or courses."),
            _question("m1q10", "A title column has NOT NULL but no other validation. Which statement is correct?", [
                "NULL is rejected, but separate validation may still be needed to reject empty or whitespace-only text.",
                "NOT NULL guarantees the title contains at least four useful words.",
                "NOT NULL automatically makes every title unique.",
                "NOT NULL allows a missing value whenever the row has a primary key.",
            ], "a", "NOT NULL checks for the absence of a value. It does not by itself validate meaningful text length, whitespace, or uniqueness."),
            _question("m1q11", "Why should a duration_minutes field use an appropriate numeric type instead of strings such as 'ten minutes'?", [
                "Numeric types prevent all access-control mistakes.",
                "Strings cannot be stored in any relational database.",
                "Numeric types automatically approve every course.",
                "Numeric values support reliable comparisons, calculations, and range constraints.",
            ], "d", "Structured numeric values can be sorted, compared, and validated as numbers. Display text such as 'minutes' can be added by the interface."),
            _question("m1q12", "A learner row has related progress rows. What should the database design specify before allowing the learner row to be deleted?", [
                "Only the learner's preferred display colour.",
                "How related rows are handled, such as rejecting the deletion or applying a deliberately chosen cascade policy.",
                "That every foreign key is disabled permanently.",
                "That related rows silently point to an unrelated learner.",
            ], "b", "Referential actions should be chosen intentionally. The application must not assume that deleting a referenced row will preserve meaningful relationships automatically."),
            _question("m1q13", "Publication status may be pending, approved, or rejected. Which schema rule can reject the value 'anything-goes'?", [
                "ORDER BY status whenever a report is opened.",
                "A primary key on the title column.",
                "CHECK (status IN ('pending', 'approved', 'rejected')).",
                "Making the status column wider.",
            ], "c", "A CHECK condition restricts stored values to the supported states. A larger text column or sorted output does not enforce that rule."),
            _question("m1q14", "A category label appears in hundreds of course records and often becomes inconsistent after renaming. Which design can reduce this duplication?", [
                "Store categories in a category table and reference the category ID from courses.",
                "Give every spelling a different meaning without reviewing it.",
                "Copy the category label into even more tables.",
                "Remove course IDs so categories become harder to change.",
            ], "a", "A separate category record creates one place to maintain a shared label. Courses can retain stable references to it through a category ID."),
            _question("m1q15", "Every learning item must belong to an existing educator. Which combination best represents this requirement in the item table?", [
                "A nullable text field containing an educator's display name.",
                "An unrelated numeric column with no constraint.",
                "A rule that sorts educators before learners.",
                "A NOT NULL educator_id with a foreign key to the appropriate educator record.",
            ], "d", "NOT NULL requires an owner reference, and a foreign key requires the referenced record to exist. The application or schema must also ensure that the referenced account has the educator role."),
            _question("m1q16", "Which change modifies the database schema rather than simply changing a course record's data?", [
                "Changing a course title from Draft to Final.",
                "Adding a language column to the courses table.",
                "Setting one learner's progress to 50.",
                "Updating the description of an existing plan.",
            ], "b", "The schema describes table structure and constraints. Adding a column changes that structure, while updating values changes stored records within it."),
        ],
        "module-2": [
            _question("m2q9", "Which condition matches course titles containing the text SQL using a basic SQL LIKE pattern?", [
                "WHERE title LIKE '%SQL%'",
                "WHERE title = '%SQL%'",
                "WHERE title IS NULL",
                "WHERE title IN ('%SQL%')",
            ], "a", "The percent wildcard in LIKE matches sequences of characters before or after SQL. Equality and IN compare literal values rather than applying that wildcard pattern."),
            _question("m2q10", "Which condition selects only subscriptions whose status is active or cancelled?", [
                "WHERE status = 'active' AND status = 'cancelled'",
                "WHERE status = 'active,cancelled'",
                "WHERE status IN ('active', 'cancelled')",
                "WHERE status IS NULL",
            ], "c", "IN checks whether the value matches one of the listed alternatives. A single status value cannot simultaneously equal two different strings with AND."),
            _question("m2q11", "In SQL, what does WHERE duration_minutes BETWEEN 30 AND 60 include?", [
                "Only durations strictly greater than 30 and strictly less than 60.",
                "Durations from 30 through 60, including both endpoints.",
                "Only the values 30 and 60, excluding those in between.",
                "Durations less than 30 or greater than 60.",
            ], "b", "BETWEEN includes its lower and upper bounds. The condition is equivalent to duration_minutes >= 30 AND duration_minutes <= 60."),
            _question("m2q12", "A four-row progress table has two NULL completed_at values and two dates. What do COUNT(*) and COUNT(completed_at) return?", [
                "Both return 2.",
                "Both return 4.",
                "COUNT(*) returns 2 and COUNT(completed_at) returns 4.",
                "COUNT(*) returns 4 and COUNT(completed_at) returns 2.",
            ], "d", "COUNT(*) counts rows. COUNT(column) counts only rows where that column is not NULL."),
            _question("m2q13", "Which query totals the amount from only paid payment records?", [
                "SELECT SUM(amount) FROM payments WHERE status = 'paid';",
                "SELECT COUNT(amount) FROM payments WHERE status = 'paid';",
                "SELECT amount FROM payments ORDER BY status;",
                "SELECT SUM(status) FROM payments WHERE amount = 'paid';",
            ], "a", "SUM adds the selected numeric amounts, while WHERE limits which payment rows participate. COUNT would report how many non-NULL values exist, not their total."),
            _question("m2q14", "Several courses share the same created_at value. Which ordering provides a consistent secondary order when IDs are unique?", [
                "ORDER BY created_at DESC, created_at DESC",
                "No ORDER BY clause, because storage order is guaranteed.",
                "ORDER BY created_at DESC, id DESC",
                "GROUP BY title without an ORDER BY clause",
            ], "c", "The unique ID breaks ties in the created_at values. An explicit tie-breaker supports consistent results when several rows share the main sort value."),
            _question("m2q15", "One learner has three subscription rows. An INNER JOIN links learners to subscriptions on the learner ID. How many joined rows represent that learner?", [
                "One, because joins always deduplicate learners automatically.",
                "Three, one for each matching subscription row.",
                "Zero, because multiple matching rows make the join invalid.",
                "An unpredictable number unrelated to the matching records.",
            ], "b", "A join returns combinations of matching rows. Multiple subscriptions therefore repeat the learner details unless the query deliberately aggregates or deduplicates them."),
            _question("m2q16", "You need active courses belonging to learner 7 in either the Data or Development category. Which filter correctly groups the category alternatives?", [
                "WHERE learner_id = 7 AND status = 'active' AND category = 'Data' OR category = 'Development'",
                "WHERE learner_id = 7 OR status = 'active' OR category = 'Data'",
                "WHERE category = 'Data' AND category = 'Development'",
                "WHERE learner_id = 7 AND status = 'active' AND (category = 'Data' OR category = 'Development')",
            ], "d", "Parentheses group the alternatives so both categories remain subject to the learner and active-status conditions. Without them, the OR branch could include unrelated Development rows."),
        ],
        "module-3": [
            _question("m3q9", "Why explicitly name columns in an INSERT statement, such as INSERT INTO courses (title, status) VALUES (?, ?)?", [
                "It grants the inserting user administrator access.",
                "It removes the need for any data validation.",
                "It prevents the database from assigning primary keys.",
                "It makes the mapping from supplied values to columns clear and less dependent on table column order.",
            ], "d", "An explicit column list documents the intended fields. Other required columns must still have valid values or defaults, and normal validation still applies."),
            _question("m3q10", "A progress API receives learner_id in a browser request. Which source should determine the learner who owns a normal self-service progress update?", [
                "Any learner_id typed into the request body.",
                "The server's authenticated account identity, combined with permission checks.",
                "The learner name last displayed on another browser tab.",
                "Whichever learner currently has the highest progress.",
            ], "b", "A user-supplied owner ID is not proof of ownership. Bind the update to the authenticated identity and enforce the allowed action on the server."),
            _question("m3q11", "An UPDATE intended for a particular existing record matches no row. What should the application consider before reporting success?", [
                "Whether the target actually exists and whether the operation achieved its intended result.",
                "How to claim that every row was changed without checking.",
                "Whether disabling constraints will make the message look better.",
                "How to insert a different learner's data as a replacement.",
            ], "a", "A successful SQL execution does not necessarily mean a target row existed or changed. Check the relevant result and handle missing targets appropriately."),
            _question("m3q12", "In SQLite, progress has a unique key on (learner_id, course_id). What is the purpose of INSERT ... ON CONFLICT(learner_id, course_id) DO UPDATE?", [
                "Delete all learners whenever two course IDs match.",
                "Ignore every database constraint permanently.",
                "Insert a new progress record or update the existing record for that learner-course pair.",
                "Allow unlimited duplicate progress rows for the same pair.",
            ], "c", "The conflict target identifies an existing learner-course record. An upsert can update that record instead of creating a duplicate, subject to the specified update and validation rules."),
            _question("m3q13", "What is a reasonable trade-off when adding an index used to find progress rows by learner_id?", [
                "Every query is guaranteed to become faster with no cost.",
                "Indexes replace the need for correct WHERE clauses.",
                "The index automatically prevents learners from reading other accounts.",
                "Suitable lookups may become faster, while the index uses storage and adds maintenance work to writes.",
            ], "d", "Indexes can help queries that use their indexed values, but they have storage and write costs. They are performance tools, not authorisation controls."),
            _question("m3q14", "A user can choose a sort column for a report. Why should the server map the choice to an allowlisted column name rather than insert arbitrary text into ORDER BY?", [
                "All column names are secret and must never appear in source code.",
                "SQL identifiers form part of command structure, so untrusted sort expressions must not be accepted as arbitrary SQL.",
                "Putting every column name in a value parameter always selects that column automatically.",
                "ORDER BY is harmless and can contain any user-supplied SQL.",
            ], "b", "Bound parameters are for values, not arbitrary SQL structure. Use a trusted mapping for supported identifiers or sort expressions and continue binding data values separately."),
            _question("m3q15", "A reporting service only reads aggregate learning statistics. Which database access level best fits that responsibility?", [
                "Read access only to the data needed for its reports.",
                "Permission to drop every table and create new administrator accounts.",
                "The same unrestricted database credentials used for all maintenance work.",
                "Permission to change learner passwords because it reads learner counts.",
            ], "a", "Least privilege limits the damage a mistaken or compromised reporting operation can cause. Reading a report does not justify schema changes or unrelated account administration."),
            _question("m3q16", "Two requests need to increment the same attempt counter. Which update avoids both requests writing the same previously read value?", [
                "Have both browsers read the old value and submit old_value + 1.",
                "Replace the counter with whichever learner ID was received last.",
                "Use an atomic database update such as SET attempt_count = attempt_count + 1 for the intended row.",
                "Remove the counter's WHERE clause so every row is incremented.",
            ], "c", "An atomic increment updates the current stored value in the database. Separately reading an old value and later writing a calculated replacement can lose concurrent increments."),
        ],
    },
    3: {
        "module-1": [
            _question("m1q9", "Which property is important for a session token that grants access to an authenticated account?", [
                "It should be difficult for another user to predict or guess.",
                "It should equal the learner's public student ID.",
                "It should be the same constant for every account.",
                "It should list the account's plain-text password.",
            ], "a", "An unpredictable session token helps prevent guessing another user's session. The server must also verify its validity, expiry, and permissions."),
            _question("m1q10", "Why might an application replace the session identifier after a successful login?", [
                "To publish the user's password under a different name.",
                "To remove all authorisation checks from later requests.",
                "To avoid carrying an attacker-known pre-login session identifier into the authenticated session.",
                "To guarantee that a session never expires.",
            ], "c", "Changing the identifier at authentication helps defend against session fixation. The authenticated session should not rely on a previously exposed or attacker-chosen identifier."),
            _question("m1q11", "Which property is appropriate for a password-reset token?", [
                "It should be a permanent public account identifier.",
                "It should be unpredictable, expire, and be invalidated after successful use.",
                "It should contain the user's current password in readable text.",
                "It should work for every account if it works for one.",
            ], "b", "A reset token can grant account control. Limiting predictability, lifetime, and reuse reduces the exposure if the token is intercepted or obtained later."),
            _question("m1q12", "An administrator is demoted to learner while a browser session remains active. What should protected administrator endpoints do?", [
                "Continue allowing all administrator actions until the browser closes.",
                "Trust a role label cached in the page indefinitely.",
                "Allow approval requests if the old administrator remembers the URL.",
                "Apply the current permissions or revoke affected sessions so the old privileges no longer work.",
            ], "d", "Role changes must affect actual server-side access. Stale interface state or remembered URLs must not preserve removed privileges."),
            _question("m1q13", "Why might a login form use the same general failure message for an unknown email and an incorrect password?", [
                "To avoid unnecessarily revealing which email addresses have accounts.",
                "To make incorrect passwords valid.",
                "To let the browser choose the account role.",
                "To replace the need for password verification.",
            ], "a", "Consistent failure messages can reduce account-enumeration clues. Authentication still needs to verify credentials correctly and handle failures safely."),
            _question("m1q14", "Why should session tokens generally not be placed in ordinary page URLs?", [
                "URLs cannot be sent over HTTPS.",
                "A token in a URL automatically expires after one second.",
                "URLs can be recorded in history, logs, shared links, and other places that expose the token.",
                "A URL token prevents the server from receiving any request.",
            ], "c", "URLs commonly travel through systems not intended to store authentication secrets. Keep session handling in a suitable protected mechanism and avoid unnecessary token exposure."),
            _question("m1q15", "A learner selects 'Remember me'. Which design still respects session security?", [
                "A permanent token that can never be revoked.",
                "A controlled longer-lived session with appropriate protection, expiry, and revocation.",
                "Store the plain-text password in the page source for future visits.",
                "Disable all future permission checks for the account.",
            ], "b", "Convenience does not remove the need for session boundaries. Persistent access should have deliberate lifetime, storage protection, and revocation behaviour."),
            _question("m1q16", "An account uses a password followed by a second-factor challenge. When should the full authenticated session be granted?", [
                "Before either factor is checked, so the page loads faster.",
                "Immediately after a username is entered.",
                "After the password alone, even if the second factor fails.",
                "After the required authentication steps have been verified successfully.",
            ], "d", "A required second factor must actually gate authenticated access. An incomplete authentication flow should not receive the same permissions as a completed one."),
        ],
        "module-2": [
            _question("m2q9", "A profile endpoint lets learners edit their display name. A request also includes role='admin'. What should the server do with that extra field?", [
                "Copy every request field onto the user record automatically.",
                "Approve the role change if the display name is valid.",
                "Accept only fields that this endpoint and role are authorised to change.",
                "Treat a JSON field as proof that the user already has that role.",
            ], "c", "An update endpoint should allow only its intended fields. Copying arbitrary request properties into an account can turn ordinary profile editing into unauthorised privilege changes."),
            _question("m2q10", "An API expects a whole-number course ID. Which validation best matches that requirement?", [
                "Validate the expected type and allowed range, then confirm the referenced course exists and is accessible.",
                "Accept any nonempty object because it can be converted into text.",
                "Use the number's appearance in a browser label as proof it is valid.",
                "Accept negative IDs and decimals without considering how they are used.",
            ], "a", "Type and range checks establish a valid identifier shape. Existence and authorisation checks then establish whether the requested resource can be used."),
            _question("m2q11", "An upload's original filename contains directory separators. How should a server avoid letting that name determine an arbitrary storage path?", [
                "Append the original filename directly to an unrestricted server path.",
                "Trust the filename whenever the file is small.",
                "Let the browser select any folder on the server.",
                "Use a controlled storage location and a safe generated name instead of trusting the supplied path.",
            ], "d", "An uploaded filename is untrusted input. Controlled paths and generated storage names prevent it from choosing locations outside the intended upload area."),
            _question("m2q12", "Why should output encoding match where a user-supplied value is inserted, such as HTML text versus an attribute?", [
                "Every output location interprets all characters in exactly the same way.",
                "Different contexts interpret characters differently, so a control suitable for one context may not safely handle another.",
                "Encoding is only needed for data from anonymous users.",
                "Changing the text colour makes all output contexts safe.",
            ], "b", "Browsers interpret HTML text, attributes, scripts, and URLs differently. Use safe APIs or encoding and validation appropriate to the actual output context."),
            _question("m2q13", "A comment passes a 500-character length check. What does that tell you about rendering it as HTML?", [
                "It is guaranteed safe because short comments cannot contain markup.",
                "It can be executed safely if the commenter is subscribed.",
                "Length validation alone does not make it safe HTML; it still needs safe rendering for its intended text context.",
                "The server can stop checking all future comments by that user.",
            ], "c", "Input length and safe output interpretation solve different problems. A short value can still contain markup or code-like text, so plain-text comments should be rendered as text."),
            _question("m2q14", "Why should a small profile-update endpoint have a reasonable request-body size limit?", [
                "To avoid processing unreasonably large input that could consume server resources.",
                "To make all SQL statements automatically parameterized.",
                "To identify the user's role from the number of bytes sent.",
                "To remove the need for authentication on small requests.",
            ], "a", "Size limits help bound resource use before expensive parsing or processing. They complement, rather than replace, field validation and access control."),
            _question("m2q15", "Why should opening an ordinary GET link not perform a destructive account change?", [
                "GET responses cannot contain HTML.",
                "GET requests always come from administrators.",
                "A link's colour determines whether its operation is authorised.",
                "Links can be followed, previewed, or prefetched without a deliberate state-changing submission.",
            ], "d", "Reading or previewing a link should not unexpectedly change an account. Use appropriate methods and protections for deliberate state-changing operations."),
            _question("m2q16", "Educators can submit an external learning-resource link. Which validation is useful before rendering it as a clickable link?", [
                "Accept any string containing the word lesson.",
                "Allow only supported URL schemes and validate the destination format instead of accepting executable schemes.",
                "Treat the full URL as raw HTML to preserve every supplied character.",
                "Skip validation because a hyperlink cannot affect browser behaviour.",
            ], "b", "Links have a URL context as well as display text. Restricting supported schemes and using safe rendering helps prevent a supplied value from being treated as executable content."),
        ],
        "module-3": [
            _question("m3q9", "Which test best checks that saved quiz attempts are private to their owner?", [
                "Check that both learners can see the same logo.",
                "Verify only that the attempt owner can open their result.",
                "Remove the quiz title from the page and assume the result is private.",
                "Create an attempt for one learner, request its ID as another learner, and verify access is denied.",
            ], "d", "An ownership test must cover access by a different account. A working owner view alone does not prove that other learners are excluded."),
            _question("m3q10", "Saving a submitted quiz requires recording its final score and marking the attempt submitted. Why perform those related changes atomically?", [
                "To guarantee that every learner receives a passing score.",
                "To avoid leaving an attempt marked submitted without its matching saved result, or vice versa.",
                "To eliminate the need for question validation.",
                "To make the same attempt visible to every account.",
            ], "b", "Related state changes should succeed or fail together. Atomic persistence prevents partial outcomes that the interface or later requests could interpret inconsistently."),
            _question("m3q11", "A quiz submission request fails because the network disconnects. Which interface response is most appropriate?", [
                "Keep the answers available, show that saving could not be confirmed, and provide a safe retry path.",
                "Show a passing grade even though the server did not confirm one.",
                "Erase every answer immediately without explanation.",
                "Disable all controls permanently so no further request can occur.",
            ], "a", "The interface should distinguish a confirmed saved result from an uncertain network outcome. Preserving work and supporting a safe retry avoids losing answers or claiming an unverified success."),
            _question("m3q12", "A schema update adds a column to existing course records. Which verification is especially important for current learners?", [
                "Only whether new demo accounts can be created from an empty database.",
                "Whether the update deletes old records so testing becomes simpler.",
                "Whether the migration preserves existing accounts, progress, and results and can run safely on restart.",
                "Whether the application changes every user's password automatically.",
            ], "c", "An upgrade must work with existing data, not just a fresh installation. Checking preservation and repeat startup behaviour helps prevent migration-related data loss."),
            _question("m3q13", "An administrator deactivates an account whose session token has not yet expired. What should protected requests from that account do?", [
                "Succeed until the token's date expires, regardless of deactivation.",
                "Use another active account automatically.",
                "Reactivate the account when the browser refreshes.",
                "Be denied according to the account's current inactive state.",
            ], "d", "Account status is part of current authorisation. A token's original validity should not override deliberate deactivation."),
            _question("m3q14", "A private API credential was accidentally committed to a public repository. Why is deleting it from the latest file alone insufficient?", [
                "Public repositories automatically make every credential invalid immediately.",
                "The credential may already have been copied or remain in history, so it should be revoked or rotated and exposure reviewed.",
                "Changing the filename always changes the credential's permissions.",
                "Only the first visitor to the repository can read committed files.",
            ], "b", "Removing visible text does not undo disclosure. Invalidate the exposed credential and address the affected access rather than assuming it stayed private."),
            _question("m3q15", "A dependency used by the website receives a security fix. Which maintenance approach is most appropriate?", [
                "Review the trusted update, apply it through the project's dependency process, and test the affected flows.",
                "Ignore every security update as long as the home page still loads.",
                "Download an unrelated executable from an unsolicited message.",
                "Remove all access checks to avoid compatibility problems.",
            ], "a", "Security maintenance includes evaluating trusted fixes and verifying that the application still behaves correctly after an update. A working home page alone does not address a known dependency weakness."),
            _question("m3q16", "Audit logs contain account identifiers and details of access events. Who should be able to retrieve them?", [
                "Every anonymous visitor, because logs are not user-facing course content.",
                "Any learner who knows the log endpoint URL.",
                "Only roles with an appropriate operational need, enforced through protected access.",
                "Anyone who includes the word admin in a query parameter.",
            ], "c", "Logs can contain sensitive operational and personal context. Their own access must be protected, rather than treating them as harmless because they are diagnostic records."),
        ],
    },
}

for _course_id, _modules in _ADDITIONAL_QUESTIONS.items():
    for _module in COURSE_ASSESSMENTS[_course_id]["modules"]:
        _module["questions"].extend(_modules[_module["id"]])

del _ADDITIONAL_QUESTIONS, _course_id, _modules, _module
