"use strict";
// Administrator audit search and operations view (Student 4, T4).
// Event details and names come from the database, so they are placed on the
// page with textContent only.

function opsElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined && text !== null) element.textContent = String(text);
  return element;
}

function opsWhen(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit", second: "2-digit" }).format(date);
}

function opsLabel(value) {
  return String(value || "").replace(/_/g, " ").replace(/^./, char => char.toUpperCase());
}

const auditFilters = { event_type: "", outcome: "", correlation_id: "" };

function adminAuditSearch() {
  setPage("Audit reports", "Administrator workspace");
  return hero("PLATFORM ACTIVITY", "A clear record of what happened.", "Every event records who acted, what happened, the outcome and a correlation ID that links all events from the same request.") +
    '<section class="panel"><form id="audit-filters" class="audit-filters panel-body" aria-label="Filter audit events">' +
    '<div><label for="audit-type">Event type</label><select id="audit-type" name="event_type"><option value="">All events</option></select></div>' +
    '<div><label for="audit-outcome">Outcome</label><select id="audit-outcome" name="outcome"><option value="">Any outcome</option><option value="success">Success</option><option value="failure">Failure</option><option value="denied">Denied</option></select></div>' +
    '<div><label for="audit-correlation">Correlation ID</label><input id="audit-correlation" name="correlation_id" maxlength="64" autocomplete="off" placeholder="e.g. 3f9c2a7d41b0e6a8"></div>' +
    '<div class="audit-filter-actions"><button class="button primary small" type="submit">Apply</button><button class="button ghost small" type="button" id="audit-clear">Clear</button></div>' +
    '</form><div class="panel-header audit-results-header"><div><h2>Event log</h2><p id="audit-summary" role="status">Loading events…</p></div></div><div id="audit-results" class="audit-list"></div></section>';
}

async function loadAuditEvents() {
  const params = new URLSearchParams(Object.entries(auditFilters).filter(([, value]) => value));
  const summary = document.getElementById("audit-summary");
  try {
    const data = await api("/api/admin/audit" + (params.toString() ? "?" + params : ""));
    const typeSelect = document.getElementById("audit-type");
    if (typeSelect && typeSelect.options.length === 1) {
      for (const type of data.event_types) typeSelect.append(new Option(opsLabel(type), type));
    }
    if (typeSelect) typeSelect.value = auditFilters.event_type;
    renderAuditEvents(data.events);
    summary.textContent = data.events.length + (data.events.length === 1 ? " event" : " events") + (params.toString() ? " match these filters" : " (most recent 200)");
  } catch (error) {
    summary.textContent = error.message;
  }
}

function renderAuditEvents(events) {
  const list = document.getElementById("audit-results");
  list.replaceChildren();
  if (!events.length) {
    list.append(opsElement("p", "feedback-empty audit-empty", "No events match these filters."));
    return;
  }
  for (const event of events) {
    const row = opsElement("div", "audit-row audit-row-" + event.outcome);
    const badge = opsElement("span", "badge " + (event.outcome === "success" ? "success" : event.outcome === "denied" ? "danger" : "warning"), opsLabel(event.outcome));
    const main = opsElement("div", "audit-main");
    main.append(opsElement("strong", "", opsLabel(event.event_type)), opsElement("p", "", event.details));
    if (event.correlation_id) {
      const chip = opsElement("button", "correlation-chip", "Request " + event.correlation_id);
      chip.type = "button";
      chip.title = "Show every event from this request";
      chip.addEventListener("click", () => { auditFilters.correlation_id = event.correlation_id; auditFilters.event_type = ""; auditFilters.outcome = ""; syncAuditForm(); loadAuditEvents(); });
      main.append(chip);
    }
    const time = opsElement("time", "", opsWhen(event.created_at));
    row.append(badge, main, opsElement("span", "audit-user", event.user_name), time);
    list.append(row);
  }
}

function syncAuditForm() {
  const form = document.getElementById("audit-filters");
  if (!form) return;
  form.elements.event_type.value = auditFilters.event_type;
  form.elements.outcome.value = auditFilters.outcome;
  form.elements.correlation_id.value = auditFilters.correlation_id;
}

function bindAuditSearch() {
  const form = document.getElementById("audit-filters");
  if (!form) return;
  syncAuditForm();
  form.addEventListener("submit", event => {
    event.preventDefault();
    auditFilters.event_type = form.elements.event_type.value;
    auditFilters.outcome = form.elements.outcome.value;
    auditFilters.correlation_id = form.elements.correlation_id.value.trim();
    loadAuditEvents();
  });
  document.getElementById("audit-clear").addEventListener("click", () => {
    Object.keys(auditFilters).forEach(key => { auditFilters[key] = ""; });
    syncAuditForm();
    loadAuditEvents();
  });
  loadAuditEvents();
}
