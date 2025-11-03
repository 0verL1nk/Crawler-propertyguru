"""
配置管理模块
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv


class Config:
    """配置管理类"""

    def __init__(self, config_dict: Optional[dict[str, Any]] = None):
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

        with config_path.open(encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        return cls(config_dict)

    def _override_from_env(self):
        """从环境变量覆盖配置"""
        # 环境变量到配置键的映射
        env_mappings = {
            # S3配置
            "AWS_ACCESS_KEY_ID": "s3.aws_access_key_id",
            "AWS_SECRET_ACCESS_KEY": "s3.aws_secret_access_key",
            "S3_BUCKET_NAME": "s3.bucket_name",
            "S3_REGION": "s3.region_name",
            # 数据库配置
            "MONGODB_URI": "database.mongodb.uri",
            "MYSQL_URI": "database.mysql.uri",
            "REDIS_URL": "database.redis.url",
            # 代理配置
            "PROXY_API_KEY": "proxy.api_key",
            "PROXY_API_URL": "proxy.api_url",
            # 安全配置
            "ENCRYPTION_KEY": "security.encryption_key",
            "API_SECRET_KEY": "security.api_key",
            # 日志级别
            "LOG_LEVEL": "logging.level",
        }

        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                self.set(config_key, env_value)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号分隔的嵌套key）

        Args:
            key: 配置键，如 'database.mongodb.host'
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split(".")
        value: Any = self.config

        for k in keys:
            if isinstance(value, dict):
                nested_value = value.get(k)
                if nested_value is None:
                    return default
                value = nested_value
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
        keys = key.split(".")
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def get_section(self, section: str) -> dict[str, Any]:
        """
        获取配置节

        Args:
            section: 配置节名称

        Returns:
            配置节字典
        """
        result = self.config.get(section, {})
        if isinstance(result, dict):
            return result
        return {}

    def __repr__(self):
        return f"Config({self.config})"
