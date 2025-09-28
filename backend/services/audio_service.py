import os
import uuid
import logging
import asyncio
import json
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, Union, List
from backend.services.dashscope_service import dashscope_service
from backend.utils.redis_client import redis_client
from config.settings import settings
from dashscope.audio.asr import RecognitionCallback, RecognitionResult

logger = logging.getLogger(__name__)

class AudioService:
    """音频服务类"""
    
    def __init__(self):
        self.dashscope = dashscope_service
        self.redis = redis_client
        self.audio_dir = os.path.join(settings.UPLOAD_FOLDER, 'audio')
        self._ensure_audio_dir()
        # 存储活跃的语音识别会话
        self.active_sessions = {}
        # 存储语音识别回调处理器
        self.recognition_callbacks = {}
    
    def _ensure_audio_dir(self):
        """确保音频目录存在"""
        try:
            os.makedirs(self.audio_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"创建音频目录失败: {e}")
    
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
    
    async def start_realtime_speech_synthesis(
        self, 
        text: str, 
        voice: str = 'zhifeng',
        format: str = 'pcm',
        sample_rate: int = 24000
    ) -> Dict[str, Any]:
        """
        开始实时语音合成
        
        Args:
            text: 要合成的文本
            voice: 音色
            format: 音频格式
            sample_rate: 采样率
            
        Returns:
            合成结果
        """
        try:
            # 调用实时语音合成服务
            result = await self.dashscope.start_realtime_speech_synthesis(
                text=text,
                voice=voice,
                format=format,
                sample_rate=sample_rate
            )
            
            return result
            
        except Exception as e:
            logger.error(f"启动实时语音合成异常: {e}")
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

    
    async def get_available_voices(self) -> List[str]:
        """获取可用音色列表"""
        try:
            return await self.dashscope.get_available_voices()
        except Exception as e:
            logger.error(f"获取音色列表异常: {e}")
            return ['zhifeng']  # 返回默认音色


    async def start_real_time_speech_recognition(
        self, 
        user_id: str,
        character_id: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        开始实时语音识别
        
        Args:
            user_id: 用户ID
            character_id: 角色ID
            conversation_id: 对话ID（可选）
            
        Returns:
            识别会话信息
        """
        try:
            # 生成会话ID
            session_id = str(uuid.uuid4())
            
            # 创建识别回调处理器
            class RecognitionCallbackHandler(RecognitionCallback):
                def __init__(self, session_id, audio_service):
                    super().__init__()
                    self.session_id = session_id
                    self.audio_service = audio_service
                    self.final_text = ""
                
                def on_open(self) -> None:
                    logger.info(f"语音识别连接已打开: {self.session_id}")
                
                def on_close(self) -> None:
                    logger.info(f"语音识别连接已关闭: {self.session_id}")
                    # 不再在连接关闭时立即移除会话，而是在stop_real_time_speech_recognition中处理
                    # 这样可以确保stop_real_time_speech_recognition方法能获取到最终的识别文本
                
                def on_event(self, result: RecognitionResult) -> None:
                    try:
                        sentence = result.get_sentence()
                        if isinstance(sentence, dict):
                            # 检查是否是最终识别结果
                            if sentence.get('end_time') is not None:
                                text = sentence.get('text', '')
                                if text.strip():
                                    # 累积最终文本，而不是覆盖
                                    if self.final_text:
                                        self.final_text += " " + text
                                    else:
                                        self.final_text = text
                                    logger.info(f"识别到最终文本片段: {text}")
                                    # 将累积的识别结果存储到会话中
                                    if self.session_id in self.audio_service.active_sessions:
                                        self.audio_service.active_sessions[self.session_id]['recognized_text'] = self.final_text
                            else:
                                # 中间结果仅用于调试，不存储
                                text = sentence.get('text', '')
                                logger.debug(f"中间识别结果: {text}")
                    except Exception as e:
                        logger.error(f"处理识别结果异常: {e}")
            
            # 创建回调实例
            callback_handler = RecognitionCallbackHandler(session_id, self)
            
            # 启动语音识别
            from dashscope.audio.asr import Recognition
            recognition = Recognition(
                model='paraformer-realtime-v2',
                format='pcm',
                sample_rate=16000,
                callback=callback_handler
            )
            
            # 启动识别
            recognition.start()
            
            # 创建会话数据
            session_data = {
                'user_id': user_id,
                'character_id': character_id,
                'conversation_id': conversation_id,
                'created_at': datetime.now(),
                'active': True,
                'recognized_text': '',  # 初始化为空字符串
                'recognition_instance': recognition,
                'callback_handler': callback_handler
            }
            
            # 存储会话和回调处理器
            self.active_sessions[session_id] = session_data
            self.recognition_callbacks[session_id] = callback_handler
            
            logger.info(f"开始实时语音识别会话: {session_id}")
            
            return {
                'success': True,
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"启动实时语音识别异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def stop_real_time_speech_recognition(
        self, 
        session_id: str
    ) -> Dict[str, Any]:
        """
        停止实时语音识别
        
        Args:
            session_id: 会话ID
            
        Returns:
            操作结果
        """
        try:
            final_text = ""
            if session_id in self.active_sessions:
                session_data = self.active_sessions[session_id]
                recognition = session_data.get('recognition_instance')
                
                # 获取最终识别文本
                final_text = session_data.get('recognized_text', '')
                
                # 停止识别
                if recognition:
                    try:
                        recognition.stop()
                    except Exception as e:
                        logger.error(f"停止语音识别异常: {e}")
                
                # 从活跃会话中移除
                del self.active_sessions[session_id]
                
                logger.info(f"停止实时语音识别会话: {session_id}")
            
            # 也从回调处理器中移除
            if session_id in self.recognition_callbacks:
                del self.recognition_callbacks[session_id]
            
            return {
                'success': True,
                'text': final_text
            }
            
        except KeyError as e:
            logger.warning(f"会话ID不存在: {e}")
            return {
                'success': True,  # 即使会话不存在，也返回成功
            }
        except Exception as e:
            logger.error(f"停止实时语音识别异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def process_audio_stream(
        self, 
        session_id: str,
        audio_data: List[int]
    ) -> Dict[str, Any]:
        """
        处理音频流数据
        
        Args:
            session_id: 会话ID
            audio_data: 音频数据（PCM格式）
            
        Returns:
            处理结果
        """
        try:
            # 检查会话是否存在且活跃
            if session_id not in self.active_sessions:
                return {
                    'success': False,
                    'error': '会话不存在'
                }
            
            session_data = self.active_sessions[session_id]
            if not session_data.get('active', False):
                return {
                    'success': False,
                    'error': '会话已停止'
                }
            
            # 获取识别实例
            recognition = session_data.get('recognition_instance')
            if not recognition:
                return {
                    'success': False,
                    'error': '识别实例不存在'
                }
            
            # 将音频数据转换为bytes
            audio_bytes = np.array(audio_data, dtype=np.int16).tobytes()
            
            # 发送音频数据到识别服务
            recognition.send_audio_frame(audio_bytes)
            
            # 不再立即返回识别到的文本，而是只在会话结束时返回
            return {
                'success': True
            }
            
        except Exception as e:
            logger.error(f"处理音频流异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# 创建全局音频服务实例
audio_service = AudioService()