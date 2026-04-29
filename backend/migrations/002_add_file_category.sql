-- 迁移 002：添加多模态文档支持

-- documents 表新增 file_category 和 ocr_text 列
ALTER TABLE documents ADD COLUMN file_category TEXT DEFAULT 'text';
ALTER TABLE documents ADD COLUMN ocr_text TEXT DEFAULT NULL;
