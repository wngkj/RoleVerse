import asyncio
import logging
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from config.settings import settings
from backend.services.user_service import user_service
from backend.services.character_service import character_service
from backend.services.conversation_service import conversation_service
from backend.services.audio_service import audio_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
settings.init_app(app)
CORS(app)

def run_async(coro):
    """运行异步函数的辅助函数"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/login')
def login_page():
    """登录页面"""
    return render_template('login.html')

# ========== 用户相关API ==========

@app.route('/api/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get('username')
        
        if not username:
            return jsonify({'success': False, 'error': '用户名不能为空'}), 400
        
        # 调用用户服务登录
        result = run_async(user_service.login_user(username))
        
        if result['success']:
            # 设置会话
            session['user_id'] = result['user_id']
            session['session_id'] = result['session_id']
            session['username'] = result['username']
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"登录异常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """用户登出"""
    try:
        session_id = session.get('session_id')
        if session_id:
            run_async(user_service.logout_user(session_id))
        
        session.clear()
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"登出异常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user/info', methods=['GET'])
def get_user_info():
    """获取用户信息"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '未登录'}), 401
        
        user = run_async(user_service.get_user_by_id(user_id))
        if user:
            return jsonify({
                'success': True,
                'user': {
                    'user_id': user.user_id,
                    'username': user.username,
                    'email': user.email,
                    'avatar_url': user.avatar_url
                }
            })
        else:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
            
    except Exception as e:
        logger.error(f"获取用户信息异常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== 角色相关API ==========

@app.route('/api/characters', methods=['GET'])
def get_characters():
    """获取角色列表"""
    try:
        limit = request.args.get('limit', 20, type=int)
        characters = run_async(character_service.get_character_list(limit))
        return jsonify({'success': True, 'characters': characters})
        
    except Exception as e:
        logger.error(f"获取角色列表异常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/characters/search', methods=['GET'])
def search_characters():
    """搜索角色"""
    try:
        query = request.args.get('q', '')
        limit = request.args.get('limit', 10, type=int)
        
        if not query:
            return jsonify({'success': False, 'error': '搜索关键词不能为空'}), 400
        
        characters = run_async(character_service.search_characters(query, limit))
        return jsonify({'success': True, 'characters': characters})
        
    except Exception as e:
        logger.error(f"搜索角色异常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/characters/<character_id>', methods=['GET'])
def get_character(character_id):
    """获取角色详情"""
    try:
        character = run_async(character_service.get_character_by_id(character_id))
        if character:
            character_data = character.model_dump()
            character_data['created_at'] = character_data['created_at'].isoformat()
            return jsonify({'success': True, 'character': character_data})
        else:
            return jsonify({'success': False, 'error': '角色不存在'}), 404
            
    except Exception as e:
        logger.error(f"获取角色详情异常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== 对话相关API ==========

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """获取用户对话列表"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '未登录'}), 401
        
        limit = request.args.get('limit', 20, type=int)
        conversations = run_async(conversation_service.get_user_conversations(user_id, limit))
        
        # 转换时间格式
        result = []
        for conv in conversations:
            conv_data = conv.model_dump()
            conv_data['created_at'] = conv_data['created_at'].isoformat()
            conv_data['updated_at'] = conv_data['updated_at'].isoformat()
            result.append(conv_data)
        
        return jsonify({'success': True, 'conversations': result})
        
    except Exception as e:
        logger.error(f"获取对话列表异常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """获取对话详情"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '未登录'}), 401
        
        conversation = run_async(conversation_service.get_conversation(conversation_id))
        if conversation and conversation.user_id == user_id:
            conv_data = conversation.model_dump()
            conv_data['created_at'] = conv_data['created_at'].isoformat()
            conv_data['updated_at'] = conv_data['updated_at'].isoformat()
            
            # 转换消息时间格式
            for msg in conv_data['messages']:
                msg['timestamp'] = msg['timestamp'].isoformat()
            
            return jsonify({'success': True, 'conversation': conv_data})
        else:
            return jsonify({'success': False, 'error': '对话不存在或无权限'}), 404
            
    except Exception as e:
        logger.error(f"获取对话详情异常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """发送聊天消息"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '未登录'}), 401
        
        data = request.get_json()
        character_id = data.get('character_id')
        message = data.get('message')
        conversation_id = data.get('conversation_id')
        
        if not character_id or not message:
            return jsonify({'success': False, 'error': '参数不完整'}), 400
        
        # 创建聊天请求
        from backend.models.data_models import ChatRequest, MessageType
        chat_request = ChatRequest(
            user_id=user_id,
            character_id=character_id,
            conversation_id=conversation_id,
            message=message,
            message_type=MessageType.TEXT
        )
        
        # 处理聊天
        response = run_async(conversation_service.chat(chat_request))
        
        # 转换响应格式
        response_data = response.model_dump()
        response_data['timestamp'] = response_data['timestamp'].isoformat()
        
        return jsonify({'success': True, 'response': response_data})
        
    except Exception as e:
        logger.error(f"聊天异常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== 音频相关API ==========

@app.route('/api/audio/speech-to-text', methods=['POST'])
def speech_to_text():
    """语音转文字"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '未登录'}), 401
        
        data = request.get_json()
        audio_data = data.get('audio_data')  # base64编码的音频
        
        if not audio_data:
            return jsonify({'success': False, 'error': '音频数据不能为空'}), 400
        
        result = run_async(audio_service.speech_to_text(audio_data))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"语音转文字异常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/audio/text-to-speech', methods=['POST'])
def text_to_speech():
    """文字转语音"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '未登录'}), 401
        
        data = request.get_json()
        text = data.get('text')
        voice = data.get('voice', 'zhifeng')
        
        if not text:
            return jsonify({'success': False, 'error': '文本不能为空'}), 400
        
        result = run_async(audio_service.text_to_speech(text, voice))
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"文字转语音异常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/audio/voice-chat', methods=['POST'])
def voice_chat():
    """语音聊天"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '未登录'}), 401
        
        data = request.get_json()
        audio_data = data.get('audio_data')
        character_id = data.get('character_id')
        conversation_id = data.get('conversation_id')
        voice = data.get('voice', 'zhifeng')
        
        if not audio_data or not character_id:
            return jsonify({'success': False, 'error': '参数不完整'}), 400
        
        result = run_async(audio_service.process_voice_chat(
            audio_data=audio_data,
            user_id=user_id,
            character_id=character_id,
            conversation_id=conversation_id,
            voice=voice
        ))
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"语音聊天异常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/audio/voices', methods=['GET'])
def get_voices():
    """获取可用音色列表"""
    try:
        voices = run_async(audio_service.get_available_voices())
        return jsonify({'success': True, 'voices': voices})
        
    except Exception as e:
        logger.error(f"获取音色列表异常: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== 静态文件服务 ==========

@app.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    """提供上传的文件"""
    return send_from_directory(settings.UPLOAD_FOLDER, filename)

# ========== 应用初始化 ==========

def init_app():
    """应用初始化"""
    try:
        # 初始化默认角色
        run_async(character_service.init_default_characters_if_needed())
        logger.info("应用初始化完成")
    except Exception as e:
        logger.error(f"应用初始化异常: {e}")

if __name__ == '__main__':
    logger.info("启动RoleVerse应用...")
    
    # 初始化应用
    init_app()
    
    app.run(
        host=settings.HOST,
        port=settings.PORT,
        debug=settings.DEBUG
    )