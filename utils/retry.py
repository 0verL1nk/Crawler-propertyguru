"""
重试装饰器工具
提供通用的重试机制，用于处理网络连接、数据库连接等可能失败的操作
"""

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from utils.logger import get_logger

logger = get_logger("RetryUtil")

F = TypeVar("F", bound=Callable[..., Any])


def retry_on_error(max_retries: int = 3, retry_delay: int = 5, logger_instance=None):
    """
    重试装饰器：当函数执行失败时自动重试

    Args:
        max_retries: 最大重试次数（默认3次）
        retry_delay: 重试间隔秒数（默认5秒）
        logger_instance: 自定义日志记录器实例（可选）

    Returns:
        装饰后的函数

    Example:
        ```python
        @retry_on_error(max_retries=3, retry_delay=5)
        def connect_to_database():
            # 可能失败的数据库连接操作
            pass
        ```
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger_instance or logger
            last_error = None

            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        _logger.info(
                            f"重试 {func.__name__}（第 {attempt + 1}/{max_retries} 次尝试）..."
                        )
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt + 1 < max_retries:
                        _logger.warning(
                            f"{func.__name__} 失败（第 {attempt + 1}/{max_retries} 次尝试）: {e}"
                        )
                        _logger.info(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                    else:
                        _logger.error(f"{func.__name__} 失败（已重试 {max_retries} 次）: {e}")

            # 所有重试都失败，抛出最后一个异常
            if last_error:
                raise last_error
            raise RuntimeError(f"{func.__name__} 执行失败")

        return wrapper  # type: ignore[return-value]

    return decorator
