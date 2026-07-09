-- 006: 学习计划表
CREATE TABLE IF NOT EXISTS study_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    duration_days INTEGER DEFAULT 7,
    current_level TEXT DEFAULT 'beginner',
    daily_hours INTEGER DEFAULT 1,
    content TEXT NOT NULL,
    progress TEXT DEFAULT '{}',
    status TEXT DEFAULT 'active',
    source TEXT DEFAULT 'manual',
    user_id INTEGER,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
