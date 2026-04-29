@echo off
chcp 65001 >nul
echo ==========================================
echo   AI学习助手 v2.0 - 启动脚本
echo ==========================================

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

:: 安装依赖（首次运行）
if not exist "backend\__init__.py" (
    echo [INFO] 安装依赖...
    pip install -r requirements.txt -q
)

:: 检查 .env
if not exist ".env" (
    echo [WARN] 未找到 .env 文件，从模板复制...
    copy .env.example .env
    echo [WARN] 请编辑 .env 文件，填入你的 LLM API Key！
    notepad .env
)

:: HuggingFace 离线模式（模型已下载到本地）
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1

echo.
echo [INFO] 启动 Flask 后端 + 前端服务...
echo.

start "AI学习助手" cmd /k "python backend\app.py"

timeout /t 3 /nobreak >nul

:: 自动打开浏览器
start http://127.0.0.1:5000

echo ==========================================
echo   启动完成！
echo   访问: http://127.0.0.1:5000
echo   首次使用请先注册账号
echo ==========================================
echo   关闭窗口即可停止服务
echo ==========================================
pause
