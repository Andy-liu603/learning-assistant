"""
文档解析服务 - 支持 PDF/PPTX/DOCX/Markdown
"""
import os
from pathlib import Path
from typing import List, Tuple
import config


def parse_document(file_path: str) -> Tuple[str, str]:
    """
    解析文档，返回 (纯文本, 文件类型)

    Args:
        file_path: 文件路径

    Returns:
        (提取的文本内容, 文件类型)
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    parsers = {
        ".pdf": parse_pdf,
        ".pptx": parse_pptx,
        ".ppt": parse_pptx,
        ".docx": parse_docx,
        ".doc": parse_docx,
        ".md": parse_markdown,
        ".markdown": parse_markdown,
        ".txt": parse_txt,
    }

    parser = parsers.get(suffix)
    if not parser:
        raise ValueError(f"不支持的文件格式: {suffix}")

    text = parser(str(path))
    return text, suffix.lstrip(".")


def parse_pdf(file_path: str) -> str:
    """解析PDF文件"""
    import fitz  # PyMuPDF
    doc = fitz.open(file_path)
    texts = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            texts.append(text.strip())
    doc.close()
    return "\n\n".join(texts)


def parse_pptx(file_path: str) -> str:
    """解析PPT/PPTX文件"""
    from pptx import Presentation
    prs = Presentation(file_path)
    texts = []
    for slide_num, slide in enumerate(prs.slides, 1):
        slide_texts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        slide_texts.append(text)
            elif shape.has_table:
                for row in shape.table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells)
                    if row_text.strip(" |"):
                        slide_texts.append(row_text)
        if slide_texts:
            texts.append(f"[幻灯片 {slide_num}]\n" + "\n".join(slide_texts))
    return "\n\n".join(texts)


def parse_docx(file_path: str) -> str:
    """解析DOCX文件"""
    from docx import Document
    doc = Document(file_path)
    texts = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            texts.append(text)
    # 也提取表格内容
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells)
            if row_text.strip(" |"):
                texts.append(row_text)
    return "\n\n".join(texts)


def parse_markdown(file_path: str) -> str:
    """解析Markdown文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def parse_txt(file_path: str) -> str:
    """解析纯文本文件"""
    # 尝试多种编码
    for encoding in ["utf-8", "gbk", "gb2312", "utf-16"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"无法解码文件: {file_path}")


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    将长文本分割为固定大小的片段

    Args:
        text: 原始文本
        chunk_size: 片段大小（字符数）
        overlap: 片段重叠大小

    Returns:
        文本片段列表
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if not text.strip():
        return []

    # 按段落分割，保持语义完整性
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # 如果单个段落就超长，强制分割
            if len(para) > chunk_size:
                for i in range(0, len(para), chunk_size - overlap):
                    sub = para[i:i + chunk_size]
                    if sub.strip():
                        chunks.append(sub.strip())
                current_chunk = ""
            else:
                current_chunk = para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks
