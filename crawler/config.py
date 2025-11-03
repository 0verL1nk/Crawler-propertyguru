"""
配置管理模块
"""

import os
import yaml
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """配置管理类"""
    
    def __init__(self, config_dict: Dict[str, Any] = None):
        """
        初始化配置
        
        Args:
            config_dict: 配置字典
        """
        self.config = config_dict or {}
        
        # 加载环境变量
        load_dotenv()
        
        # 从环境变量覆盖配置
        self._override_from_env()
    
    @classmethod
    def from_yaml(cls, config_file: str = "config.yaml"):
        """
        从YAML文件加载配置
        
        Args:
            config_file: 配置文件路径
        
        Returns:
            Config实例
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        
        return cls(config_dict)
    
    def _override_from_env(self):
        """从环境变量覆盖配置"""
        # S3配置
        if os.getenv('AWS_ACCESS_KEY_ID'):
            self.set('s3.aws_access_key_id', os.getenv('AWS_ACCESS_KEY_ID'))
        if os.getenv('AWS_SECRET_ACCESS_KEY'):
            self.set('s3.aws_secret_access_key', os.getenv('AWS_SECRET_ACCESS_KEY'))
        if os.getenv('S3_BUCKET_NAME'):
            self.set('s3.bucket_name', os.getenv('S3_BUCKET_NAME'))
        if os.getenv('S3_REGION'):
            self.set('s3.region_name', os.getenv('S3_REGION'))
        
        # 数据库配置
        if os.getenv('MONGODB_URI'):
            self.set('database.mongodb.uri', os.getenv('MONGODB_URI'))
        if os.getenv('MYSQL_URI'):
            self.set('database.mysql.uri', os.getenv('MYSQL_URI'))
        if os.getenv('REDIS_URL'):
            self.set('database.redis.url', os.getenv('REDIS_URL'))
        
        # 代理配置
        if os.getenv('PROXY_API_KEY'):
            self.set('proxy.api_key', os.getenv('PROXY_API_KEY'))
        if os.getenv('PROXY_API_URL'):
            self.set('proxy.api_url', os.getenv('PROXY_API_URL'))
        
        # 安全配置
        if os.getenv('ENCRYPTION_KEY'):
            self.set('security.encryption_key', os.getenv('ENCRYPTION_KEY'))
        if os.getenv('API_SECRET_KEY'):
            self.set('security.api_key', os.getenv('API_SECRET_KEY'))
        
        # 日志级别
        if os.getenv('LOG_LEVEL'):
            self.set('logging.level', os.getenv('LOG_LEVEL'))
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号分隔的嵌套key）
        
        Args:
            key: 配置键，如 'database.mongodb.host'
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def set(self, key: str, value: Any):
        """
        设置配置值（支持点号分隔的嵌套key）
        
        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置节
        
        Args:
            section: 配置节名称
        
        Returns:
            配置节字典
        """
        return self.config.get(section, {})
    
    def __repr__(self):
        return f"Config({self.config})"

