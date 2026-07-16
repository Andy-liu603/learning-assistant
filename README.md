# AI 学习助手 v2.5

> RAG 增强个人学习系统 — 上传资料、AI 问答、掌握度追踪，形成学习闭环。

[![Version](https://img.shields.io/badge/version-2.5-blue)](.) [![License](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![Tests](https://img.shields.io/badge/tests-28%20passed-brightgreen)](.)

## 产品定位

将「阅读」变成「掌握」的量化学习过程：上传资料 → 自动解析+向量化 → AI 问答+出题 → 掌握度追踪 → 学习闭环。

## 版本历程

| 版本 | 阶段 | 核心能力 |
|------|------|---------|
| v2.5 | 深度化 | 统一向量集合 + 语义切分 + 长期用户记忆（AI 眼中的你） |
| v2.4 | 通用化 | 全科定位 + 学习计划 + 学习仪表盘 |
| v2.3 | 增长 | 多模态（GLM-4.6V）+ 测评闭环 |
| v2.1 | 起步 | 杂志大刊风 AI 学习助手 |

## 技术架构

```
┌──────────────────────────────────────────────────┐
│  前端：纯 JS SPA (Hash路由) + ECharts + IndexedDB   │
├──────────────────────────────────────────────────┤
│  后端：Flask (8蓝图, 55+ API) + JWT + SSH + Limiter │
├──────────────────────────────────────────────────┤
│  AI：Multi-Provider LLM + BGE-small-zh-v1.5 本地嵌入│
├──────────────────────────────────────────────────┤
│  数据：SQLite (15表) + ChromaDB (统一集合 + HNSW索引)  │
└──────────────────────────────────────────────────┘
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 .env（填入大模型 API Key）
cp .env.example .env

# 3. 一键启动
python backend/app.py
# 访问 http://127.0.0.1:5000
# API 文档 http://127.0.0.1:5000/api/docs/
```

## 项目文档

| 文档 | 类型 | 说明 |
|------|------|------|
| [01-PRD产品需求文档.md](docs/01-PRD产品需求文档.md) | 产品 | 用户画像 + 竞品分析 + 功能矩阵 + 路线图 |
| [02-用户画像与验证方案.md](docs/02-用户画像与验证方案.md) | 产品 | 3 个用户画像 + 使用路径 + 验证方式 |
| [03-RAG自实验设计.md](docs/03-RAG自实验设计.md) | 产品 | RAG vs 传统阅读对照实验 |
| [04-系统架构文档.md](docs/04-系统架构文档.md) | 技术 | 四层架构图 + ER 图 + 安全设计 |
| [05-核心模块文档.md](docs/05-核心模块文档.md) | 技术 | 9 个模块 API + 数据流 + 设计决策 |
| [06-后端技术选型说明.md](docs/06-后端技术选型说明.md) | PM+技术 | 每个技术决策的"为什么" |
| [07-前端技术选型说明.md](docs/07-前端技术选型说明.md) | PM+技术 | Vanilla JS 选择的产品思维论证 |
| [08-安全检查报告.md](docs/08-安全检查报告.md) | 质量 | XSS/SQL注入/CSRF 五维安全审计 |
| [09-UX用户体验报告.md](docs/09-UX用户体验报告.md) | 质量 | 5 条操作路径 + 性能基准 + 兼容性 |
| [10-手动测试方案.md](docs/10-手动测试方案.md) | QA | 27 个用例覆盖 7 大模块 |

## 技术栈

- **后端**: Flask 3.1（8 蓝图，55+ API）+ JWT + 速率限制
- **数据**: SQLite（15 表）+ ChromaDB（统一集合，HNSW 索引）
- **AI**: DeepSeek + GLM-4.6V（OpenAI 兼容协议）+ BGE-small-zh-v1.5 本地嵌入
- **前端**: Vanilla JS SPA（Hash 路由）+ ECharts + IndexedDB
- **质量**: pytest 28 用例 + Swagger 文档 + 安全审计

## v2.5 核心更新

- **统一向量集合** — 每用户一个 ChromaDB collection，跨文档一次检索
- **语义切分升级** — 中文句感知 + 表格保护，chunk=800 / overlap=150
- **长期用户记忆** — 对话后提取学习画像，注入 system prompt（"AI 眼中的你"）
- **掌握度阈值优化** — L2 备选路径 + L3 薄弱点消除

详细变更见 [CHANGELOG.md](CHANGELOG.md)。

## 许可

[MIT](LICENSE) · 个人作品集，展示 AI 应用全链路能力。

