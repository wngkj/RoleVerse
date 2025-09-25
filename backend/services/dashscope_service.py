import asyncio
import base64
import json
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
from datetime import datetime
import requests
from config.settings import settings

# 尝试导入pyaudio，如果失败则设置为None
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    pyaudio = None
    PYAUDIO_AVAILABLE = False
    logging.warning("PyAudio未安装，语音识别功能将受限")

from dashscope.audio.asr import (Recognition, RecognitionCallback, RecognitionResult)

logger = logging.getLogger(__name__)

class DashScopeService:
    """阿里百炼平台服务类"""
    
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.chat_model = settings.CHAT_MODEL
        self.speech_recognition_model = settings.SPEECH_RECOGNITION_MODEL
        self.speech_synthesis_model = settings.SPEECH_SYNTHESIS_MODEL
        self.image_generation_model = settings.IMAGE_GENERATION_MODEL
        
        # API端点
        self.base_url = "https://dashscope.aliyuncs.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.8,
        max_tokens: int = 2000,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        对话补全
        
        Args:
            messages: 对话消息列表，格式如 [{"role": "user", "content": "hello"}]
            temperature: 温度参数
            max_tokens: 最大令牌数
            stream: 是否流式输出
            
        Returns:
            对话响应
        """
        try:
            url = f"{self.base_url}/services/aigc/text-generation/generation"
            
            payload = {
                "model": self.chat_model,
                "input": {
                    "messages": messages
                },
                "parameters": {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "result_format": "message"
                }
            }
            
            if stream:
                payload["parameters"]["incremental_output"] = True
            
            # 使用异步HTTP请求
            response = await self._make_async_request("POST", url, json=payload)
            
            if response.get("status_code") == 200:
                output = response.get("output", {})
                choices = output.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    return {
                        'success': True,
                        'content': content,
                        'usage': response.get("usage", {}),
                        'request_id': response.get("request_id", "")
                    }
            
            return {
                'success': False,
                'error': response.get("message", "未知错误")
            }
                
        except Exception as e:
            logger.error(f"对话补全异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def speech_recognition(self, audio_data: Optional[bytes] = None, format: str = 'pcm') -> Dict[str, Any]:
        """
        实时语音识别
        
        Args:
            audio_data: 音频数据（用于文件识别，此处保留但不使用）
            format: 音频格式
            
        Returns:
            识别结果
        """
        try:
            # 检查PyAudio是否可用
            if not PYAUDIO_AVAILABLE or pyaudio is None:
                return {
                    'success': False,
                    'error': 'PyAudio未安装，无法进行实时语音识别。请安装PyAudio库。'
                }
            
            # 创建回调类处理识别结果
            class RecognitionCallbackImpl(RecognitionCallback):
                def __init__(self):
                    self.final_text = None
                    self.stop = False
                    self.process = None

                def on_open(self) -> None:
                    print('RecognitionCallback open.')
                    # 使用 PyAudio 进行音频录制
                    if pyaudio is not None:
                        p = pyaudio.PyAudio()
                        # 配置音频流
                        stream = p.open(format=pyaudio.paInt16,
                                        channels=1,
                                        rate=16000,
                                        input=True,
                                        frames_per_buffer=3200)
                        self.process = stream

                def on_close(self) -> None:
                    print('RecognitionCallback close.')
                    if self.process:
                        self.process.stop_stream()
                        self.process.close()
                        self.process = None

                def on_event(self, result: RecognitionResult) -> None:
                    sentence = result.get_sentence()
                    # 如果返回的 sentence 是字典类型并且 'end_time' 不为 None，表示识别结束
                    if isinstance(sentence, dict) and sentence.get('end_time') is not None:
                        print('Final sentence: ', sentence.get('text'))
                        self.final_text = sentence.get('text')
                        self.stop = True
                    print('RecognitionCallback sentence: ', sentence)

            # 创建回调实例
            callback = RecognitionCallbackImpl()
            
            # 创建识别实例
            recognition = Recognition(
                model='paraformer-realtime-v2',
                format='pcm',
                sample_rate=16000,
                callback=callback
            )
            
            # 启动识别
            recognition.start()
            
            # 模拟音频数据流处理
            try:
                while not callback.stop:
                    if callback.process and pyaudio is not None:
                        # 从 PyAudio 流中读取音频数据
                        data = callback.process.read(3200)
                        if data:
                            recognition.send_audio_frame(data)
                    else:
                        print("Process is None.")
                        break
            except Exception as e:
                print(f"音频处理异常: {e}")
            finally:
                recognition.stop()
                if callback.process:
                    callback.process.stop_stream()
                    callback.process.close()
            
            # 返回识别结果
            if callback.final_text:
                return {
                    'success': True,
                    'text': callback.final_text
                }
            else:
                return {
                    'success': False,
                    'error': '未识别到有效语音内容'
                }
                
        except Exception as e:
            logger.error(f"语音识别异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def speech_synthesis(  # pyright: ignore[reportUnreachable]
        self, 
        text: str, 
        voice: str = 'zhifeng',
        format: str = 'wav',
        sample_rate: int = 16000
    ) -> Dict[str, Any]:
        """
        语音合成
        
        Args:
            text: 要合成的文本
            voice: 音色
            format: 音频格式
            sample_rate: 采样率
            
        Returns:
            合成结果
        """
        try:
            url = f"{self.base_url}/services/audio/tts/speech-synthesis"
            
            payload = {
                "model": self.speech_synthesis_model,
                "input": {
                    "text": text
                },
                "parameters": {
                    "voice": voice,
                    "format": format,
                    "sample_rate": sample_rate
                }
            }
            
            response = await self._make_async_request("POST", url, json=payload)
            
            if response.get("status_code") == 200:
                output = response.get("output", {})
                audio_url = output.get("audio_url", "")
                
                # 如果有音频URL，下载音频数据
                audio_data = None
                if audio_url:
                    audio_data = await self._download_audio(audio_url)
                
                return {
                    'success': True,
                    'audio_data': audio_data,
                    'audio_url': audio_url,
                    'request_id': response.get("request_id", "")
                }
            
            return {
                'success': False,
                'error': response.get("message", "语音合成失败")
            }
                
        except Exception as e:
            logger.error(f"语音合成异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def generate_character_avatar(
        self, 
        character_name: str, 
        character_description: str,
        style: str = 'anime'
    ) -> Dict[str, Any]:
        """
        生成角色头像
        
        Args:
            character_name: 角色名称
            character_description: 角色描述
            style: 图片风格
            
        Returns:
            生成结果
        """
        try:
            # 构建提示词
            prompt = f"Portrait of {character_name}, {character_description}, {style} style, high quality, detailed"
            
            url = f"{self.base_url}/services/aigc/image-synthesis/generation"
            
            payload = {
                "model": self.image_generation_model,
                "input": {
                    "prompt": prompt
                },
                "parameters": {
                    "size": "512*512",
                    "n": 1
                }
            }
            
            response = await self._make_async_request("POST", url, json=payload)
            
            if response.get("status_code") == 200:
                output = response.get("output", {})
                results = output.get("results", [])
                if results:
                    image_url = results[0].get("url", "")
                    return {
                        'success': True,
                        'image_url': image_url,
                        'request_id': response.get("request_id", "")
                    }
            
            return {
                'success': False,
                'error': response.get("message", "头像生成失败")
            }
                
        except Exception as e:
            logger.error(f"头像生成异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _make_async_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """异步HTTP请求"""
        try:
            def make_request():
                if method.upper() == "POST":
                    response = requests.post(url, headers=self.headers, **kwargs)
                else:
                    response = requests.get(url, headers=self.headers, **kwargs)
                
                if response.status_code == 200:
                    result = response.json()
                    result["status_code"] = 200
                    return result
                else:
                    return {
                        "status_code": response.status_code,
                        "message": response.text
                    }
            
            return await asyncio.get_event_loop().run_in_executor(None, make_request)
            
        except Exception as e:
            logger.error(f"HTTP请求异常: {e}")
            return {
                "status_code": 500,
                "message": str(e)
            }
    
    async def _download_audio(self, audio_url: str) -> Optional[bytes]:
        """下载音频数据"""
        try:
            def download():
                response = requests.get(audio_url)
                if response.status_code == 200:
                    return response.content
                return None
            
            return await asyncio.get_event_loop().run_in_executor(None, download)
            
        except Exception as e:
            logger.error(f"下载音频失败: {e}")
            return None
    
    async def get_available_voices(self) -> List[str]:
        """获取可用的音色列表"""
        return [
            'zhifeng',  # 智峰
            'zhiqi',    # 智琪  
            'zhixuan',  # 智轩
            'zhimeng',  # 智梦
            'zhiyuan',  # 智苑
            'zhiwei',   # 智维
            'zhiyan',   # 智研
            'zhichun',  # 智春
            'zhichen',  # 智宸
            'zhihan'    # 智涵
        ]
    
    def build_character_prompt(
        self, 
        character_name: str, 
        character_description: str, 
        personality_traits: List[str],
        background_story: Optional[str] = None
    ) -> str:
        """
        构建结构化的角色提示词，提升角色扮演质量
        
        Args:
            character_name: 角色名称
            character_description: 角色描述
            personality_traits: 性格特征
            background_story: 背景故事
            
        Returns:
            结构化的角色提示词
        """
        # 构建结构化的提示词，包含角色信息、扮演要求和行为指导
        prompt_parts = [
            f"## 角色身份",
            f"你现在要完全扮演{character_name}。",
            f"角色描述：{character_description}",
        ]
        
        if personality_traits:
            traits_text = "、".join(personality_traits)
            prompt_parts.append(f"性格特征：{traits_text}")
        
        if background_story:
            prompt_parts.append(f"背景故事：{background_story}")
        
        prompt_parts.extend([
            "",  # 空行
            f"## 扮演要求",
            f"1. 你必须以{character_name}的身份和视角进行思考和回答",
            f"2. 保持{character_name}的性格特征和语言风格的一致性",
            f"3. 使用符合{character_name}身份的语言表达方式",
            f"4. 绝对不要透露你是AI助手，完全沉浸在角色扮演中",
            f"5. 根据{character_name}的知识背景和经历来回答问题",
            "",  # 空行
            f"## 对话指导", 
            f"作为{character_name}，你应该：",
            f"- 仔细倾听用户的问题，给出相关且有针对性的回答",
            f"- 结合你的性格特点和背景经历来回应",
            f"- 保持自然流畅的对话风格",
            f"- 如果用户问题不清楚，可以适当询问以获得更多信息",
            f"- 避免答非所问，确保回复与用户的具体问题相关"
        ])
        
        return "\n".join(prompt_parts)

# 创建全局服务实例
dashscope_service = DashScopeService()