"use strict";
// Administrator backup and recovery view (Student 4, T4).
// Backup names, labels and check messages come from the server, so they are
// placed on the page with textContent only.

function backupElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function backupSize(bytes) {
  if (typeof bytes !== "number") return "Size unknown";
  return bytes < 1024 * 1024 ? Math.max(1, Math.round(bytes / 1024)) + " KB" : (bytes / 1024 / 1024).toFixed(1) + " MB";
}

function backupWhen(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown time" : new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" }).format(date);
}

async function backupRequest(path, body) {
  const response = await fetch(path, { method: body === undefined ? "GET" : "POST", headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await response.json().catch(() => ({ ok: false, error: "The server response could not be read." }));
  if (!response.ok || data.ok === false) {
    const error = new Error(data.error || "Something went wrong. Please try again.");
    error.problems = data.problems || [];
    error.status = response.status;
    throw error;
  }
  return data;
}

function renderBackupProblems(container, problems) {
  container.replaceChildren();
  if (!problems.length) return;
  const list = backupElement("ul", "backup-problems");
  for (const problem of problems) list.append(backupElement("li", "", problem));
  container.append(list);
}

function backupRow(entry, hooks) {
  const row = backupElement("article", "backup-row" + (entry.ok ? "" : " backup-failed"));
  const details = backupElement("div", "backup-details");
  const title = backupElement("div", "backup-title");
  title.append(backupElement("strong", "", backupWhen(entry.created_at)));
  title.append(backupElement("span", "badge " + (entry.ok ? "success" : "danger"), entry.ok ? "Checks passed" : "Failed checks"));
  if (entry.label && entry.label !== "manual") title.append(backupElement("span", "badge neutral", entry.label));
  details.append(title);
  details.append(backupElement("p", "backup-name", entry.name));
  const counts = entry.row_counts || {};
  details.append(backupElement("p", "backup-meta", [backupSize(entry.size), (counts.users ?? "?") + " users", (counts.audit_events ?? "?") + " audit events", "by " + (entry.created_by || "unknown")].join(" · ")));
  const problems = backupElement("div", "backup-problem-box");
  renderBackupProblems(problems, entry.problems || []);
  details.append(problems);

  const actions = backupElement("div", "backup-actions");
  const verify = backupElement("button", "button secondary small", "Verify");
  verify.type = "button";
  verify.addEventListener("click", () => hooks.verify(entry, verify, problems, row));
  const restore = backupElement("button", "button danger small", "Restore…");
  restore.type = "button";
  restore.addEventListener("click", () => toggleRestoreForm(row, entry, hooks));
  actions.append(verify, restore);
  row.append(details, actions);
  return row;
}

function toggleRestoreForm(row, entry, hooks) {
  const existing = row.querySelector(".restore-form");
  if (existing) { existing.remove(); return; }
  const form = backupElement("form", "restore-form");
  const id = "restore-confirm-" + entry.name.replace(/[^a-z0-9]/gi, "");
  const label = backupElement("label", "", "Restoring replaces all current data and signs everyone out. A safety backup of the current data is taken first. Type the backup name to confirm.");
  label.htmlFor = id;
  const input = document.createElement("input");
  input.id = id; input.autocomplete = "off"; input.spellcheck = false; input.placeholder = entry.name;
  const submit = backupElement("button", "button danger small", "Restore this backup");
  submit.type = "submit";
  const error = backupElement("div", "inline-error");
  error.setAttribute("role", "alert");
  form.append(label, input, submit, error);
  form.addEventListener("submit", event => { event.preventDefault(); hooks.restore(entry, input.value.trim(), submit, error); });
  row.append(form);
  input.focus();
}

async function loadBackups(container, onRestored) {
  container.replaceChildren(backupElement("p", "muted backup-loading", "Loading backups…"));
  let data;
  try { data = await backupRequest("/api/admin/backups"); }
  catch (error) { container.replaceChildren(backupElement("p", "inline-error", error.message)); return; }
  const hooks = {
    async verify(entry, button, problemBox, row) {
      setLoading(button, true, "Checking…");
      try {
        const result = await backupRequest("/api/admin/backups/" + encodeURIComponent(entry.name) + "/verify", {});
        renderBackupProblems(problemBox, result.problems);
        row.classList.toggle("backup-failed", !result.valid);
        toast(result.valid ? "All integrity checks passed." : "This backup failed its integrity checks.", !result.valid);
      } catch (error) { toast(error.message, true); }
      finally { setLoading(button, false); }
    },
    async restore(entry, confirmText, button, errorBox) {
      errorBox.replaceChildren();
      setLoading(button, true, "Restoring…");
      try {
        const result = await backupRequest("/api/admin/backups/" + encodeURIComponent(entry.name) + "/restore", { confirm: confirmText });
        await onRestored(result.message);
      } catch (error) {
        const problems = backupElement("div");
        renderBackupProblems(problems, error.problems || []);
        errorBox.replaceChildren(backupElement("p", "", error.message), problems);
        toast(error.status === 409 ? "Restore refused: the backup failed its integrity checks." : error.message, true);
      } finally { setLoading(button, false); }
    }
  };
  container.replaceChildren();
  if (!data.backups.length) {
    container.append(backupElement("p", "muted backup-empty", "No backups yet. Create one before making large changes."));
    return;
  }
  for (const entry of data.backups) container.append(backupRow(entry, hooks));
}

async function createBackup(button, container, onRestored) {
  setLoading(button, true, "Backing up…");
  try {
    const data = await backupRequest("/api/admin/backups", {});
    toast(data.message);
    await loadBackups(container, onRestored);
  } catch (error) { toast(error.message, true); }
  finally { setLoading(button, false); }
}
