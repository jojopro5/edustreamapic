"use strict";
// Learner feedback in the lesson dialog, and the admin moderation list.
// Comments are user-written text: every comment is put on the page with
// textContent or as a text node, never through innerHTML, so markup a learner
// types (for example <script> while discussing the Secure Web course) shows as
// plain text and cannot run.

const FEEDBACK_MAX = 500;
const feedbackState = { itemId: null };

function feedbackDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" }).format(date);
}

function feedbackElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function renderFeedbackList(entries) {
  const list = document.getElementById("feedback-list");
  list.replaceChildren();
  if (!entries.length) {
    list.append(feedbackElement("li", "feedback-empty", "No feedback yet. Be the first to share what you think."));
    return;
  }
  for (const entry of entries) list.append(feedbackItem(entry));
}

function feedbackItem(entry) {
  const item = feedbackElement("li", "feedback-item");
  item.dataset.feedbackId = String(entry.id);
  const meta = feedbackElement("div", "feedback-meta");
  meta.append(feedbackElement("strong", "", entry.mine ? "You" : entry.author));
  meta.append(feedbackElement("time", "", feedbackDate(entry.created_at) + (entry.edited_at ? " · edited" : "")));
  const body = feedbackElement("p", "feedback-body", entry.body);
  item.append(meta, body);
  if (entry.mine) {
    const actions = feedbackElement("div", "feedback-item-actions");
    const editButton = feedbackElement("button", "text-link", "Edit");
    editButton.type = "button";
    editButton.addEventListener("click", () => startFeedbackEdit(item, entry));
    const deleteButton = feedbackElement("button", "text-link feedback-delete", "Delete");
    deleteButton.type = "button";
    deleteButton.addEventListener("click", () => deleteFeedback(entry.id, deleteButton));
    actions.append(editButton, deleteButton);
    item.append(actions);
  }
  return item;
}

function startFeedbackEdit(item, entry) {
  const form = feedbackElement("form", "feedback-edit-form");
  const label = feedbackElement("label", "sr-only", "Edit your feedback");
  const area = document.createElement("textarea");
  area.id = "feedback-edit-" + entry.id;
  label.htmlFor = area.id;
  area.maxLength = FEEDBACK_MAX;
  area.rows = 3;
  area.value = entry.body;
  const error = feedbackElement("p", "inline-error");
  error.setAttribute("role", "alert");
  const actions = feedbackElement("div", "feedback-item-actions");
  const save = feedbackElement("button", "button secondary small", "Save");
  save.type = "submit";
  const cancel = feedbackElement("button", "text-link", "Cancel");
  cancel.type = "button";
  cancel.addEventListener("click", () => item.replaceWith(feedbackItem(entry)));
  actions.append(save, cancel);
  form.append(label, area, actions, error);
  form.addEventListener("submit", async event => {
    event.preventDefault();
    save.disabled = true;
    try {
      const data = await api("/api/feedback-entries/" + entry.id + "/edit", { method: "POST", body: JSON.stringify({ body: area.value }) });
      item.replaceWith(feedbackItem(data.feedback));
    } catch (failure) { error.textContent = failure.message; }
    finally { save.disabled = false; }
  });
  item.replaceChildren(form);
  area.focus();
}

async function deleteFeedback(id, button) {
  button.disabled = true;
  try {
    await api("/api/feedback-entries/" + id + "/delete", { method: "POST", body: "{}" });
    await loadFeedback(feedbackState.itemId);
  } catch (failure) {
    document.getElementById("feedback-error").textContent = failure.message;
    button.disabled = false;
  }
}

async function loadFeedback(itemId) {
  feedbackState.itemId = itemId;
  const list = document.getElementById("feedback-list");
  document.getElementById("feedback-error").textContent = "";
  document.getElementById("feedback-body").value = "";
  updateFeedbackCount();
  list.replaceChildren(feedbackElement("li", "feedback-empty", "Loading feedback…"));
  try {
    const data = await api("/api/feedback/" + itemId);
    if (feedbackState.itemId === itemId) renderFeedbackList(data.feedback);
  } catch (failure) {
    list.replaceChildren(feedbackElement("li", "feedback-empty", failure.message));
  }
}

function updateFeedbackCount() {
  const area = document.getElementById("feedback-body");
  document.getElementById("feedback-count").textContent = area.value.length + " / " + FEEDBACK_MAX;
}

async function postFeedback(event) {
  event.preventDefault();
  const area = document.getElementById("feedback-body");
  const error = document.getElementById("feedback-error");
  const button = event.submitter || event.currentTarget.querySelector('button[type="submit"]');
  error.textContent = "";
  if (area.value.trim().length < 2) { error.textContent = "Write at least 2 characters."; return; }
  button.disabled = true;
  try {
    await api("/api/feedback/" + feedbackState.itemId, { method: "POST", body: JSON.stringify({ body: area.value }) });
    await loadFeedback(feedbackState.itemId);
  } catch (failure) { error.textContent = failure.message; }
  finally { button.disabled = false; }
}

// Admin moderation list. Builds DOM nodes so comment text stays inert here too.
function renderModerationList(container, entries, onChange) {
  container.replaceChildren();
  if (!entries.length) {
    container.append(feedbackElement("p", "feedback-empty", "No learner feedback yet."));
    return;
  }
  for (const entry of entries) {
    const row = feedbackElement("article", "moderation-row" + (entry.status === "hidden" ? " is-hidden" : ""));
    const details = feedbackElement("div", "moderation-details");
    const meta = feedbackElement("div", "feedback-meta");
    meta.append(feedbackElement("strong", "", entry.author), feedbackElement("span", "", "on " + entry.item_title), feedbackElement("time", "", feedbackDate(entry.created_at)));
    details.append(meta, feedbackElement("p", "feedback-body", entry.body));
    if (entry.status === "hidden") details.append(feedbackElement("p", "helper", "Hidden by " + (entry.moderator || "an administrator") + " · " + feedbackDate(entry.moderated_at)));
    const button = feedbackElement("button", "button small " + (entry.status === "hidden" ? "secondary" : "danger"), entry.status === "hidden" ? "Restore" : "Hide");
    button.type = "button";
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const data = await api("/api/admin/feedback/" + entry.id + "/moderate", { method: "POST", body: JSON.stringify({ action: entry.status === "hidden" ? "restore" : "hide" }) });
        await onChange(data.message);
      } catch (failure) { toast(failure.message, true); button.disabled = false; }
    });
    row.append(details, button);
    container.append(row);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("feedback-form")?.addEventListener("submit", postFeedback);
  document.getElementById("feedback-body")?.addEventListener("input", updateFeedbackCount);
});
