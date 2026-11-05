"""Practice questions and answer keys, kept out of the public static directory."""


QUIZZES = {
    1: {
        "item_id": 1,
        "title": "Digital Safety Foundations practice quiz",
        "pass_percent": 80,
        "questions": [
            {
                "id": "q1",
                "prompt": "An unexpected email asks you to enter your EduStream password through an unfamiliar link. What is the safest response?",
                "options": [
                    {"id": "a", "text": "Open the link immediately because the message says it is urgent."},
                    {"id": "b", "text": "Open EduStream using its known address and verify the request separately."},
                    {"id": "c", "text": "Reply to the email with your password."},
                    {"id": "d", "text": "Ask a classmate to enter their password into the link first."},
                ],
                "correct_option_id": "b",
                "explanation": "Urgency and unfamiliar links can be phishing signals. Use the service's known address and verify unexpected requests without sharing your password.",
            },
            {
                "id": "q2",
                "prompt": "Which approach best protects your learner account's password?",
                "options": [
                    {"id": "a", "text": "Reuse the password from your email account so it is easy to remember."},
                    {"id": "b", "text": "Use your first name followed by your student ID."},
                    {"id": "c", "text": "Use a long, unique password and store it in a trusted password manager."},
                    {"id": "d", "text": "Share one password with everyone in your project group."},
                ],
                "correct_option_id": "c",
                "explanation": "A long, unique password limits the damage caused by password reuse. A trusted password manager can help keep different passwords for different accounts.",
            },
            {
                "id": "q3",
                "prompt": "What is the purpose of multi-factor authentication?",
                "options": [
                    {"id": "a", "text": "Require another independent verification factor when signing in."},
                    {"id": "b", "text": "Let several students sign in using one shared password."},
                    {"id": "c", "text": "Remove the need to check a user's identity."},
                    {"id": "d", "text": "Give every learner administrator access."},
                ],
                "correct_option_id": "a",
                "explanation": "Multi-factor authentication adds another verification factor, which helps protect an account when its password alone has been compromised.",
            },
            {
                "id": "q4",
                "prompt": "You change a course URL and unexpectedly see another learner's private progress. What should you do?",
                "options": [
                    {"id": "a", "text": "Download the information to show your classmates."},
                    {"id": "b", "text": "Change the learner's progress to test whether it saves."},
                    {"id": "c", "text": "Stop accessing it and report the issue to the educator or administrator."},
                    {"id": "d", "text": "Post a screenshot publicly so other learners can try it."},
                ],
                "correct_option_id": "c",
                "explanation": "Private progress belongs to its learner. Stop accessing the record and report the access-control problem through an appropriate channel.",
            },
            {
                "id": "q5",
                "prompt": "A learner is not allowed to approve educator content. Where must EduStream enforce that rule?",
                "options": [
                    {"id": "a", "text": "Only in the button colour on the page."},
                    {"id": "b", "text": "On the server, by checking the signed-in user's role for each protected action."},
                    {"id": "c", "text": "Only in a note asking learners not to click."},
                    {"id": "d", "text": "Nowhere, as long as the administrator link is difficult to guess."},
                ],
                "correct_option_id": "b",
                "explanation": "The server must check authorisation before performing a protected action. Hiding a link or changing its appearance does not enforce the permission.",
            },
        ],
    },
    2: {
        "item_id": 2,
        "title": "SQL Essentials practice quiz",
        "pass_percent": 80,
        "questions": [
            {
                "id": "q1",
                "prompt": "What is the purpose of the primary key in a learners table?",
                "options": [
                    {"id": "a", "text": "Store the same value in every learner's row."},
                    {"id": "b", "text": "Sort learner names automatically whenever the table is read."},
                    {"id": "c", "text": "Uniquely identify each learner's row."},
                    {"id": "d", "text": "Hide the table from all SELECT queries."},
                ],
                "correct_option_id": "c",
                "explanation": "A primary key identifies one row uniquely. Other tables can reference that key to link related records, such as a learner's subscriptions.",
            },
            {
                "id": "q2",
                "prompt": "Which SQL query returns only the titles of approved courses from a courses table?",
                "options": [
                    {"id": "a", "text": "SELECT title FROM courses WHERE status = 'approved';"},
                    {"id": "b", "text": "SELECT title FROM courses;"},
                    {"id": "c", "text": "DELETE FROM courses WHERE status = 'approved';"},
                    {"id": "d", "text": "SELECT status FROM courses ORDER BY title;"},
                ],
                "correct_option_id": "a",
                "explanation": "SELECT title chooses the title column, and WHERE status = 'approved' filters the rows. Without WHERE, the query would also return titles from other publication states.",
            },
            {
                "id": "q3",
                "prompt": "A subscriptions table stores learner_id, which refers to learners.id. How can a query return each matching subscription together with the learner's name?",
                "options": [
                    {"id": "a", "text": "Delete learner_id so both tables contain fewer columns."},
                    {"id": "b", "text": "Use ORDER BY on subscriptions without reading the learners table."},
                    {"id": "c", "text": "Join the tables using the learner's name and subscription price."},
                    {"id": "d", "text": "Use an INNER JOIN with subscriptions.learner_id = learners.id."},
                ],
                "correct_option_id": "d",
                "explanation": "An INNER JOIN returns matching rows from the two tables. Comparing the stored learner_id with learners.id links each subscription to the correct learner record.",
            },
            {
                "id": "q4",
                "prompt": "A progress record has no completion date yet, so completed_at is NULL. Which condition finds these records?",
                "options": [
                    {"id": "a", "text": "WHERE completed_at = NULL"},
                    {"id": "b", "text": "WHERE completed_at IS NULL"},
                    {"id": "c", "text": "WHERE completed_at = 'NULL'"},
                    {"id": "d", "text": "WHERE completed_at IS NOT NULL"},
                ],
                "correct_option_id": "b",
                "explanation": "IS NULL tests for a missing value. The string 'NULL' is text, and an ordinary equality comparison with NULL does not test whether a value is missing.",
            },
            {
                "id": "q5",
                "prompt": "A learner enters a course title into a search box. How should the application pass this value into its SQL query?",
                "options": [
                    {"id": "a", "text": "Join the raw search text directly into the SQL command."},
                    {"id": "b", "text": "Trust the value because it came from the website's own search box."},
                    {"id": "c", "text": "Use a parameterized query and pass the search value separately."},
                    {"id": "d", "text": "Give the learner permission to edit the database schema."},
                ],
                "correct_option_id": "c",
                "explanation": "Bound parameters keep user-supplied values separate from SQL command text. This prevents a search value from being interpreted as additional SQL instructions.",
            },
        ],
    },
    3: {
        "item_id": 3,
        "title": "Secure Web Application Design practice quiz",
        "pass_percent": 80,
        "questions": [
            {
                "id": "q1",
                "prompt": "Which statement correctly distinguishes authentication from authorisation?",
                "options": [
                    {"id": "a", "text": "Authentication checks who is signing in; authorisation checks what that user is allowed to do."},
                    {"id": "b", "text": "Authentication selects a page colour; authorisation chooses a font."},
                    {"id": "c", "text": "Once authentication succeeds, every user should receive administrator permissions."},
                    {"id": "d", "text": "Both checks are unnecessary when a page has a hidden link."},
                ],
                "correct_option_id": "a",
                "explanation": "Authentication establishes identity, while authorisation enforces permissions. A signed-in learner still needs permission for the particular resource or action being requested.",
            },
            {
                "id": "q2",
                "prompt": "A signed-in learner sends a request to update another learner's progress by changing an ID. What should the server do?",
                "options": [
                    {"id": "a", "text": "Accept the request because the sender is signed in."},
                    {"id": "b", "text": "Allow it whenever the progress value is between 0 and 100."},
                    {"id": "c", "text": "Trust the learner ID sent by the browser without checking ownership."},
                    {"id": "d", "text": "Check the signed-in user's permission for that record and reject the unauthorised update."},
                ],
                "correct_option_id": "d",
                "explanation": "Permission must be checked for the specific record, not just for the page or login session. Learner progress updates should use the authenticated learner's identity and enforce ownership on the server.",
            },
            {
                "id": "q3",
                "prompt": "A content submission form checks that duration is between 5 and 600 minutes. Where should this validation be enforced?",
                "options": [
                    {"id": "a", "text": "Only in the placeholder text beside the input."},
                    {"id": "b", "text": "On the server for every submission, with browser validation also helping the user."},
                    {"id": "c", "text": "Only in browser JavaScript because requests cannot bypass the form."},
                    {"id": "d", "text": "Only after the invalid value has been saved and published."},
                ],
                "correct_option_id": "b",
                "explanation": "Browser checks provide quick feedback but can be bypassed. The server must validate the submitted value before storing it or using it in an operation.",
            },
            {
                "id": "q4",
                "prompt": "What does the HttpOnly attribute on a session cookie help prevent?",
                "options": [
                    {"id": "a", "text": "The server reading the cookie during a request."},
                    {"id": "b", "text": "Every possible cross-site request automatically."},
                    {"id": "c", "text": "Page JavaScript directly reading the session cookie through document.cookie."},
                    {"id": "d", "text": "The session ever expiring."},
                ],
                "correct_option_id": "c",
                "explanation": "HttpOnly keeps the cookie unavailable to document.cookie. It does not replace other controls such as HTTPS, authorisation checks, or protection against unwanted cross-site requests.",
            },
            {
                "id": "q5",
                "prompt": "What should a secure sign-out process do with the user's active server-side session?",
                "options": [
                    {"id": "a", "text": "Invalidate the session and clear the session cookie in the browser."},
                    {"id": "b", "text": "Only hide the dashboard while leaving the session valid."},
                    {"id": "c", "text": "Save the session token in a public page so signing in is faster next time."},
                    {"id": "d", "text": "Grant the session more permissions before returning to the login page."},
                ],
                "correct_option_id": "a",
                "explanation": "Invalidating the server-side session prevents that session token from continuing to authorise requests. Clearing the browser cookie also removes the browser's copy used for subsequent requests.",
            },
        ],
    },
}


def public_quiz(quiz: dict) -> dict:
    """Return only the fields needed to display an unanswered practice quiz."""
    return {
        "item_id": quiz["item_id"],
        "title": quiz["title"],
        "pass_percent": quiz["pass_percent"],
        "questions": [
            {
                "id": question["id"],
                "prompt": question["prompt"],
                "options": [dict(option) for option in question["options"]],
            }
            for question in quiz["questions"]
        ],
    }
