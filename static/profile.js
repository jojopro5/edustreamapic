"use strict";
// Learner registration on the sign-in screen, and the "My profile" view for every role.
// Names and bios are user-written, so they are set with textContent or .value only.

function profileView() {
  setPage("My profile", state.user.role === "admin" ? "Administrator workspace" : state.user.role === "educator" ? "Educator workspace" : "Learner workspace");
  const educator = state.user.role === "educator";
  return hero("YOUR ACCOUNT", "Your profile and password.", "Only you can see or change these details. " + (educator ? "Learners and administrators see your name and bio next to your resources." : "Other learners see only your first name and initial.")) +
    '<section class="section-grid profile-grid"><article class="panel"><div class="panel-header"><div><h2>Profile</h2><p id="profile-meta">Loading…</p></div></div>' +
    '<form id="profile-form" class="panel-body form-grid" novalidate><div class="span-2"><label for="profile-name">Full name</label><input id="profile-name" name="full_name" minlength="2" maxlength="80" autocomplete="name" required></div>' +
    '<div class="span-2"><label for="profile-email">Email address</label><input id="profile-email" type="email" disabled aria-describedby="profile-email-help"><p class="helper" id="profile-email-help">Your sign-in email cannot be changed in this prototype.</p></div>' +
    (educator ? '<div class="span-2"><label for="profile-bio">Educator bio</label><textarea id="profile-bio" name="bio" maxlength="400" aria-describedby="profile-bio-help"></textarea><p class="helper" id="profile-bio-help">Up to 400 characters about your teaching background. Keep personal contact details out.</p></div>' : '') +
    '<p id="profile-error" class="inline-error span-2" role="alert"></p><div class="span-2 form-actions"><span>Saved changes are recorded in the audit log.</span><button class="button primary" type="submit">Save profile</button></div></form></article>' +
    '<article class="panel"><div class="panel-header"><div><h2>Change password</h2><p>Changing it signs you out on every other device.</p></div></div>' +
    '<form id="password-form" class="panel-body form-grid" novalidate><div class="span-2"><label for="current-password">Current password</label><input id="current-password" name="current_password" type="password" autocomplete="current-password" required></div>' +
    '<div class="span-2"><label for="new-password">New password</label><input id="new-password" name="new_password" type="password" autocomplete="new-password" minlength="10" maxlength="128" required aria-describedby="new-password-help"><p class="helper" id="new-password-help">At least 10 characters, not a common password and not your email.</p></div>' +
    '<p id="password-error" class="inline-error span-2" role="alert"></p><div class="span-2 form-actions"><span></span><button class="button secondary" type="submit">Change password</button></div></form></article></section>';
}

async function bindProfileView() {
  const form = document.getElementById("profile-form");
  const passwordForm = document.getElementById("password-form");
  try {
    const { profile } = await api("/api/profile");
    form.elements.full_name.value = profile.full_name;
    document.getElementById("profile-email").value = profile.email;
    if (form.elements.bio) form.elements.bio.value = profile.bio;
    document.getElementById("profile-meta").textContent = profile.role.charAt(0).toUpperCase() + profile.role.slice(1) + " account · joined " + formatDate(profile.created_at);
  } catch (error) { document.getElementById("profile-error").textContent = error.message; }
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const button = event.submitter;
    const error = document.getElementById("profile-error");
    error.textContent = "";
    setLoading(button, true, "Saving…");
    try {
      const payload = { full_name: form.elements.full_name.value };
      if (form.elements.bio) payload.bio = form.elements.bio.value;
      const data = await api("/api/profile", { method: "POST", body: JSON.stringify(payload) });
      await loadDashboard(data.message);
    } catch (failure) { error.textContent = failure.message; }
    finally { setLoading(button, false); }
  });
  passwordForm.addEventListener("submit", async event => {
    event.preventDefault();
    const button = event.submitter;
    const error = document.getElementById("password-error");
    error.textContent = "";
    setLoading(button, true, "Changing…");
    try {
      const data = await api("/api/profile/password", { method: "POST", body: JSON.stringify({ current_password: passwordForm.elements.current_password.value, new_password: passwordForm.elements.new_password.value }) });
      passwordForm.reset();
      toast(data.message);
    } catch (failure) { error.textContent = failure.message; }
    finally { setLoading(button, false); }
  });
}

async function register(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = event.submitter || form.querySelector('button[type="submit"]');
  const error = document.getElementById("register-error");
  error.textContent = "";
  setLoading(button, true, "Creating account…");
  try {
    const payload = { full_name: form.elements.full_name.value, email: form.elements.email.value, password: form.elements.password.value };
    const data = await api("/api/register", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    state.user = data.user; state.view = "subscription";
    await loadDashboard(data.message);
  } catch (failure) { error.textContent = failure.message; }
  finally { setLoading(button, false); }
}

document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("show-register");
  const form = document.getElementById("register-form");
  if (!toggle || !form) return;
  toggle.addEventListener("click", () => {
    const open = form.classList.toggle("hidden") === false;
    toggle.setAttribute("aria-expanded", String(open));
    if (open) document.getElementById("register-name").focus();
  });
  form.addEventListener("submit", register);
});
