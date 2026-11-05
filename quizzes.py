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
    }
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
