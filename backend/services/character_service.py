import uuid
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
        self._init_default_characters()
    
    def _init_default_characters(self):
        """初始化默认角色"""
        self.default_characters = [
            {
                'name': '哈利波特',
                'description': '英国魔法师，霍格沃茨魔法学校格兰芬多学院学生，以勇敢和正义感闻名',
                'personality_traits': ['勇敢', '正义', '忠诚', '善良', '有责任感'],
                'background_story': '在一岁时父母被伏地魔杀害，被姨妈姨父收养。十一岁时收到霍格沃茨录取通知书，开始了魔法世界的学习和冒险。'
            },
            {
                'name': '苏格拉底',
                'description': '古希腊著名哲学家，被誉为西方哲学奠基人之一，以苏格拉底式问答法闻名',
                'personality_traits': ['智慧', '好奇', '谦逊', '理性', '爱思辨'],
                'background_story': '生活在古雅典，致力于通过对话和提问来寻求真理和智慧，提出"未经审视的生活不值得过"的著名观点。'
            },
            {
                'name': '夏洛克福尔摩斯',
                'description': '英国著名侦探，居住在贝克街221B号，以卓越的推理能力和观察力解决各种疑难案件',
                'personality_traits': ['理性', '敏锐', '冷静', '傲慢', '专注'],
                'background_story': '伦敦的咨询侦探，与华生医生合作破案。擅长通过细微观察和逻辑推理解决看似不可能的案件。'
            },
            {
                'name': '孔子',
                'description': '春秋时期的思想家和教育家，儒家学派创始人，以其道德哲学和教育理念影响深远',
                'personality_traits': ['仁爱', '智慧', '谦逊', '有教无类', '重视礼仪'],
                'background_story': '生于春秋末期，周游列国推行其政治理想，晚年专注于教育，培养了众多弟子，其思想影响中华文化数千年。'
            }
        ]
    
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
        """如果需要则初始化默认角色"""
        try:
            # 检查是否已有角色
            existing_characters = await self.get_character_list(limit=1)
            if existing_characters:
                return
            
            logger.info("初始化默认角色...")
            
            for char_info in self.default_characters:
                result = await self.create_character(
                    name=char_info['name'],
                    description=char_info['description'],
                    personality_traits=char_info['personality_traits'],
                    background_story=char_info['background_story'],
                    generate_avatar=False  # 暂时不生成头像
                )
                
                if result['success']:
                    logger.info(f"默认角色创建成功: {char_info['name']}")
                else:
                    logger.error(f"默认角色创建失败: {char_info['name']} - {result.get('error')}")
            
        except Exception as e:
            logger.error(f"初始化默认角色异常: {e}")
    
    async def get_character_prompt(self, character_id: str) -> Optional[str]:
        """获取角色提示词"""
        try:
            character = await self.get_character_by_id(character_id)
            return character.prompt_template if character else None
            
        except Exception as e:
            logger.error(f"获取角色提示词异常: {e}")
            return None

# 创建全局角色服务实例
character_service = CharacterService()