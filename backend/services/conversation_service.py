import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from backend.models.data_models import (
    Conversation, Message, ConversationSummary,
    MessageRole, MessageType, ChatRequest, ChatResponse
)
from backend.utils.redis_client import redis_client
from backend.services.dashscope_service import dashscope_service
from backend.services.character_service import character_service

logger = logging.getLogger(__name__)

class ConversationService:
    """对话服务类"""
    
    def __init__(self):
        self.redis = redis_client
        self.dashscope = dashscope_service
        self.character_service = character_service
    
    async def create_conversation(
        self, 
        user_id: str, 
        character_id: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建新对话
        
        Args:
            user_id: 用户ID
            character_id: 角色ID
            title: 对话标题
            
        Returns:
            创建结果
        """
        try:
            # 验证角色是否存在
            character = await self.character_service.get_character_by_id(character_id)
            if not character:
                return {
                    'success': False,
                    'error': '角色不存在'
                }
            
            # 生成对话ID
            conversation_id = str(uuid.uuid4())
            
            # 生成默认标题
            if not title:
                title = f"与{character.name}的对话"
            
            # 创建对话对象
            conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                character_id=character_id,
                title=title,
                messages=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                is_active=True
            )
            
            # 存储到Redis
            conversation_key = f"conversation:{conversation_id}"
            conversation_data = conversation.model_dump()
            conversation_data['created_at'] = conversation_data['created_at'].isoformat()
            conversation_data['updated_at'] = conversation_data['updated_at'].isoformat()
            
            success = self.redis.set_data(conversation_key, conversation_data)
            
            if success:
                # 添加到用户对话列表
                user_conversations_key = f"user_conversations:{user_id}"
                self.redis.list_push(user_conversations_key, conversation_id)
                
                # 添加到角色对话列表
                character_conversations_key = f"character_conversations:{character_id}"
                self.redis.list_push(character_conversations_key, conversation_id)
                
                logger.info(f"对话创建成功: {conversation_id}")
                return {
                    'success': True,
                    'conversation_id': conversation_id,
                    'conversation': conversation_data
                }
            else:
                return {
                    'success': False,
                    'error': '对话创建失败'
                }
                
        except Exception as e:
            logger.error(f"创建对话异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话"""
        try:
            conversation_key = f"conversation:{conversation_id}"
            conversation_data = self.redis.get_data(conversation_key)
            
            if conversation_data:
                # 转换时间字段
                conversation_data['created_at'] = datetime.fromisoformat(conversation_data['created_at'])
                conversation_data['updated_at'] = datetime.fromisoformat(conversation_data['updated_at'])
                
                # 转换消息列表
                messages = []
                for msg_data in conversation_data.get('messages', []):
                    if 'timestamp' in msg_data:
                        msg_data['timestamp'] = datetime.fromisoformat(msg_data['timestamp'])
                    messages.append(Message(**msg_data))
                
                conversation_data['messages'] = messages
                return Conversation(**conversation_data)
            
            return None
            
        except Exception as e:
            logger.error(f"获取对话异常: {e}")
            return None
    
    async def add_message(
        self, 
        conversation_id: str, 
        role: MessageRole,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        audio_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """添加消息到对话"""
        try:
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                return None
            
            # 创建消息
            message_id = str(uuid.uuid4())
            message = Message(
                message_id=message_id,
                conversation_id=conversation_id,
                role=role,
                content=content,
                message_type=message_type,
                audio_url=audio_url,
                metadata=metadata or {},
                timestamp=datetime.now()
            )
            
            # 添加到对话
            conversation.messages.append(message)
            conversation.updated_at = datetime.now()
            
            # 保存对话
            await self._save_conversation(conversation)
            
            return message
            
        except Exception as e:
            logger.error(f"添加消息异常: {e}")
            return None
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        处理聊天请求
        
        Args:
            request: 聊天请求
            
        Returns:
            聊天响应
        """
        try:
            # 获取或创建对话
            conversation = None
            if request.conversation_id:
                conversation = await self.get_conversation(request.conversation_id)
            
            if not conversation:
                # 创建新对话
                result = await self.create_conversation(
                    request.user_id, 
                    request.character_id
                )
                if not result['success']:
                    raise Exception(result['error'])
                
                conversation_id = result['conversation_id']
                conversation = await self.get_conversation(conversation_id)
            else:
                conversation_id = conversation.conversation_id
            
            # 添加用户消息
            user_message = await self.add_message(
                conversation_id,
                MessageRole.USER,
                request.message,
                request.message_type
            )
            
            if not user_message:
                raise Exception("添加用户消息失败")
            
            # 获取角色信息
            character = await self.character_service.get_character_by_id(request.character_id)
            if not character:
                raise Exception("角色不存在")
            
            # 构建对话历史
            if conversation:
                messages = await self._build_chat_messages(conversation, character)
            else:
                messages = [{"role": "system", "content": character.prompt_template}]
            
            # 调用AI生成回复，使用更高的温度参数提升回复多样性
            ai_response = await self.dashscope.chat_completion(messages, temperature=0.8)
            
            if not ai_response['success']:
                raise Exception(f"AI回复生成失败: {ai_response['error']}")
            
            ai_content = ai_response['content']
            
            # 添加AI消息
            ai_message = await self.add_message(
                conversation_id,
                MessageRole.ASSISTANT,
                ai_content,
                MessageType.TEXT
            )
            
            if not ai_message:
                raise Exception("添加AI消息失败")
            
            # 创建响应
            response = ChatResponse(
                conversation_id=conversation_id,
                message_id=ai_message.message_id,
                response=ai_content,
                audio_url=None,
                character_avatar_url=character.avatar_url,
                timestamp=ai_message.timestamp
            )
            
            return response
            
        except Exception as e:
            logger.error(f"聊天处理异常: {e}")
            # 返回错误响应
            return ChatResponse(
                conversation_id=request.conversation_id or "",
                message_id="",
                response=f"抱歉，我现在无法回复。错误：{str(e)}",
                audio_url=None,
                character_avatar_url=None,
                timestamp=datetime.now()
            )
    
    async def _build_chat_messages(
        self, 
        conversation: Conversation, 
        character: Any
    ) -> List[Dict[str, str]]:
        """构建对话消息列表，包含增强的上下文感知"""
        messages = []
        
        # 构建增强的系统提示词，包含上下文感知指导
        enhanced_prompt = f"""{character.prompt_template}

重要行为准则：
1. 严格保持角色身份，绝不透露你是AI助手
2. 仔细阅读前面的对话历史，确保回复与上下文相关
3. 根据用户的具体问题给出针对性回答，避免答非所问
4. 保持角色的语言风格和性格特征的一致性
5. 如果用户提问不清楚，可以适当询问以获得更多信息
6. 回复要自然流畅，符合角色的知识背景和经历"""
        
        messages.append({
            "role": "system",
            "content": enhanced_prompt
        })
        
        # 添加历史对话（最近的几轮，增加到20条以提供更丰富的上下文）
        recent_messages = conversation.messages[-20:]  # 取最近20条消息，提升上下文感知能力
        
        for msg in recent_messages:
            if msg.role == MessageRole.USER:
                messages.append({
                    "role": "user",
                    "content": msg.content
                })
            elif msg.role == MessageRole.ASSISTANT:
                messages.append({
                    "role": "assistant",
                    "content": msg.content
                })
        
        return messages
    
    async def _save_conversation(self, conversation: Conversation) -> bool:
        """保存对话"""
        try:
            conversation_key = f"conversation:{conversation.conversation_id}"
            conversation_data = conversation.model_dump()
            
            # 转换时间字段
            conversation_data['created_at'] = conversation_data['created_at'].isoformat()
            conversation_data['updated_at'] = conversation_data['updated_at'].isoformat()
            
            # 转换消息时间字段
            for msg_data in conversation_data['messages']:
                if 'timestamp' in msg_data:
                    msg_data['timestamp'] = msg_data['timestamp'].isoformat()
            
            return self.redis.set_data(conversation_key, conversation_data)
            
        except Exception as e:
            logger.error(f"保存对话异常: {e}")
            return False
    
    async def get_user_conversations(
        self, 
        user_id: str, 
        limit: int = 20
    ) -> List[ConversationSummary]:
        """获取用户对话摘要列表"""
        try:
            user_conversations_key = f"user_conversations:{user_id}"
            conversation_ids = self.redis.list_range(user_conversations_key, 0, limit - 1)
            
            summaries = []
            for conversation_id in conversation_ids:
                summary = await self._get_conversation_summary(conversation_id)
                if summary:
                    summaries.append(summary)
            
            return summaries
            
        except Exception as e:
            logger.error(f"获取用户对话列表异常: {e}")
            return []
    
    async def _get_conversation_summary(self, conversation_id: str) -> Optional[ConversationSummary]:
        """获取对话摘要"""
        try:
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                return None
            
            # 获取角色信息
            character = await self.character_service.get_character_by_id(conversation.character_id)
            character_name = character.name if character else "未知角色"
            
            # 获取最后一条消息
            last_message = ""
            if conversation.messages:
                last_msg = conversation.messages[-1]
                last_message = last_msg.content[:50] + "..." if len(last_msg.content) > 50 else last_msg.content
            
            return ConversationSummary(
                conversation_id=conversation.conversation_id,
                user_id=conversation.user_id,
                character_id=conversation.character_id,
                character_name=character_name,
                title=conversation.title,
                last_message=last_message,
                message_count=len(conversation.messages),
                created_at=conversation.created_at,
                updated_at=conversation.updated_at
            )
            
        except Exception as e:
            logger.error(f"获取对话摘要异常: {e}")
            return None
    
    async def get_conversations_by_character(
        self, 
        user_id: str, 
        character_id: str,
        limit: int = 10
    ) -> List[ConversationSummary]:
        """获取用户与特定角色的对话列表"""
        try:
            all_conversations = await self.get_user_conversations(user_id, limit * 2)
            
            # 筛选特定角色的对话
            character_conversations = [
                conv for conv in all_conversations 
                if conv.character_id == character_id
            ]
            
            return character_conversations[:limit]
            
        except Exception as e:
            logger.error(f"获取角色对话列表异常: {e}")
            return []
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        try:
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                return False
            
            # 删除对话数据
            conversation_key = f"conversation:{conversation_id}"
            success = self.redis.delete_data(conversation_key)
            
            if success:
                # 从用户对话列表中移除
                user_conversations_key = f"user_conversations:{conversation.user_id}"
                self._remove_from_list(user_conversations_key, conversation_id)
                
                # 从角色对话列表中移除
                character_conversations_key = f"character_conversations:{conversation.character_id}"
                self._remove_from_list(character_conversations_key, conversation_id)
                
                logger.info(f"对话删除成功: {conversation_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除对话异常: {e}")
            return False
    
    def _remove_from_list(self, list_key: str, item_to_remove: str):
        """从 Redis 列表中移除指定元素"""
        try:
            # 获取列表所有元素
            items = self.redis.list_range(list_key, 0, -1)
            if item_to_remove in items:
                # 删除列表
                self.redis.delete_data(list_key)
                # 重新添加其他元素
                for item in items:
                    if item != item_to_remove:
                        self.redis.list_push(list_key, item)
        except Exception as e:
            logger.error(f"从列表中移除元素异常: {e}")
    
    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """更新对话标题"""
        try:
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                return False
            
            conversation.title = title
            conversation.updated_at = datetime.now()
            
            return await self._save_conversation(conversation)
            
        except Exception as e:
            logger.error(f"更新对话标题异常: {e}")
            return False

# 创建全局对话服务实例
conversation_service = ConversationService()