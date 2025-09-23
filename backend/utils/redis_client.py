import redis
import json
import logging
from typing import Optional, Any, Dict, List, Union
from datetime import datetime, timedelta
from config.settings import settings

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis客户端类"""
    
    def __init__(self):
        self.client = None
        self.connect()
    
    def connect(self):
        """连接Redis"""
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # 测试连接
            self.client.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self.client = None
    
    def get_client(self) -> Optional[redis.Redis]:
        """获取Redis客户端实例"""
        if self.client is None:
            self.connect()
        return self.client
    
    def is_connected(self) -> bool:
        """检查Redis连接状态"""
        try:
            if self.client is None:
                return False
            self.client.ping()
            return True
        except:
            return False
    
    def set_data(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """存储数据"""
        try:
            client = self.get_client()
            if client is None:
                logger.error("Redis客户端未连接")
                return False
                
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, default=str)
            
            if expire:
                result = client.setex(key, expire, value)
                return bool(result)
            else:
                result = client.set(key, value)
                return bool(result)
        except Exception as e:
            logger.error(f"Redis存储数据失败: {e}")
            return False
    
    def get_data(self, key: str) -> Optional[Any]:
        """获取数据"""
        try:
            client = self.get_client()
            if client is None:
                logger.warning("Redis客户端未连接，返回None")
                return None
                
            value = client.get(key)
            if value is None:
                return None
            
            # 尝试解析JSON
            try:
                return json.loads(str(value))
            except json.JSONDecodeError:
                return str(value)
        except Exception as e:
            logger.error(f"Redis获取数据失败: {e}")
            return None
    
    def delete_data(self, key: str) -> bool:
        """删除数据"""
        try:
            client = self.get_client()
            if client is None:
                return False
            return bool(client.delete(key))
        except Exception as e:
            logger.error(f"Redis删除数据失败: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            client = self.get_client()
            if client is None:
                return False
            return bool(client.exists(key))
        except Exception as e:
            logger.error(f"Redis检查键存在失败: {e}")
            return False
    
    def expire_key(self, key: str, seconds: int) -> bool:
        """设置键过期时间"""
        try:
            client = self.get_client()
            if client is None:
                return False
            result = client.expire(key, seconds)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis设置过期时间失败: {e}")
            return False
    
    def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """根据模式获取键列表"""
        try:
            client = self.get_client()
            if client is None:
                return []
            keys = client.keys(pattern)
            if isinstance(keys, list):
                return [str(key) for key in keys]
            return []
        except Exception as e:
            logger.error(f"Redis获取键列表失败: {e}")
            return []
    
    def hash_set(self, name: str, key: str, value: Any) -> bool:
        """哈希表设置值"""
        try:
            client = self.get_client()
            if client is None:
                return False
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, default=str)
            return bool(client.hset(name, key, value))
        except Exception as e:
            logger.error(f"Redis哈希表设置失败: {e}")
            return False
    
    def hash_get(self, name: str, key: str) -> Optional[Any]:
        """哈希表获取值"""
        try:
            client = self.get_client()
            if client is None:
                return None
            value = client.hget(name, key)
            if value is None:
                return None
            try:
                return json.loads(str(value))
            except json.JSONDecodeError:
                return str(value)
        except Exception as e:
            logger.error(f"Redis哈希表获取失败: {e}")
            return None
    
    def hash_get_all(self, name: str) -> Dict[str, Any]:
        """哈希表获取所有值"""
        try:
            client = self.get_client()
            if client is None:
                return {}
            data = client.hgetall(name)
            result = {}
            if isinstance(data, dict):
                for key, value in data.items():
                    try:
                        result[key] = json.loads(str(value))
                    except json.JSONDecodeError:
                        result[key] = str(value)
            return result
        except Exception as e:
            logger.error(f"Redis哈希表获取所有值失败: {e}")
            return {}
    
    def hash_delete(self, name: str, key: str) -> bool:
        """哈希表删除键"""
        try:
            client = self.get_client()
            if client is None:
                return False
            return bool(client.hdel(name, key))
        except Exception as e:
            logger.error(f"Redis哈希表删除失败: {e}")
            return False
    
    def list_push(self, name: str, value: Any, left: bool = True) -> bool:
        """列表插入值"""
        try:
            client = self.get_client()
            if client is None:
                return False
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, default=str)
            
            if left:
                return bool(client.lpush(name, value))
            else:
                return bool(client.rpush(name, value))
        except Exception as e:
            logger.error(f"Redis列表插入失败: {e}")
            return False
    
    def list_pop(self, name: str, left: bool = True) -> Optional[Any]:
        """列表弹出值"""
        try:
            client = self.get_client()
            if client is None:
                return None
            
            if left:
                value = client.lpop(name)
            else:
                value = client.rpop(name)
            
            if value is None:
                return None
            
            try:
                return json.loads(str(value))
            except json.JSONDecodeError:
                return str(value)
        except Exception as e:
            logger.error(f"Redis列表弹出失败: {e}")
            return None
    
    def list_range(self, name: str, start: int = 0, end: int = -1) -> List[Any]:
        """获取列表范围"""
        try:
            client = self.get_client()
            if client is None:
                return []
            values = client.lrange(name, start, end)
            result = []
            if isinstance(values, list):
                for value in values:
                    try:
                        result.append(json.loads(str(value)))
                    except json.JSONDecodeError:
                        result.append(str(value))
            return result
        except Exception as e:
            logger.error(f"Redis获取列表范围失败: {e}")
            return []

redis_client = RedisClient()