import uuid
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from backend.models.data_models import Character
from backend.utils.redis_client import redis_client
from backend.services.dashscope_service import dashscope_service

logger = logging.getLogger(__name__)

class CharacterService:
    """角色服务类"""
    
    def __init__(self):
        self.redis = redis_client
        self.dashscope = dashscope_service
    
    async def create_character(
        self, 
        name: str, 
        description: str,
        personality_traits: List[str],
        background_story: Optional[str] = None,
        generate_avatar: bool = True
    ) -> Dict[str, Any]:
        """
        创建角色
        
        Args:
            name: 角色名称
            description: 角色描述
            personality_traits: 性格特征
            background_story: 背景故事
            generate_avatar: 是否生成头像
            
        Returns:
            创建结果
        """
        try:
            # 检查角色是否已存在
            existing_character = await self.get_character_by_name(name)
            if existing_character:
                return {
                    'success': False,
                    'error': '角色已存在'
                }
            
            # 生成角色ID
            character_id = str(uuid.uuid4())
            
            # 生成头像（如果需要）
            avatar_url = None
            if generate_avatar:
                avatar_result = await self.dashscope.generate_character_avatar(
                    name, description, style='anime'
                )
                if avatar_result['success']:
                    avatar_url = avatar_result['image_url']
            
            # 生成角色提示词
            prompt_template = self.dashscope.build_character_prompt(
                name, description, personality_traits, background_story
            )
            
            # 创建角色对象
            character = Character(
                character_id=character_id,
                name=name,
                description=description,
                avatar_url=avatar_url,
                prompt_template=prompt_template,
                personality_traits=personality_traits,
                background_story=background_story,
                created_at=datetime.now(),
                is_active=True
            )
            
            # 存储到Redis
            character_key = f"character:{character_id}"
            character_name_key = f"character_name:{name}"
            
            character_data = character.model_dump()
            character_data['created_at'] = character_data['created_at'].isoformat()
            
            success1 = self.redis.set_data(character_key, character_data)
            success2 = self.redis.set_data(character_name_key, character_id)
            
            if success1 and success2:
                # 添加到角色列表
                self.redis.list_push("character_list", character_id)
                
                logger.info(f"角色创建成功: {name}")
                return {
                    'success': True,
                    'character': character_data
                }
            else:
                return {
                    'success': False,
                    'error': '角色创建失败'
                }
                
        except Exception as e:
            logger.error(f"创建角色异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_character_by_id(self, character_id: str) -> Optional[Character]:
        """根据角色ID获取角色"""
        try:
            character_key = f"character:{character_id}"
            character_data = self.redis.get_data(character_key)
            
            if character_data:
                # 转换时间字段
                if 'created_at' in character_data:
                    character_data['created_at'] = datetime.fromisoformat(character_data['created_at'])
                
                return Character(**character_data)
            return None
            
        except Exception as e:
            logger.error(f"获取角色异常: {e}")
            return None
    
    async def get_character_by_name(self, name: str) -> Optional[Character]:
        """根据角色名称获取角色"""
        try:
            character_name_key = f"character_name:{name}"
            character_id = self.redis.get_data(character_name_key)
            
            if character_id:
                return await self.get_character_by_id(character_id)
            return None
            
        except Exception as e:
            logger.error(f"根据名称获取角色异常: {e}")
            return None
    
    async def search_characters(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索角色
        
        Args:
            query: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            角色列表
        """
        try:
            characters = []
            query_lower = query.lower()
            
            # 获取所有角色
            all_characters = await self.get_character_list()
            
            # 模糊匹配
            for char_data in all_characters:
                name = char_data.get('name', '').lower()
                description = char_data.get('description', '').lower()
                
                if (query_lower in name or 
                    query_lower in description or
                    any(query_lower in trait.lower() for trait in char_data.get('personality_traits', []))):
                    characters.append(char_data)
                    
                    if len(characters) >= limit:
                        break
            
            # 如果没有找到匹配的角色，尝试智能创建新角色
            if not characters:
                logger.info(f"未找到匹配角色 '{query}'，尝试智能创建")
                new_character = await self.create_smart_character(query)
                if new_character:
                    characters.append(new_character)
            
            return characters
            
        except Exception as e:
            logger.error(f"搜索角色异常: {e}")
            return []
    
    async def get_character_list(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取角色列表"""
        try:
            # 获取所有角色键
            character_keys = self.redis.get_keys_by_pattern("character:*")
            characters = []
            
            for key in character_keys[:limit]:
                character_data = self.redis.get_data(key)
                if character_data and isinstance(character_data, dict):
                    # 只返回基本信息
                    characters.append({
                        'character_id': character_data.get('character_id'),
                        'name': character_data.get('name'),
                        'description': character_data.get('description'),
                        'avatar_url': character_data.get('avatar_url'),
                        'personality_traits': character_data.get('personality_traits', []),
                        'created_at': character_data.get('created_at'),
                        'is_active': character_data.get('is_active', True)
                    })
            
            return characters
            
        except Exception as e:
            logger.error(f"获取角色列表异常: {e}")
            return []
    
    async def update_character(self, character_id: str, **kwargs) -> bool:
        """更新角色信息"""
        try:
            character = await self.get_character_by_id(character_id)
            if not character:
                return False
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(character, key):
                    setattr(character, key, value)
            
            # 如果更新了角色信息，重新生成提示词
            if any(key in kwargs for key in ['name', 'description', 'personality_traits', 'background_story']):
                character.prompt_template = self.dashscope.build_character_prompt(
                    character.name,
                    character.description,
                    character.personality_traits,
                    character.background_story
                )
            
            # 保存到Redis
            character_key = f"character:{character_id}"
            character_data = character.model_dump()
            character_data['created_at'] = character_data['created_at'].isoformat()
            
            return self.redis.set_data(character_key, character_data)
            
        except Exception as e:
            logger.error(f"更新角色异常: {e}")
            return False
    
    async def delete_character(self, character_id: str) -> bool:
        """删除角色"""
        try:
            character = await self.get_character_by_id(character_id)
            if not character:
                return False
            
            # 删除角色数据
            character_key = f"character:{character_id}"
            character_name_key = f"character_name:{character.name}"
            
            success1 = self.redis.delete_data(character_key)
            success2 = self.redis.delete_data(character_name_key)
            
            return success1 and success2
            
        except Exception as e:
            logger.error(f"删除角色异常: {e}")
            return False
    
    async def init_default_characters_if_needed(self):
        """不再初始化默认角色，所有角色都通过搜索创建"""
        # 移除默认角色初始化逻辑
        logger.info("系统不再预置默认角色，所有角色都将通过搜索创建")
        pass
    
    async def get_character_prompt(self, character_id: str) -> Optional[str]:
        """获取角色提示词"""
        try:
            character = await self.get_character_by_id(character_id)
            return character.prompt_template if character else None
            
        except Exception as e:
            logger.error(f"获取角色提示词异常: {e}")
            return None
    
    async def create_smart_character(self, character_name: str) -> Optional[Dict[str, Any]]:
        """
        智能创建新角色
        
        Args:
            character_name: 角色名称
            
        Returns:
            创建的角色信息
        """
        try:
            logger.info(f"开始智能创建角色: {character_name}")
            
            # 使用AI生成角色描述和特征
            character_info = await self._generate_character_info(character_name)
            
            if not character_info:
                logger.warning(f"无法生成角色信息: {character_name}")
                return None
            
            # 创建角色
            result = await self.create_character(
                name=character_name,
                description=character_info['description'],
                personality_traits=character_info['personality_traits'],
                background_story=character_info.get('background_story'),
                generate_avatar=False  # 暂时不生成头像，避免耗时
            )
            
            if result['success']:
                logger.info(f"智能创建角色成功: {character_name}")
                character_data = result['character']
                return {
                    'character_id': character_data['character_id'],
                    'name': character_data['name'],
                    'description': character_data['description'],
                    'avatar_url': character_data.get('avatar_url'),
                    'personality_traits': character_data.get('personality_traits', []),
                    'created_at': character_data.get('created_at'),
                    'is_active': character_data.get('is_active', True)
                }
            else:
                logger.error(f"智能创建角色失败: {character_name} - {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"智能创建角色异常: {e}")
            return None
    
    async def _generate_character_info(self, character_name: str) -> Optional[Dict[str, Any]]:
        """
        使用AI生成角色信息
        
        Args:
            character_name: 角色名称
            
        Returns:
            角色信息字典
        """
        try:
            # 构建提示词请求AI生成角色信息
            prompt = f"""请为名为"{character_name}"的角色生成详细信息。

请返回以下格式的JSON，注意字段名必须完全一致：
{{
    "description": "角色的简要描述（50字内）",
    "personality_traits": ["性格特1", "性格特2", "性格特3"],
    "background_story": "背景故事（100字内）"
}}

重要：请严格按照上述JSON格式返回，personality_traits字段名不要拼错。
请确保内容精准、符合角色特点，且适合角色扮演对话。"""
            
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # 调用AI生成
            response = await self.dashscope.chat_completion(messages, temperature=0.7)
            
            if response['success']:
                try:
                    # 解析JSON响应
                    character_info = json.loads(response['content'])
                    
                    # 验证必要字段并尝试修复常见错误
                    if 'description' in character_info:
                        # 修复personality_traits字段名的常见拼写错误
                        if 'personity_traits' in character_info and 'personality_traits' not in character_info:
                            character_info['personality_traits'] = character_info.pop('personity_traits')
                        
                        # 验证必要字段
                        if ('personality_traits' in character_info and
                            isinstance(character_info['personality_traits'], list)):
                            return character_info
                        else:
                            logger.warning(f"AI生成的角色信息缺少必要字段: {character_info}")
                            return self._create_default_character_info(character_name)
                    else:
                        logger.warning(f"AI生成的角色信息格式不正确: {character_info}")
                        return self._create_default_character_info(character_name)
                        
                except Exception as e:
                    logger.warning(f"AI响应解析失败: {response['content']} - {e}")
                    # 如果解析失败，使用默认信息
                    return self._create_default_character_info(character_name)
            else:
                logger.warning(f"AI生成角色信息失败: {response.get('error')}")
                return self._create_default_character_info(character_name)
                
        except Exception as e:
            logger.error(f"生成角色信息异常: {e}")
            return self._create_default_character_info(character_name)
    
    def _create_default_character_info(self, character_name: str) -> Dict[str, Any]:
        """创建默认角色信息"""
        return {
            'description': f'一个名为{character_name}的独特角色，具有丰富的个性和背景故事',
            'personality_traits': ['智慧', '友善', '有趣'],
            'background_story': f'{character_name}是一个有着独特经历和丰富内心世界的角色，愿意与人分享思想和经历。'
        }

    async def update_all_character_prompts(self) -> bool:
        """
        更新所有角色的提示词为新的结构化格式
        
        Returns:
            是否成功
        """
        try:
            # 获取所有角色
            characters = await self.get_character_list()
            
            for char_data in characters:
                character_id = char_data['character_id']
                character = await self.get_character_by_id(character_id)
                
                if character:
                    # 重新生成提示词
                    new_prompt = self.dashscope.build_character_prompt(
                        character.name,
                        character.description,
                        character.personality_traits,
                        character.background_story
                    )
                    
                    # 更新角色
                    success = await self.update_character(
                        character_id, 
                        prompt_template=new_prompt
                    )
                    
                    if success:
                        logger.info(f"角色 {character.name} 的提示词更新成功")
                    else:
                        logger.error(f"角色 {character.name} 的提示词更新失败")
            
            return True
            
        except Exception as e:
            logger.error(f"更新所有角色提示词异常: {e}")
            return False

# 创建全局角色服务实例
character_service = CharacterService()