"""
向量数据库服务 - 使用 ChromaDB 实现本地向量存储与检索
v2.5: 每用户统一集合（替代每文档独立集合），跨文档检索 1 次 query
"""
import json
import re
from pathlib import Path
from typing import List, Tuple, Optional
import config


class VectorStore:
    """ChromaDB 向量存储封装"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 强制 HuggingFace 离线模式，避免每次初始化都联网
        import os
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

        import chromadb
        from chromadb.config import Settings

        self.client = chromadb.PersistentClient(
            path=str(config.VECTOR_DB_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
        self.embedding_model = config.EMBEDDING_MODEL
        self._embedding_fn = None
        self._initialized = True

    def _get_embedding_function(self):
        """延迟加载 embedding 函数（ONNX 可选加速，默认 PyTorch）"""
        if self._embedding_fn is None:
            from sentence_transformers import SentenceTransformer
            import logging
            log = logging.getLogger("ai_learning")

            use_onnx = os.environ.get("EMBEDDING_ONNX", "").lower() in ("1", "true", "yes")
            model = None

            if use_onnx:
                try:
                    model = SentenceTransformer(self.embedding_model, backend="onnx")
                    try:
                        model.save_pretrained(self.embedding_model)
                    except Exception:
                        pass
                    log.info(f"[VectorStore] ONNX 加速已启用: {self.embedding_model}")
                except Exception as e:
                    log.warning(f"[VectorStore] ONNX 不可用，回退 PyTorch: {e}")

            if model is None:
                model = SentenceTransformer(self.embedding_model)
                log.info(f"[VectorStore] PyTorch 后端: {self.embedding_model}")

            self._embedding_fn = model.encode
        return self._embedding_fn

    # ─── v2.5: 统一集合命名 ───

    def _collection_name(self, user_id: int = None) -> str:
        """v2.5: 每用户一个集合，替代每文档独立集合"""
        return f"user_{user_id}_docs" if user_id else "learning_docs"

    def _get_or_create_collection(self, user_id: int = None):
        """获取或创建用户的统一向量集合"""
        return self.client.get_or_create_collection(
            name=self._collection_name(user_id),
            metadata={"hnsw:space": "cosine"}
        )

    # ─── 公开 API（签名不变） ───

    def add_chunks(self, doc_id: int, chunks: List[str], user_id: int = None) -> List[str]:
        """
        将文本片段添加到向量数据库（v2.5: 写入统一集合）
        """
        if not chunks:
            return []

        collection = self._get_or_create_collection(user_id)
        embedding_fn = self._get_embedding_function()
        embeddings = embedding_fn(chunks).tolist()
        ids = [f"chunk_{doc_id}_{i}" for i in range(len(chunks))]
        metadatas = [{"doc_id": doc_id, "chunk_index": i, "user_id": user_id}
                     for i in range(len(chunks))]

        batch_size = 100
        for start in range(0, len(chunks), batch_size):
            end = start + batch_size
            collection.add(
                ids=ids[start:end],
                embeddings=embeddings[start:end],
                documents=chunks[start:end],
                metadatas=metadatas[start:end]
            )

        return ids

    def search(self, query: str, doc_id: int = None, top_k: int = 5,
               user_id: int = None) -> List[Tuple[str, float, dict]]:
        """
        语义搜索最相关的文本片段
        v2.5: 统一集合 + where 过滤，1 次 query（替代 N 次 per-collection query）
        返回: [(content, score, metadata), ...]
        """
        embedding_fn = self._get_embedding_function()
        query_embedding = embedding_fn([query]).tolist()
        collection = self._get_or_create_collection(user_id)
        where = {"doc_id": doc_id} if doc_id is not None else None

        try:
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=top_k,
                where=where
            )
        except Exception:
            return []

        if not results or not results.get("documents") or not results["documents"][0]:
            return []

        documents = results["documents"][0]
        distances = results.get("distances", [[]])[0]
        metadatas = (results.get("metadatas", [[]])[0]
                     if results.get("metadatas") else [{}] * len(documents))

        return [
            (doc, 1.0 - dist, meta or {})
            for doc, dist, meta in zip(documents, distances, metadatas)
        ]

    def delete_document(self, doc_id: int, user_id: int = None):
        """
        删除文档的所有向量
        v2.5: 不再删除整个 collection，仅删该文档的向量（where 过滤）
        """
        try:
            collection = self._get_or_create_collection(user_id)
            collection.delete(where={"doc_id": doc_id})
        except Exception:
            pass

    def get_document_count(self, doc_id: int, user_id: int = None) -> int:
        """
        获取文档的向量数量
        v2.5: 用 get(where=) 计数，不再按 collection 计数
        """
        try:
            collection = self._get_or_create_collection(user_id)
            res = collection.get(where={"doc_id": doc_id}, include=[])
            return len(res.get("ids", []))
        except Exception:
            return 0

    # ─── v2.5: 旧数据迁移 ───

    def migrate_legacy_collections(self):
        """
        一次性迁移旧版每文档独立集合 → 统一集合。
        幂等：无旧集合则直接跳过；写入校验通过后才删旧集合。
        """
        import logging
        log = logging.getLogger("ai_learning")

        legacy = re.compile(r"^(?:user_(\d+)_)?doc_(\d+)$")
        old_colls = [c for c in self.client.list_collections() if legacy.match(c.name)]
        if not old_colls:
            log.info("[VectorStore] 无旧版集合，跳过迁移")
            return

        for old in old_colls:
            m = legacy.match(old.name)
            uid = int(m.group(1)) if m.group(1) else None
            try:
                data = old.get(include=["embeddings", "documents", "metadatas"])
            except Exception as e:
                log.error(f"[VectorStore] 读取旧集合 {old.name} 失败: {e}")
                continue

            ids = data.get("ids", [])
            if not ids:
                self.client.delete_collection(old.name)
                continue

            target = self._get_or_create_collection(uid)
            existing = set(target.get(ids=ids, include=[]).get("ids", []))
            add_ids, add_emb, add_docs, add_meta = [], [], [], []
            for i, cid in enumerate(ids):
                if cid in existing:
                    continue
                add_ids.append(cid)
                add_emb.append(data["embeddings"][i])
                add_docs.append(data["documents"][i])
                add_meta.append(data["metadatas"][i])

            if not add_ids:
                self.client.delete_collection(old.name)
                continue

            target.add(ids=add_ids, embeddings=add_emb,
                       documents=add_docs, metadatas=add_meta)

            if set(target.get(ids=add_ids, include=[]).get("ids", [])) == set(add_ids):
                self.client.delete_collection(old.name)
                log.info(f"[VectorStore] 已迁移并清理旧集合 {old.name}（{len(add_ids)} 条）")
            else:
                log.warning(f"[VectorStore] 迁移校验未通过，保留旧集合 {old.name}")
