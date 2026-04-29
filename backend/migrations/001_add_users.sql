-- 迁移 001：添加多用户支持
-- 执行时机：应用启动时（如果表不存在则创建）

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 2. 用户设置表
CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    preferences TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. 为所有现有表添加 user_id（如果列不存在）
-- 注意：如果旧库有数据，这些数据会被设为 user_id=1（默认管理员用户）

-- documents
ALTER TABLE documents ADD COLUMN user_id INTEGER REFERENCES users(id);

-- document_chunks
ALTER TABLE document_chunks ADD COLUMN user_id INTEGER REFERENCES users(id);

-- conversations
ALTER TABLE conversations ADD COLUMN user_id INTEGER REFERENCES users(id);

-- messages
ALTER TABLE messages ADD COLUMN user_id INTEGER REFERENCES users(id);

-- learning_progress
ALTER TABLE learning_progress ADD COLUMN user_id INTEGER REFERENCES users(id);

-- study_sessions
ALTER TABLE study_sessions ADD COLUMN user_id INTEGER REFERENCES users(id);

-- knowledge_points
ALTER TABLE knowledge_points ADD COLUMN user_id INTEGER REFERENCES users(id);

-- assessments
ALTER TABLE assessments ADD COLUMN user_id INTEGER REFERENCES users(id);

-- assessment_questions
ALTER TABLE assessment_questions ADD COLUMN user_id INTEGER REFERENCES users(id);

-- weekly_reports
ALTER TABLE weekly_reports ADD COLUMN user_id INTEGER REFERENCES users(id);
