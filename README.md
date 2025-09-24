# RoleVerse - AI角色扮演聊天网站

一个基于AI大模型的角色扮演聊天网站，用户可以与不同的虚拟角色进行语音和文字对话。

## 技术栈

- **后端**: Python + Flask + LangChain 0.3
- **前端**: HTML + CSS + JavaScript  
- **数据库**: Redis
- **AI服务**: 阿里百炼平台 (Qwen系列模型)
- **语音**: 语音识别 + 语音合成

## 功能特性

1. **用户系统**: 伪账户登录，个人对话记录管理
2. **角色扮演**: 支持各种虚拟角色，如哈利波特、苏格拉底等
3. **多模态交互**: 支持文字和语音对话
4. **对话管理**: 按角色分类的对话记录，支持历史记录查看
5. **智能头像**: 根据角色动态生成头像
6. **实时语音**: 语音识别和合成，波浪动画效果

## 项目结构

```
RoleVerse/
├── app.py                 # Flask应用入口
├── requirements.txt       # Python依赖
├── config/
│   └── settings.py       # 配置文件
├── backend/
│   ├── models/           # 数据模型
│   ├── services/         # 业务逻辑服务
│   ├── utils/           # 工具类
│   └── api/             # API接口
├── frontend/            # 前端页面
├── static/             # 静态资源
│   ├── css/
│   ├── js/
│   └── images/
└── templates/          # HTML模板
```

## 安装和运行

1. 激活环境：
```bash
conda activate langchain
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量（在config/settings.py中设置）

4. 启动应用：
```bash
python app.py
```

## 环境配置

- 需要配置阿里百炼平台的API密钥
- 需要Redis服务运行在本地或配置远程Redis