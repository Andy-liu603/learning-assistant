"""
测试：DocumentDAO
使用 SQLite 内存数据库
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import sqlite3
import config


@pytest.fixture
def test_db():
    """创建临时文件数据库用于测试"""
    import tempfile, os
    tmp = tempfile.mktemp(suffix='.db')
    original_path = config.DATABASE_PATH
    config.DATABASE_PATH = Path(tmp)

    from backend.models.database import init_db, get_db, run_migrations
    init_db()
    run_migrations()
    yield
    config.DATABASE_PATH = original_path
    try:
        os.unlink(tmp)
        os.unlink(tmp + '-wal')
        os.unlink(tmp + '-shm')
    except:
        pass


class TestDocumentDAO:
    def test_create_document(self, test_db):
        from backend.models.database import DocumentDAO
        doc_id = DocumentDAO.create("test.pdf", "pdf", "/tmp/test.pdf", 1024)
        assert doc_id > 0

        doc = DocumentDAO.get_by_id(doc_id)
        assert doc is not None
        assert doc["filename"] == "test.pdf"
        assert doc["file_type"] == "pdf"
        assert doc["status"] == "uploaded"

    def test_get_all(self, test_db):
        from backend.models.database import DocumentDAO
        DocumentDAO.create("doc1.pdf", "pdf", "/tmp/doc1.pdf")
        DocumentDAO.create("doc2.md", "md", "/tmp/doc2.md")

        docs = DocumentDAO.get_all()
        assert len(docs) == 2

    def test_update_status(self, test_db):
        from backend.models.database import DocumentDAO
        doc_id = DocumentDAO.create("test.pdf", "pdf", "/tmp/test.pdf")
        DocumentDAO.update_status(doc_id, "parsed", chunk_count=5)

        doc = DocumentDAO.get_by_id(doc_id)
        assert doc["status"] == "parsed"
        assert doc["chunk_count"] == 5

    def test_delete(self, test_db):
        from backend.models.database import DocumentDAO
        doc_id = DocumentDAO.create("test.pdf", "pdf", "/tmp/test.pdf")
        DocumentDAO.delete(doc_id)

        doc = DocumentDAO.get_by_id(doc_id)
        assert doc is None


class TestConversationDAO:
    def test_create_conversation(self, test_db):
        from backend.models.database import ConversationDAO
        conv_id = ConversationDAO.create(title="测试对话")
        assert conv_id > 0

        convs = ConversationDAO.get_all()
        assert len(convs) == 1
        assert convs[0]["title"] == "测试对话"

    def test_add_and_get_messages(self, test_db):
        from backend.models.database import ConversationDAO
        conv_id = ConversationDAO.create("测试对话")
        ConversationDAO.add_message(conv_id, "user", "你好")
        ConversationDAO.add_message(conv_id, "assistant", "你好！有什么可以帮你的？")

        msgs = ConversationDAO.get_messages(conv_id)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

    def test_delete_conversation(self, test_db):
        from backend.models.database import ConversationDAO
        conv_id = ConversationDAO.create("测试对话")
        ConversationDAO.delete(conv_id)

        convs = ConversationDAO.get_all()
        assert len(convs) == 0
