# 学习助手 v2.4

> 面向知识工作者的 RAG 增强全科学习系统

## 项目定位

学习助手是一个 **全科个人知识管理平台**，基于 RAG（检索增强生成）技术，帮助用户将学习资料转化为结构化的知识体系。无论是文科、理科、工科还是商科内容，系统都能提供智能问答、自动测评、进度追踪和 AI 报告生成。

### 从 v1.0 到 v2.4 的演进

| 版本 | 重点 | 关键里程碑 |
|------|------|-----------|
| v1.0 | MVP 验证 | 文档解析 + ChromaDB 向量化 + 基础问答 |
| v2.0 | 产品化 | JWT 多用户认证 + 异步文档处理 + 双模型架构 |
| v2.3 | 体验升级 | 纯 JS SPA 前端 + SSE 流式输出 + 多模态支持 + 测评系统 |
| v2.4 | 通用化 | 全科学习助手定位 + 学习仪表盘 + 学习计划生成 + 量化评估 |

## 架构概览

```
┌──────────────────────────────────────────────┐
│  前端：纯 JS SPA (Hash路由) + ECharts + IndexedDB │
├──────────────────────────────────────────────┤
│  后端：Flask (7蓝图, 55+ API) + JWT + SSE + ThreadPool  │
├──────────────────────────────────────────────┤
│  AI：Multi-Provider LLM + Sentence-Transformer  │
├──────────────────────────────────────────────┤
│  数据：SQLite (14表) + ChromaDB (HNSW索引)        │
└──────────────────────────────────────────────┘
```

## 核心功能

| 模块 | 功能 | 技术亮点 |
|------|------|---------|
| 学习仪表盘 | 学习数据聚合概览 | 90天热力图 + 掌握度环形图 + 趋势折线图 |
| 智能对话 | 基于文档的 RAG 问答 | SSE 流式输出，支持多模型热切换 |
| AI 资讯追踪 | RSS + URL 导入 + AI 摘要 | 14个预置AI资讯源，LLM趋势分析 |
| 资料库 | 文档上传/解析/向量化 | 支持 PDF/PPTX/DOCX/MD/图片，视觉模型理解 |
| 知识测评 | AI 自动出题 + 智能评判 | 选择/判断/简答混合，知识点关联 |
| 学习进度 | 五级掌握度追踪 | L0-L4 体系，薄弱点自动识别 |
| 学习计划 | AI 生成结构化学习计划 | 基于薄弱点补强 + 进度跟踪 |
| 学习报告 | 周报自动生成 + 下载 | LLM 数据分析，Markdown 格式 |

## 快速开始

### 环境要求

- Python 3.9+
- Windows / macOS / Linux

### 安装与启动

```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY

# 5. 启动服务
python backend/app.py

# 6. 访问
# http://127.0.0.1:5000
```

Windows 用户也可双击 `start.bat` 一键启动。

### API 文档

启动后访问 `http://127.0.0.1:5000/api/docs/` 查看 Swagger API 文档。

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Flask 3.1 | 轻量级，适合个人项目 |
| 数据库 | SQLite + ChromaDB | 零配置，WAL 模式，HNSW 向量索引 |
| LLM | DeepSeek / GLM-4.6V | OpenAI 兼容协议，多 Provider 热切换 |
| 嵌入模型 | BGE-small-zh-v1.5 | 本地运行，cosine 相似度 |
| 前端 | Vanilla JS SPA | 零框架，Hash 路由，ES Modules |
| 图表 | ECharts 5.5 | 环形图、热力图、折线图 |
| 认证 | JWT (HS256) | 7天过期，用户数据隔离 |
| 部署 | Flask 内置服务器 | 单进程，localhost |

详细技术选型说明见 `docs/后端技术选型说明.md` 和 `docs/前端技术选型说明.md`。

## 项目结构

```
AI学习助手2.0/
├── backend/              # Flask 后端
│   ├── app.py            # 应用入口 + 蓝图注册
│   ├── routes/           # 7 个蓝图路由模块
│   ├── services/         # 业务逻辑层（LLM/文档/资讯/向量）
│   ├── models/           # 数据访问层（SQLite DAO）
│   ├── middleware/       # JWT 认证中间件
│   ├── utils/            # 日志工具
│   └── migrations/       # SQL 迁移脚本
├── frontend/             # 纯 JS SPA 前端
│   ├── index.html        # SPA 入口
│   ├── css/              # 4 个样式文件
│   └── js/               # 11 个 JS 模块
├── data/                 # 运行时数据
│   ├── learning.db       # SQLite 数据库
│   ├── vector_db/        # ChromaDB 向量存储
│   ├── uploads/          # 上传文件
│   └── reports/          # 学习报告
├── docs/                 # 项目文档
│   ├── 系统架构文档.md
│   ├── 后端技术选型说明.md
│   ├── 前端技术选型说明.md
│   ├── 核心模块文档.md
│   └── PRD.md
├── tests/                # 测试
├── config.py             # 全局配置
├── requirements.txt      # Python 依赖
└── start.bat             # Windows 启动脚本
```

## 路线图

- [x] v2.3：多 Provider 架构 + SSE 流式 + 测评系统
- [x] v2.4：全科定位 + 仪表盘 + 学习计划 + 量化评估
- [ ] v3.0：多人协作 + OAuth 登录 + 知识图谱可视化

## 许可

个人学习项目，用于展示 RAG 系统设计与全栈开发能力。
