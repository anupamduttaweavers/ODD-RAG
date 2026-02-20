"use strict";

/**
 * Shared authentication helper used by every admin page except the login page.
 *
 * On load it checks for a valid session via /chat/admin/api/auth/me.
 * If the session is invalid the browser is redirected to the login page.
 * Exposes adminFetch() which automatically attaches the Bearer token.
 */

const ADMIN_AUTH = (() => {
    const LOGIN_URL = "/chat/admin/login";
    const ME_URL = "/chat/admin/api/auth/me";
    const LOGOUT_URL = "/chat/admin/api/auth/logout";

    let _token = localStorage.getItem("admin_token") || "";
    let _user = null;

    function _headers(extra) {
        const h = { "Content-Type": "application/json" };
        if (_token) h["Authorization"] = "Bearer " + _token;
        return Object.assign(h, extra || {});
    }

    async function _checkSession() {
        if (!_token) {
            _redirectLogin();
            return;
        }
        try {
            const res = await fetch(ME_URL, { headers: _headers() });
            if (!res.ok) throw new Error("session invalid");
            _user = await res.json();
            _renderUserBadge();
        } catch {
            localStorage.removeItem("admin_token");
            _redirectLogin();
        }
    }

    function _redirectLogin() {
        const dest = encodeURIComponent(window.location.pathname);
        window.location.href = LOGIN_URL + "?next=" + dest;
    }

    function _renderUserBadge() {
        const el = document.getElementById("adminUserBadge");
        if (!el || !_user) return;
        el.innerHTML =
            '<span class="badge badge-idle" style="margin-right:8px;">' +
            _user.role.toUpperCase() +
            "</span>" +
            _user.username +
            ' &nbsp;<a href="#" id="adminLogoutBtn" style="color:rgba(255,255,255,.85);font-size:12px;">Logout</a>';
        const btn = document.getElementById("adminLogoutBtn");
        if (btn) btn.addEventListener("click", logout);
    }

    async function logout(e) {
        if (e) e.preventDefault();
        try {
            await fetch(LOGOUT_URL, { method: "POST", headers: _headers() });
        } catch { /* best-effort */ }
        localStorage.removeItem("admin_token");
        window.location.href = LOGIN_URL;
    }

    async function adminFetch(url, opts) {
        opts = opts || {};
        opts.headers = _headers(opts.headers);
        const res = await fetch(url, opts);
        if (res.status === 401) {
            localStorage.removeItem("admin_token");
            _redirectLogin();
            throw new Error("Session expired");
        }
        return res;
    }

    function getUser() {
        return _user;
    }

    function isSuperadmin() {
        return _user && _user.role === "superadmin";
    }

    _checkSession();

    return { adminFetch, logout, getUser, isSuperadmin };
})();
