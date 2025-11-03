"""
日志管理模块
"""

import os
import sys
from loguru import logger
from pathlib import Path


def get_logger(name: str = "crawler", log_file: str = "logs/crawler.log", 
               level: str = "INFO", rotation: str = "10 MB", 
               retention: str = "30 days"):
    """
    获取配置好的logger实例
    
    Args:
        name: 日志名称
        log_file: 日志文件路径
        level: 日志级别
        rotation: 日志轮转大小
        retention: 日志保留时间
    
    Returns:
        logger实例
    """
    # 确保日志目录存在
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 移除默认handler
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )
    
    # 添加文件输出
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=level,
        rotation=rotation,
        retention=retention,
        compression="zip",
        encoding="utf-8"
    )
    
    return logger


# 默认logger实例
default_logger = get_logger()

