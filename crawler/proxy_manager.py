"""
代理IP管理模块
支持多种代理源：文件、API、Redis
"""

import time
import random
import requests
from typing import Optional, List, Dict
from threading import Lock
from collections import defaultdict
from utils.logger import get_logger

logger = get_logger("ProxyManager")


class Proxy:
    """代理对象"""
    
    def __init__(self, ip: str, port: int, protocol: str = "http", 
                 username: str = None, password: str = None):
        self.ip = ip
        self.port = port
        self.protocol = protocol
        self.username = username
        self.password = password
        self.fail_count = 0
        self.last_used = 0
        self.response_time = 0
        
    def get_proxy_dict(self) -> Dict[str, str]:
        """获取代理字典格式"""
        if self.username and self.password:
            proxy_url = f"{self.protocol}://{self.username}:{self.password}@{self.ip}:{self.port}"
        else:
            proxy_url = f"{self.protocol}://{self.ip}:{self.port}"
        
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    
    def __str__(self):
        return f"{self.protocol}://{self.ip}:{self.port}"


class ProxyManager:
    """代理管理器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.proxies: List[Proxy] = []
        self.proxy_stats = defaultdict(int)
        self.lock = Lock()
        self.max_fails = config.get('max_fails', 3)
        self.test_url = config.get('test_url', 'https://www.httpbin.org/ip')
        self.pool_type = config.get('pool_type', 'file')
        
        # 加载代理
        self._load_proxies()
        
    def _load_proxies(self):
        """加载代理列表"""
        if self.pool_type == 'file':
            self._load_from_file()
        elif self.pool_type == 'api':
            self._load_from_api()
        else:
            logger.warning(f"不支持的代理池类型: {self.pool_type}")
    
    def _load_from_file(self):
        """从文件加载代理"""
        proxy_file = self.config.get('proxy_file', 'proxies.txt')
        try:
            with open(proxy_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
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
        """从API加载代理"""
        api_url = self.config.get('api_url')
        api_key = self.config.get('api_key')
        
        if not api_url:
            logger.error("未配置代理API URL")
            return
        
        try:
            headers = {}
            if api_key:
                headers['Authorization'] = f"Bearer {api_key}"
            
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 根据实际API格式解析
            data = response.json()
            proxies_data = data.get('proxies', [])
            
            for proxy_data in proxies_data:
                proxy = Proxy(
                    ip=proxy_data.get('ip'),
                    port=proxy_data.get('port'),
                    protocol=proxy_data.get('protocol', 'http'),
                    username=proxy_data.get('username'),
                    password=proxy_data.get('password')
                )
                self.proxies.append(proxy)
            
            logger.info(f"从API加载了 {len(self.proxies)} 个代理")
        except Exception as e:
            logger.error(f"从API加载代理失败: {e}")
    
    def _parse_proxy(self, proxy_str: str) -> Optional[Proxy]:
        """
        解析代理字符串
        支持格式:
        - ip:port
        - protocol://ip:port
        - protocol://username:password@ip:port
        """
        try:
            if '://' in proxy_str:
                protocol, rest = proxy_str.split('://', 1)
            else:
                protocol = 'http'
                rest = proxy_str
            
            username, password = None, None
            if '@' in rest:
                auth, rest = rest.split('@', 1)
                username, password = auth.split(':', 1)
            
            ip, port = rest.split(':', 1)
            
            return Proxy(
                ip=ip,
                port=int(port),
                protocol=protocol,
                username=username,
                password=password
            )
        except Exception as e:
            logger.warning(f"解析代理失败: {proxy_str}, 错误: {e}")
            return None
    
    def get_proxy(self) -> Optional[Proxy]:
        """获取一个可用代理"""
        with self.lock:
            if not self.proxies:
                logger.warning("代理池为空")
                return None
            
            # 过滤掉失败次数过多的代理
            available_proxies = [p for p in self.proxies if p.fail_count < self.max_fails]
            
            if not available_proxies:
                logger.warning("没有可用代理，重置失败计数")
                for proxy in self.proxies:
                    proxy.fail_count = 0
                available_proxies = self.proxies
            
            # 选择使用最少的代理
            proxy = min(available_proxies, key=lambda p: p.last_used)
            proxy.last_used = time.time()
            
            return proxy
    
    def mark_success(self, proxy: Proxy):
        """标记代理使用成功"""
        with self.lock:
            proxy.fail_count = max(0, proxy.fail_count - 1)
            self.proxy_stats[str(proxy)] += 1
            logger.debug(f"代理成功: {proxy}")
    
    def mark_failure(self, proxy: Proxy):
        """标记代理使用失败"""
        with self.lock:
            proxy.fail_count += 1
            logger.warning(f"代理失败 ({proxy.fail_count}/{self.max_fails}): {proxy}")
            
            if proxy.fail_count >= self.max_fails:
                logger.error(f"代理已禁用: {proxy}")
    
    def test_proxy(self, proxy: Proxy, timeout: int = 10) -> bool:
        """测试代理是否可用"""
        try:
            start_time = time.time()
            response = requests.get(
                self.test_url,
                proxies=proxy.get_proxy_dict(),
                timeout=timeout,
                verify=False
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
            "usage": dict(self.proxy_stats)
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

