-- v2.5: 长期用户记忆系统 — 用户学习画像
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    learning_style TEXT DEFAULT '',
    confusion_patterns TEXT DEFAULT '',
    recent_insights TEXT DEFAULT '',
    profile_text TEXT DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
