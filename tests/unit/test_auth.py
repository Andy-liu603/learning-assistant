"""认证模块测试 — 6 个用例"""
import pytest
import json, os, sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "backend"))
os.chdir(_ROOT)

from backend.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """注册用户并返回 token"""
    client.post("/api/auth/register", json={
        "username": "authtest", "email": "authtest@test.com", "password": "test123456"
    })
    resp = client.post("/api/auth/login", json={
        "username": "authtest", "password": "test123456"
    })
    token = resp.get_json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}


class TestAuthPositive:
    """正向测试"""

    def test_register_new_user(self, client):
        """注册新用户 -> 201 + JWT token"""
        resp = client.post("/api/auth/register", json={
            "username": "newuser", "email": "new@test.com", "password": "pass123456"
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert "access_token" in data
        assert data["user"]["username"] == "newuser"

    def test_login_existing_user(self, client):
        """登录已注册用户 -> 200 + JWT token"""
        client.post("/api/auth/register", json={
            "username": "loginuser", "email": "login@test.com", "password": "pass123456"
        })
        resp = client.post("/api/auth/login", json={
            "username": "loginuser", "password": "pass123456"
        })
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()

    def test_get_me_with_valid_token(self, client, auth_headers):
        """有效 token 获取用户信息 -> 200"""
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["username"] == "authtest"


class TestAuthNegative:
    """逆向测试"""

    def test_register_duplicate_username(self, client):
        """重复用户名注册 -> 409"""
        client.post("/api/auth/register", json={
            "username": "duplicate", "email": "d1@test.com", "password": "pass123456"
        })
        resp = client.post("/api/auth/register", json={
            "username": "duplicate", "email": "d2@test.com", "password": "pass123456"
        })
        assert resp.status_code == 409

    def test_login_wrong_password(self, client):
        """错误密码登录 -> 401"""
        client.post("/api/auth/register", json={
            "username": "wrongpw", "email": "wp@test.com", "password": "right123456"
        })
        resp = client.post("/api/auth/login", json={
            "username": "wrongpw", "password": "wrong123456"
        })
        assert resp.status_code == 401


class TestAuthBoundary:
    """边界测试"""

    def test_register_empty_username(self, client):
        """空用户名注册 -> 400"""
        resp = client.post("/api/auth/register", json={
            "username": "", "email": "empty@test.com", "password": "pass123456"
        })
        assert resp.status_code == 400
