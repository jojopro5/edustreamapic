const quizUiState = {
  itemId: null,
  quiz: null,
  lastAttempt: null,
  result: null,
  submitting: false,
  requestId: 0,
  controller: null
};

function quizElement(id) { return document.getElementById(id); }
function quizEscape(value = "") {
  return String(value).replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
}

async function quizRequest(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  const data = await response.json().catch(() => ({ ok: false, error: "The quiz response could not be read. Please try again." }));
  if (!response.ok || data.ok === false) throw new Error(data.error || "The quiz could not be loaded. Please try again.");
  return data;
}

function quizSetError(message) {
  const error = quizElement("quiz-error");
  if (error) error.textContent = message;
}

function quizAnswers(form) {
  const data = new FormData(form);
  return Object.fromEntries(quizUiState.quiz.questions.flatMap(question => {
    const answer = data.get(question.id);
    return answer === null ? [] : [[question.id, answer]];
  }));
}

function quizUpdateCounter() {
  const form = quizElement("quiz-form");
  if (!form || !quizUiState.quiz) return;
  const answered = Object.keys(quizAnswers(form)).length;
  const total = quizUiState.quiz.questions.length;
  quizElement("quiz-answer-count").textContent = `${answered} of ${total} answered`;
  quizElement("quiz-answer-progress").value = answered;
}

function quizClearFeedback() {
  quizUiState.result = null;
  const result = quizElement("quiz-result");
  result.hidden = true;
  result.innerHTML = "";
  document.querySelectorAll("#quiz-form .quiz-question").forEach(question => {
    question.classList.remove("quiz-question-correct", "quiz-question-incorrect");
    question.querySelector(".quiz-question-feedback").textContent = "";
    question.querySelectorAll(".quiz-option").forEach(option => option.classList.remove("quiz-option-correct", "quiz-option-incorrect"));
    question.querySelectorAll("input").forEach(input => input.removeAttribute("aria-describedby"));
  });
  quizElement("quiz-submit").textContent = "Submit answers";
}

function quizRender() {
  const quiz = quizUiState.quiz;
  const total = quiz.questions.length;
  quizElement("quiz-title").textContent = quiz.title;
  const lastAttempt = quizUiState.lastAttempt;
  const previous = lastAttempt ? `<p class="quiz-previous">Last saved result: <strong>${quizEscape(lastAttempt.score)}%</strong> · ${quizEscape(lastAttempt.correct)} of ${quizEscape(lastAttempt.total_questions)} correct</p>` : "";
  quizElement("quiz-content").innerHTML = `
    <div class="quiz-introduction">
      <div class="quiz-facts"><span>${total} questions</span><span>${quizEscape(quiz.pass_percent)}% practice pass mark</span></div>
      <p>Select one answer for each question. You can change any answer before or after checking your result.</p>
      ${previous}
    </div>
    <form id="quiz-form" novalidate>
      <div class="quiz-progress-row"><span id="quiz-answer-count" role="status" aria-live="polite">0 of ${total} answered</span><span>One answer per question</span></div>
      <progress id="quiz-answer-progress" max="${total}" value="0" aria-label="Questions answered"></progress>
      <div class="quiz-questions">
        ${quiz.questions.map((question, questionIndex) => `
          <fieldset class="quiz-question" data-question-id="${quizEscape(question.id)}">
            <legend><span class="quiz-question-number">${questionIndex + 1}</span><span>${quizEscape(question.prompt)}</span></legend>
            <div class="quiz-options">
              ${question.options.map((option, optionIndex) => `
                <label class="quiz-option" data-option-id="${quizEscape(option.id)}" for="quiz-option-${questionIndex}-${optionIndex}">
                  <input id="quiz-option-${questionIndex}-${optionIndex}" type="radio" name="${quizEscape(question.id)}" value="${quizEscape(option.id)}" required>
                  <span>${quizEscape(option.text)}</span>
                </label>`).join("")}
            </div>
            <div id="quiz-feedback-${questionIndex}" class="quiz-question-feedback"></div>
          </fieldset>`).join("")}
      </div>
      <p id="quiz-error" class="quiz-error" role="alert"></p>
      <section id="quiz-result" class="quiz-result" aria-labelledby="quiz-result-title" aria-live="polite" hidden></section>
      <div class="quiz-submit-row"><p>Your score is saved to your account. Course progress stays separate.</p><button id="quiz-submit" class="quiz-submit" type="submit">Submit answers</button></div>
    </form>`;
  const form = quizElement("quiz-form");
  form.addEventListener("change", () => {
    if (quizUiState.result) quizClearFeedback();
    quizSetError("");
    quizUpdateCounter();
  });
  form.addEventListener("submit", quizSubmit);
}

function quizShowResult(result) {
  quizUiState.result = result;
  quizUiState.lastAttempt = result;
  const form = quizElement("quiz-form");
  quizUiState.quiz.questions.forEach((question, index) => {
    const feedback = result.feedback.find(item => item.question_id === question.id);
    if (!feedback) return;
    const fieldset = [...form.querySelectorAll(".quiz-question")].find(element => element.dataset.questionId === question.id);
    const correctOption = question.options.find(option => option.id === feedback.correct_option_id);
    fieldset.classList.add(feedback.correct ? "quiz-question-correct" : "quiz-question-incorrect");
    fieldset.querySelectorAll(".quiz-option").forEach(option => {
      option.classList.toggle("quiz-option-correct", option.dataset.optionId === feedback.correct_option_id);
      option.classList.toggle("quiz-option-incorrect", !feedback.correct && option.dataset.optionId === feedback.selected_option_id);
    });
    const feedbackElement = fieldset.querySelector(".quiz-question-feedback");
    feedbackElement.innerHTML = `<strong>${feedback.correct ? "Correct." : "Not quite."}</strong> ${quizEscape(feedback.explanation)}${!feedback.correct && correctOption ? `<span class="quiz-correct-answer">Correct answer: ${quizEscape(correctOption.text)}</span>` : ""}`;
    fieldset.querySelectorAll("input").forEach(input => input.setAttribute("aria-describedby", `quiz-feedback-${index}`));
  });
  const summary = quizElement("quiz-result");
  summary.hidden = false;
  summary.classList.toggle("quiz-result-passed", result.passed);
  summary.innerHTML = `<div><span class="quiz-score">${quizEscape(result.score)}%</span><h3 id="quiz-result-title">${result.passed ? "Practice quiz passed" : "Keep practising"}</h3><p>${quizEscape(result.correct)} of ${quizEscape(result.total_questions)} answers correct. Review the feedback above or try again.</p></div><button id="quiz-retake" class="quiz-retake" type="button">Retake quiz</button>`;
  quizElement("quiz-submit").textContent = "Check answers again";
  quizElement("quiz-retake").addEventListener("click", () => {
    quizUiState.result = null;
    quizRender();
    const first = quizElement("quiz-form").querySelector("input");
    if (first) first.focus();
  });
  summary.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function quizSubmit(event) {
  event.preventDefault();
  if (quizUiState.submitting) return;
  const form = event.currentTarget;
  const answers = quizAnswers(form);
  const unansweredIndex = quizUiState.quiz.questions.findIndex(question => !Object.hasOwn(answers, question.id));
  if (unansweredIndex >= 0) {
    quizSetError(`Please answer question ${unansweredIndex + 1} before submitting.`);
    const firstUnanswered = [...form.elements].find(element => element.name === quizUiState.quiz.questions[unansweredIndex].id);
    if (firstUnanswered) firstUnanswered.focus();
    return;
  }
  const requestId = quizUiState.requestId;
  const submit = quizElement("quiz-submit");
  const previousText = submit.textContent;
  quizUiState.submitting = true;
  quizSetError("");
  submit.disabled = true;
  submit.setAttribute("aria-busy", "true");
  submit.textContent = "Checking answers…";
  const controls = [...form.querySelectorAll('input[type="radio"]')];
  controls.forEach(input => { input.disabled = true; });
  try {
    quizUiState.controller = new AbortController();
    const response = await quizRequest(`/api/quiz/${quizUiState.itemId}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers }),
      signal: quizUiState.controller.signal
    });
    if (requestId !== quizUiState.requestId) return;
    if (!response.result || !Array.isArray(response.result.feedback)) throw new Error("The quiz result could not be read. Please try again.");
    quizShowResult(response.result);
  } catch (error) {
    if (requestId === quizUiState.requestId && error.name !== "AbortError") {
      quizSetError(error.message || "Your result could not be saved. Please try again.");
      submit.textContent = previousText;
    }
  } finally {
    if (requestId === quizUiState.requestId) {
      quizUiState.submitting = false;
      submit.disabled = false;
      submit.removeAttribute("aria-busy");
      controls.forEach(input => { input.disabled = false; });
    }
  }
}

async function openQuiz(itemId) {
  const id = Number(itemId);
  if (!Number.isSafeInteger(id) || id < 1) return;
  const dialog = quizElement("quiz-dialog");
  if (!dialog) return;
  const lessonDialog = document.querySelector("#lesson-dialog[open]");
  if (lessonDialog) lessonDialog.close();
  quizUiState.controller?.abort();
  quizUiState.requestId += 1;
  const requestId = quizUiState.requestId;
  quizUiState.itemId = id;
  quizUiState.quiz = null;
  quizUiState.result = null;
  quizUiState.submitting = false;
  quizElement("quiz-title").textContent = "Practice quiz";
  quizElement("quiz-content").innerHTML = '<div class="quiz-loading" role="status"><span class="quiz-spinner" aria-hidden="true"></span><p>Loading your questions…</p></div>';
  if (!dialog.open) dialog.showModal();
  try {
    quizUiState.controller = new AbortController();
    const response = await quizRequest(`/api/quiz/${id}`, { signal: quizUiState.controller.signal });
    if (requestId !== quizUiState.requestId) return;
    if (!response.quiz || !Array.isArray(response.quiz.questions) || response.quiz.questions.length === 0) throw new Error("No quiz questions are available for this learning item.");
    quizUiState.quiz = response.quiz;
    quizUiState.lastAttempt = response.last_attempt || null;
    quizRender();
  } catch (error) {
    if (requestId !== quizUiState.requestId || error.name === "AbortError") return;
    quizElement("quiz-content").innerHTML = `<div class="quiz-load-error"><h3>We could not open this quiz</h3><p role="alert">${quizEscape(error.message || "Please try again.")}</p><button id="quiz-retry" class="quiz-submit" type="button">Try again</button></div>`;
    quizElement("quiz-retry").addEventListener("click", () => openQuiz(id));
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const dialog = quizElement("quiz-dialog");
  quizElement("quiz-close")?.addEventListener("click", () => dialog.close());
  dialog?.addEventListener("close", () => {
    quizUiState.requestId += 1;
    quizUiState.controller?.abort();
    quizUiState.submitting = false;
  });
});
