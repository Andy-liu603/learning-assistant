# 参与贡献 / Contributing

感谢你关注 **AI 学习助手 2.0**！这是一个个人学习项目（RAG 增强的全科个人学习助手），用于 AI 应用开发方向的作品展示。欢迎提 Issue 与 PR，但请先阅读以下约定。

## 开发环境

```bash
# 1. 克隆
git clone https://github.com/Andy-liu603/learning-assistant.git
cd learning-assistant

# 2. 创建虚拟环境（本项目使用 .venv）
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env             # 然后填入你的 API Key

# 4. 启动
start.bat                        # 或按 backend / frontend 各自的启动说明
```

## 分支与提交

- 主分支为 `master`，请基于它切出特性分支：`feat/xxx`、`fix/xxx`、`docs/xxx`。
- 提交信息建议遵循约定式提交（Conventional Commits）：
  `feat:` 新功能 · `fix:` 修复 · `docs:` 文档 · `chore:` 杂务 · `refactor:` 重构。
- 提交前请确保：`pytest` 通过，且不要提交 `data/`、`*.db`、`*.bin`、`.env` 等生成/敏感文件（已被 `.gitignore` 忽略）。

## 代码风格

- 后端 Python：遵循 PEP 8，关键模块含 docstring。
- 前端：原生 JS（Vanilla）+ Hash 路由，无构建步骤；改 CSS/JS 时记得更新 `?v=N` 版本号以绕过缓存。

## 提 PR 前自查

- [ ] 本地测试通过
- [ ] 没有把密钥、向量库、大文件提交进来
- [ ] README / 相关文档已同步更新（如涉及用户可见变更）

---

> 本项目以学习与展示为目的，不保证长期维护。如有疑问欢迎开 Issue。
