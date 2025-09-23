# RoleVerse 安装和运行指南

## 系统要求

- Python 3.8+
- Conda 环境管理器
- Redis 数据库
- 阿里百炼平台API密钥

## 安装步骤

### 1. 创建和激活Conda环境

```bash
# 创建langchain环境
conda create -n langchain python=3.10 -y

# 激活环境
conda activate langchain
```

### 2. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt
```

### 3. 安装和启动Redis

#### Windows方案1：使用Docker
```bash
docker run -d -p 6379:6379 --name redis redis:latest
```

#### Windows方案2：下载Redis for Windows
1. 从 https://github.com/tporadowski/redis/releases 下载Redis
2. 解压并运行 `redis-server.exe`

#### Linux/macOS
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS with Homebrew
brew install redis
brew services start redis
```

### 4. 配置API密钥

1. 复制 `.env.example` 为 `.env`
2. 在 `.env` 文件中填入您的阿里百炼平台API密钥：

```env
DASHSCOPE_API_KEY=your-actual-api-key-here
```

### 5. 运行应用

#### Windows
```bash
# 运行启动脚本
start.bat
```

#### Linux/macOS
```bash
# 激活环境
conda activate langchain

# 启动应用
python app.py
```

## 访问应用

应用启动后，在浏览器中访问：http://localhost:5000

## 功能说明

### 1. 用户登录
- 输入用户名即可登录（伪登录）
- 首次使用会自动创建账户

### 2. 角色搜索
- 在搜索框中输入角色名称，如"哈利波特"、"苏格拉底"
- 系统预置了一些默认角色

### 3. 文字聊天
- 选择角色后可以进行文字对话
- 支持多轮对话，有上下文记忆

### 4. 语音聊天
- 点击麦克风按钮开始语音录制
- 系统会将语音转为文字，AI回复后再转为语音播放
- 需要浏览器麦克风权限

### 5. 对话记录
- 左侧边栏显示历史对话
- 按角色分类显示
- 点击可重新打开历史对话

## 故障排除

### Redis连接失败
- 确保Redis服务正在运行
- 检查端口6379是否被占用
- 可以暂时忽略Redis错误，应用会使用降级功能

### API调用失败
- 检查网络连接
- 确认API密钥正确
- 查看控制台日志获取详细错误信息

### 语音功能不工作
- 确保浏览器支持语音录制（Chrome、Firefox等现代浏览器）
- 允许网站访问麦克风权限
- 检查麦克风设备是否正常

### 头像不显示
- 如果API密钥配置正确，头像会自动生成
- 没有API密钥时使用默认头像

## 技术架构

- **后端**: Python + Flask + LangChain 0.3
- **前端**: HTML + CSS + JavaScript (原生)
- **数据存储**: Redis
- **AI服务**: 阿里百炼平台 (Qwen系列模型)
- **语音处理**: Web Speech API + 百炼语音服务

## 开发说明

项目结构：
```
RoleVerse/
├── app.py                 # Flask应用入口
├── requirements.txt       # Python依赖
├── start.bat             # Windows启动脚本
├── config/
│   └── settings.py       # 配置文件
├── backend/
│   ├── models/           # 数据模型
│   ├── services/         # 业务逻辑
│   └── utils/           # 工具类
├── templates/            # HTML模板
└── static/              # 静态资源
    ├── css/
    ├── js/
    └── images/
```

如有问题，请查看控制台日志或联系开发者。