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
_logger_rotation = "100 MB"  # 增大轮转大小，避免频繁轮转
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
):
    """
    获取配置好的logger实例（全局单例，多次调用返回同一个logger）

    Args:
        name: 日志名称（仅用于兼容性，实际使用全局logger）
        log_file: 日志文件路径（如果为None，从配置文件读取）
        level: 日志级别（如果为None，从配置文件读取）

    Returns:
        logger实例（全局单例）

    Note:
        不再支持 rotation 和 retention 参数，每个进程使用独立的日志文件
    """
    global _logger_initialized

    # 如果已经初始化过，直接返回全局logger
    if _logger_initialized:
        return logger

    # 加载配置（只加载一次）
    _load_log_config()

    # 使用参数或配置值
    final_level = level or _logger_level
    final_log_file = log_file or _logger_file

    # 只在第一次调用时初始化 handler
    if not _logger_initialized:
        # 确保日志目录存在
        log_path = Path(final_log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 为每个进程创建独立的日志文件（避免多进程冲突）
        # 格式: logs/crawler.PID.log
        log_stem = log_path.stem
        log_suffix = log_path.suffix
        process_log_file = log_path.parent / f"{log_stem}.{os.getpid()}{log_suffix}"

        # 移除默认handler
        logger.remove()

        # 添加控制台输出
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=final_level,
            colorize=True,
        )

        # 添加文件输出（每个进程独立文件，不轮转）
        # 注意：每个进程有独立的日志文件，不需要 rotation/retention/compression
        logger.add(
            str(process_log_file),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=final_level,
            rotation=None,  # 禁用轮转，每个进程一个文件
            retention=None,  # 禁用自动清理
            compression=None,  # 不压缩
            encoding="utf-8",
            enqueue=True,  # 异步写入，提高性能并避免阻塞
        )

        _logger_initialized = True
        logger.info(f"日志系统初始化完成: {process_log_file}")

    return logger
