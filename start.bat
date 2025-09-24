@echo off
echo =============================================
echo RoleVerse AI角色扮演聊天网站启动脚本
echo =============================================

echo.
echo 正在激活conda环境...
call conda activate langchain
if %errorlevel% neq 0 (
    echo 错误: 无法激活langchain环境
    echo 请确保已安装conda并创建了langchain环境
    pause
    exit /b 1
)

echo.
echo 正在安装Python依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误: 依赖安装失败
    pause
    exit /b 1
)

echo.
echo 检查Redis连接...
python -c "import redis; r = redis.Redis(host='localhost', port=6379); r.ping(); print('Redis连接正常')" 2>nul
if %errorlevel% neq 0 (
    echo 警告: Redis连接失败，请确保Redis服务正在运行
    echo 如果没有安装Redis，可以：
    echo 1. 下载Redis for Windows
    echo 2. 或使用Docker: docker run -d -p 6379:6379 redis
    echo.
    echo 是否继续启动应用？（Redis连接失败时部分功能可能不可用）
    pause
)

echo.
echo 配置检查...
if not exist ".env" (
    echo 警告: .env文件不存在，使用默认配置
    echo 请编辑.env文件并添加您的百炼平台API密钥
)

echo.
echo 正在启动RoleVerse应用...
echo 应用将在 http://localhost:5000 启动
echo 首次启动可能需要一些时间来初始化...
echo.

python app.py

echo.
echo 应用已停止
pause