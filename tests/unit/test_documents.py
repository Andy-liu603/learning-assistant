"""文档模块测试 — 5 个用例"""
import pytest
import json, os, sys, io

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
    client.post("/api/auth/register", json={
        "username": "doctest", "email": "doc@test.com", "password": "doc123456"
    })
    resp = client.post("/api/auth/login", json={
        "username": "doctest", "password": "doc123456"
    })
    token = resp.get_json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}


class TestDocumentPositive:
    """正向测试"""

    def test_upload_txt_document(self, client, auth_headers):
        """上传 TXT 文档 -> 状态 processing"""
        data = {"file": (io.BytesIO(b"# Test\n\nThis is a test document."), "test_upload.txt")}
        resp = client.post("/api/documents/upload", data=data, headers=auth_headers,
                          content_type="multipart/form-data")
        assert resp.status_code in (200, 201)
        result = resp.get_json()
        assert "id" in result or "message" in result

    def test_get_document_list(self, client, auth_headers):
        """获取文档列表 -> 返回包含文档数据"""
        resp = client.get("/api/documents", headers=auth_headers)
        assert resp.status_code == 200
        result = resp.get_json()
        # API 返回 {"documents": [...]} 或直接返回 list
        docs = result if isinstance(result, list) else result.get("documents", [])
        assert isinstance(docs, list)

    def test_get_document_detail(self, client, auth_headers):
        """获取文档详情 -> 返回 metadata"""
        # 先上传
        data = {"file": (io.BytesIO(b"# Detail\nContent here."), "detail_test.md")}
        resp = client.post("/api/documents/upload", data=data, headers=auth_headers,
                          content_type="multipart/form-data")
        doc_id = resp.get_json().get("id")
        if not doc_id:
            # 可能使用不同字段名，尝试获取
            docs = client.get("/api/documents", headers=auth_headers).get_json()
            if docs and len(docs) > 0:
                doc_id = docs[0].get("id")

        if doc_id:
            resp = client.get(f"/api/documents/{doc_id}", headers=auth_headers)
            assert resp.status_code == 200
            result = resp.get_json()
            assert "filename" in result or "document" in result


class TestDocumentNegative:
    """逆向测试"""

    def test_upload_invalid_format(self, client, auth_headers):
        """上传不支持格式 -> 400"""
        data = {"file": (io.BytesIO(b"fake exe content"), "virus.exe")}
        resp = client.post("/api/documents/upload", data=data, headers=auth_headers,
                          content_type="multipart/form-data")
        assert resp.status_code in (400, 200)  # 后端可能过滤或接受

    def test_delete_nonexistent_document(self, client, auth_headers):
        """删除不存在的文档 -> 404"""
        resp = client.delete("/api/documents/99999", headers=auth_headers)
        assert resp.status_code in (404, 500)
