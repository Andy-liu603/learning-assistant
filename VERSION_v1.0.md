# AI 学习助手 v1.0 — 版本摘要

## 项目概述

**AI 学习助手** 是一个面向 AI 产品经理（PM）的个人学习工具。支持上传学习资料，基于文档内容进行 RAG 智能问答、自动生成知识测评、追踪学习进度，并自动生成周学习报告。

---

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | Flask | 3.1.1 |
| 前端 UI | Streamlit | 1.44.1 |
| LLM | DeepSeek V4 Pro (OpenAI 兼容接口) | — |
| 向量数据库 | ChromaDB | 1.0.8 |
| 嵌入模型 | all-MiniLM-L6-v2 (本地离线, 384维) | 4.1.0 |
| 数据库 | SQLite | — |
| 文档解析 | PyMuPDF / python-pptx / python-docx / markdown | — |
| 图表 | Plotly + ECharts | — |

---

## 架构

```
┌──────────────────────┐
│  前端 (Streamlit)    │  http://127.0.0.1:8501
│  + 备用 HTML/JS       │  http://127.0.0.1:5000
└────────┬─────────────┘
         │ HTTP REST
┌────────▼─────────────┐
│  后端 (Flask)         │  http://127.0.0.1:5000
│  ├─ 路由层 (Blueprint)│
│  ├─ 服务层            │
│  │  ├─ LLMService    │  → DeepSeek API
│  │  ├─ DocumentService│ → 文档解析+向量化
│  │  ├─ VectorStore   │  → ChromaDB
│  │  └─ ReportService │  → 周报生成
│  └─ DAO 层            │  → SQLite
└──────────────────────┘
```

---

## 功能模块

### 1. 智能对话 (Chat)
- 基于上传文档的 RAG 增强问答
- 多轮对话上下文记忆
- 关联文档筛选
- AI 回答附引用来源

### 2. 资料库 (Documents)
- 支持格式：PDF、PPTX、DOCX、Markdown、TXT
- 上传后自动解析 → 分块 → 向量化 → 入库
- 文档状态追踪（processing / ready / error）
- 文档删除（级联清理向量+数据库+文件）

### 3. 知识测评 (Quiz)
- AI 自动从文档内容生成测评题
- 题型：选择题、判断题、简答题
- 提交后 AI 自动评判+给出反馈
- 测评历史记录

### 4. 学习进度 (Progress)
- 按文档追踪学习状态（未开始/学习中/已完成）
- 知识点掌握度追踪
- 薄弱知识点识别
- 学习时长记录
- 掌握度雷达图

### 5. 周报 (Weekly Report)
- 基于学习数据 AI 自动生成周报
- 支持自定义日期范围
- 历史报告存档

---

## 数据库设计 (9 张表)

| 表名 | 说明 |
|------|------|
| documents | 文档元数据 |
| document_chunks | 文档分块 |
| conversations | 对话会话 |
| messages | 对话消息 |
| learning_progress | 学习进度 |
| study_sessions | 学习会话记录 |
| knowledge_points | 知识点掌握度 |
| assessments | 测评会话 |
| assessment_questions | 测评题目 |
| weekly_reports | 周报存档 |

---

## API 端点 (共 20+)

- `GET /api/health` — 健康检查
- `GET/POST/DELETE /api/documents` — 文档管理
- `POST /api/documents/upload` — 上传文档
- `GET/POST/DELETE /api/conversations` — 对话管理
- `POST /api/conversations/<id>/messages` — RAG 消息
- `POST /api/practice/generate` — 生成练习题
- `GET /api/progress/*` — 进度数据
- `POST /api/assessments` — 创建测评
- `POST /api/assessments/<id>/submit` — 提交答案
- `POST /api/reports/generate` — 生成周报

---

## 当前运行数据

- 已上传 3 篇文档（PM 学习主题）
- 3 个 ChromaDB 向量集合
- 1 份示例周报（2026-04-25）

---

## v1.0 已知局限

1. **无用户认证** — 单用户本地应用，无多用户支持
2. **同步处理** — 文档解析和 AI 调用同步阻塞，大文件需等待
3. **单文档集合** — 每个文档独立 ChromaDB 集合，跨文档检索效率低
4. **无测试覆盖** — 无单元测试、集成测试
5. **无日志系统** — logs/ 目录为空，问题排查困难
6. **嵌入模型老旧** — all-MiniLM-L6-v2 已非最佳选择
7. **前端双轨制** — Streamlit + HTML 两套前端并存，维护成本高
8. **单 LLM 支持** — 仅对接 DeepSeek，未支持多模型切换
9. **无流式输出** — LLM 响应需等待全部完成后才返回
10. **桌面端体验弱** — 需手动启动，无系统托盘/开机自启
