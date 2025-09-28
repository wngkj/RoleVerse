# RoleVerse - AI角色扮演聊天网站

一个基于AI大模型的角色扮演聊天网站，用户可以与不同的虚拟角色进行对话。

## 🚀 技术栈

- **后端**: Python + Flask + LangChain 0.3
- **前端**: HTML + CSS + JavaScript  
- **数据库**: Redis
- **AI服务**: 阿里百炼平台 (Qwen系列模型)

## ✨ 功能特性

1. **用户系统**: 伪账户登录，个人对话记录管理
2. **角色扮演**: 支持各种虚拟角色，如哈利波特、苏格拉底等
3. **对话管理**: 按角色分类的对话记录，支持历史记录查看、删除对话等
4. **实时语音**: 暂未实现

## 📁 项目结构

```
RoleVerse/
├── app.py                 # Flask应用入口，包含所有API路由和主应用逻辑
├── requirements.txt       # Python依赖包列表
├── config/
│   └── settings.py       # 应用配置文件，包含环境变量和配置参数
├── backend/
│   ├── models/           # 数据模型定义
│   │   └── data_models.py # 数据模型类，如用户、角色、对话等
│   ├── services/         # 业务逻辑服务
│   │   ├── user_service.py      # 用户相关服务，如登录、登出等
│   │   ├── character_service.py # 角色相关服务，如角色创建、搜索等
│   │   ├── conversation_service.py # 对话相关服务，如消息处理、对话管理等
│   │   ├── audio_service.py      # 音频相关服务，如语音识别、语音合成等，语音部分暂未实现
│   │   └── dashscope_service.py # 阿里百炼平台API服务封装
│   └── utils/            # 工具类
│       └── redis_client.py      # Redis数据库连接和操作工具
├── static/               # 静态资源
│   ├── css/             # 样式文件
│   │   ├── style.css    # 主要样式文件
│   │   └── login.css    # 登录页面样式
│   ├── js/              # JavaScript文件
│   │   ├── app.js       # 主应用JavaScript逻辑
│   │   ├── audio.js     # 音频处理相关JavaScript逻辑
│   │   └── login.js     # 登录页面JavaScript逻辑
│   └── images/          # 图片资源
└── templates/           # HTML模板
    ├── index.html       # 主页面模板
    └── login.html       # 登录页面模板
```

## 🛠️ 安装和运行

### 1. 配置环境

```bash
git clone https://github.com/wngkj/RoleVerse.git
conda create -n roleverse python=3.10
conda activate roleverse
cd RoleVerse
pip install -r requirements.txt
```

从阿里云百炼平台获得Dashscope的API密钥，填入到`env.txt`文件中，随后将该文件重命名为`.env`

### 2. 安装Redis

进入该链接下载zip压缩包并解压，打开解压后的文件夹，随后运行`redis-server.exe`
https://github.com/tporadowski/redis/releases

### 3. 启动应用

```bash
python /config/settings.py
python app.py
```

打开浏览器，访问 http://127.0.0.1:5000