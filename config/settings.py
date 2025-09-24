import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Settings:
    """应用配置类"""
    
    # Flask配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # Redis配置
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    
    # 阿里百炼平台配置
    DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', '')
    
    # 模型配置
    CHAT_MODEL = os.getenv('CHAT_MODEL', 'qwen-plus')
    SPEECH_RECOGNITION_MODEL = os.getenv('SPEECH_RECOGNITION_MODEL', 'paraformer-realtime-v2')
    SPEECH_SYNTHESIS_MODEL = os.getenv('SPEECH_SYNTHESIS_MODEL', 'cosyvoice-v1')
    IMAGE_GENERATION_MODEL = os.getenv('IMAGE_GENERATION_MODEL', 'wanx-v1')
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 会话配置
    SESSION_TIMEOUT = 3600  # 1小时
    MAX_CONVERSATION_LENGTH = 50  # 最大对话轮数
    
    @classmethod
    def init_app(cls, app):
        """初始化Flask应用配置"""
        app.config['SECRET_KEY'] = cls.SECRET_KEY
        app.config['MAX_CONTENT_LENGTH'] = cls.MAX_CONTENT_LENGTH
        
        # 创建上传目录
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)

# 创建全局配置实例
settings = Settings()