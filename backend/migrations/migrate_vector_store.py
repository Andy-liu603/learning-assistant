"""
手动触发向量集合迁移（幂等，可重复执行）
用法: python backend/migrations/migrate_vector_store.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.vector_store import VectorStore

if __name__ == "__main__":
    VectorStore().migrate_legacy_collections()
    print("向量集合迁移完成（幂等，可重复执行）")
