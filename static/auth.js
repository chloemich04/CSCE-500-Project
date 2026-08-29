function getToken() {
  return localStorage.getItem("access_token");
}

function setToken(token) {
  localStorage.setItem("access_token", token);
}

function clearToken() {
  localStorage.removeItem("access_token");
}

function decodeToken(token) {
  try {
    const payload = token.split(".")[1];
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch (err) {
    return null;
  }
}

function renderAuthStatus() {
  const el = document.getElementById("auth-status");
  if (!el) return;

  const token = getToken();
  const data = token ? decodeToken(token) : null;
  if (!data) {
    el.innerHTML =
      'You are not logged in. <a href="/login">Log in</a> or <a href="/register">create an account</a>.';
    return;
  }

  el.innerHTML =
    "Logged in as <strong>" +
    data.email +
    "</strong> (" +
    data.account_type +
    ') · <button type="button" class="secondary" id="logout-btn">Log out</button>';

  const btn = document.getElementById("logout-btn");
  if (btn) {
    btn.addEventListener("click", function () {
      clearToken();
      window.location.href = "/";
    });
  }
}

document.addEventListener("DOMContentLoaded", renderAuthStatus);
