"""
日志管理模块
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger

# 全局日志配置（避免重复读取配置文件）
_logger_configured = False
_logger_initialized = False
_logger_level = "INFO"
_logger_file = "logs/crawler.log"
_logger_rotation = "10 MB"
_logger_retention = "30 days"


def _load_log_config():
    """从配置文件加载日志配置"""
    global _logger_configured, _logger_level, _logger_file, _logger_rotation, _logger_retention

    if _logger_configured:
        return

    try:
        # 尝试从环境变量读取
        env_level = os.getenv("LOG_LEVEL")
        if env_level:
            _logger_level = env_level
            _logger_configured = True
            return

        # 尝试从配置文件读取
        config_file = Path("config.yaml")
        if config_file.exists():
            import yaml

            with config_file.open(encoding="utf-8") as f:
                config_dict = yaml.safe_load(f)
                log_config = config_dict.get("logging", {})
                if log_config:
                    _logger_level = log_config.get("level", "INFO")
                    _logger_file = log_config.get("file", "logs/crawler.log")
                    _logger_rotation = log_config.get("rotation", "10 MB")
                    _logger_retention = log_config.get("retention", "30 days")
                    _logger_configured = True
    except Exception:
        # 如果读取失败，使用默认值
        pass


def get_logger(
    name: str = "crawler",  # noqa: ARG001
    log_file: str | None = None,
    level: str | None = None,
    rotation: str | None = None,
    retention: str | None = None,
):
    """
    获取配置好的logger实例

    Args:
        name: 日志名称
        log_file: 日志文件路径（如果为None，从配置文件读取）
        level: 日志级别（如果为None，从配置文件读取）
        rotation: 日志轮转大小（如果为None，从配置文件读取）
        retention: 日志保留时间（如果为None，从配置文件读取）

    Returns:
        logger实例
    """
    global _logger_initialized

    # 加载配置（只加载一次）
    _load_log_config()

    # 使用参数或配置值
    final_level = level or _logger_level
    final_log_file = log_file or _logger_file
    final_rotation = rotation or _logger_rotation
    final_retention = retention or _logger_retention

    # 只在第一次调用时初始化 handler
    if not _logger_initialized:
        # 确保日志目录存在
        log_path = Path(final_log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 移除默认handler
        logger.remove()

        # 添加控制台输出
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=final_level,
            colorize=True,
        )

        # 添加文件输出
        logger.add(
            final_log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=final_level,
            rotation=final_rotation,
            retention=final_retention,
            compression="zip",
            encoding="utf-8",
        )

        _logger_initialized = True

    return logger
