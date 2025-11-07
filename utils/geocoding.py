"""
地理编码工具
将地址转换为地理坐标（经纬度）
"""

from __future__ import annotations

import time
from decimal import Decimal

import requests

from .logger import get_logger
from .retry import retry_on_error

logger = get_logger("Geocoding")

# Nominatim API 配置
NOMINATIM_API_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "PropertyGuruCrawler/1.0"
NOMINATIM_RATE_LIMIT_DELAY = 1.0  # 秒，Nominatim 要求最多每秒1次请求


@retry_on_error(max_retries=3, retry_delay=2, logger_instance=logger)
def geocode_address(
    address: str,
    country: str = "Singapore",
    timeout: int = 10,
) -> tuple[Decimal | None, Decimal | None]:
    """
    将地址转换为地理坐标（纬度、经度）

    Args:
        address: 地址字符串，如 "32 Lentor Hills Road"
        country: 国家名称，默认为 "Singapore"
        timeout: 请求超时时间（秒）

    Returns:
        (latitude, longitude) 元组，失败时返回 (None, None)

    说明：
        使用 OpenStreetMap Nominatim API 进行地理编码
        - 免费使用，无需 API Key
        - 需要遵守使用政策：最多每秒1次请求
        - User-Agent 必须设置为应用名称
        - 自动重试机制：失败后最多重试3次
    """
    if not address or not address.strip():
        logger.debug("地址为空，无法进行地理编码")
        return None, None

    # 构造完整查询地址
    full_address = f"{address}, {country}"

    logger.debug(f"开始地理编码: {full_address}")

    # 构造请求参数
    params = {
        "q": full_address,
        "format": "json",
        "limit": 1,  # 只返回最佳匹配结果
        "addressdetails": 0,  # 不需要详细地址信息
    }

    headers = {
        "User-Agent": NOMINATIM_USER_AGENT,
    }

    # 发送请求
    response = requests.get(
        NOMINATIM_API_URL,
        params=params,
        headers=headers,
        timeout=timeout,
    )

    # 检查响应状态
    if response.status_code != 200:
        logger.warning(f"地理编码API返回错误状态码: {response.status_code}, 地址: {full_address}")
        # 不抛出异常，直接返回 None（避免无意义的重试）
        time.sleep(NOMINATIM_RATE_LIMIT_DELAY)
        return None, None

    # 解析响应
    results = response.json()

    if not results or len(results) == 0:
        logger.debug(f"地理编码未找到结果: {full_address}")
        # 遵守速率限制后返回
        time.sleep(NOMINATIM_RATE_LIMIT_DELAY)
        return None, None

    # 获取第一个结果
    result = results[0]
    lat_str = result.get("lat")
    lon_str = result.get("lon")

    if not lat_str or not lon_str:
        logger.warning(f"地理编码结果缺少坐标: {full_address}")
        time.sleep(NOMINATIM_RATE_LIMIT_DELAY)
        return None, None

    # 转换为 Decimal 类型
    latitude = Decimal(lat_str)
    longitude = Decimal(lon_str)

    logger.debug(f"地理编码成功: {full_address} -> ({latitude}, {longitude})")

    # 遵守速率限制
    time.sleep(NOMINATIM_RATE_LIMIT_DELAY)

    return latitude, longitude


def batch_geocode_addresses(
    addresses: list[str],
    country: str = "Singapore",
    delay: float = NOMINATIM_RATE_LIMIT_DELAY,
) -> dict[str, tuple[Decimal | None, Decimal | None]]:
    """
    批量地理编码多个地址

    Args:
        addresses: 地址列表
        country: 国家名称
        delay: 每次请求之间的延迟（秒）

    Returns:
        字典，key 为地址，value 为 (latitude, longitude) 元组
    """
    results = {}

    for address in addresses:
        if address in results:
            continue  # 跳过已处理的地址

        lat, lon = geocode_address(address, country=country)
        results[address] = (lat, lon)

        # 额外延迟（如果需要）
        if delay > NOMINATIM_RATE_LIMIT_DELAY:
            time.sleep(delay - NOMINATIM_RATE_LIMIT_DELAY)

    return results
