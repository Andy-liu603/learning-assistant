"""
文档处理服务 - 上传、解析、入库全流程
"""
import os
import shutil
from typing import Tuple
from pathlib import Path
import config
from models.database import DocumentDAO, get_db
from services.document_parser import parse_document, chunk_text
from services.vector_store import VectorStore


class DocumentService:
    """文档上传与处理全流程"""

    @staticmethod
    def save_upload(file, filename: str, user_id: int = None) -> Tuple[str, str, int]:
        """
        保存上传文件

        Returns:
            (file_path, file_type, file_size)
        """
        suffix = Path(filename).suffix.lower()
        import uuid
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"

        # 按用户分目录
        if user_id:
            user_dir = config.UPLOAD_DIR / str(user_id)
            user_dir.mkdir(parents=True, exist_ok=True)
            dest_path = user_dir / unique_name
        else:
            dest_path = config.UPLOAD_DIR / unique_name

        file.save(str(dest_path))
        file_size = dest_path.stat().st_size

        return str(dest_path), suffix.lstrip("."), file_size

    @staticmethod
    def process_document(doc_id: int, progress_callback=None) -> dict:
        """
        处理文档：解析 → 分块 → 向量化 → 入库

        Args:
            doc_id: 文档ID
            progress_callback: callable(stage_label, progress_pct) 进度回调

        Returns:
            处理结果 {"chunks": int, "status": str}
        """
        doc = DocumentDAO.get_by_id(doc_id)
        if not doc:
            return {"error": "文档不存在"}

        file_category = doc.get("file_category", "text")

        try:
            # 1. 解析文档
            if progress_callback:
                if file_category == "multimodal":
                    progress_callback("正在调用视觉模型理解图片...", 25)
                else:
                    progress_callback("正在解析文档文本...", 30)

            if file_category == "multimodal":
                text, file_type = DocumentService._parse_multimodal(doc["file_path"], progress_callback)
            else:
                text, file_type = parse_document(doc["file_path"])

            if not text or not text.strip():
                DocumentDAO.update_status(doc_id, "error")
                return {"error": "文档内容为空"}

            # 2. 文本分块
            if progress_callback:
                progress_callback("正在切分文本块...", 50)
            chunks = chunk_text(text)
            if not chunks:
                DocumentDAO.update_status(doc_id, "error")
                return {"error": "分块结果为空"}

            # 3. 存入向量数据库
            if progress_callback:
                progress_callback(f"正在向量化 {len(chunks)} 个文本块...", 65)
            user_id = doc.get("user_id")
            vector_store = VectorStore()
            vector_ids = vector_store.add_chunks(doc_id, chunks, user_id=user_id)

            # 4. 存入SQLite
            if progress_callback:
                progress_callback("正在保存到数据库...", 85)
            conn = get_db()
            for i, chunk in enumerate(chunks):
                vid = vector_ids[i] if i < len(vector_ids) else None
                conn.execute(
                    "INSERT INTO document_chunks (document_id, chunk_index, content, vector_id, user_id) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (doc_id, i, chunk, vid, user_id)
                )
            # 保存 OCR 文本（多模态文件）
            if file_category == "multimodal":
                conn.execute(
                    "UPDATE documents SET ocr_text = ? WHERE id = ?",
                    (text, doc_id)
                )
            conn.commit()
            conn.close()

            # 5. 更新文档状态
            DocumentDAO.update_status(doc_id, "parsed", len(chunks))

            return {
                "chunks": len(chunks),
                "status": "parsed",
                "file_type": file_type,
                "text_length": len(text),
                "file_category": file_category
            }

        except Exception as e:
            DocumentDAO.update_status(doc_id, "error")
            return {"error": str(e)}

    @staticmethod
    def _parse_multimodal(file_path: str, progress_callback=None) -> tuple:
        """
        多模态文件解析：调用视觉模型理解图片/混合内容

        当前实现：返回文件元信息作为占位文本
        完整实现在 P1 #7 中接入 MiniMax 2.7 vision API 后激活
        """
        ext = Path(file_path).suffix.lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"):
            # 纯图片：尝试用视觉模型理解
            # TODO P1 #7: 接入 MiniMax 2.7 vision API
            import base64
            try:
                with open(file_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode("utf-8")
                # 占位：返回图片基本信息
                file_size_kb = Path(file_path).stat().st_size / 1024
                text = (
                    f"[图片文件] 文件名: {Path(file_path).name}\n"
                    f"文件大小: {file_size_kb:.1f} KB\n"
                    f"格式: {ext.upper()}\n"
                    f"说明: 此图片尚未经过视觉模型分析。请在设置中配置 MiniMax 2.7 API Key 后重新解析，"
                    f"系统将自动调用视觉模型理解图片内容并生成结构化描述。"
                )
                return text, ext.lstrip(".")
            except Exception as e:
                return f"[图片解析失败] {e}", ext.lstrip(".")
        else:
            # 混合内容（如 PDF 中的图片）：先提取文本
            return parse_document(file_path)

    @staticmethod
    def delete_document(doc_id: int) -> dict:
        """删除文档及其所有关联数据"""
        doc = DocumentDAO.get_by_id(doc_id)
        if not doc:
            return {"error": "文档不存在"}

        # 删除文件
        try:
            os.remove(doc["file_path"])
        except OSError:
            pass

        # 删除向量数据
        user_id = doc.get("user_id")
        vector_store = VectorStore()
        vector_store.delete_document(doc_id, user_id=user_id)

        # 删除数据库记录（级联删除 chunks, progress 等）
        DocumentDAO.delete(doc_id)

        return {"status": "deleted", "doc_id": doc_id}

    @staticmethod
    def search_documents(query: str, doc_id: int = None, top_k: int = 5, user_id: int = None) -> list:
        """语义搜索文档内容"""
        vector_store = VectorStore()
        return vector_store.search(query, doc_id, top_k, user_id=user_id)
