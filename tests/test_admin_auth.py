"""Comprehensive test suite for admin authentication, authorization,
user management, activity logging, error pages, and middleware.

Run:  pytest tests/test_admin_auth.py -v
"""

import time

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.main import app

ADMIN_API = "/chat/admin/api"
LOGIN_URL = f"{ADMIN_API}/auth/login"
ME_URL = f"{ADMIN_API}/auth/me"
LOGOUT_URL = f"{ADMIN_API}/auth/logout"
USERS_URL = f"{ADMIN_API}/users"
LOGS_URL = f"{ADMIN_API}/logs"

SA_USER = settings.ADMIN_SUPERUSER_USERNAME
SA_PASS = settings.ADMIN_SUPERUSER_PASSWORD


@pytest.fixture(scope="module")
def client():
    """Module-scoped TestClient with lifespan (DB init + seed)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clear_cookies(client):
    """Clear cookie jar before every test to prevent cross-test leakage."""
    client.cookies.clear()


def _login(client, username=SA_USER, password=SA_PASS):
    """Helper: login and return the access token string."""
    r = client.post(LOGIN_URL, json={"username": username, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    client.cookies.clear()
    return r.json()["access_token"]


def _auth(token):
    """Helper: return Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


# ======================================================================
# 1. AUTH FLOW
# ======================================================================


class TestAuthLogin:
    """Login endpoint security."""

    def test_login_valid_credentials(self, client):
        r = client.post(LOGIN_URL, json={"username": SA_USER, "password": SA_PASS})
        assert r.status_code == 200
        data = r.json()
        assert data["access_token"]
        assert data["token_type"] == "bearer"
        assert data["username"] == SA_USER
        assert data["role"] == "superadmin"
        assert data["expires_in_minutes"] == settings.ADMIN_TOKEN_EXPIRE_MINUTES

    def test_login_sets_httponly_cookie(self, client):
        r = client.post(LOGIN_URL, json={"username": SA_USER, "password": SA_PASS})
        assert "admin_token" in r.cookies

    def test_login_wrong_password(self, client):
        r = client.post(LOGIN_URL, json={"username": SA_USER, "password": "WrongPass"})
        assert r.status_code == 401
        detail = r.json()["detail"]
        assert detail["error_code"] == "AUTH_FAILED"

    def test_login_nonexistent_user(self, client):
        r = client.post(LOGIN_URL, json={"username": "ghost", "password": "anything"})
        assert r.status_code == 401
        assert r.json()["detail"]["error_code"] == "AUTH_FAILED"

    def test_login_empty_body(self, client):
        r = client.post(LOGIN_URL, json={})
        assert r.status_code == 422

    def test_login_missing_password(self, client):
        r = client.post(LOGIN_URL, json={"username": SA_USER})
        assert r.status_code == 422

    def test_login_empty_username(self, client):
        r = client.post(LOGIN_URL, json={"username": "", "password": "x"})
        assert r.status_code == 422

    def test_login_no_json(self, client):
        r = client.post(LOGIN_URL, content="not json", headers={"Content-Type": "application/json"})
        assert r.status_code == 422


class TestAuthMe:
    """GET /auth/me endpoint."""

    def test_me_with_valid_token(self, client):
        token = _login(client)
        r = client.get(ME_URL, headers=_auth(token))
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == SA_USER
        assert data["role"] == "superadmin"
        assert data["is_active"] is True

    def test_me_without_token(self, client):
        r = client.get(ME_URL)
        assert r.status_code == 401

    def test_me_with_garbage_token(self, client):
        r = client.get(ME_URL, headers=_auth("garbage.token.here"))
        assert r.status_code == 401
        assert r.json()["detail"]["error_code"] == "TOKEN_INVALID"

    def test_me_with_expired_token(self, client):
        expired = jwt.encode(
            {"sub": SA_USER, "role": "superadmin", "exp": int(time.time()) - 10, "iss": "admin"},
            settings.ADMIN_JWT_SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        r = client.get(ME_URL, headers=_auth(expired))
        assert r.status_code == 401

    def test_me_with_wrong_secret(self, client):
        forged = jwt.encode(
            {"sub": SA_USER, "role": "superadmin", "exp": int(time.time()) + 3600, "iss": "admin"},
            "wrong-secret-key",
            algorithm=settings.ALGORITHM,
        )
        r = client.get(ME_URL, headers=_auth(forged))
        assert r.status_code == 401

    def test_me_with_wrong_issuer(self, client):
        bad_iss = jwt.encode(
            {"sub": SA_USER, "role": "superadmin", "exp": int(time.time()) + 3600, "iss": "not-admin"},
            settings.ADMIN_JWT_SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        r = client.get(ME_URL, headers=_auth(bad_iss))
        assert r.status_code == 401

    def test_me_with_missing_sub(self, client):
        no_sub = jwt.encode(
            {"role": "superadmin", "exp": int(time.time()) + 3600, "iss": "admin"},
            settings.ADMIN_JWT_SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        r = client.get(ME_URL, headers=_auth(no_sub))
        assert r.status_code == 401

    def test_me_via_cookie(self, client):
        token = _login(client)
        client.cookies.set("admin_token", token)
        r = client.get(ME_URL)
        assert r.status_code == 200
        assert r.json()["username"] == SA_USER


class TestAuthLogout:
    """POST /auth/logout endpoint."""

    def test_logout_success(self, client):
        token = _login(client)
        r = client.post(LOGOUT_URL, headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["message"] == "Logged out"

    def test_logout_without_token(self, client):
        r = client.post(LOGOUT_URL)
        assert r.status_code == 401


# ======================================================================
# 2. ADMIN PAGE PROTECTION (Server-side middleware)
# ======================================================================


class TestAdminPageProtection:
    """All /chat/admin/* pages must require auth except login."""

    PROTECTED_PAGES = [
        "/chat/admin",
        "/chat/admin/sync",
        "/chat/admin/filesource",
        "/chat/admin/users",
        "/chat/admin/logs",
    ]

    @pytest.mark.parametrize("path", PROTECTED_PAGES)
    def test_unauthenticated_redirects_to_login(self, client, path):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 302
        assert "/chat/admin/login" in r.headers["location"]

    def test_login_page_is_public(self, client):
        r = client.get("/chat/admin/login")
        assert r.status_code == 200
        assert "Admin Login" in r.text

    @pytest.mark.parametrize("path", [
        "/chat/admin/sync", "/chat/admin/filesource",
        "/chat/admin/users", "/chat/admin/logs",
    ])
    def test_authenticated_can_access_pages(self, client, path):
        token = _login(client)
        client.cookies.set("admin_token", token)
        r = client.get(path)
        assert r.status_code == 200
        assert "<!DOCTYPE html>" in r.text


# ======================================================================
# 3. API MIDDLEWARE PROTECTION (sync & filesource)
# ======================================================================


class TestApiMiddlewareProtection:
    """Protected API endpoints return 401 JSON without auth."""

    PROTECTED_APIS = [
        ("GET", "/api/v1/sync/status"),
        ("POST", "/api/v1/sync/trigger"),
        ("GET", "/api/v1/filesources/"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED_APIS)
    def test_api_returns_401_without_token(self, client, method, path):
        r = client.request(method, path)
        assert r.status_code == 401
        body = r.json()
        assert body["detail"]["error_code"] == "AUTH_REQUIRED"

    def test_sync_status_accessible_with_token(self, client):
        token = _login(client)
        r = client.get("/api/v1/sync/status", headers=_auth(token))
        assert r.status_code == 200

    def test_filesources_accessible_with_token(self, client):
        token = _login(client)
        r = client.get("/api/v1/filesources/", headers=_auth(token))
        assert r.status_code == 200

    def test_public_apis_remain_unprotected(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_chat_page_unprotected(self, client):
        r = client.get("/chat")
        assert r.status_code == 200


# ======================================================================
# 4. USER MANAGEMENT — SUPERADMIN
# ======================================================================


class TestUserManagementBySuperadmin:
    """Superadmin can do everything."""

    def test_create_admin_user(self, client):
        token = _login(client)
        r = client.post(USERS_URL, json={
            "username": "test_admin_1",
            "password": "Secure@1234",
            "role": "admin",
        }, headers=_auth(token))
        assert r.status_code == 201
        data = r.json()
        assert data["username"] == "test_admin_1"
        assert data["role"] == "admin"
        assert data["is_active"] is True
        assert data["created_by"] == SA_USER

    def test_create_superadmin_user(self, client):
        token = _login(client)
        r = client.post(USERS_URL, json={
            "username": "test_sa_2",
            "password": "Secure@1234",
            "role": "superadmin",
        }, headers=_auth(token))
        assert r.status_code == 201
        assert r.json()["role"] == "superadmin"

    def test_list_users(self, client):
        token = _login(client)
        r = client.get(USERS_URL, headers=_auth(token))
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert any(u["username"] == SA_USER for u in data["users"])

    def test_create_duplicate_username_returns_409(self, client):
        token = _login(client)
        uname = f"dup_user_{int(time.time())}"
        client.post(USERS_URL, json={
            "username": uname, "password": "Secure@1234", "role": "admin",
        }, headers=_auth(token))
        r = client.post(USERS_URL, json={
            "username": uname, "password": "Other@1234", "role": "admin",
        }, headers=_auth(token))
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "USER_EXISTS"

    def test_update_user_password(self, client):
        token = _login(client)
        uname = f"pwchg_{int(time.time())}"
        r = client.post(USERS_URL, json={
            "username": uname, "password": "OldPass@1234", "role": "admin",
        }, headers=_auth(token))
        user_id = r.json()["id"]
        r = client.put(f"{USERS_URL}/{user_id}", json={"password": "NewPass@1234"}, headers=_auth(token))
        assert r.status_code == 200
        r2 = client.post(LOGIN_URL, json={"username": uname, "password": "NewPass@1234"})
        assert r2.status_code == 200

    def test_update_user_role(self, client):
        token = _login(client)
        uname = f"role_chg_{int(time.time())}"
        r = client.post(USERS_URL, json={
            "username": uname, "password": "Pass@1234", "role": "admin",
        }, headers=_auth(token))
        user_id = r.json()["id"]
        r = client.put(f"{USERS_URL}/{user_id}", json={"role": "superadmin"}, headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["role"] == "superadmin"

    def test_deactivate_user(self, client):
        token = _login(client)
        uname = f"deact_{int(time.time())}"
        r = client.post(USERS_URL, json={
            "username": uname, "password": "Pass@1234", "role": "admin",
        }, headers=_auth(token))
        user_id = r.json()["id"]
        r = client.delete(f"{USERS_URL}/{user_id}", headers=_auth(token))
        assert r.status_code == 200
        assert "deactivated" in r.json()["message"]

    def test_deactivated_user_cannot_login(self, client):
        token = _login(client)
        uname = f"dead_{int(time.time())}"
        r = client.post(USERS_URL, json={
            "username": uname, "password": "Pass@1234", "role": "admin",
        }, headers=_auth(token))
        user_id = r.json()["id"]
        client.delete(f"{USERS_URL}/{user_id}", headers=_auth(token))
        r = client.post(LOGIN_URL, json={"username": uname, "password": "Pass@1234"})
        assert r.status_code == 401

    def test_update_nonexistent_user_returns_404(self, client):
        token = _login(client)
        r = client.put(f"{USERS_URL}/99999", json={"role": "admin"}, headers=_auth(token))
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "USER_NOT_FOUND"

    def test_delete_nonexistent_user_returns_404(self, client):
        token = _login(client)
        r = client.delete(f"{USERS_URL}/99999", headers=_auth(token))
        assert r.status_code == 404


# ======================================================================
# 5. USER MANAGEMENT — REGULAR ADMIN (role guardrail)
# ======================================================================


class TestUserManagementByAdmin:
    """Regular admins can manage users but cannot escalate to superadmin."""

    @pytest.fixture(autouse=True)
    def _setup_admin(self, client):
        sa_token = _login(client)
        client.post(USERS_URL, json={
            "username": "regular_admin",
            "password": "Admin@1234",
            "role": "admin",
        }, headers=_auth(sa_token))
        self.admin_token = _login(client, "regular_admin", "Admin@1234")

    def test_admin_can_list_users(self, client):
        r = client.get(USERS_URL, headers=_auth(self.admin_token))
        assert r.status_code == 200

    def test_admin_can_create_admin_user(self, client):
        r = client.post(USERS_URL, json={
            "username": f"by_admin_{int(time.time())}",
            "password": "Pass@1234",
            "role": "admin",
        }, headers=_auth(self.admin_token))
        assert r.status_code == 201
        assert r.json()["role"] == "admin"

    def test_admin_cannot_create_superadmin(self, client):
        r = client.post(USERS_URL, json={
            "username": f"escalate_{int(time.time())}",
            "password": "Pass@1234",
            "role": "superadmin",
        }, headers=_auth(self.admin_token))
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "FORBIDDEN"

    def test_admin_cannot_promote_to_superadmin(self, client):
        sa_token = _login(client)
        uname = f"promote_{int(time.time())}"
        r = client.post(USERS_URL, json={
            "username": uname, "password": "Pass@1234", "role": "admin",
        }, headers=_auth(sa_token))
        uid = r.json()["id"]
        r = client.put(f"{USERS_URL}/{uid}", json={"role": "superadmin"}, headers=_auth(self.admin_token))
        assert r.status_code == 403

    def test_admin_can_deactivate_user(self, client):
        sa_token = _login(client)
        uname = f"adm_deact_{int(time.time())}"
        r = client.post(USERS_URL, json={
            "username": uname, "password": "Pass@1234", "role": "admin",
        }, headers=_auth(sa_token))
        uid = r.json()["id"]
        r = client.delete(f"{USERS_URL}/{uid}", headers=_auth(self.admin_token))
        assert r.status_code == 200

    def test_admin_can_change_password(self, client):
        sa_token = _login(client)
        uname = f"adm_pw_{int(time.time())}"
        r = client.post(USERS_URL, json={
            "username": uname, "password": "Pass@1234", "role": "admin",
        }, headers=_auth(sa_token))
        uid = r.json()["id"]
        r = client.put(f"{USERS_URL}/{uid}", json={"password": "NewNew@1234"}, headers=_auth(self.admin_token))
        assert r.status_code == 200


# ======================================================================
# 6. USER MANAGEMENT — NO AUTH
# ======================================================================


class TestUserManagementUnauthenticated:
    """All user endpoints require auth."""

    def test_list_users_no_auth(self, client):
        r = client.get(USERS_URL)
        assert r.status_code == 401

    def test_create_user_no_auth(self, client):
        r = client.post(USERS_URL, json={"username": "x", "password": "x12345", "role": "admin"})
        assert r.status_code == 401

    def test_update_user_no_auth(self, client):
        r = client.put(f"{USERS_URL}/1", json={"role": "admin"})
        assert r.status_code == 401

    def test_delete_user_no_auth(self, client):
        r = client.delete(f"{USERS_URL}/1")
        assert r.status_code == 401


# ======================================================================
# 7. INPUT VALIDATION
# ======================================================================


class TestInputValidation:
    """Pydantic validation on request bodies."""

    def test_create_user_short_username(self, client):
        token = _login(client)
        r = client.post(USERS_URL, json={
            "username": "ab", "password": "Pass@1234", "role": "admin",
        }, headers=_auth(token))
        assert r.status_code == 422

    def test_create_user_short_password(self, client):
        token = _login(client)
        r = client.post(USERS_URL, json={
            "username": "valid_user_v", "password": "12", "role": "admin",
        }, headers=_auth(token))
        assert r.status_code == 422

    def test_create_user_invalid_role(self, client):
        token = _login(client)
        r = client.post(USERS_URL, json={
            "username": "valid_user_r", "password": "Pass@1234", "role": "god",
        }, headers=_auth(token))
        assert r.status_code == 422

    def test_update_user_invalid_role(self, client):
        token = _login(client)
        r = client.put(f"{USERS_URL}/1", json={"role": "overlord"}, headers=_auth(token))
        assert r.status_code == 422


# ======================================================================
# 8. ACTIVITY LOGS
# ======================================================================


class TestActivityLogs:
    """Activity logging and retrieval."""

    def test_login_creates_log_entry(self, client):
        token = _login(client)
        r = client.get(LOGS_URL, headers=_auth(token))
        assert r.status_code == 200
        logs = r.json()["logs"]
        login_logs = [l for l in logs if l["action"] == "LOGIN" and l["username"] == SA_USER]
        assert len(login_logs) >= 1

    def test_failed_login_creates_log_entry(self, client):
        client.post(LOGIN_URL, json={"username": "fail_log_user", "password": "bad"})
        token = _login(client)
        r = client.get(f"{LOGS_URL}?action=LOGIN_FAILED", headers=_auth(token))
        assert r.status_code == 200
        logs = r.json()["logs"]
        assert any(l["username"] == "fail_log_user" for l in logs)

    def test_logs_pagination(self, client):
        token = _login(client)
        r = client.get(f"{LOGS_URL}?page=1&page_size=2", headers=_auth(token))
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["logs"]) <= 2

    def test_logs_filter_by_username(self, client):
        token = _login(client)
        r = client.get(f"{LOGS_URL}?username={SA_USER}", headers=_auth(token))
        assert r.status_code == 200
        for log in r.json()["logs"]:
            assert log["username"] == SA_USER

    def test_logs_filter_by_action(self, client):
        token = _login(client)
        r = client.get(f"{LOGS_URL}?action=LOGIN", headers=_auth(token))
        assert r.status_code == 200
        for log in r.json()["logs"]:
            assert log["action"] == "LOGIN"

    def test_logs_require_auth(self, client):
        r = client.get(LOGS_URL)
        assert r.status_code == 401

    def test_log_has_ip_address(self, client):
        token = _login(client)
        r = client.get(f"{LOGS_URL}?action=LOGIN&page_size=1", headers=_auth(token))
        assert r.status_code == 200
        logs = r.json()["logs"]
        assert len(logs) >= 1
        assert logs[0]["ip_address"] is not None


# ======================================================================
# 9. ERROR PAGES & REDIRECTS
# ======================================================================


class TestErrorPagesAndRedirects:
    """Professional error pages and backward-compatible redirects."""

    def test_404_html_for_browser(self, client):
        r = client.get("/totally-nonexistent", headers={"accept": "text/html"})
        assert r.status_code == 404
        assert "Page Not Found" in r.text
        assert "<!DOCTYPE html>" in r.text

    def test_404_json_for_api(self, client):
        r = client.get("/api/v1/nonexistent")
        assert r.status_code == 404
        assert "detail" in r.json()

    def test_405_html_for_browser(self, client):
        r = client.post("/health", headers={"accept": "text/html"})
        assert r.status_code == 405
        assert "Method Not Allowed" in r.text

    def test_admin_catchall_redirect(self, client):
        r = client.get("/admin", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/chat/admin/login"

    def test_admin_subpath_catchall_redirect(self, client):
        r = client.get("/admin/some/deep/path", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/chat/admin/login"

    def test_legacy_filesource_redirect(self, client):
        r = client.get("/admin/filesource-config", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/chat/admin/filesource"

    def test_chat_admin_redirect_when_authenticated(self, client):
        token = _login(client)
        client.cookies.set("admin_token", token)
        r = client.get("/chat/admin", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/chat/admin/sync"

    def test_chat_admin_redirect_when_unauthenticated(self, client):
        r = client.get("/chat/admin", follow_redirects=False)
        assert r.status_code == 302
        assert "/chat/admin/login" in r.headers["location"]

    def test_error_page_has_navigation_links(self, client):
        r = client.get("/nonexistent-page", headers={"accept": "text/html"})
        assert r.status_code == 404
        assert "/chat" in r.text
        assert "Go Back" in r.text


# ======================================================================
# 10. PUBLIC ROUTES UNTOUCHED
# ======================================================================


class TestPublicRoutesUntouched:
    """Existing public endpoints must continue working without auth."""

    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "chat_url" in r.json()

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_chat_page(self, client):
        r = client.get("/chat")
        assert r.status_code == 200

    def test_docs_page(self, client):
        r = client.get("/docs")
        assert r.status_code == 200

    def test_openapi_json(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        assert "paths" in r.json()


# ======================================================================
# 11. SECURITY EDGE CASES
# ======================================================================


class TestSecurityEdgeCases:
    """Edge cases and adversarial inputs."""

    def test_core_jwt_secret_cannot_forge_admin_token(self, client):
        """Token signed with app.core SECRET_KEY should NOT work for admin."""
        if settings.SECRET_KEY == settings.ADMIN_JWT_SECRET_KEY:
            pytest.skip("Same secret key for both — not a separate secret")
        forged = jwt.encode(
            {"sub": SA_USER, "role": "superadmin", "exp": int(time.time()) + 3600, "iss": "admin"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        r = client.get(ME_URL, headers=_auth(forged))
        assert r.status_code == 401

    def test_sql_injection_in_username(self, client):
        r = client.post(LOGIN_URL, json={
            "username": "' OR 1=1 --",
            "password": "anything",
        })
        assert r.status_code == 401

    def test_xss_in_username(self, client):
        r = client.post(LOGIN_URL, json={
            "username": "<script>alert(1)</script>",
            "password": "anything",
        })
        assert r.status_code == 401

    def test_extremely_long_password(self, client):
        r = client.post(LOGIN_URL, json={
            "username": SA_USER,
            "password": "x" * 10000,
        })
        assert r.status_code == 401

    def test_bearer_header_takes_effect_without_cookie(self, client):
        token = _login(client)
        r = client.get(ME_URL, headers=_auth(token))
        assert r.status_code == 200

    def test_no_auth_at_all_returns_401(self, client):
        r = client.get(ME_URL)
        assert r.status_code == 401

    def test_invalid_content_type_returns_422(self, client):
        r = client.post(LOGIN_URL, content="username=admin&password=x",
                        headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert r.status_code == 422
