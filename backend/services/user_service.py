import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from backend.models.data_models import User, UserSession
from backend.utils.redis_client import redis_client
from config.settings import settings

logger = logging.getLogger(__name__)

class UserService:
    """用户服务类"""
    
    def __init__(self):
        self.redis = redis_client
    
    async def create_user(self, username: str, email: Optional[str] = None) -> Dict[str, Any]:
        """
        创建用户
        
        Args:
            username: 用户名
            email: 邮箱（可选）
            
        Returns:
            创建结果
        """
        try:
            # 检查用户名是否已存在
            if await self.get_user_by_username(username):
                return {
                    'success': False,
                    'error': '用户名已存在'
                }
            
            # 生成用户ID
            user_id = str(uuid.uuid4())
            
            # 创建用户对象
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                avatar_url=None,
                created_at=datetime.now(),
                last_login=datetime.now(),
                is_active=True
            )
            
            # 存储到Redis
            user_key = f"user:{user_id}"
            username_key = f"username:{username}"
            
            user_data = user.model_dump()
            user_data['created_at'] = user_data['created_at'].isoformat()
            user_data['last_login'] = user_data['last_login'].isoformat()
            
            success1 = self.redis.set_data(user_key, user_data)
            success2 = self.redis.set_data(username_key, user_id)
            
            if success1 and success2:
                logger.info(f"用户创建成功: {username}")
                return {
                    'success': True,
                    'user': user_data
                }
            else:
                return {
                    'success': False,
                    'error': '用户创建失败'
                }
                
        except Exception as e:
            logger.error(f"创建用户异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据用户ID获取用户"""
        try:
            user_key = f"user:{user_id}"
            user_data = self.redis.get_data(user_key)
            
            if user_data:
                # 转换时间字段
                if 'created_at' in user_data:
                    user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
                if 'last_login' in user_data and user_data['last_login']:
                    user_data['last_login'] = datetime.fromisoformat(user_data['last_login'])
                
                return User(**user_data)
            return None
            
        except Exception as e:
            logger.error(f"获取用户异常: {e}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        try:
            username_key = f"username:{username}"
            user_id = self.redis.get_data(username_key)
            
            if user_id:
                return await self.get_user_by_id(user_id)
            return None
            
        except Exception as e:
            logger.error(f"根据用户名获取用户异常: {e}")
            return None
    
    async def update_user(self, user_id: str, **kwargs) -> bool:
        """更新用户信息"""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            # 保存到Redis
            user_key = f"user:{user_id}"
            user_data = user.model_dump()
            user_data['created_at'] = user_data['created_at'].isoformat()
            if user_data['last_login']:
                user_data['last_login'] = user_data['last_login'].isoformat()
            
            return self.redis.set_data(user_key, user_data)
            
        except Exception as e:
            logger.error(f"更新用户异常: {e}")
            return False
    
    async def login_user(self, username: str) -> Dict[str, Any]:
        """
        用户登录（伪登录）
        
        Args:
            username: 用户名
            
        Returns:
            登录结果
        """
        try:
            # 获取或创建用户
            user = await self.get_user_by_username(username)
            if not user:
                # 自动创建用户
                result = await self.create_user(username)
                if not result['success']:
                    return result
                user_data = result['user']
                user_id = user_data['user_id']
            else:
                user_id = user.user_id
                # 更新最后登录时间
                await self.update_user(user_id, last_login=datetime.now())
            
            # 创建会话
            session = await self.create_session(user_id)
            if session:
                return {
                    'success': True,
                    'user_id': user_id,
                    'session_id': session.session_id,
                    'username': username
                }
            else:
                return {
                    'success': False,
                    'error': '创建会话失败'
                }
                
        except Exception as e:
            logger.error(f"用户登录异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_session(self, user_id: str) -> Optional[UserSession]:
        """创建用户会话"""
        try:
            session_id = str(uuid.uuid4())
            session = UserSession(
                session_id=session_id,
                user_id=user_id,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                is_active=True
            )
            
            # 存储会话
            session_key = f"session:{session_id}"
            session_data = session.model_dump()
            session_data['created_at'] = session_data['created_at'].isoformat()
            session_data['last_activity'] = session_data['last_activity'].isoformat()
            
            # 设置会话过期时间
            success = self.redis.set_data(session_key, session_data, expire=settings.SESSION_TIMEOUT)
            
            if success:
                # 在用户下记录会话
                user_sessions_key = f"user_sessions:{user_id}"
                self.redis.list_push(user_sessions_key, session_id)
                return session
            
            return None
            
        except Exception as e:
            logger.error(f"创建会话异常: {e}")
            return None
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """获取会话"""
        try:
            session_key = f"session:{session_id}"
            session_data = self.redis.get_data(session_key)
            
            if session_data:
                # 转换时间字段
                session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
                session_data['last_activity'] = datetime.fromisoformat(session_data['last_activity'])
                
                return UserSession(**session_data)
            return None
            
        except Exception as e:
            logger.error(f"获取会话异常: {e}")
            return None
    
    async def validate_session(self, session_id: str) -> Optional[str]:
        """验证会话并返回用户ID"""
        try:
            session = await self.get_session(session_id)
            if session and session.is_active:
                # 更新最后活动时间
                await self.update_session_activity(session_id)
                return session.user_id
            return None
            
        except Exception as e:
            logger.error(f"验证会话异常: {e}")
            return None
    
    async def update_session_activity(self, session_id: str) -> bool:
        """更新会话活动时间"""
        try:
            session = await self.get_session(session_id)
            if session:
                session.last_activity = datetime.now()
                
                session_key = f"session:{session_id}"
                session_data = session.model_dump()
                session_data['created_at'] = session_data['created_at'].isoformat()
                session_data['last_activity'] = session_data['last_activity'].isoformat()
                
                return self.redis.set_data(session_key, session_data, expire=settings.SESSION_TIMEOUT)
            return False
            
        except Exception as e:
            logger.error(f"更新会话活动时间异常: {e}")
            return False
    
    async def logout_user(self, session_id: str) -> bool:
        """用户登出"""
        try:
            session_key = f"session:{session_id}"
            return self.redis.delete_data(session_key)
            
        except Exception as e:
            logger.error(f"用户登出异常: {e}")
            return False
    
    async def get_user_list(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户列表"""
        try:
            # 获取所有用户键
            user_keys = self.redis.get_keys_by_pattern("user:*")
            users = []
            
            for key in user_keys[:limit]:
                user_data = self.redis.get_data(key)
                if user_data:
                    # 只返回基本信息
                    users.append({
                        'user_id': user_data.get('user_id'),
                        'username': user_data.get('username'),
                        'created_at': user_data.get('created_at'),
                        'is_active': user_data.get('is_active', True)
                    })
            
            return users
            
        except Exception as e:
            logger.error(f"获取用户列表异常: {e}")
            return []

# 创建全局用户服务实例
user_service = UserService()