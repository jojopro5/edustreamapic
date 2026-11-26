"use strict";
// Educator course files. The server is the real check (type, signature, size,
// ownership, pending status); these client checks only give faster feedback.

const UPLOAD_MAX_BYTES = 5 * 1024 * 1024;
const UPLOAD_TYPES = ["pdf", "png", "txt"];

function checkAttachment(file) {
  const extension = (file.name.split(".").pop() || "").toLowerCase();
  if (!file.name.includes(".") || !UPLOAD_TYPES.includes(extension)) return "Only PDF, PNG and plain text (.txt) files can be uploaded.";
  if (file.size > UPLOAD_MAX_BYTES) return "Files must be 5 MB or smaller.";
  return "";
}

async function uploadAttachment(itemId, file) {
  const response = await fetch("/api/content/" + itemId + "/attachment", {
    method: "POST",
    headers: { "Content-Type": "application/octet-stream", "X-File-Name": encodeURIComponent(file.name) },
    body: file
  });
  const data = await response.json().catch(() => ({ ok: false, error: "The upload response could not be read." }));
  if (!response.ok || data.ok === false) throw new Error(data.error || "The file could not be uploaded.");
  return data.attachment;
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + " KB";
  return (bytes / 1024 / 1024).toFixed(1) + " MB";
}

function attachmentLink(item) {
  if (!item.attachment) return "";
  return '<a class="attachment-link" href="/api/content/' + Number(item.id) + '/attachment" download>' + escapeHtml(item.attachment.name) + ' · ' + escapeHtml(item.attachment.type.toUpperCase()) + ', ' + formatFileSize(item.attachment.size_bytes) + '</a>';
}

function showLessonAttachment(item) {
  const wrapper = document.getElementById("dialog-attachment");
  const link = document.getElementById("dialog-attachment-link");
  if (!wrapper || !link) return;
  wrapper.classList.toggle("hidden", !item.attachment);
  if (!item.attachment) return;
  link.href = "/api/content/" + Number(item.id) + "/attachment";
  link.textContent = "Download course file: " + item.attachment.name + " (" + formatFileSize(item.attachment.size_bytes) + ")";
}

// Adds the optional file field to the Content Studio form, above the description.
function addAttachmentField(form) {
  if (form.querySelector("#content-file")) return;
  const wrapper = document.createElement("div");
  wrapper.className = "span-2";
  wrapper.innerHTML = '<label for="content-file">Course file <span class="muted">(optional)</span></label><input id="content-file" name="attachment" type="file" accept=".pdf,.png,.txt,application/pdf,image/png,text/plain" aria-describedby="file-helper"><p class="helper" id="file-helper">PDF, PNG or plain text, up to 5 MB. Use your own or synthetic material only. The file can be replaced until an administrator reviews the item.</p>';
  const description = form.querySelector("#content-description")?.closest(".span-2");
  form.insertBefore(wrapper, description || form.querySelector(".form-actions"));
}
