const state = {
  user: null, dashboard: null, view: "overview", activeItem: null, subjectId: null,
  filter: "all", accessFilter: "all", learningFilter: "all", query: "", sort: "default", signingIn: false
};
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
const formatMoney = value => new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD" }).format(value);
const formatDate = value => {
  if (!value) return "—";
  const date = new Date(/^\d{4}-\d{2}-\d{2}$/.test(value) ? value + "T12:00:00" : value);
  return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "short", year: "numeric" }).format(date);
};
const formatTime = value => new Intl.DateTimeFormat("en-AU", { hour: "numeric", minute: "2-digit" }).format(new Date(value));
const titleCase = value => String(value || "").replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());

const ICONS = {
  home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
  book: '<path d="M12 5v16M3 4h4a7 7 0 0 1 5 2 7 7 0 0 1 5-2h4v15h-4a7 7 0 0 0-5 2 7 7 0 0 0-5-2H3Z"/>',
  library: '<path d="M4 3h4v18H4zM11 3h4v18h-4zM18 4l4 16-3 1-4-16Z"/>',
  layers: '<path d="m12 3 10 5-10 5L2 8Zm-10 9 10 5 10-5M2 16l10 5 10-5"/>',
  check: '<path d="m5 12 4 4 10-10"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  trend: '<path d="m3 17 6-6 4 4 8-10M15 5h6v6"/>',
  shield: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
  card: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h4"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  play: '<path d="m9 5 11 7-11 7Z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M22 21v-2a4 4 0 0 0-3-3.87"/><circle cx="9" cy="7" r="4"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  audit: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h6M9 11h6M9 15h3"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
  code: '<path d="m7 7-5 5 5 5m10-10 5 5-5 5M14 4l-4 16"/>',
  logout: '<path d="M9 3H4v18h5M10 12h11m-4-4 4 4-4 4"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  award: '<circle cx="12" cy="8" r="5"/><path d="m8 12-2 9 6-3 6 3-2-9"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-2l2 2M18 17a7 7 0 0 1-12 2l-2-2"/>'
};
function icon(name, className = "") {
  return '<svg class="ui-icon ' + className + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICONS[name] || ICONS.book) + '</svg>';
}
function courseTheme(item) {
  const category = String(item.category).toLowerCase();
  if (category.includes("data") || category.includes("sql")) return { colour: "violet", icon: "database", label: "DATA & DATABASES" };
  if (category.includes("develop") || category.includes("web")) return { colour: "teal", icon: "code", label: "WEB DEVELOPMENT" };
  return { colour: "blue", icon: "shield", label: titleCase(item.category).toUpperCase() };
}
async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
  const data = await response.json().catch(() => ({ ok: false, error: "The server response could not be read. Please try again." }));
  if (!response.ok || data.ok === false) throw new Error(data.error || data.message || "Something went wrong. Please try again.");
  return data;
}
function toast(message, error = false) {
  const element = $("#toast");
  element.innerHTML = icon(error ? "close" : "check") + '<span>' + escapeHtml(message) + '</span>';
  element.className = "toast show" + (error ? " error" : "");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { element.className = "toast"; }, 4000);
}
function setLoading(button, loading, label = "Please wait…") {
  if (!button) return;
  if (loading) {
    if (!button.disabled) button.dataset.original = button.innerHTML;
    button.innerHTML = '<span class="spinner" aria-hidden="true"></span>' + escapeHtml(label);
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  } else {
    button.innerHTML = button.dataset.original || button.innerHTML;
    button.disabled = false;
    button.removeAttribute("aria-busy");
  }
}
const NAV = {
  learner: [["overview", "home", "Overview"], ["learning", "book", "My learning"], ["library", "library", "Explore courses"], ["subscription", "card", "Subscription & billing"]],
  educator: [["overview", "home", "Overview"], ["studio", "plus", "Content studio"], ["content", "layers", "My content"]],
  admin: [["overview", "home", "Overview"], ["approvals", "shield", "Approval queue"], ["audit", "audit", "Audit reports"]]
};
function setupShell() {
  $("#login-screen").classList.add("hidden");
  $("#app-shell").classList.remove("hidden");
  $("#user-name").textContent = state.user.full_name;
  $("#user-role").textContent = state.user.role;
  $("#user-avatar").textContent = state.user.full_name.split(/\s+/).slice(0, 2).map(part => part[0]).join("");
  $("#workspace-label").textContent = state.user.role === "learner" ? "YOUR LEARNING SPACE" : "WORKSPACE";
  $("#menu-button").innerHTML = icon("menu");
  $("#logout-button").innerHTML = icon("logout") + "<span>Sign out</span>";
  renderNav(); renderSidebar(); syncMenuAccessibility();
}
function renderNav() {
  const nav = $("#main-nav");
  const activeView = state.view === "subject" ? "library" : state.view;
  nav.innerHTML = NAV[state.user.role].map(([view, glyph, label]) =>
    '<button type="button" class="nav-button' + (activeView === view ? ' active' : '') + '" data-view="' + view + '"' + (activeView === view ? ' aria-current="page"' : '') + '>' + icon(glyph) + '<span>' + label + '</span>' + (view === "approvals" && state.dashboard.stats.pending_content ? '<span class="nav-count">' + state.dashboard.stats.pending_content + '</span>' : '') + '</button>'
  ).join("");
  $$("[data-view]", nav).forEach(button => button.addEventListener("click", () => changeView(button.dataset.view)));
}
function renderSidebar() {
  const d = state.dashboard;
  const learner = state.user.role === "learner";
  const heading = learner ? (d.subscription?.plan_name || "Choose your") + " plan" : state.user.role === "educator" ? "Ready to share?" : "Keep content safe";
  const body = learner ? d.stats.available + " courses included. Make room for your next skill." : state.user.role === "educator" ? "Create a resource and send it for review." : d.stats.pending_content + " resources are waiting for your review.";
  const view = learner ? "subscription" : state.user.role === "educator" ? "studio" : "approvals";
  $("#sidebar-support").innerHTML = icon(learner ? "layers" : "shield", "sidebar-card-icon") + '<span class="sidebar-card-label">' + (learner ? "YOUR SUBSCRIPTION" : "NEXT STEP") + '</span><strong>' + escapeHtml(heading) + '</strong><p>' + escapeHtml(body) + '</p><button class="sidebar-cta" type="button">' + (learner ? "Manage plan" : "Open workspace") + icon("chevron") + '</button>';
  $("#sidebar-support button").addEventListener("click", () => changeView(view));
}
function changeView(view) {
  if (!NAV[state.user.role].some(([name]) => name === view)) return;
  state.view = view; renderNav(); render(); closeMenu();
  $("#app-content").focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: "instant" });
}
async function loadDashboard(message) {
  const data = await api("/api/dashboard");
  state.dashboard = data; state.user = data.user;
  setupShell(); render();
  if (message) toast(message);
}
function hero(kicker, title, description, action = "") {
  return '<section class="hero"><div><span class="eyebrow">' + escapeHtml(kicker) + '</span><h1>' + escapeHtml(title) + '</h1><p>' + escapeHtml(description) + '</p></div>' + (action || '<span class="date-chip">' + icon("clock") + new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "short", year: "numeric" }).format(new Date()) + '</span>') + '</section>';
}
function statCard(label, value, detail, colour = "blue", glyph = "book") {
  return '<article class="stat-card accent-' + colour + '"><span class="stat-symbol">' + icon(glyph) + '</span><div class="stat-content"><span class="stat-label">' + escapeHtml(label) + '</span><strong class="stat-value">' + escapeHtml(value) + '</strong><small>' + escapeHtml(detail) + '</small></div></article>';
}
function progressClass(value) { return "progress-" + Math.max(0, Math.min(100, Math.round(Number(value || 0) / 5) * 5)); }
function progressBar(value, label = "Learning progress") {
  return '<div class="progress-line" role="progressbar" aria-label="' + escapeHtml(label) + '" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + (Number(value) || 0) + '"><span class="' + progressClass(value) + '"></span></div>';
}
function statusBadge(status) {
  const type = { approved: "success", pending: "warning", rejected: "danger", active: "success", paid: "success" }[status] || "neutral";
  return '<span class="badge ' + type + '"><span class="badge-dot" aria-hidden="true"></span>' + escapeHtml(titleCase(status)) + '</span>';
}
function setPage(title, kicker = "EDUSTREAM") {
  $("#page-title").textContent = title; $("#page-kicker").textContent = kicker;
  document.title = title + " | EduStream";
}
function render() {
  const views = {
    learner: { overview: learnerOverview, learning: learnerLearning, library: learnerLibrary, subject: learnerSubject, subscription: learnerSubscription },
    educator: { overview: educatorOverview, studio: educatorStudio, content: educatorContent },
    admin: { overview: adminOverview, approvals: adminApprovals, audit: adminAudit }
  };
  $("#app-content").innerHTML = (views[state.user.role][state.view] || views[state.user.role].overview)();
  bindViewEvents();
}
function learnerOverview() {
  setPage("Overview", "Learner workspace");
  const d = state.dashboard;
  const entitled = d.items.filter(item => item.entitled);
  const nextItem = entitled.find(item => item.progress_percent > 0 && item.progress_percent < 100) || entitled.find(item => item.progress_percent < 100) || entitled[0];
  const percentage = Math.max(0, Math.min(100, d.stats.average_progress));
  const ringLength = 2 * Math.PI * 48;
  return hero("A LITTLE PROGRESS, EVERY DAY", "Welcome back, " + state.user.full_name.split(" ")[0] + ".", "Your next skill is waiting. Pick up a course or find something new to learn.", '<button class="button primary" data-go="library">' + icon("library") + 'Explore courses</button>') +
    '<section class="stats-grid" aria-label="Learning overview">' +
    statCard("Courses included", d.stats.available, "In your current plan", "blue", "book") +
    statCard("In progress", entitled.filter(item => item.progress_percent > 0 && item.progress_percent < 100).length, "Keep your momentum", "violet", "play") +
    statCard("Completed", d.stats.completed, "Skills you've worked on", "teal", "award") +
    statCard("Overall progress", percentage + "%", "Across included courses", "orange", "trend") + '</section>' +
    '<section class="dashboard-focus">' +
    (nextItem ? '<article class="spotlight"><div class="spotlight-content"><span class="spotlight-label">' + icon("play") + 'CONTINUE YOUR JOURNEY</span><span class="spotlight-category">' + escapeHtml(nextItem.category) + ' · ' + nextItem.duration_minutes + ' min</span><h2>' + escapeHtml(nextItem.title) + '</h2><p>' + escapeHtml(nextItem.description) + '</p><div class="spotlight-progress"><div><span>Your progress</span><strong>' + nextItem.progress_percent + '%</strong></div>' + progressBar(nextItem.progress_percent) + '</div><button class="button white" data-open-item="' + nextItem.id + '">' + icon("play") + (nextItem.progress_percent > 0 ? 'Continue learning' : 'Start learning') + '</button></div><div class="spotlight-symbol" aria-hidden="true">' + icon(courseTheme(nextItem).icon) + '</div><span class="spotlight-watermark" aria-hidden="true">LEARN</span></article>' : '<article class="spotlight"><div class="spotlight-content"><span class="spotlight-label">YOUR NEXT STEP</span><h2>Make space for learning.</h2><p>Choose a subscription to start exploring approved courses.</p><button class="button white" data-go="subscription">View plans</button></div></article>') +
    '<article class="panel learning-summary"><div class="summary-heading"><span class="eyebrow">YOUR LEARNING</span><h2>A little closer to your goals</h2></div><div class="progress-ring"><svg viewBox="0 0 120 120" role="img" aria-label="Overall learning progress ' + percentage + ' percent"><circle class="ring-track" cx="60" cy="60" r="48"/><circle class="ring-value" cx="60" cy="60" r="48" stroke-dasharray="' + (percentage / 100 * ringLength) + ' ' + ringLength + '"/></svg><span><strong>' + percentage + '%</strong><small>overall progress</small></span></div><div class="summary-detail"><span>' + icon("award") + 'Courses completed</span><strong>' + d.stats.completed + ' / ' + entitled.length + '</strong></div><button class="button ghost full" data-go="learning">View my learning</button></article></section>' +
    '<section class="courses-section"><div class="section-title"><div><span class="eyebrow">CURATED FOR YOUR NEXT STEP</span><h2>Your learning library</h2></div><button class="text-link" data-go="library">Browse all courses ' + icon("chevron") + '</button></div><div class="course-grid">' + (d.items.slice(0, 3).map(courseCard).join("") || emptyState("Your library is getting ready", "New approved learning items will appear here.", "book")) + '</div></section>';
}
function courseCard(item) {
  const theme = courseTheme(item);
  return '<article class="course-card"><div class="course-cover cover-' + theme.colour + '"><span class="cover-category">' + escapeHtml(theme.label) + '</span><span class="cover-symbol">' + icon(theme.icon) + '</span><span class="cover-type">' + icon(item.content_type === "video" ? "play" : "book") + escapeHtml(titleCase(item.content_type)) + '</span></div><div class="course-body"><div class="course-meta"><span>' + icon("clock") + item.duration_minutes + ' min</span><span class="badge ' + (item.entitled ? 'success' : 'neutral') + '">' + icon(item.entitled ? "check" : "lock") + (item.entitled ? 'Included' : 'Locked') + '</span></div><h3>' + escapeHtml(item.title) + '</h3><p>' + escapeHtml(item.description) + '</p><div class="course-progress-label"><span>' + (item.entitled ? 'Your progress' : 'Available with an upgrade') + '</span><strong>' + (item.entitled ? item.progress_percent + '%' : icon("lock")) + '</strong></div>' + progressBar(item.entitled ? item.progress_percent : 0) + '<button class="text-link course-guide-link" data-subject-id="' + item.id + '">' + icon("book") + 'Why learn this topic?' + icon("chevron") + '</button><div class="course-footer">' + (item.entitled ? '<button class="button ' + (item.progress_percent === 100 ? 'secondary' : 'primary') + ' full" data-open-item="' + item.id + '">' + icon(item.progress_percent === 100 ? "check" : "play") + (item.progress_percent === 100 ? 'Review course' : item.progress_percent > 0 ? 'Continue learning' : 'Start learning') + '</button>' : '<button class="button ghost full" data-go="subscription">' + icon("lock") + 'Explore subscription plans</button>') + '</div></div></article>';
}
function filteredItems() {
  const query = state.query.trim().toLowerCase();
  const items = state.dashboard.items.filter(item =>
    (state.filter === "all" || item.category === state.filter) &&
    (state.accessFilter === "all" || (state.accessFilter === "included" ? item.entitled : !item.entitled)) &&
    (!query || (item.title + " " + item.category + " " + item.description).toLowerCase().includes(query))
  );
  if (state.sort === "title") items.sort((a, b) => a.title.localeCompare(b.title));
  if (state.sort === "duration") items.sort((a, b) => a.duration_minutes - b.duration_minutes);
  return items;
}
function showSubject(itemId) {
  if (!state.dashboard.items.some(item => item.id === itemId)) return;
  state.subjectId = itemId; state.view = "subject";
  renderNav(); render(); closeMenu();
  $("#app-content").focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: "instant" });
}
function videoPreview(video) {
  const label = video.thumbnail || video.source ? 'Watch ' + video.title + ' on YouTube' : 'Find videos on YouTube';
  return '<a class="video-preview' + (video.thumbnail ? '' : ' thumbnail-unavailable') + '" href="' + escapeHtml(video.url) + '" target="_blank" rel="noopener noreferrer" aria-label="' + escapeHtml(label) + ' — opens in a new tab">' +
    (video.thumbnail ? '<img class="video-thumbnail-image" src="' + escapeHtml(video.thumbnail) + '" width="1280" height="720" alt="" loading="lazy" decoding="async">' : '') +
    '<span class="thumbnail-placeholder" aria-hidden="true">' + icon("play") + '<span>' + (video.thumbnail ? 'YouTube video' : 'Explore topic videos') + '</span></span><span class="video-provider" aria-hidden="true">YouTube</span><span class="video-play-overlay" aria-hidden="true">' + icon("play") + '</span></a>';
}
function topicVideos(guide) {
  const seen = new Set();
  return [guide.video, ...(guide.relatedVideos || [])].filter(video => {
    if (!video?.url || seen.has(video.url)) return false;
    seen.add(video.url);
    return true;
  });
}
function videoResourceCard(video, related = false) {
  const headingTag = related ? "h3" : "h2";
  const isVideo = Boolean(video.thumbnail || video.source);
  const label = isVideo ? "Watch on YouTube" : "Find videos on YouTube";
  return '<article class="panel video-resource' + (related ? ' video-resource--related' : '') + '">' + videoPreview(video) +
    '<div class="panel-body"><div class="video-card-label"><span class="eyebrow">' + (related ? 'ANOTHER WAY TO LEARN' : isVideo ? 'RECOMMENDED YOUTUBE RESOURCE' : 'EXPLORE THIS TOPIC') + '</span>' +
    (video.level ? '<span class="badge neutral">' + escapeHtml(video.level) + '</span>' : '') + '</div><' + headingTag + '>' + escapeHtml(video.title) + '</' + headingTag +
    '><p class="video-creator">' + escapeHtml(video.creator) + '</p><p class="video-reason">' + escapeHtml(video.topic) +
    '</p><a class="button video-button full" href="' + escapeHtml(video.url) + '" target="_blank" rel="noopener noreferrer">' + icon("play") + label +
    '<span class="sr-only"> — opens in a new tab</span></a><p class="resource-disclosure">External resource. Opens YouTube in a new tab.</p></div></article>';
}
function relatedVideoSection(videos) {
  if (videos.length < 2) return "";
  const related = videos.slice(1);
  return '<section class="related-video-section" aria-labelledby="related-videos-title"><div class="section-title"><div><span class="eyebrow">EXPAND YOUR UNDERSTANDING</span><h2 id="related-videos-title">More videos for this topic</h2><p>Try a different explanation or go deeper into a skill.</p></div><span class="badge info">' + related.length + ' more ' + (related.length === 1 ? 'video' : 'videos') +
    '</span></div><div class="related-video-grid">' + related.map(video => videoResourceCard(video, true)).join("") + '</div></section>';
}
function learnerSubject() {
  const item = state.dashboard.items.find(item => item.id === state.subjectId);
  if (!item) return learnerLibrary();
  setPage("Course guide", "Learner workspace");
  const theme = courseTheme(item);
  const guide = getCourseGuide(item);
  const videos = topicVideos(guide);
  const videoCount = videos.filter(video => video.thumbnail || video.source).length;
  return '<button class="text-link back-link" data-go="library">' + icon("chevron") + 'Back to courses</button>' +
    '<section class="subject-intro cover-' + theme.colour + '"><div><span class="eyebrow">' + escapeHtml(item.category) + ' · COURSE GUIDE</span><h1>' + escapeHtml(item.title) + '</h1><p>' + escapeHtml(guide.introduction) + '</p><div class="subject-meta"><span>' + icon("clock") + item.duration_minutes + ' min</span><span>' + icon("book") + titleCase(item.content_type) + '</span><span>' + icon(item.entitled ? "check" : "lock") + (item.entitled ? 'Included in your plan' : 'Subscription required for protected content') + '</span><span>' + icon("play") + (videoCount ? videoCount + ' YouTube ' + (videoCount === 1 ? 'video' : 'videos') : 'YouTube topic search') + '</span></div></div><span class="subject-symbol" aria-hidden="true">' + icon(theme.icon) + '</span></section>' +
    '<section class="subject-layout"><div class="subject-main"><article class="panel subject-why"><div class="panel-body"><span class="eyebrow">START WITH THE WHY</span><h2>Why learn this topic?</h2><p>' + escapeHtml(guide.why) + '</p><div class="practical-use">' + icon("trend") + '<div><h3>Where you will use it</h3><p>' + escapeHtml(guide.application) + '</p></div></div></div></article><article class="panel"><div class="panel-body"><span class="eyebrow">BUILD YOUR UNDERSTANDING</span><h2>What you can learn</h2><ul class="outcome-list">' + guide.skills.map(skill => '<li><span>' + icon("check") + '</span>' + escapeHtml(skill) + '</li>').join("") + '</ul></div></article><article class="panel"><div class="panel-body"><span class="eyebrow">CONNECT IT TO EDUSTREAM</span><h2>Real examples from this project</h2><ol class="example-list">' + guide.examples.map(example => '<li>' + escapeHtml(example) + '</li>').join("") + '</ol></div></article></div>' +
    '<aside class="subject-aside">' + videoResourceCard(videos[0]) + '<article class="panel subject-access"><div class="panel-body"><span class="eyebrow">KEEP EXPLORING</span><h2>Ready to put it into practice?</h2><p>' + (item.entitled ? 'Your plan includes this learning item. Open it to record your progress.' : 'You can read this guide and watch the external resource. Choose a plan to access the protected learning item.') + '</p>' + (item.entitled ? '<button class="button primary full" data-open-item="' + item.id + '">' + icon("play") + 'Open learning item</button>' : '<button class="button primary full" data-go="subscription">View subscription plans</button>') + '</div></article></aside></section>' + relatedVideoSection(videos);
}
function learnerLibrary() {
  setPage("Explore courses", "Learner workspace");
  const categories = ["all", ...new Set(state.dashboard.items.map(item => item.category))];
  return hero("FIND YOUR NEXT SKILL", "A world of learning, in one place.", "Explore approved courses in cybersecurity, data, and web development.") +
    '<section class="library-controls" aria-label="Find a course"><div class="search-box">' + icon("search") + '<label class="sr-only" for="course-search">Search courses</label><input id="course-search" type="search" value="' + escapeHtml(state.query) + '" placeholder="Search by course, topic, or skill" autocomplete="off"><button id="clear-search" class="icon-button ' + (state.query ? '' : 'hidden') + '" type="button" aria-label="Clear search">' + icon("close") + '</button></div><div class="select-control"><label for="course-access">Access</label><select id="course-access"><option value="all"' + (state.accessFilter === "all" ? ' selected' : '') + '>All courses</option><option value="included"' + (state.accessFilter === "included" ? ' selected' : '') + '>Included in my plan</option><option value="locked"' + (state.accessFilter === "locked" ? ' selected' : '') + '>Locked courses</option></select></div><div class="select-control"><label for="course-sort">Sort by</label><select id="course-sort"><option value="default"' + (state.sort === "default" ? ' selected' : '') + '>Recommended</option><option value="title"' + (state.sort === "title" ? ' selected' : '') + '>Course name</option><option value="duration"' + (state.sort === "duration" ? ' selected' : '') + '>Shortest first</option></select></div></section>' +
    '<div class="toolbar"><div class="filter-group" aria-label="Course categories">' + categories.map(category => '<button class="filter' + (state.filter === category ? ' active' : '') + '" aria-pressed="' + (state.filter === category) + '" data-filter="' + escapeHtml(category) + '">' + escapeHtml(category === "all" ? "All topics" : category) + '</button>').join("") + '</div><span id="results-count" class="results-count" role="status"></span></div><section id="course-results" class="course-grid" aria-label="Course results">' + libraryResults() + '</section>';
}
function libraryResults() {
  const items = filteredItems();
  return items.length ? items.map(courseCard).join("") : '<div class="library-empty">' + emptyState("No courses found", "Try a different search or reset your filters.", "search") + '<button class="button secondary" data-reset-filters>Reset filters</button></div>';
}
function updateLibraryResults() {
  $("#course-results").innerHTML = libraryResults();
  $("#results-count").textContent = filteredItems().length + (filteredItems().length === 1 ? " course" : " courses");
  $("#clear-search").classList.toggle("hidden", !state.query);
  bindCourseEvents($("#course-results"));
}
function learnerLearning() {
  setPage("My learning", "Learner workspace");
  const items = state.dashboard.items.filter(item => item.entitled && (state.learningFilter === "all" || (state.learningFilter === "completed" ? item.progress_percent === 100 : item.progress_percent > 0 && item.progress_percent < 100)));
  return hero("YOUR PERSONAL LEARNING SPACE", "Keep your momentum.", "All your included courses and progress, ready when you are.", '<button class="button primary" data-go="library">' + icon("plus") + 'Find a new course</button>') + '<div class="toolbar"><div class="filter-group">' + [["all", "All my courses"], ["progress", "In progress"], ["completed", "Completed"]].map(([value, text]) => '<button class="filter ' + (state.learningFilter === value ? 'active' : '') + '" aria-pressed="' + (state.learningFilter === value) + '" data-learning-filter="' + value + '">' + text + '</button>').join("") + '</div><span class="results-count">' + items.length + ' courses</span></div><section class="course-grid">' + (items.length ? items.map(courseCard).join("") : '<div class="library-empty">' + emptyState(state.learningFilter === "completed" ? "Your next milestone is ahead" : "Ready for your next course?", state.learningFilter === "completed" ? "Finish an included course and it will appear here." : "Start one of your included courses to build your progress.", "book") + '<button class="button secondary" data-go="library">Explore courses</button></div>') + '</section>';
}
function learnerSubscription() {
  setPage("Subscription & billing", "Learner workspace");
  const d = state.dashboard;
  const currentPlanId = d.subscription?.plan_id;
  return hero("ACCESS THAT WORKS FOR YOU", "Your plan. Your next possibility.", "Manage your subscription and review your billing records.") +
    '<div class="subscription-summary"><div class="subscription-summary-icon">' + icon("card") + '</div><div><span class="eyebrow">CURRENT SUBSCRIPTION</span><h2>' + escapeHtml(d.subscription?.plan_name || "No active plan") + '</h2></div><div class="subscription-detail"><span>Access ends</span><strong>' + formatDate(d.subscription?.end_date) + '</strong></div><div class="subscription-detail"><span>Courses included</span><strong>' + d.stats.available + '</strong></div>' + statusBadge(d.subscription ? "active" : "inactive") + '</div><section class="plan-grid" aria-label="Subscription plans">' + d.plans.map(plan => {
      const current = plan.id === currentPlanId;
      const features = plan.code === "starter" ? ["Foundation courses", "Your personal progress tracker", "Access while your plan is active"] : ["All currently approved courses", "New content after approval", "Your personal progress tracker"];
      return '<article class="plan-card' + (current ? ' current' : '') + (plan.code === "plus" ? ' featured-plan' : '') + '"><div class="plan-top">' + icon(plan.code === "starter" ? "book" : plan.code === "plus" ? "layers" : "users") + '<span class="badge ' + (current ? 'info' : 'neutral') + '">' + (current ? 'Your plan' : plan.code === "plus" ? 'Full catalogue' : 'Monthly plan') + '</span></div><h3>' + escapeHtml(plan.name) + '</h3><div class="price">' + formatMoney(plan.price_monthly) + '<small>AUD / month</small></div><ul class="plan-features">' + features.map(feature => '<li>' + icon("check") + escapeHtml(feature) + '</li>').join("") + '</ul><button class="button ' + (current ? 'ghost' : plan.code === "plus" ? 'primary' : 'secondary') + '"' + (current ? ' disabled' : ' data-plan-id="' + plan.id + '"') + '>' + (current ? 'Current plan' : 'Choose ' + escapeHtml(plan.name)) + '</button>' + (current ? '<button class="text-link renew-plan" data-plan-id="' + plan.id + '">' + icon("refresh") + 'Renew for 30 days</button>' : '') + '</article>';
    }).join("") + '</section><p class="billing-note">' + icon("card") + 'Demo billing: plan changes record a simulated payment. No money is charged.</p><section class="panel billing-panel"><div class="panel-header"><div><h2>Billing history</h2><p>Your most recent subscription records</p></div><span class="badge neutral">AUD</span></div>' +
    (d.payments.length ? '<div class="table-wrap"><table class="data-table"><thead><tr><th scope="col">Recorded on</th><th scope="col">Description</th><th scope="col">Amount</th><th scope="col">Status</th></tr></thead><tbody>' + d.payments.map(payment => '<tr><td>' + formatDate(payment.paid_at) + '</td><td><strong>Subscription payment</strong><span class="muted">Simulated transaction</span></td><td>' + formatMoney(payment.amount) + '</td><td>' + statusBadge(payment.status) + '</td></tr>').join("") + '</tbody></table></div>' : emptyState("No billing records yet", "Your subscription activity will appear here.", "card")) + '</section>';
}
function educatorOverview() {
  setPage("Overview", "Educator workspace");
  const d = state.dashboard;
  return hero("SHARE WHAT YOU KNOW", "Hello, " + state.user.full_name.split(" ")[0] + ".", "Build useful resources and follow them from submission to publication.", '<button class="button primary" data-go="studio">' + icon("plus") + 'Create learning item</button>') + '<section class="stats-grid">' +
    statCard("Your resources", d.stats.total, "All submitted items", "blue", "layers") + statCard("Approved", d.stats.approved, "Available to learners", "teal", "check") + statCard("Under review", d.stats.pending, "Awaiting a decision", "orange", "clock") + statCard("Needs revision", d.stats.rejected, "Rejected submissions", "red", "audit") + '</section><div class="workflow-strip"><span>' + icon("plus") + 'Create a resource</span>' + icon("chevron") + '<span>' + icon("shield") + 'Administrator reviews</span>' + icon("chevron") + '<span>' + icon("book") + 'Learners get access</span></div><section class="panel"><div class="panel-header"><div><h2>Your recent resources</h2><p>Publication status at a glance</p></div><button class="text-link" data-go="content">View all ' + icon("chevron") + '</button></div>' + contentTable(d.items.slice(0, 5)) + '</section>';
}
function educatorStudio() {
  setPage("Content studio", "Educator workspace");
  return hero("CONTENT STUDIO", "What will you teach today?", "Give your resource a clear title and learning outcome. An administrator reviews it before publication.") +
    '<section class="section-grid studio-grid"><article class="panel"><div class="panel-header"><div><h2>Learning item details</h2><p>Tell learners what they will discover</p></div>' + statusBadge("draft") + '</div><form id="content-form" class="panel-body form-grid"><div class="span-2"><label for="content-title">Resource title</label><input id="content-title" name="title" minlength="4" maxlength="100" placeholder="e.g. Safe Data Handling Essentials" required></div><div><label for="content-category">Category</label><input id="content-category" name="category" minlength="3" maxlength="40" placeholder="e.g. Cybersecurity" required></div><div><label for="content-type">Content type</label><select id="content-type" name="content_type"><option value="course">Course</option><option value="video">Video</option><option value="article">Article</option><option value="quiz">Quiz</option><option value="workshop">Workshop</option></select></div><div><label for="content-duration">Duration in minutes</label><input id="content-duration" name="duration_minutes" type="number" min="5" max="600" value="30" required></div><div class="span-2"><label for="content-description">Learning outcome and description</label><textarea id="content-description" name="description" minlength="20" maxlength="500" placeholder="What will a learner understand or be able to do after completing this resource?" required aria-describedby="description-helper"></textarea><p class="helper" id="description-helper">20–500 characters. Keep learner personal information out of your resource.</p></div><div class="span-2 form-actions"><span>' + icon("shield") + 'Private until approved</span><button class="button primary" type="submit">Submit for review</button></div></form></article><aside class="panel studio-guide"><div class="panel-body"><span class="guide-icon">' + icon("shield") + '</span><span class="eyebrow">BEFORE YOU SUBMIT</span><h2>A good resource starts here.</h2><p class="muted">Help learners understand the content before they open it.</p><ol class="review-checklist">' + [["A clear learning outcome", "Explain what the learner will learn."], ["Accurate details", "Check the category, format, and duration."], ["No personal information", "Keep learner data private."], ["Ready for review", "An admin will decide when it can be published."]].map(([title, body]) => '<li><strong>' + title + '</strong><span>' + body + '</span></li>').join("") + '</ol></div></aside></section>';
}
function educatorContent() {
  setPage("My content", "Educator workspace");
  return hero("YOUR RESOURCE COLLECTION", "Everything you've created.", "Keep track of your submitted, approved, and rejected resources.", '<button class="button primary" data-go="studio">' + icon("plus") + 'Create a resource</button>') + '<section class="panel">' + contentTable(state.dashboard.items) + '</section>';
}
function contentTable(items) {
  if (!items.length) return emptyState("Your first resource starts here", "Create a learning item in Content Studio to get started.", "layers");
  return '<div class="table-wrap"><table class="data-table"><thead><tr><th scope="col">Resource</th><th scope="col">Format</th><th scope="col">Duration</th><th scope="col">Status</th><th scope="col">Created</th></tr></thead><tbody>' + items.map(item => '<tr><td><div class="resource-cell"><span class="resource-icon theme-' + courseTheme(item).colour + '">' + icon(courseTheme(item).icon) + '</span><span><strong>' + escapeHtml(item.title) + '</strong><span class="muted">' + escapeHtml(item.category) + '</span></span></div></td><td>' + titleCase(item.content_type) + '</td><td>' + item.duration_minutes + ' min</td><td>' + statusBadge(item.status) + '</td><td>' + formatDate(item.created_at) + '</td></tr>').join("") + '</tbody></table></div>';
}
function adminOverview() {
  setPage("Overview", "Administrator workspace");
  const d = state.dashboard;
  return hero("A HEALTHY LEARNING COMMUNITY", "Your platform, at a glance.", "Review content, monitor subscriptions, and follow account activity.", '<button class="button primary" data-go="approvals">' + icon("shield") + 'Review content</button>') + '<section class="stats-grid">' + statCard("Learners", d.stats.learners, "Registered accounts", "blue", "users") + statCard("Active plans", d.stats.active_subscriptions, "Subscribed learners", "teal", "card") + statCard("Published items", d.stats.approved_content, "Approved resources", "violet", "book") + statCard("Awaiting review", d.stats.pending_content, "Publication decisions", "orange", "clock") +
    '</section><section class="section-grid"><article class="panel"><div class="panel-header"><div><h2>Ready for your review</h2><p>Make sure new content is safe and useful</p></div><button class="text-link" data-go="approvals">View queue ' + icon("chevron") + '</button></div>' + approvalList(d.pending_items.slice(0, 4)) + '</article><aside class="panel"><div class="panel-header"><div><h2>Recent activity</h2><p>Latest recorded events</p></div></div><div class="panel-body activity-list">' +
    (d.audit.slice(0, 5).map(event => '<div class="activity-item"><span class="activity-icon">' + icon(event.event_type.includes("login") ? "users" : event.event_type.includes("content") ? "book" : "audit") + '</span><div><strong>' + escapeHtml(titleCase(event.event_type)) + '</strong><small>' + escapeHtml(event.user_name) + '</small><time>' + formatDate(event.created_at) + ' · ' + formatTime(event.created_at) + '</time></div></div>').join("") || emptyState("Nothing recorded yet", "Account activity will appear here.", "audit")) + '</div><div class="panel-bottom"><button class="text-link" data-go="audit">View audit reports ' + icon("chevron") + '</button></div></aside></section>';
}
function adminApprovals() {
  setPage("Approval queue", "Administrator workspace");
  return hero("CONTENT REVIEW", "Good learning begins with a review.", "Read the resource details before deciding whether it is ready for learners.") + '<section class="panel"><div class="panel-header"><div><h2>Pending resources</h2><p>' + state.dashboard.pending_items.length + (state.dashboard.pending_items.length === 1 ? ' item needs' : ' items need') + ' a publication decision</p></div>' + statusBadge("pending") + '</div>' + approvalList(state.dashboard.pending_items) + '</section>';
}
function approvalList(items) {
  if (!items.length) return emptyState("You're all caught up", "New educator submissions will appear here for your review.", "shield");
  return '<div class="approval-list">' + items.map(item => '<article class="approval-card"><span class="resource-icon theme-' + courseTheme(item).colour + '">' + icon(courseTheme(item).icon) + '</span><div class="approval-details"><span class="eyebrow">' + escapeHtml(item.category) + '</span><h3>' + escapeHtml(item.title) + '</h3><p>' + escapeHtml(item.description) + '</p><div class="approval-meta"><span>' + icon("users") + escapeHtml(item.educator_name) + '</span><span>' + icon("clock") + item.duration_minutes + ' min · ' + titleCase(item.content_type) + '</span><span>Submitted ' + formatDate(item.created_at) + '</span></div></div><div class="approval-actions"><button class="button secondary small" data-review-id="' + item.id + '" data-decision="approved">' + icon("check") + 'Approve</button><button class="button danger small" data-review-id="' + item.id + '" data-decision="rejected">' + icon("close") + 'Reject</button></div></article>').join("") + '</div>';
}
function adminAudit() {
  setPage("Audit reports", "Administrator workspace");
  return hero("PLATFORM ACTIVITY", "A clear record of what happened.", "Follow account access, subscription changes, learning progress, and publication decisions.") + '<section class="panel"><div class="panel-header"><div><h2>Event log</h2><p>The 30 most recent recorded events</p></div><span class="badge neutral">' + state.dashboard.audit.length + ' events</span></div><div class="audit-list">' +
    (state.dashboard.audit.map(event => '<div class="audit-row"><span class="activity-icon ' + (event.event_type.includes("denied") ? 'theme-red' : '') + '">' + icon(event.event_type.includes("denied") ? "lock" : "audit") + '</span><div><strong>' + escapeHtml(titleCase(event.event_type)) + '</strong><p>' + escapeHtml(event.details) + '</p></div><span class="audit-user">' + escapeHtml(event.user_name) + '</span><time>' + formatDate(event.created_at) + '<small>' + formatTime(event.created_at) + '</small></time></div>').join("") || emptyState("No events recorded", "New activity will be shown here.", "audit")) + '</div></section>';
}
function emptyState(title, body, glyph = "book") {
  return '<div class="empty-state"><span>' + icon(glyph) + '</span><h3>' + escapeHtml(title) + '</h3><p>' + escapeHtml(body) + '</p></div>';
}
function bindCourseEvents(root = $("#app-content")) {
  $$(".video-thumbnail-image", root).forEach(image => {
    const showFallback = () => { image.hidden = true; image.closest(".video-preview").classList.add("thumbnail-unavailable"); };
    image.addEventListener("error", showFallback, { once: true });
    if (image.complete && image.naturalWidth === 0) showFallback();
  });
  $$("[data-go]", root).forEach(button => button.addEventListener("click", () => changeView(button.dataset.go)));
  $$("[data-subject-id]", root).forEach(button => button.addEventListener("click", () => showSubject(Number(button.dataset.subjectId))));
  $$("[data-open-item]", root).forEach(button => button.addEventListener("click", () => openLesson(Number(button.dataset.openItem), button)));
  $("[data-reset-filters]", root)?.addEventListener("click", () => { state.filter = "all"; state.query = ""; state.accessFilter = "all"; state.sort = "default"; render(); });
}
function bindViewEvents() {
  bindCourseEvents();
  $$("[data-filter]").forEach(button => button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    $$("[data-filter]").forEach(other => { other.classList.toggle("active", other === button); other.setAttribute("aria-pressed", String(other === button)); });
    updateLibraryResults();
  }));
  $$("[data-learning-filter]").forEach(button => button.addEventListener("click", () => { state.learningFilter = button.dataset.learningFilter; render(); }));
  $("#course-search")?.addEventListener("input", event => { state.query = event.target.value; updateLibraryResults(); });
  $("#clear-search")?.addEventListener("click", () => { state.query = ""; $("#course-search").value = ""; updateLibraryResults(); $("#course-search").focus(); });
  $("#course-access")?.addEventListener("change", event => { state.accessFilter = event.target.value; updateLibraryResults(); });
  $("#course-sort")?.addEventListener("change", event => { state.sort = event.target.value; updateLibraryResults(); });
  if (state.view === "library") $("#results-count").textContent = filteredItems().length + (filteredItems().length === 1 ? " course" : " courses");
  $$("[data-plan-id]").forEach(button => button.addEventListener("click", () => changePlan(Number(button.dataset.planId), button)));
  $$("[data-review-id]").forEach(button => button.addEventListener("click", () => reviewContent(Number(button.dataset.reviewId), button.dataset.decision, button)));
  $("#content-form")?.addEventListener("submit", submitContent);
}
async function openLesson(itemId, button) {
  setLoading(button, true, "Opening…");
  try {
    const data = await api("/api/access/" + itemId);
    const item = state.dashboard.items.find(item => item.id === itemId);
    state.activeItem = { ...data.item, progress_percent: item?.progress_percent || 0 };
    $("#dialog-title").textContent = data.item.title;
    $("#dialog-description").textContent = data.item.description;
    $("#dialog-body").textContent = data.lesson.body;
    $("#dialog-metadata").textContent = data.item.category + " · " + data.item.duration_minutes + " minutes";
    $("#dialog-error").textContent = "";
    $("#progress-slider").value = state.activeItem.progress_percent;
    $("#progress-output").value = $("#progress-slider").value + "%";
    $("#lesson-dialog").showModal();
  } catch (error) { toast(error.message, true); }
  finally { setLoading(button, false); }
}
async function saveProgress(button) {
  if (!state.activeItem) return;
  setLoading(button, true, "Saving…");
  $("#dialog-error").textContent = "";
  try {
    const progress = Number($("#progress-slider").value);
    await api("/api/progress", { method: "POST", body: JSON.stringify({ item_id: state.activeItem.id, progress }) });
    $("#lesson-dialog").close();
    await loadDashboard(progress === 100 ? "Course completed. Well done!" : "Your progress is saved at " + progress + "%.");
  } catch (error) { $("#dialog-error").textContent = error.message; }
  finally { setLoading(button, false); }
}
async function changePlan(planId, button) {
  setLoading(button, true, "Updating plan…");
  try {
    const data = await api("/api/subscription", { method: "POST", body: JSON.stringify({ plan_id: planId }) });
    await loadDashboard(data.message);
  } catch (error) { toast(error.message, true); }
  finally { setLoading(button, false); }
}
async function submitContent(event) {
  event.preventDefault();
  const button = event.submitter;
  setLoading(button, true, "Submitting…");
  try {
    const payload = Object.fromEntries(new FormData(event.currentTarget));
    payload.duration_minutes = Number(payload.duration_minutes);
    const data = await api("/api/content", { method: "POST", body: JSON.stringify(payload) });
    state.view = "content";
    await loadDashboard(data.message);
  } catch (error) { toast(error.message, true); }
  finally { setLoading(button, false); }
}
async function reviewContent(itemId, decision, button) {
  setLoading(button, true, decision === "approved" ? "Approving…" : "Rejecting…");
  try {
    const data = await api("/api/admin/content/" + itemId + "/review", { method: "POST", body: JSON.stringify({ decision }) });
    await loadDashboard(data.message);
  } catch (error) { toast(error.message, true); }
  finally { setLoading(button, false); }
}
async function login(event) {
  event.preventDefault();
  if (state.signingIn) return;
  state.signingIn = true;
  const button = $('#login-form button[type="submit"]');
  setLoading(button, true, "Signing in…");
  $$(".demo-account").forEach(demo => { demo.disabled = true; });
  try {
    const data = await api("/api/login", { method: "POST", body: JSON.stringify({ email: $("#email").value, password: $("#password").value }) });
    state.user = data.user; state.view = "overview";
    state.filter = "all"; state.query = ""; state.accessFilter = "all"; state.learningFilter = "all"; state.sort = "default";
    await loadDashboard();
  } catch (error) { toast(error.message, true); }
  finally { state.signingIn = false; setLoading(button, false); $$(".demo-account").forEach(demo => { demo.disabled = false; }); }
}
async function logout() {
  const button = $("#logout-button");
  setLoading(button, true, "Signing out…");
  try {
    await api("/api/logout", { method: "POST", body: "{}" });
    closeMenu(); $("#lesson-dialog").close();
    clearTimeout(toast.timer); $("#toast").className = "toast";
    state.user = null; state.dashboard = null; state.view = "overview"; state.activeItem = null;
    $("#app-shell").classList.add("hidden"); $("#login-screen").classList.remove("hidden");
    $("#login-form").reset(); $("#password").type = "password";
    $("#toggle-password").textContent = "Show";
    $("#toggle-password").setAttribute("aria-label", "Show password");
    window.scrollTo({ top: 0, behavior: "instant" });
    document.title = "EduStream | Your learning space";
  } catch (error) { toast("Sign out could not be completed. Please try again.", true); }
  finally { setLoading(button, false); }
}
function syncMenuAccessibility() {
  const mobile = window.matchMedia("(max-width: 850px)").matches;
  const open = $("#sidebar").classList.contains("open");
  $("#sidebar").inert = mobile && !open;
  $("#app-main").inert = mobile && open;
}
function openMenu() {
  $("#sidebar").classList.add("open"); $("#mobile-overlay").classList.add("show");
  $("#menu-button").setAttribute("aria-expanded", "true");
  syncMenuAccessibility(); $("#main-nav button")?.focus();
}
function closeMenu() {
  $("#sidebar").classList.remove("open"); $("#mobile-overlay").classList.remove("show");
  $("#menu-button").setAttribute("aria-expanded", "false");
  syncMenuAccessibility();
}
async function initialise() {
  $("#login-form").addEventListener("submit", login);
  $("#logout-button").addEventListener("click", logout);
  $("#menu-button").addEventListener("click", () => $("#sidebar").classList.contains("open") ? closeMenu() : openMenu());
  $("#mobile-overlay").addEventListener("click", () => { closeMenu(); $("#menu-button").focus(); });
  window.matchMedia("(max-width: 850px)").addEventListener("change", () => { closeMenu(); });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && $("#sidebar").classList.contains("open")) { closeMenu(); $("#menu-button").focus(); }
    if (event.key === "Tab" && $("#sidebar").classList.contains("open") && window.matchMedia("(max-width: 850px)").matches) {
      const controls = $$('a[href], button:not([disabled])', $("#sidebar"));
      if (event.shiftKey && document.activeElement === controls[0]) { event.preventDefault(); controls.at(-1).focus(); }
      if (!event.shiftKey && document.activeElement === controls.at(-1)) { event.preventDefault(); controls[0].focus(); }
    }
  });
  $(".sidebar-brand").addEventListener("click", event => { event.preventDefault(); if (state.user) changeView("overview"); });
  $("#close-dialog").addEventListener("click", () => $("#lesson-dialog").close());
  $("#save-progress").addEventListener("click", event => saveProgress(event.currentTarget));
  $("#progress-slider").addEventListener("input", event => { $("#progress-output").value = event.target.value + "%"; });
  $("#toggle-password").addEventListener("click", event => {
    const input = $("#password"); input.type = input.type === "password" ? "text" : "password";
    event.currentTarget.textContent = input.type === "password" ? "Show" : "Hide";
    event.currentTarget.setAttribute("aria-label", input.type === "password" ? "Show password" : "Hide password");
  });
  $$(".demo-account").forEach(button => button.addEventListener("click", () => {
    if (state.signingIn) return;
    $("#email").value = button.dataset.email; $("#password").value = button.dataset.password;
    $("#login-form").requestSubmit();
  }));
  try {
    const session = await api("/api/session");
    if (session.authenticated) { state.user = session.user; await loadDashboard(); }
  } catch (error) { toast("Unable to connect. Check that the EduStream server is running.", true); }
}
document.addEventListener("DOMContentLoaded", initialise);
