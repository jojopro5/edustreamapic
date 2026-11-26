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

const auditFilters = { event_type: "", outcome: "", correlation_id: "", user_id: "" };

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
    summary.textContent = data.events.length + (data.events.length === 1 ? " event" : " events") + (params.toString() ? " match these filters" + (auditFilters.user_id ? " for account " + auditFilters.user_id : "") : " (most recent 200)");
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
      chip.addEventListener("click", () => { auditFilters.correlation_id = event.correlation_id; auditFilters.event_type = ""; auditFilters.outcome = ""; auditFilters.user_id = ""; syncAuditForm(); loadAuditEvents(); });
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
    auditFilters.user_id = "";
    loadAuditEvents();
  });
  document.getElementById("audit-clear").addEventListener("click", () => {
    Object.keys(auditFilters).forEach(key => { auditFilters[key] = ""; });
    syncAuditForm();
    loadAuditEvents();
  });
  loadAuditEvents();
}

// Operations view: analytics summary and open issues.
function adminOperations() {
  setPage("Operations", "Administrator workspace");
  return hero("OPERATIONS", "Spot problems and trace them.", "Each open issue links to the audit events that show it. Fix the cause, then confirm the issue clears here.") +
    '<section class="panel"><div class="panel-header"><div><h2>Open issues</h2><p id="ops-issue-summary" role="status">Checking…</p></div><button class="button ghost small" type="button" id="ops-refresh">Refresh</button></div><div id="ops-issues"></div></section>' +
    '<div class="ops-grid"><section class="panel"><div class="panel-header"><div><h2>Subscriptions and payments</h2><p>Active plans now; payments in the last 30 days</p></div></div><div id="ops-billing"></div></section>' +
    '<section class="panel"><div class="panel-header"><div><h2>Denied requests</h2><p>Last 7 days, by event type</p></div></div><div id="ops-denied"></div></section></div>' +
    '<section class="panel ops-courses"><div class="panel-header"><div><h2>Course engagement</h2><p>Learners who recorded progress, average progress and finals passed</p></div></div><div id="ops-courses" class="table-wrap"></div></section>';
}

function opsTable(headers, rows) {
  const table = opsElement("table", "ops-table");
  const head = table.createTHead().insertRow();
  headers.forEach(([label, numeric]) => { const th = opsElement("th", numeric ? "num" : "", label); th.scope = "col"; head.append(th); });
  const body = table.createTBody();
  rows.forEach(row => {
    const tr = body.insertRow();
    row.forEach((value, index) => tr.append(opsElement("td", headers[index][1] ? "num" : "", value)));
  });
  return table;
}

async function loadOperations() {
  const summary = document.getElementById("ops-issue-summary");
  try {
    const data = await api("/api/admin/operations");
    const issues = document.getElementById("ops-issues");
    issues.replaceChildren();
    summary.textContent = data.issues.length ? data.issues.length + (data.issues.length === 1 ? " issue needs attention" : " issues need attention") : "No open issues";
    if (!data.issues.length) issues.append(opsElement("p", "ops-ok", "Everything looks healthy. Seeded problems and real ones appear here."));
    for (const issue of data.issues) {
      const row = opsElement("article", "ops-issue");
      const badge = opsElement("span", "badge " + (issue.severity === "high" ? "danger" : issue.severity === "medium" ? "warning" : "neutral"), issue.severity.charAt(0).toUpperCase() + issue.severity.slice(1));
      const body = opsElement("div");
      body.append(opsElement("strong", "", issue.title), opsElement("p", "", issue.detail), opsElement("p", "", "Next step: " + issue.action));
      const trace = opsElement("button", "button ghost small", "View related events");
      trace.type = "button";
      trace.addEventListener("click", () => {
        Object.keys(auditFilters).forEach(key => { auditFilters[key] = ""; });
        auditFilters.event_type = issue.event_type || "";
        auditFilters.user_id = issue.user_id ? String(issue.user_id) : "";
        if (issue.user_id) auditFilters.outcome = "denied";
        changeView("audit");
      });
      body.append(trace);
      row.append(badge, body);
      issues.append(row);
    }
    const billing = document.getElementById("ops-billing");
    const payments = data.analytics.payments_30_days;
    billing.replaceChildren(
      opsTable([["Plan"], ["Active", true]], data.analytics.plans.map(plan => [plan.plan, plan.active_subscriptions])),
      opsTable([["Payments"], ["Count", true], ["Amount (AUD)", true]], ["paid", "failed", "pending", "refunded"].filter(status => payments[status]).map(status => [status.charAt(0).toUpperCase() + status.slice(1), payments[status].count, payments[status].amount.toFixed(2)]))
    );
    const denied = document.getElementById("ops-denied");
    denied.replaceChildren(data.analytics.denied_7_days.length ? opsTable([["Event"], ["Count", true]], data.analytics.denied_7_days.map(row => [opsLabel(row.event_type), row.count])) : opsElement("p", "ops-ok", "No denied requests."));
    document.getElementById("ops-courses").replaceChildren(opsTable([["Course"], ["Learners", true], ["Average progress", true], ["Finals passed", true]], data.analytics.courses.map(course => [course.title, course.learners_started, course.average_progress === null ? "–" : course.average_progress + "%", course.finals_passed])));
  } catch (error) { summary.textContent = error.message; }
}

function bindOperations() {
  document.getElementById("ops-refresh").addEventListener("click", loadOperations);
  loadOperations();
}

// Published items with a takedown action, shown under the approval queue.
function renderPublishedList(container, items) {
  container.replaceChildren();
  const header = opsElement("div", "panel-header");
  const heading = opsElement("div");
  heading.append(opsElement("h2", "", "Published resources"), opsElement("p", "", "Take down an item that should no longer be shown. A reason is required and recorded."));
  header.append(heading);
  container.append(header);
  if (!items.length) { container.append(opsElement("p", "ops-ok", "Nothing is published yet.")); return; }
  for (const item of items) {
    const row = opsElement("form", "ops-issue takedown-row");
    const details = opsElement("div");
    details.append(opsElement("strong", "", item.title), opsElement("p", "", item.category + " · by " + item.educator_name));
    const label = opsElement("label", "sr-only", "Reason for taking down " + item.title);
    const input = document.createElement("input");
    input.id = "takedown-" + item.id;
    label.htmlFor = input.id;
    input.maxLength = 300;
    input.placeholder = "Reason (required)";
    const button = opsElement("button", "button danger small", "Take down");
    button.type = "submit";
    const controls = opsElement("div", "takedown-controls");
    controls.append(label, input, button);
    details.append(controls);
    row.append(opsElement("span", "badge success", "Live"), details);
    row.addEventListener("submit", async event => {
      event.preventDefault();
      button.disabled = true;
      try {
        const data = await api("/api/admin/content/" + item.id + "/takedown", { method: "POST", body: JSON.stringify({ reason: input.value }) });
        await loadDashboard(data.message);
      } catch (error) { toast(error.message, true); button.disabled = false; }
    });
    container.append(row);
  }
}
