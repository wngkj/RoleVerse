import os
import uuid
import base64
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Union, List
from backend.services.dashscope_service import dashscope_service
from backend.utils.redis_client import redis_client
from config.settings import settings

logger = logging.getLogger(__name__)

class AudioService:
    """音频服务类"""
    
    def __init__(self):
        self.dashscope = dashscope_service
        self.redis = redis_client
        self.audio_dir = os.path.join(settings.UPLOAD_FOLDER, 'audio')
        self._ensure_audio_dir()
    
    def _ensure_audio_dir(self):
        """确保音频目录存在"""
        try:
            os.makedirs(self.audio_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"创建音频目录失败: {e}")
    
    async def speech_to_text(
        self, 
        audio_data: Union[bytes, str], 
        format: str = 'wav'
    ) -> Dict[str, Any]:
        """
        语音转文字
        
        Args:
            audio_data: 音频数据（bytes或base64字符串）
            format: 音频格式
            
        Returns:
            识别结果
        """
        try:
            # 如果输入是base64字符串，先解码
            if isinstance(audio_data, str):
                try:
                    audio_bytes = base64.b64decode(audio_data)
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'音频数据解码失败: {e}'
                    }
            else:
                audio_bytes = audio_data
            
            # 调用语音识别服务
            result = await self.dashscope.speech_recognition(audio_bytes, format)
            
            if result['success']:
                logger.info(f"语音识别成功: {result['text']}")
            else:
                logger.error(f"语音识别失败: {result['error']}")
            
            return result
            
        except Exception as e:
            logger.error(f"语音转文字异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def text_to_speech(
        self, 
        text: str, 
        voice: str = 'zhifeng',
        format: str = 'wav',
        save_file: bool = True
    ) -> Dict[str, Any]:
        """
        文字转语音
        
        Args:
            text: 要转换的文本
            voice: 音色
            format: 音频格式
            save_file: 是否保存文件
            
        Returns:
            合成结果
        """
        try:
            # 调用语音合成服务
            result = await self.dashscope.speech_synthesis(
                text=text,
                voice=voice,
                format=format
            )
            
            if not result['success']:
                return result
            
            audio_data = result.get('audio_data')
            if not audio_data:
                return {
                    'success': False,
                    'error': '未获取到音频数据'
                }
            
            # 保存音频文件（如果需要）
            audio_url = None
            if save_file:
                audio_url = await self._save_audio_file(audio_data, format)
            
            return {
                'success': True,
                'audio_data': audio_data,
                'audio_url': audio_url,
                'text': text,
                'voice': voice,
                'format': format
            }
            
        except Exception as e:
            logger.error(f"文字转语音异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _save_audio_file(self, audio_data: bytes, format: str) -> Optional[str]:
        """
        保存音频文件
        
        Args:
            audio_data: 音频数据
            format: 音频格式
            
        Returns:
            文件URL
        """
        try:
            # 生成文件名
            file_id = str(uuid.uuid4())
            filename = f"{file_id}.{format}"
            file_path = os.path.join(self.audio_dir, filename)
            
            # 写入文件
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            # 生成URL
            audio_url = f"/static/uploads/audio/{filename}"
            
            # 缓存文件信息
            file_info = {
                'file_id': file_id,
                'filename': filename,
                'file_path': file_path,
                'url': audio_url,
                'format': format,
                'size': len(audio_data),
                'created_at': datetime.now().isoformat()
            }
            
            file_key = f"audio_file:{file_id}"
            self.redis.set_data(file_key, file_info, expire=86400)  # 24小时过期
            
            return audio_url
            
        except Exception as e:
            logger.error(f"保存音频文件异常: {e}")
            return None
    
    async def get_audio_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """获取音频文件信息"""
        try:
            file_key = f"audio_file:{file_id}"
            return self.redis.get_data(file_key)
        except Exception as e:
            logger.error(f"获取音频文件信息异常: {e}")
            return None
    
    async def delete_audio_file(self, file_id: str) -> bool:
        """删除音频文件"""
        try:
            # 获取文件信息
            file_info = await self.get_audio_file_info(file_id)
            if not file_info:
                return False
            
            # 删除物理文件
            file_path = file_info.get('file_path')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            
            # 删除缓存信息
            file_key = f"audio_file:{file_id}"
            self.redis.delete_data(file_key)
            
            return True
            
        except Exception as e:
            logger.error(f"删除音频文件异常: {e}")
            return False
    
    async def process_voice_chat(
        self, 
        audio_data: Union[bytes, str],
        user_id: str,
        character_id: str,
        conversation_id: Optional[str] = None,
        voice: str = 'zhifeng'
    ) -> Dict[str, Any]:
        """
        处理语音聊天
        
        Args:
            audio_data: 用户语音数据
            user_id: 用户ID
            character_id: 角色ID
            conversation_id: 对话ID（可选）
            voice: AI回复音色
            
        Returns:
            处理结果
        """
        try:
            # 1. 语音转文字
            stt_result = await self.speech_to_text(audio_data)
            if not stt_result['success']:
                return {
                    'success': False,
                    'error': f"语音识别失败: {stt_result['error']}"
                }
            
            user_text = stt_result['text']
            if not user_text.strip():
                return {
                    'success': False,
                    'error': '未识别到有效语音内容'
                }
            
            # 2. 获取AI文字回复（这里需要调用对话服务）
            from backend.services.conversation_service import conversation_service
            from backend.models.data_models import ChatRequest, MessageType
            
            chat_request = ChatRequest(
                user_id=user_id,
                character_id=character_id,
                conversation_id=conversation_id,
                message=user_text,
                message_type=MessageType.AUDIO
            )
            
            chat_response = await conversation_service.chat(chat_request)
            ai_text = chat_response.response
            
            # 3. AI文字转语音
            tts_result = await self.text_to_speech(
                text=ai_text,
                voice=voice,
                save_file=True
            )
            
            if not tts_result['success']:
                # 如果语音合成失败，至少返回文字回复
                return {
                    'success': True,
                    'user_text': user_text,
                    'ai_text': ai_text,
                    'ai_audio_url': None,
                    'conversation_id': chat_response.conversation_id,
                    'message_id': chat_response.message_id,
                    'warning': f"语音合成失败: {tts_result['error']}"
                }
            
            return {
                'success': True,
                'user_text': user_text,
                'ai_text': ai_text,
                'ai_audio_url': tts_result['audio_url'],
                'conversation_id': chat_response.conversation_id,
                'message_id': chat_response.message_id,
                'character_avatar_url': chat_response.character_avatar_url
            }
            
        except Exception as e:
            logger.error(f"处理语音聊天异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_available_voices(self) -> List[str]:
        """获取可用音色列表"""
        try:
            return await self.dashscope.get_available_voices()
        except Exception as e:
            logger.error(f"获取音色列表异常: {e}")
            return ['zhifeng']  # 返回默认音色
    
    async def cleanup_old_files(self, days: int = 7) -> int:
        """
        清理旧音频文件
        
        Args:
            days: 清理多少天前的文件
            
        Returns:
            清理的文件数量
        """
        try:
            cleanup_count = 0
            cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
            
            # 遍历音频目录
            for filename in os.listdir(self.audio_dir):
                file_path = os.path.join(self.audio_dir, filename)
                
                # 检查文件修改时间
                if os.path.isfile(file_path):
                    file_mtime = os.path.getmtime(file_path)
                    if file_mtime < cutoff_time:
                        try:
                            os.remove(file_path)
                            cleanup_count += 1
                            logger.debug(f"清理旧音频文件: {filename}")
                        except Exception as e:
                            logger.error(f"删除文件失败 {filename}: {e}")
            
            logger.info(f"音频文件清理完成，共清理 {cleanup_count} 个文件")
            return cleanup_count
            
        except Exception as e:
            logger.error(f"清理音频文件异常: {e}")
            return 0

# 创建全局音频服务实例
audio_service = AudioService()