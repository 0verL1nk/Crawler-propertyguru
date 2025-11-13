"""
代理IP管理模块
支持多种代理源：文件、API、Redis
支持IP池持久化，中断后可继续使用未过期的IP
"""

from __future__ import annotations

import json
import os
import random
import string
import time
from collections import defaultdict
from pathlib import Path
from threading import RLock
from typing import Any

import requests

from utils.logger import get_logger

logger = get_logger("ProxyManager")


class Proxy:
    """代理对象"""

    def __init__(
        self,
        ip: str,
        port: int,
        protocol: str = "http",
        username: str | None = None,
        password: str | None = None,
        expires_at: float | None = None,
    ):
        self.ip = ip
        self.port = port
        self.protocol = protocol
        self.username = username
        self.password = password
        self.fail_count = 0
        self.last_used: float = 0.0
        self.response_time: float = 0.0
        self.expires_at: float | None = expires_at  # IP过期时间（时间戳）
        self.created_at: float = time.time()  # IP创建时间

    def get_proxy_dict(self) -> dict[str, str]:
        """获取代理字典格式"""
        if self.username and self.password:
            proxy_url = f"{self.protocol}://{self.username}:{self.password}@{self.ip}:{self.port}"
        else:
            proxy_url = f"{self.protocol}://{self.ip}:{self.port}"

        return {"http": proxy_url, "https": proxy_url}

    def __str__(self):
        return f"{self.protocol}://{self.ip}:{self.port}"

    def to_dict(self) -> dict:
        """转换为字典（用于持久化）"""
        return {
            "ip": self.ip,
            "port": self.port,
            "protocol": self.protocol,
            "username": self.username,
            "password": self.password,
            "fail_count": self.fail_count,
            "last_used": self.last_used,
            "response_time": self.response_time,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Proxy:
        """从字典创建Proxy对象"""
        proxy = cls(
            ip=data["ip"],
            port=data["port"],
            protocol=data.get("protocol", "http"),
            username=data.get("username"),
            password=data.get("password"),
            expires_at=data.get("expires_at"),
        )
        # 恢复其他字段
        proxy.created_at = data.get("created_at", time.time())
        return proxy


class ProxyManager:
    """代理管理器"""

    def __init__(self, config: dict):
        self.config = config
        self.proxies: list[Proxy] = []
        self.proxy_stats: defaultdict[str, int] = defaultdict(int)
        self.lock = RLock()
        self.max_fails = config.get("max_fails", 3)
        self.test_url = config.get("test_url", "https://www.httpbin.org/ip")
        self.pool_type = config.get("pool_type", "file")
        self.cloudbypass_enabled = self.pool_type == "cloudbypass"

        # CloudBypass住宅代理配置
        self.cloudbypass_account: str | None = None
        self.cloudbypass_password: str | None = None
        self.cloudbypass_region: str = "SG"
        self.cloudbypass_host: str = "gw-res.cloudbypass.com"
        self.cloudbypass_port: int = 1288
        self.cloudbypass_protocol: str = "http"
        self.cloudbypass_ttl_minutes: int = 30
        self.cloudbypass_session_length: int = 12
        self.cloudbypass_ttl_label: str = "30m"

        # 默认IP有效期（秒）
        self.ip_ttl = config.get("ip_ttl", 300)

        if self.cloudbypass_enabled:
            self.cloudbypass_account = (
                config.get("cloudbypass_account")
                or os.getenv("CLOUDBYPASS_ACCOUNT")
            )
            self.cloudbypass_password = (
                config.get("cloudbypass_password")
                or os.getenv("CLOUDBYPASS_PASSWORD")
            )
            self.cloudbypass_region = (
                config.get("cloudbypass_region")
                or os.getenv("CLOUDBYPASS_REGION")
                or "SG"
            )
            self.cloudbypass_host = (
                config.get("cloudbypass_host")
                or os.getenv("CLOUDBYPASS_HOST")
                or "gw-res.cloudbypass.com"
            )
            self.cloudbypass_port = int(
                config.get("cloudbypass_port")
                or os.getenv("CLOUDBYPASS_PORT")
                or 1288
            )
            self.cloudbypass_protocol = (
                config.get("cloudbypass_protocol")
                or os.getenv("CLOUDBYPASS_PROTOCOL")
                or "http"
            ).lower()

            ttl_minutes_value = (
                config.get("cloudbypass_ttl_minutes")
                or os.getenv("CLOUDBYPASS_TTL_MINUTES")
                or 30
            )
            try:
                self.cloudbypass_ttl_minutes = int(ttl_minutes_value)
            except (TypeError, ValueError):
                logger.warning(
                    "CloudBypass TTL 配置无效，使用默认 30 分钟: %s",
                    ttl_minutes_value,
                )
                self.cloudbypass_ttl_minutes = 30

            session_length_value = (
                config.get("cloudbypass_session_length")
                or os.getenv("CLOUDBYPASS_SESSION_LENGTH")
                or 12
            )
            try:
                self.cloudbypass_session_length = int(session_length_value)
            except (TypeError, ValueError):
                logger.warning(
                    "CloudBypass 会话长度配置无效，使用默认 12: %s",
                    session_length_value,
                )
                self.cloudbypass_session_length = 12

            ttl_label = (
                config.get("cloudbypass_ttl_label")
                or os.getenv("CLOUDBYPASS_TTL_LABEL")
            )
            if ttl_label:
                self.cloudbypass_ttl_label = str(ttl_label)
            else:
                self.cloudbypass_ttl_label = f"{self.cloudbypass_ttl_minutes}m"

            if not self.cloudbypass_account or not self.cloudbypass_password:
                raise ValueError(
                    "未配置 CloudBypass 代理账号或密码（cloudbypass_account/cloudbypass_password）"
                )

            # CloudBypass 的 IP 在 TTL 之后必须刷新
            self.ip_ttl = self.cloudbypass_ttl_minutes * 60

        # 直连代理API相关配置
        self.min_proxy_count = config.get("min_proxy_count", 3)  # 最小代理数量，低于此值时会刷新
        self.last_api_request: float = 0.0  # 上次API请求时间（用于限制请求频率）
        self.api_request_interval = config.get("api_request_interval", 1.0)  # API请求间隔（秒）

        # IP池持久化配置
        proxy_pool_file = config.get("proxy_pool_file") or os.getenv(
            "PROXY_POOL_FILE", "proxy_pool.json"
        )
        if proxy_pool_file:
            self.proxy_pool_file = Path(proxy_pool_file)
        else:
            self.proxy_pool_file = Path("proxy_pool.json")

        # 加载代理（优先从持久化文件加载，避免浪费IP）
        self._load_proxies()

    def _load_proxies(self):
        """加载代理列表"""
        # 对于直连代理API，优先从持久化文件加载未过期的IP
        if self.pool_type == "direct_api":
            self._load_from_persistent_pool()
            # 不再在初始化时自动补充IP，只有在实际使用时才补充
            # 这样可以避免在不需要代理时浪费IP资源
        elif self.pool_type == "cloudbypass":
            self._load_from_persistent_pool()
        elif self.pool_type == "file":
            self._load_from_file()
        elif self.pool_type == "api":
            self._load_from_api()
        else:
            logger.warning(f"不支持的代理池类型: {self.pool_type}")

    def _load_from_file(self):
        """从文件加载代理"""
        proxy_file = self.config.get("proxy_file", "proxies.txt")
        try:
            with Path(proxy_file).open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    proxy = self._parse_proxy(line)
                    if proxy:
                        self.proxies.append(proxy)

            logger.info(f"从文件加载了 {len(self.proxies)} 个代理")
        except FileNotFoundError:
            logger.warning(f"代理文件不存在: {proxy_file}")
        except Exception as e:
            logger.error(f"加载代理文件失败: {e}")

    def _load_from_api(self):
        """从API加载代理（通用格式）"""
        api_url = self.config.get("api_url")
        api_key = self.config.get("api_key")

        if not api_url:
            logger.error("未配置代理API URL")
            return

        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            response = requests.get(api_url, headers=headers, timeout=10, verify=False)
            response.raise_for_status()

            # 根据实际API格式解析
            data = response.json()
            proxies_data = data.get("proxies", [])

            for proxy_data in proxies_data:
                proxy = Proxy(
                    ip=proxy_data.get("ip"),
                    port=proxy_data.get("port"),
                    protocol=proxy_data.get("protocol", "http"),
                    username=proxy_data.get("username"),
                    password=proxy_data.get("password"),
                )
                self.proxies.append(proxy)

            logger.info(f"从API加载了 {len(self.proxies)} 个代理")
        except Exception as e:
            logger.error(f"从API加载代理失败: {e}")

    def _load_from_persistent_pool(self):
        """从持久化文件加载IP池"""
        if not self.proxy_pool_file.exists():
            logger.debug("IP池持久化文件不存在，将创建新文件")
            return

        try:
            with self.proxy_pool_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            current_time = time.time()
            loaded_count = 0
            expired_count = 0

            for proxy_data in data.get("proxies", []):
                proxy = Proxy.from_dict(proxy_data)

                # 恢复其他状态
                proxy.fail_count = proxy_data.get("fail_count", 0)
                proxy.last_used = proxy_data.get("last_used", 0.0)
                proxy.response_time = proxy_data.get("response_time", 0.0)

                # 检查是否过期
                if proxy.expires_at is not None and current_time >= proxy.expires_at:
                    expired_count += 1
                    continue

                # 检查是否已被封
                if proxy.fail_count >= self.max_fails:
                    expired_count += 1
                    continue

                self.proxies.append(proxy)
                loaded_count += 1

            logger.info(
                f"从持久化文件加载了 {loaded_count} 个有效IP，跳过了 {expired_count} 个过期/失效IP"
            )
        except Exception as e:
            logger.warning(f"加载IP池持久化文件失败: {e}，将重新获取IP")

    def _save_proxy_pool(self):
        """保存IP池到持久化文件"""
        try:
            with self.lock:
                proxies_data = [proxy.to_dict() for proxy in self.proxies]

            data = {
                "proxies": proxies_data,
                "last_update": time.time(),
                "pool_type": self.pool_type,
            }

            with self.proxy_pool_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"IP池已保存到: {self.proxy_pool_file}")
        except Exception as e:
            logger.error(f"保存IP池失败: {e}")

    def _check_and_wait_rate_limit(self, force_refresh: bool):
        """检查并等待API请求频率限制"""
        if force_refresh:
            return
        current_time = time.time()
        if current_time - self.last_api_request < self.api_request_interval:
            wait_time = self.api_request_interval - (current_time - self.last_api_request)
            logger.debug(f"等待 {wait_time:.2f} 秒后再次请求API（频率限制）")
            time.sleep(wait_time)

    def _get_direct_api_config(self) -> dict | None:
        """获取直连代理API配置"""
        import os

        api_base_url = self.config.get("api_base_url", "") or os.getenv(
            "PROXY_DIRECT_API_BASE_URL", ""
        )
        secret = self.config.get("secret") or os.getenv("PROXY_DIRECT_SECRET")
        order_no = self.config.get("order_no") or os.getenv("PROXY_DIRECT_ORDER_NO")

        if not api_base_url or not secret or not order_no:
            logger.error("未配置直连代理API参数（api_base_url, secret, order_no）")
            return None

        # 获取配置，支持从环境变量读取，并转换为整数
        count_str = self.config.get("count") or os.getenv("PROXY_DIRECT_COUNT", "10")
        proxy_type_str = self.config.get("proxy_type") or os.getenv("PROXY_DIRECT_PROXY_TYPE", "1")
        return_account_str = self.config.get("return_account") or os.getenv(
            "PROXY_DIRECT_RETURN_ACCOUNT", "2"
        )

        try:
            count = int(count_str) if count_str else 10
            proxy_type = int(proxy_type_str) if proxy_type_str else 1
            return_account = int(return_account_str) if return_account_str else 2
        except (ValueError, TypeError):
            logger.warning("直连代理API参数类型错误，使用默认值")
            count = 10
            proxy_type = 1
            return_account = 2

        return {
            "api_base_url": api_base_url,
            "secret": secret,
            "order_no": order_no,
            "count": count,
            "proxy_type": proxy_type,
            "return_account": return_account,
        }

    def _build_direct_api_url(self, config: dict) -> str:
        """构建直连代理API URL"""
        import urllib.parse

        params = {
            "secret": config["secret"],
            "orderNo": config["order_no"],
            "count": config["count"],
            "isTxt": 0,
            "proxyType": config["proxy_type"],
            "returnAccount": config["return_account"],
        }
        api_url = f"{config['api_base_url']}?{urllib.parse.urlencode(params)}"
        masked_url = api_url.replace(config["secret"], "***").replace(config["order_no"], "***")
        logger.debug(f"请求直连代理API: {masked_url}")
        return api_url

    def _request_direct_api(self, api_url: str) -> dict | None:
        """请求直连代理API并返回响应数据"""
        try:
            self.last_api_request = time.time()
            response = requests.get(api_url, timeout=10, verify=False, allow_redirects=False)
            response.encoding = "utf-8"
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except Exception as e:
            logger.error(f"请求直连代理API失败: {e}", exc_info=True)
            return None

    def _parse_proxy_response(self, data: dict) -> list[Proxy]:
        """解析API响应数据，返回代理列表"""
        if data.get("code") != "0":
            logger.error(f"直连代理API返回错误: {data}")
            return []

        proxies_data = data.get("obj", [])
        new_proxies = []
        expires_at = time.time() + self.ip_ttl

        for proxy_data in proxies_data:
            proxy = self._create_proxy_from_data(proxy_data, expires_at)
            if proxy:
                new_proxies.append(proxy)

        return new_proxies

    def _create_proxy_from_data(self, proxy_data: dict, expires_at: float) -> Proxy | None:
        """从代理数据创建Proxy对象"""
        ip = proxy_data.get("ip")
        port = proxy_data.get("port")
        account = proxy_data.get("account")
        password = proxy_data.get("password")

        if not ip or not port:
            logger.warning(f"代理数据不完整: {proxy_data}")
            return None

        try:
            port_int = int(port)
        except (ValueError, TypeError):
            logger.warning(f"无效的端口号: {port}")
            return None

        return Proxy(
            ip=ip,
            port=port_int,
            protocol="http",
            username=account,
            password=password,
            expires_at=expires_at,
        )

    def _merge_new_proxies(self, new_proxies: list[Proxy], force_refresh: bool):
        """合并新代理到现有代理池"""
        if force_refresh:
            self.proxies = new_proxies
            logger.info(f"强制刷新：从直连代理API加载了 {len(new_proxies)} 个代理")
        else:
            existing_keys = {(p.ip, p.port) for p in self.proxies}
            added_count = 0
            for proxy in new_proxies:
                if (proxy.ip, proxy.port) not in existing_keys:
                    self.proxies.append(proxy)
                    added_count += 1
                else:
                    logger.debug(f"跳过重复代理: {proxy.ip}:{proxy.port}")
            logger.info(f"从直连代理API新增了 {added_count} 个代理，当前总数: {len(self.proxies)}")

    def _load_from_direct_api(self, force_refresh: bool = False):
        """
        从直连代理API加载代理（如熊猫代理等）

        Args:
            force_refresh: 是否强制刷新（忽略请求频率限制）
        """
        self._check_and_wait_rate_limit(force_refresh)

        config = self._get_direct_api_config()
        if not config:
            return

        api_url = self._build_direct_api_url(config)
        data = self._request_direct_api(api_url)
        if not data:
            return

        new_proxies = self._parse_proxy_response(data)
        if not new_proxies:
            return

        self._merge_new_proxies(new_proxies, force_refresh)
        self._save_proxy_pool()

    # CloudBypass 相关方法
    def _generate_cloudbypass_session(self) -> str:
        alphabet = string.ascii_lowercase + string.digits
        return "".join(random.choices(alphabet, k=self.cloudbypass_session_length))

    def _create_cloudbypass_proxy(self) -> Proxy:
        session_id = self._generate_cloudbypass_session()
        username = (
            f"{self.cloudbypass_account}-res_"
            f"{self.cloudbypass_region}_{session_id}-{self.cloudbypass_ttl_label}"
        )
        expires_at = time.time() + self.cloudbypass_ttl_minutes * 60
        proxy = Proxy(
            ip=self.cloudbypass_host,
            port=self.cloudbypass_port,
            protocol=self.cloudbypass_protocol,
            username=username,
            password=self.cloudbypass_password,
            expires_at=expires_at,
        )
        return proxy

    def _generate_cloudbypass_proxies(self, count: int):
        if not self.cloudbypass_enabled:
            return

        created = 0
        for _ in range(max(count, 0)):
            try:
                proxy = self._create_cloudbypass_proxy()
                self.proxies.append(proxy)
                created += 1
            except Exception as exc:
                logger.error(f"创建 CloudBypass 代理失败: {exc}")

        if created > 0:
            logger.info(f"生成 {created} 个 CloudBypass 代理，当前总数: {len(self.proxies)}")

    def _cleanup_cloudbypass_proxies(self):
        if not self.cloudbypass_enabled:
            return

        current_time = time.time()
        before = len(self.proxies)
        self.proxies = [
            proxy
            for proxy in self.proxies
            if proxy.fail_count < self.max_fails
            and proxy.expires_at is not None
            and current_time < proxy.expires_at
        ]
        removed = before - len(self.proxies)
        if removed > 0:
            logger.debug(f"移除了 {removed} 个过期或失效的 CloudBypass 代理")
            self._save_proxy_pool()

    def _ensure_cloudbypass_pool(self) -> list[Proxy]:
        self._cleanup_cloudbypass_proxies()
        available = [p for p in self.proxies if p.fail_count < self.max_fails]
        if len(available) < self.min_proxy_count:
            needed = max(self.min_proxy_count - len(available), 1)
            logger.info(
                f"可用 CloudBypass 代理不足 ({len(available)}/{self.min_proxy_count})，生成新的代理"
            )
            self._generate_cloudbypass_proxies(needed)
            self._cleanup_cloudbypass_proxies()
            available = [p for p in self.proxies if p.fail_count < self.max_fails]
            if available:
                self._save_proxy_pool()
        return available

    def _parse_proxy(self, proxy_str: str) -> Proxy | None:
        """
        解析代理字符串
        支持格式:
        - ip:port
        - protocol://ip:port
        - protocol://username:password@ip:port
        """
        try:
            if "://" in proxy_str:
                protocol, rest = proxy_str.split("://", 1)
            else:
                protocol = "http"
                rest = proxy_str

            username, password = None, None
            if "@" in rest:
                auth, rest = rest.split("@", 1)
                username, password = auth.split(":", 1)

            ip, port = rest.split(":", 1)

            return Proxy(
                ip=ip, port=int(port), protocol=protocol, username=username, password=password
            )
        except Exception as e:
            logger.warning(f"解析代理失败: {proxy_str}, 错误: {e}")
            return None

    def _cleanup_expired_proxies(self):
        """
        清理过期的代理
        注意：即使超过过期时间，只要IP还能用（未被封），仍然保留
        只有在fail_count超过max_fails时才真正移除
        """
        current_time = time.time()
        expired_count = 0

        valid_proxies = []
        for proxy in self.proxies:
            # 如果失败次数过多，直接移除（不管是否过期）
            if proxy.fail_count >= self.max_fails:
                expired_count += 1
                continue

            # 如果代理有过期时间且已过期，但仍然可用（fail_count < max_fails），保留
            # 因为用户要求"在IP被封前都可以用"
            if proxy.expires_at is None:
                # 没有过期时间的代理（如从文件加载的）保留
                valid_proxies.append(proxy)
            elif current_time < proxy.expires_at:
                # 未过期的代理保留
                valid_proxies.append(proxy)
            else:
                # 已过期但还能用的代理也保留（避免浪费）
                # 只有在真正被封时才移除
                valid_proxies.append(proxy)

        if expired_count > 0:
            logger.debug(f"清理了 {expired_count} 个失效代理（fail_count >= max_fails）")
            self.proxies = valid_proxies

    def get_proxy(self) -> Proxy | None:
        """获取一个可用代理"""
        with self.lock:
            available_proxies: list[Proxy] | None = None

            if self.pool_type == "direct_api":
                self._cleanup_expired_proxies()

                # 如果可用代理数量不足，尝试刷新
                # 同时检查是否有大量代理即将过期（用于提前刷新）
                current_time = time.time()
                available_count = len([p for p in self.proxies if p.fail_count < self.max_fails])

                # 统计即将在1分钟内过期的代理数量
                expiring_soon_count = len(
                    [
                        p
                        for p in self.proxies
                        if (
                            p.expires_at is not None
                            and p.expires_at > current_time
                            and p.expires_at < current_time + 60
                            and p.fail_count < self.max_fails
                        )
                    ]
                )

                # 如果可用代理不足，或者大量代理即将过期，则刷新
                if available_count < self.min_proxy_count:
                    logger.info(
                        f"可用代理数量不足 ({available_count} < {self.min_proxy_count})，刷新代理池"
                    )
                    self._load_from_direct_api(force_refresh=False)
                    self._cleanup_expired_proxies()
                    self._save_proxy_pool()  # 保存更新后的IP池
                elif expiring_soon_count >= self.min_proxy_count:
                    logger.info(f"有 {expiring_soon_count} 个代理即将过期，提前刷新代理池")
                    self._load_from_direct_api(force_refresh=False)
                    self._cleanup_expired_proxies()
                    self._save_proxy_pool()  # 保存更新后的IP池

                if not self.proxies:
                    logger.warning("代理池为空，尝试重新加载")
                    self._load_from_direct_api(force_refresh=True)
                    if not self.proxies:
                        logger.error("无法从API获取代理")
                        return None
                    self._save_proxy_pool()

                available_proxies = [p for p in self.proxies if p.fail_count < self.max_fails]

            elif self.pool_type == "cloudbypass":
                available_proxies = self._ensure_cloudbypass_pool()
                if not available_proxies:
                    logger.error("没有可用的 CloudBypass 代理")
                    return None

            else:
                if not self.proxies:
                    logger.warning("代理池为空")
                    return None
                available_proxies = [p for p in self.proxies if p.fail_count < self.max_fails]

            if not available_proxies:
                logger.warning("没有可用代理，重置失败计数")
                for proxy in self.proxies:
                    proxy.fail_count = 0
                # 重置失败计数后，所有代理都应该可用（只要没过期或未被封）
                available_proxies = [p for p in self.proxies if p.fail_count < self.max_fails]

                if not available_proxies:
                    logger.error("所有代理都已失效（fail_count >= max_fails）")
                    return None

            # 选择使用最少的代理（优先选择未使用过的）
            proxy = min(available_proxies, key=lambda p: p.last_used)
            proxy.last_used = time.time()

            return proxy

    def mark_success(self, proxy: Proxy):
        """标记代理使用成功"""
        with self.lock:
            proxy.fail_count = max(0, proxy.fail_count - 1)
            self.proxy_stats[str(proxy)] += 1
            logger.debug(f"代理成功: {proxy}")

            # 动态代理需要持久化最新状态
            if self.pool_type in {"direct_api", "cloudbypass"}:
                self._save_proxy_pool()

    def mark_failure(self, proxy: Proxy):
        """标记代理使用失败"""
        with self.lock:
            proxy.fail_count += 1
            logger.warning(f"代理失败 ({proxy.fail_count}/{self.max_fails}): {proxy}")

            if proxy.fail_count >= self.max_fails:
                logger.error(f"代理已禁用: {proxy}")
                if self.pool_type == "cloudbypass" and proxy in self.proxies:
                    self.proxies.remove(proxy)
                    logger.debug("已移除失效的 CloudBypass 代理")

            # 动态代理需要持久化最新状态
            if self.pool_type in {"direct_api", "cloudbypass"}:
                self._save_proxy_pool()

    def test_proxy(self, proxy: Proxy, timeout: int = 10) -> bool:
        """测试代理是否可用"""
        try:
            start_time = time.time()
            response = requests.get(
                self.test_url, proxies=proxy.get_proxy_dict(), timeout=timeout, verify=False
            )
            response.raise_for_status()

            proxy.response_time = time.time() - start_time
            logger.debug(f"代理测试成功: {proxy}, 响应时间: {proxy.response_time:.2f}s")
            return True
        except Exception as e:
            logger.debug(f"代理测试失败: {proxy}, 错误: {e}")
            return False

    def test_all_proxies(self):
        """测试所有代理"""
        logger.info("开始测试所有代理...")
        valid_proxies = []

        for proxy in self.proxies:
            if self.test_proxy(proxy):
                valid_proxies.append(proxy)

        self.proxies = valid_proxies
        logger.info(f"测试完成，可用代理数: {len(self.proxies)}")

    def get_stats(self) -> dict:
        """获取代理使用统计"""
        return {
            "total": len(self.proxies),
            "available": len([p for p in self.proxies if p.fail_count < self.max_fails]),
            "usage": dict(self.proxy_stats),
        }

    def add_proxy(self, proxy: Proxy):
        """添加代理"""
        with self.lock:
            self.proxies.append(proxy)
            logger.info(f"添加代理: {proxy}")

    def remove_proxy(self, proxy: Proxy):
        """移除代理"""
        with self.lock:
            if proxy in self.proxies:
                self.proxies.remove(proxy)
                logger.info(f"移除代理: {proxy}")
