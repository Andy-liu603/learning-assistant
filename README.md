# AI学习助手 - 产品PM专版

个人AI学习助手，专为产品经理设计。支持文档上传解析、智能问答、学习进度追踪、周报生成。

## 架构

```
ai-learning-assistant/
├── backend/              # Flask API 服务
│   ├── app.py           # Flask 入口
│   ├── routes/          # API 路由
│   ├── services/        # 业务逻辑
│   ├── models/          # 数据模型
│   └── utils/           # 工具函数
├── frontend/            # Streamlit 前端
│   └── app.py
├── data/                # 本地数据
│   ├── uploads/         # 上传文件
│   ├── vector_db/       # 向量数据库
│   └── reports/         # 学习报告
├── requirements.txt
└── config.py
```

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 Claude API Key

# 3. 启动后端
cd backend
python app.py

# 4. 启动前端（新终端）
cd frontend
streamlit run app.py
```

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 前端 | Streamlit | 简洁美观的 Python Web UI |
| 后端 | Flask | 轻量 REST API |
| LLM | Claude API (Anthropic) | 智能问答 |
| 向量库 | ChromaDB | 本地向量存储，零依赖 |
| 数据库 | SQLite | 本地持久化 |
| 文档解析 | PyMuPDF / python-pptx / markdown |
