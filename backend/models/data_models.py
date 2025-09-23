from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"

class User(BaseModel):
    """用户模型"""
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    is_active: bool = Field(default=True, description="是否激活")

class Character(BaseModel):
    """角色模型"""
    character_id: str = Field(..., description="角色ID")
    name: str = Field(..., description="角色名称")
    description: str = Field(..., description="角色描述")
    avatar_url: Optional[str] = Field(None, description="角色头像URL")
    prompt_template: str = Field(..., description="角色prompt模板")
    personality_traits: List[str] = Field(default_factory=list, description="性格特征")
    background_story: Optional[str] = Field(None, description="背景故事")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    is_active: bool = Field(default=True, description="是否激活")

class Message(BaseModel):
    """消息模型"""
    message_id: str = Field(..., description="消息ID")
    conversation_id: str = Field(..., description="对话ID")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    message_type: MessageType = Field(default=MessageType.TEXT, description="消息类型")
    audio_url: Optional[str] = Field(None, description="音频文件URL")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")

class Conversation(BaseModel):
    """对话模型"""
    conversation_id: str = Field(..., description="对话ID")
    user_id: str = Field(..., description="用户ID")
    character_id: str = Field(..., description="角色ID")
    title: str = Field(..., description="对话标题")
    messages: List[Message] = Field(default_factory=list, description="消息列表")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    is_active: bool = Field(default=True, description="是否激活")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

class ConversationSummary(BaseModel):
    """对话摘要模型"""
    conversation_id: str = Field(..., description="对话ID")
    user_id: str = Field(..., description="用户ID")
    character_id: str = Field(..., description="角色ID")
    character_name: str = Field(..., description="角色名称")
    title: str = Field(..., description="对话标题")
    last_message: Optional[str] = Field(None, description="最后一条消息")
    message_count: int = Field(default=0, description="消息数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

class ChatRequest(BaseModel):
    """聊天请求模型"""
    user_id: str = Field(..., description="用户ID")
    character_id: str = Field(..., description="角色ID")
    conversation_id: Optional[str] = Field(None, description="对话ID")
    message: str = Field(..., description="用户消息")
    message_type: MessageType = Field(default=MessageType.TEXT, description="消息类型")

class ChatResponse(BaseModel):
    """聊天响应模型"""
    conversation_id: str = Field(..., description="对话ID")
    message_id: str = Field(..., description="消息ID")
    response: str = Field(..., description="AI响应")
    audio_url: Optional[str] = Field(None, description="音频URL")
    character_avatar_url: Optional[str] = Field(None, description="角色头像URL")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")

class AudioProcessRequest(BaseModel):
    """音频处理请求模型"""
    audio_data: str = Field(..., description="音频数据（base64编码）")
    user_id: str = Field(..., description="用户ID")
    character_id: str = Field(..., description="角色ID")
    conversation_id: Optional[str] = Field(None, description="对话ID")

class UserSession(BaseModel):
    """用户会话模型"""
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_activity: datetime = Field(default_factory=datetime.now, description="最后活动时间")
    is_active: bool = Field(default=True, description="是否激活")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="会话元数据")