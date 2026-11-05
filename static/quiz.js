const quizUiState = {
  itemId: null, overview: null, attempt: null, answers: {}, questionIndex: 0,
  view: 'hub', requestId: 0, controller: null, busy: false,
  dirty: false, revision: 0, saveTimer: null, savePromise: null,
  saveMessage: '', saveFailed: false, returnFocus: null
};

function quizElement(id) { return document.getElementById(id); }
function quizEscape(value = '') {
  return String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
}
async function quizRequest(url, options = {}) {
  const controller = new AbortController();
  const parentSignal = options.signal;
  const forwardAbort = () => controller.abort(parentSignal.reason);
  let timedOut = false;
  if (parentSignal?.aborted) forwardAbort();
  else parentSignal?.addEventListener('abort', forwardAbort, { once: true });
  const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, 15000);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } });
    let data;
    try { data = await response.json(); }
    catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new Error('The assessment response could not be read. Please try again.');
    }
    if (!response.ok || data.ok === false) throw new Error(data.error || 'The assessment could not be loaded. Please try again.');
    return data;
  } catch (error) {
    if (timedOut) throw new Error('The request timed out. Your saved attempt is safe; please try again.');
    throw error;
  } finally {
    clearTimeout(timeout);
    parentSignal?.removeEventListener('abort', forwardAbort);
  }
}
function quizDate(value) {
  if (!value) return 'Not submitted';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Saved attempt' : date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}
function quizSetError(message) {
  const error = quizElement('quiz-error');
  if (error) error.textContent = message;
}
function quizSetSave(message, failed = false) {
  quizUiState.saveMessage = message;
  quizUiState.saveFailed = failed;
  const status = quizElement('assessment-save-status');
  if (status) { status.textContent = message; status.classList.toggle('failed', failed); }
}
function quizTitle(title, description) {
  quizElement('quiz-title').textContent = title;
  quizElement('quiz-description').textContent = description;
  document.querySelector('.quiz-eyebrow').textContent = 'COURSE ASSESSMENTS';
}
function quizLoading(message) {
  quizElement('quiz-content').innerHTML = `<div class="quiz-loading" role="status"><span class="quiz-spinner" aria-hidden="true"></span><p>${quizEscape(message)}</p></div>`;
}
function quizLoadError(error, retry) {
  quizElement('quiz-content').innerHTML = `<div class="quiz-load-error"><h3>We could not open this assessment</h3><p role="alert">${quizEscape(error.message || 'Please try again.')}</p><button id="quiz-retry" class="quiz-submit" type="button">Try again</button></div>`;
  quizElement('quiz-retry').addEventListener('click', retry);
}
function quizSetBusy(busy) {
  quizUiState.busy = busy;
  quizElement('quiz-close').disabled = busy;
  quizElement('quiz-content').setAttribute('aria-busy', String(busy));
  quizElement('quiz-content').querySelectorAll('button, input').forEach(control => {
    if (busy) { control.dataset.assessmentWasDisabled = String(control.disabled); control.disabled = true; }
    else if ('assessmentWasDisabled' in control.dataset) {
      control.disabled = control.dataset.assessmentWasDisabled === 'true';
      delete control.dataset.assessmentWasDisabled;
    }
  });
}
function quizHubCard(assessment, index) {
  const draft = assessment.draft_attempt_id;
  const badge = assessment.passed ? '<span class="assessment-badge passed">Passed</span>' : draft ? '<span class="assessment-badge progress">In progress</span>' : assessment.locked ? '<span class="assessment-badge">Locked</span>' : assessment.attempt_count ? '<span class="assessment-badge failed">Try again</span>' : '<span class="assessment-badge">Not started</span>';
  const label = draft ? 'Continue attempt' : assessment.attempt_count ? 'Start new attempt' : assessment.kind === 'final' ? 'Start final exam' : 'Start module quiz';
  const score = assessment.best_score === null ? 'No grade yet' : `Best grade: ${assessment.best_score}%`;
  return `<article class="assessment-card ${assessment.kind === 'final' ? 'final' : ''} ${assessment.passed ? 'passed' : ''}">
    <span class="assessment-number" aria-hidden="true">${assessment.kind === 'final' ? 'F' : String(index + 1).padStart(2, '0')}</span>
    <div><span class="assessment-kicker">${assessment.kind === 'final' ? 'Final assessment' : `Module ${index + 1}`}</span><h4>${quizEscape(assessment.title)}</h4><p>${quizEscape(assessment.description)}</p>
      <div class="assessment-meta"><span>${assessment.question_count} questions</span><span>About ${assessment.estimated_minutes} min</span><span>${quizEscape(score)}</span></div>
      ${assessment.locked ? `<p class="assessment-lock-note">${quizEscape(assessment.lock_reason || 'Pass all module quizzes to unlock the final exam.')}</p>` : ''}
    </div>
    <div class="assessment-card-action">${badge}<button class="assessment-button ${assessment.passed ? 'secondary' : ''}" data-assessment-start="${quizEscape(assessment.id)}" ${assessment.locked ? 'disabled' : ''}>${assessment.locked ? 'Complete modules first' : label}</button></div>
  </article>`;
}
function quizRenderHub() {
  const { course, assessments } = quizUiState.overview;
  quizUiState.view = 'hub';
  quizUiState.attempt = null;
  quizUiState.answers = {};
  quizElement('quiz-dialog').scrollTop = 0;
  quizTitle(course.title, 'Complete your module quizzes, then demonstrate what you have learned in the final exam.');
  const history = assessments.flatMap(assessment => assessment.history.map(attempt => ({ ...attempt, title: assessment.title }))).sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));
  quizElement('quiz-content').innerHTML = `
    <section class="assessment-summary"><div><span class="assessment-kicker">Your assessment journey</span><h3>${course.completed ? 'All assessments passed.' : 'Build your knowledge, one module at a time.'}</h3><p>Earn at least ${course.pass_percent}% in each module quiz to unlock the final exam. Your best grade is kept, and you can try again. New attempts use a different question set from your previous attempt.</p></div><div class="assessment-summary-grade"><strong>${course.passed_count} / ${course.total_assessments}</strong><span>Assessments passed</span><progress value="${course.passed_count}" max="${course.total_assessments}" aria-label="Assessments passed"></progress></div></section>
    <div class="assessment-section-heading"><h3>Module quizzes &amp; final exam</h3><span>${course.pass_percent}% to pass each</span></div>
    <div class="assessment-list">${assessments.map(quizHubCard).join('')}</div>
    <div class="assessment-section-heading"><h3>Your attempt history</h3><span>Best grades are retained</span></div>
    ${history.length ? `<div class="assessment-history-wrap"><table class="assessment-history"><thead><tr><th scope="col">Assessment</th><th scope="col">Grade</th><th scope="col">Submitted</th><th scope="col">Review</th></tr></thead><tbody>${history.map(attempt => `<tr><td>${quizEscape(attempt.title)}</td><td><span class="assessment-badge ${attempt.passed ? 'passed' : 'failed'}">${attempt.score}% · ${attempt.passed ? 'Passed' : 'Not passed'}</span></td><td><time>${quizEscape(quizDate(attempt.submitted_at))}</time></td><td><button class="assessment-link" data-attempt-review="${attempt.attempt_id}" aria-label="Review ${quizEscape(attempt.title)} attempt, ${attempt.score} percent">View feedback</button></td></tr>`).join('')}</tbody></table></div>` : '<div class="assessment-empty">Your submitted attempts and grades will appear here. Saved drafts can be continued from the cards above.</div>'}
    <p id="quiz-error" class="quiz-error" role="alert"></p>`;
  quizElement('quiz-content').querySelectorAll('[data-assessment-start]').forEach(button => button.addEventListener('click', () => quizStartAssessment(button.dataset.assessmentStart)));
  quizElement('quiz-content').querySelectorAll('[data-attempt-review]').forEach(button => button.addEventListener('click', () => quizOpenAttempt(Number(button.dataset.attemptReview))));
}
async function quizLoadHub() {
  const requestId = ++quizUiState.requestId;
  quizUiState.controller?.abort();
  quizUiState.controller = new AbortController();
  quizLoading('Loading your assessments and grades…');
  try {
    const data = await quizRequest(`/api/assessments/${quizUiState.itemId}`, { signal: quizUiState.controller.signal });
    if (requestId !== quizUiState.requestId) return;
    if (!data.course || !Array.isArray(data.assessments)) throw new Error('The course assessments could not be read.');
    quizUiState.overview = data;
    quizRenderHub();
  } catch (error) { if (requestId === quizUiState.requestId && error.name !== 'AbortError') quizLoadError(error, quizLoadHub); }
}
function quizAcceptAttempt(attempt) {
  if (!attempt || !Array.isArray(attempt.questions) || !attempt.questions.length) throw new Error('No questions are available for this assessment.');
  clearTimeout(quizUiState.saveTimer);
  quizUiState.attempt = attempt;
  quizUiState.answers = { ...attempt.answers };
  quizUiState.questionIndex = 0;
  quizUiState.dirty = false;
  quizUiState.revision = 0;
  quizUiState.saveMessage = attempt.status === 'submitted' ? 'Submitted · read-only review' : 'All changes saved';
  quizUiState.saveFailed = false;
  quizRenderAttempt();
  quizElement('quiz-dialog').scrollTop = 0;
  (quizElement('quiz-result-title') || quizElement('assessment-question-heading'))?.focus({ preventScroll: true });
}
async function quizStartAssessment(assessmentId) {
  if (quizUiState.busy) return;
  const requestId = quizUiState.requestId;
  quizSetBusy(true);
  quizSetError('');
  try {
    await quizFlushSave();
    const data = await quizRequest(`/api/assessments/${quizUiState.itemId}/start`, { method: 'POST', body: JSON.stringify({ assessment_id: assessmentId }) });
    if (requestId !== quizUiState.requestId) return;
    quizAcceptAttempt(data.attempt);
  } catch (error) { if (requestId === quizUiState.requestId) quizSetError(error.message); }
  finally { if (requestId === quizUiState.requestId) quizSetBusy(false); }
}
async function quizOpenAttempt(attemptId) {
  if (quizUiState.busy) return;
  const requestId = quizUiState.requestId;
  quizSetBusy(true);
  quizSetError('');
  try {
    await quizFlushSave();
    const data = await quizRequest(`/api/assessment-attempts/${attemptId}`);
    if (requestId === quizUiState.requestId) quizAcceptAttempt(data.attempt);
  } catch (error) { if (requestId === quizUiState.requestId) quizSetError(error.message); }
  finally { if (requestId === quizUiState.requestId) quizSetBusy(false); }
}
function quizAnsweredCount() { return quizUiState.attempt.questions.filter(question => quizUiState.answers[question.id]).length; }
function quizNavigation() {
  const attempt = quizUiState.attempt;
  return attempt.questions.map((question, index) => {
    const feedback = attempt.result?.feedback.find(value => value.question_id === question.id);
    const answered = Boolean(quizUiState.answers[question.id]);
    const state = feedback ? (feedback.correct ? 'Correct' : 'Incorrect') : answered ? 'Answered' : 'Not answered';
    return `<button type="button" data-question-index="${index}" class="${index === quizUiState.questionIndex ? 'active' : ''} ${answered ? 'answered' : ''} ${feedback ? feedback.correct ? 'correct' : 'incorrect' : ''}" aria-label="Question ${index + 1}, ${state}" ${index === quizUiState.questionIndex ? 'aria-current="step"' : ''}>${index + 1}</button>`;
  }).join('');
}
function quizResultBanner() {
  const result = quizUiState.attempt.result;
  if (!result) return '';
  return `<section id="quiz-result" class="quiz-result ${result.passed ? 'quiz-result-passed' : ''}" aria-labelledby="quiz-result-title"><div><span class="quiz-score">${result.score}%</span><span class="assessment-kicker">Best: ${result.best_score}%</span></div><div><h3 id="quiz-result-title" tabindex="-1">${result.passed ? 'Assessment passed' : 'Keep learning, then try again'}</h3><p>${result.correct} of ${result.total_questions} answers correct. ${result.course_completed ? 'You have passed all module quizzes and the final exam.' : result.passed ? 'Your grade has been saved. Return to the assessment overview to continue.' : `You need ${quizUiState.attempt.pass_percent}% to pass. Review the feedback and revisit the course material before your next attempt.`}</p><div class="assessment-result-actions"><button id="assessment-result-hub" class="assessment-button secondary" type="button">Back to assessments</button><button id="quiz-retake" class="assessment-button" type="button">Try another attempt</button></div></div></section>`;
}
function quizRenderAttempt() {
  const attempt = quizUiState.attempt;
  if (!attempt) return;
  quizUiState.view = 'attempt';
  const submitted = attempt.status === 'submitted';
  const question = attempt.questions[quizUiState.questionIndex];
  const feedback = attempt.result?.feedback.find(value => value.question_id === question.id);
  const count = quizAnsweredCount();
  quizTitle(attempt.title, submitted ? 'Your submitted attempt is saved. Review each answer and its explanation below.' : 'Choose one answer per question. Your progress is saved so you can continue later.');
  quizElement('quiz-content').innerHTML = `
    <div class="assessment-toolbar"><button id="assessment-back" class="assessment-link" type="button">← Back to assessments</button><span id="assessment-save-status" class="assessment-save-status ${quizUiState.saveFailed ? 'failed' : ''}" role="status" aria-live="polite">${quizEscape(quizUiState.saveMessage)}</span></div>
    ${quizResultBanner()}
    <div class="assessment-runner"><aside class="assessment-sidebar" aria-label="Question navigation"><h3>${submitted ? 'Review answers' : 'Your questions'}</h3><p id="quiz-answer-count">${count} of ${attempt.questions.length} answered</p><nav class="assessment-question-nav" aria-label="Jump to question">${quizNavigation()}</nav><progress id="quiz-answer-progress" max="${attempt.questions.length}" value="${count}" aria-label="Questions answered"></progress><p class="assessment-sidebar-note">${submitted ? 'Select a number to review its feedback.' : 'You can answer in any order. Filled squares show answered questions.'}</p></aside>
    <div class="assessment-question-panel"><div class="assessment-question-meta"><span>QUESTION ${quizUiState.questionIndex + 1} OF ${attempt.questions.length}</span><span>1 point · ${attempt.pass_percent}% to pass</span></div>
    <form id="quiz-form"><fieldset class="quiz-question" data-question-id="${quizEscape(question.id)}"><legend tabindex="-1" id="assessment-question-heading">${quizEscape(question.prompt)}</legend><div class="quiz-options">${question.options.map((option, index) => `<label class="quiz-option ${feedback && option.id === feedback.correct_option_id ? 'quiz-option-correct' : feedback && option.id === feedback.selected_option_id && !feedback.correct ? 'quiz-option-incorrect' : ''}" for="quiz-option-${index}" data-option-id="${quizEscape(option.id)}"><input id="quiz-option-${index}" type="radio" name="${quizEscape(question.id)}" value="${quizEscape(option.id)}" ${quizUiState.answers[question.id] === option.id ? 'checked' : ''} ${submitted ? 'disabled' : ''} ${feedback ? 'aria-describedby="assessment-feedback"' : ''}><span>${quizEscape(option.text)}</span></label>`).join('')}</div></fieldset>
    ${feedback ? `<div id="assessment-feedback" class="quiz-question-feedback ${feedback.correct ? '' : 'incorrect'}"><strong>${feedback.correct ? 'Correct answer.' : 'Review this answer.'}</strong>${quizEscape(feedback.explanation)}${!feedback.correct ? `<p>Correct answer: ${quizEscape(question.options.find(option => option.id === feedback.correct_option_id)?.text || '')}</p>` : ''}</div>` : ''}
    <div class="assessment-question-actions"><button id="assessment-previous" class="assessment-button secondary" type="button" ${quizUiState.questionIndex === 0 ? 'disabled' : ''}>Previous</button>${quizUiState.questionIndex < attempt.questions.length - 1 ? '<button id="assessment-next" class="assessment-button" type="button">Next question →</button>' : submitted ? '<button id="assessment-finish-review" class="assessment-button" type="button">Back to assessments</button>' : '<button id="assessment-review" class="assessment-button" type="button">Review &amp; submit</button>'}</div>
    ${!submitted && quizUiState.questionIndex < attempt.questions.length - 1 ? '<button id="assessment-review-early" class="assessment-link assessment-review-early" type="button">Review all answers</button>' : ''}
    </form></div></div><p id="quiz-error" class="quiz-error" role="alert"></p>`;
  quizElement('assessment-back').addEventListener('click', quizBackToHub);
  quizElement('assessment-result-hub')?.addEventListener('click', quizBackToHub);
  quizElement('assessment-finish-review')?.addEventListener('click', quizBackToHub);
  quizElement('quiz-retake')?.addEventListener('click', () => quizStartAssessment(attempt.assessment_id));
  quizElement('quiz-form').addEventListener('submit', event => event.preventDefault());
  quizElement('quiz-form').addEventListener('change', event => {
    if (submitted || event.target.type !== 'radio') return;
    quizUiState.answers[question.id] = event.target.value;
    quizUiState.dirty = true;
    quizUiState.revision += 1;
    quizSetError('');
    quizSetSave('Saving your answer…');
    const answered = quizAnsweredCount();
    quizElement('quiz-answer-count').textContent = `${answered} of ${attempt.questions.length} answered`;
    quizElement('quiz-answer-progress').value = answered;
    const navButton = quizElement('quiz-content').querySelector(`[data-question-index="${quizUiState.questionIndex}"]`);
    navButton.classList.add('answered');
    navButton.setAttribute('aria-label', `Question ${quizUiState.questionIndex + 1}, Answered`);
    clearTimeout(quizUiState.saveTimer);
    quizUiState.saveTimer = setTimeout(() => quizFlushSave().catch(() => {}), 350);
  });
  quizElement('quiz-content').querySelectorAll('[data-question-index]').forEach(button => button.addEventListener('click', () => quizMoveQuestion(Number(button.dataset.questionIndex))));
  quizElement('assessment-previous').addEventListener('click', () => quizMoveQuestion(quizUiState.questionIndex - 1));
  quizElement('assessment-next')?.addEventListener('click', () => quizMoveQuestion(quizUiState.questionIndex + 1));
  quizElement('assessment-review')?.addEventListener('click', quizRenderReview);
  quizElement('assessment-review-early')?.addEventListener('click', quizRenderReview);
}
function quizMoveQuestion(index) {
  if (quizUiState.busy) return;
  quizUiState.questionIndex = Math.max(0, Math.min(index, quizUiState.attempt.questions.length - 1));
  quizRenderAttempt();
  quizElement('assessment-question-heading').focus({ preventScroll: true });
  quizElement('assessment-question-heading').scrollIntoView({ block: 'nearest' });
}
async function quizFlushSave() {
  clearTimeout(quizUiState.saveTimer);
  if (quizUiState.savePromise) { await quizUiState.savePromise; return quizFlushSave(); }
  if (!quizUiState.dirty || !quizUiState.attempt || quizUiState.attempt.status === 'submitted') return;
  const attemptId = quizUiState.attempt.id;
  const requestId = quizUiState.requestId;
  const operation = (async () => {
    while (quizUiState.dirty && quizUiState.attempt?.id === attemptId && requestId === quizUiState.requestId) {
      const revision = quizUiState.revision;
      const answers = { ...quizUiState.answers };
      quizSetSave('Saving your answer…');
      try {
        const data = await quizRequest(`/api/assessment-attempts/${attemptId}/save`, { method: 'POST', body: JSON.stringify({ answers }) });
        if (requestId !== quizUiState.requestId || quizUiState.attempt?.id !== attemptId) return;
        quizUiState.attempt.saved_at = data.attempt.saved_at;
        if (revision === quizUiState.revision) quizUiState.dirty = false;
        quizSetSave(quizUiState.dirty ? 'Saving your latest answer…' : 'All changes saved');
      } catch (error) {
        if (requestId === quizUiState.requestId) {
          quizSetSave('Not saved — keep this window open and try again.', true);
          quizSetError(`${error.message} Your latest answers are still in this window. Use Save again before leaving.`);
          quizShowSaveRetry();
        }
        throw error;
      }
    }
  })();
  quizUiState.savePromise = operation;
  try { await operation; } finally { if (quizUiState.savePromise === operation) quizUiState.savePromise = null; }
}
function quizShowSaveRetry() {
  if (quizElement('assessment-save-retry')) return;
  const retry = document.createElement('button');
  retry.type = 'button'; retry.id = 'assessment-save-retry'; retry.className = 'assessment-button secondary'; retry.textContent = 'Save again';
  retry.addEventListener('click', async () => {
    retry.disabled = true;
    try { await quizFlushSave(); quizSetError(''); retry.remove(); } catch (_) { retry.disabled = false; }
  });
  quizElement('quiz-error')?.after(retry);
}
function quizRenderReview() {
  if (quizUiState.busy) return;
  quizUiState.view = 'review';
  quizElement('quiz-dialog').scrollTop = 0;
  const attempt = quizUiState.attempt;
  const answered = quizAnsweredCount();
  quizTitle('Review before you submit', attempt.title);
  quizElement('quiz-content').innerHTML = `<div class="assessment-toolbar"><button id="assessment-return-questions" class="assessment-link" type="button">← Back to questions</button><span id="assessment-save-status" class="assessment-save-status ${quizUiState.saveFailed ? 'failed' : ''}" role="status" aria-live="polite">${quizEscape(quizUiState.saveMessage)}</span></div>
    <div class="assessment-confirmation"><strong>${answered} of ${attempt.questions.length} questions answered.</strong><br>${answered === attempt.questions.length ? 'Check your choices below. Submitting grades this attempt and makes these answers read-only. You can start a new attempt afterwards.' : 'Answer every question before submitting. Select an unanswered question below to finish it.'}</div>
    <div class="assessment-review-list">${attempt.questions.map((question, index) => {
      const option = question.options.find(value => value.id === quizUiState.answers[question.id]);
      return `<div class="assessment-review-row ${option ? '' : 'unanswered'}"><span class="assessment-number">${index + 1}</span><div><p>${quizEscape(question.prompt)}</p><small>${option ? `Your answer: ${quizEscape(option.text)}` : 'Not answered yet'}</small></div><button class="assessment-link" data-review-question="${index}" type="button">${option ? 'Change' : 'Answer'}</button></div>`;
    }).join('')}</div><div class="assessment-question-actions"><button id="assessment-return-questions-bottom" class="assessment-button secondary" type="button">Keep editing</button><button id="quiz-submit" class="quiz-submit" type="button" ${answered !== attempt.questions.length ? 'disabled' : ''}>Submit for grading</button></div><p id="quiz-error" class="quiz-error" role="alert"></p>`;
  quizElement('assessment-return-questions').addEventListener('click', () => quizMoveQuestion(quizUiState.questionIndex));
  quizElement('assessment-return-questions-bottom').addEventListener('click', () => quizMoveQuestion(quizUiState.questionIndex));
  quizElement('quiz-content').querySelectorAll('[data-review-question]').forEach(button => button.addEventListener('click', () => quizMoveQuestion(Number(button.dataset.reviewQuestion))));
  quizElement('quiz-submit').addEventListener('click', quizSubmit);
}
async function quizSubmit() {
  if (quizUiState.busy || !quizUiState.attempt || quizUiState.attempt.status === 'submitted') return;
  if (quizAnsweredCount() !== quizUiState.attempt.questions.length) { quizSetError('Please answer every question before submitting.'); return; }
  const requestId = quizUiState.requestId;
  quizSetBusy(true);
  quizSetError('');
  quizElement('quiz-submit').textContent = 'Submitting your answers…';
  try {
    await quizFlushSave();
    const data = await quizRequest(`/api/assessment-attempts/${quizUiState.attempt.id}/submit`, { method: 'POST', body: JSON.stringify({ answers: quizUiState.answers }) });
    if (requestId !== quizUiState.requestId) return;
    quizAcceptAttempt(data.attempt);
    document.dispatchEvent(new CustomEvent('assessment-updated'));
    quizElement('quiz-result')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (error) {
    if (requestId === quizUiState.requestId) { quizSetError(error.message); const button = quizElement('quiz-submit'); if (button) button.textContent = 'Submit for grading'; }
  } finally { if (requestId === quizUiState.requestId) quizSetBusy(false); }
}
async function quizBackToHub() {
  if (quizUiState.busy) return;
  quizSetBusy(true);
  try { await quizFlushSave(); quizSetBusy(false); await quizLoadHub(); }
  catch (error) { quizSetError(error.message); }
  finally { quizSetBusy(false); }
}
async function quizClose() {
  if (quizUiState.busy) return;
  quizSetBusy(true);
  try {
    await quizFlushSave();
    quizUiState.requestId += 1;
    quizUiState.controller?.abort();
    quizElement('quiz-dialog').close();
    quizUiState.returnFocus?.focus?.();
  } catch (error) { quizSetError(error.message); }
  finally { quizSetBusy(false); }
}
async function openQuiz(itemId) {
  const id = Number(itemId);
  if (!Number.isSafeInteger(id) || id < 1 || quizUiState.busy) return;
  const dialog = quizElement('quiz-dialog');
  if (!dialog) return;
  try { await quizFlushSave(); } catch (_) { return; }
  quizUiState.returnFocus = document.activeElement;
  document.querySelector('#lesson-dialog[open]')?.close();
  quizUiState.itemId = id;
  quizUiState.attempt = null;
  quizUiState.overview = null;
  quizUiState.answers = {};
  quizUiState.dirty = false;
  quizTitle('Course assessments', 'Loading your module quizzes, final exam, and saved grades.');
  if (!dialog.open) dialog.showModal();
  await quizLoadHub();
}
document.addEventListener('DOMContentLoaded', () => {
  const dialog = quizElement('quiz-dialog');
  quizElement('quiz-close')?.addEventListener('click', quizClose);
  dialog?.addEventListener('cancel', event => { event.preventDefault(); quizClose(); });
  dialog?.addEventListener('close', () => { quizUiState.requestId += 1; quizUiState.controller?.abort(); clearTimeout(quizUiState.saveTimer); });
});

window.addEventListener('beforeunload', event => {
  if (quizUiState.dirty && quizUiState.attempt?.status === 'in_progress') { event.preventDefault(); event.returnValue = ''; }
});
