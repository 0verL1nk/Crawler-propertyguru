"""
代理工具模块
提供静态IP代理和动态代理池的统一接口
支持SSL证书（Bright Data等需要证书的代理服务）
"""

import ssl
import os
from pathlib import Path
from typing import Optional, Dict, Union
from .logger import get_logger

logger = get_logger("ProxyUtils")


class ResidentialProxy:
    """住宅代理（动态IP，自动轮换，支持SSL证书）
    
    虽然代理URL是固定的，但代理服务商会自动为每次请求分配不同的住宅IP，
    实现动态IP轮换，避免被封禁。适合大规模爬取和批量处理任务。
    """
    
    def __init__(self, proxy_url: str, ssl_cert_path: Optional[str] = None):
        """
        初始化静态代理
        
        Args:
            proxy_url: 代理URL，格式:
                - http://host:port
                - http://user:pass@host:port
                - https://host:port
                - socks5://host:port
            ssl_cert_path: SSL证书文件路径（可选），用于Bright Data等需要证书的代理
                如果不提供，会尝试从环境变量 PROXY_SSL_CERT 读取
        
        Examples:
            >>> # 不使用证书
            >>> proxy = ResidentialProxy('http://user:pass@host:port')
            >>> 
            >>> # 使用SSL证书（Bright Data动态住宅代理）
            >>> proxy = ResidentialProxy(
            ...     'http://user:pass@brd.superproxy.io:33335',
            ...     ssl_cert_path='cert/ca-certificate.crt'
            ... )
            >>> # 每次请求会自动使用不同的住宅IP
        """
        self.proxy_url = proxy_url
        self.ssl_cert_path = ssl_cert_path or os.getenv('PROXY_SSL_CERT')
        self.ssl_context = None
        
        # 初始化SSL上下文（如果提供证书）
        self._init_ssl_context()
        
        self._parse_proxy()
    
    def _init_ssl_context(self):
        """初始化SSL上下文"""
        if self.ssl_cert_path:
            cert_path = Path(self.ssl_cert_path)
            if cert_path.exists():
                try:
                    self.ssl_context = ssl.create_default_context(cafile=str(cert_path))
                    logger.info(f"SSL证书已加载: {self.ssl_cert_path}")
                except Exception as e:
                    logger.error(f"加载SSL证书失败: {e}")
                    self.ssl_context = None
            else:
                logger.warning(f"SSL证书文件不存在: {self.ssl_cert_path}")
                self.ssl_context = None
    
    def _parse_proxy(self):
        """解析代理URL"""
        try:
            # 解析协议
            if '://' in self.proxy_url:
                self.protocol = self.proxy_url.split('://')[0]
                rest = self.proxy_url.split('://', 1)[1]
            else:
                self.protocol = 'http'
                rest = self.proxy_url
            
            # 解析认证信息和地址
            if '@' in rest:
                auth_part, addr_part = rest.rsplit('@', 1)
                if ':' in auth_part:
                    self.username, self.password = auth_part.split(':', 1)
                else:
                    self.username = auth_part
                    self.password = ''
                
                # 显示隐藏后的代理信息用于日志
                masked_proxy = f"{self.protocol}://***:***@{addr_part}"
            else:
                self.username = None
                self.password = None
                addr_part = rest
                masked_proxy = f"{self.protocol}://{addr_part}"
            
            # 解析主机和端口
            if ':' in addr_part:
                self.host, port_str = addr_part.rsplit(':', 1)
                self.port = int(port_str)
            else:
                self.host = addr_part
                self.port = 8080 if self.protocol == 'http' else 1080
            
            logger.info(f"住宅代理已配置（动态IP）: {masked_proxy}")
            
        except Exception as e:
            logger.error(f"解析代理URL失败: {e}")
            raise ValueError(f"无效的代理URL格式: {self.proxy_url}")
    
    def get_proxies(self) -> Dict[str, str]:
        """
        获取requests格式的代理字典
        
        Returns:
            代理字典，格式: {'http': 'proxy_url', 'https': 'proxy_url'}
        """
        return {
            'http': self.proxy_url,
            'https': self.proxy_url
        }
    
    def get_urllib_handler(self):
        """
        获取urllib格式的代理handler
        
        Returns:
            ProxyHandler实例
        
        Example:
            >>> import urllib.request
            >>> proxy = ResidentialProxy('http://user:pass@host:port')
            >>> opener = urllib.request.build_opener(proxy.get_urllib_handler())
            >>> opener.open(url)
        """
        import urllib.request
        return urllib.request.ProxyHandler(self.get_proxies())
    
    def get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """
        获取SSL上下文
        
        Returns:
            SSL上下文或None
        """
        return self.ssl_context
    
    def get_requests_verify(self) -> Union[bool, str]:
        """
        获取requests的verify参数
        
        Returns:
            - 如果有SSL证书，返回证书路径
            - 如果没有，返回False（禁用SSL验证）
        """
        if self.ssl_cert_path and Path(self.ssl_cert_path).exists():
            return str(self.ssl_cert_path)
        return False  # Bright Data代理需要禁用默认验证或使用自定义证书
    
    def test(self, test_url: str = 'https://httpbin.org/ip', timeout: int = 10) -> bool:
        """
        测试代理是否可用（支持SSL证书）
        
        Args:
            test_url: 测试URL
            timeout: 超时时间
        
        Returns:
            是否可用
        """
        try:
            import requests
            logger.info(f"测试代理连接: {test_url}")
            
            # 使用SSL证书或禁用验证
            verify = self.get_requests_verify()
            
            response = requests.get(
                test_url,
                proxies=self.get_proxies(),
                timeout=timeout,
                verify=verify
            )
            
            response.raise_for_status()
            
            # 尝试解析IP
            try:
                data = response.json()
                ip = data.get('origin', 'Unknown')
                logger.info(f"代理测试成功，IP: {ip}")
            except:
                logger.info("代理测试成功")
            
            return True
            
        except Exception as e:
            logger.error(f"代理测试失败: {e}")
            return False
    
    def __str__(self):
        """字符串表示（隐藏密码）"""
        if self.username:
            return f"{self.protocol}://{self.username}:***@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
    
    def __repr__(self):
        return f"ResidentialProxy('{self.proxy_url}')"


class ProxyAdapter:
    """代理适配器 - 统一静态代理和动态代理池的接口（支持SSL证书）"""
    
    def __init__(self, proxy: Union[str, 'ResidentialProxy', 'ProxyManager'] = None, 
                 ssl_cert_path: Optional[str] = None):
        """
        初始化代理适配器
        
        Args:
            proxy: 可以是:
                - 字符串: 住宅代理URL（动态IP）
                - ResidentialProxy实例
                - ProxyManager实例（从crawler.proxy_manager导入）
                - None: 不使用代理
            ssl_cert_path: SSL证书文件路径（当proxy是字符串时使用）
        
        Examples:
            >>> # 使用住宅代理（带SSL证书，动态IP）
            >>> adapter = ProxyAdapter(
            ...     'http://user:pass@brd.superproxy.io:33335',
            ...     ssl_cert_path='cert/ca-certificate.crt'
            ... )
            >>> 
            >>> # 使用代理管理器
            >>> from crawler.proxy_manager import ProxyManager
            >>> pm = ProxyManager(config)
            >>> adapter = ProxyAdapter(pm)
        """
        self.proxy = None
        self.proxy_type = 'none'
        
        if proxy is None:
            self.proxy_type = 'none'
        elif isinstance(proxy, str):
            # 字符串 -> 住宅代理（支持SSL证书，动态IP）
            self.proxy = ResidentialProxy(proxy, ssl_cert_path=ssl_cert_path)
            self.proxy_type = 'static'
        elif isinstance(proxy, ResidentialProxy):
            # ResidentialProxy实例
            self.proxy = proxy
            self.proxy_type = 'static'
        else:
            # 假设是ProxyManager实例
            self.proxy = proxy
            self.proxy_type = 'dynamic'
        
        logger.info(f"代理适配器初始化: {self.proxy_type}")
    
    def get_proxies(self) -> Optional[Dict[str, str]]:
        """
        获取代理字典
        
        Returns:
            代理字典或None
        """
        if self.proxy_type == 'none':
            return None
        elif self.proxy_type == 'static':
            return self.proxy.get_proxies()
        elif self.proxy_type == 'dynamic':
            # 从代理管理器获取
            proxy_obj = self.proxy.get_proxy()
            if proxy_obj:
                return proxy_obj.get_proxy_dict()
            return None
        return None
    
    def get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """
        获取SSL上下文（仅静态代理支持）
        
        Returns:
            SSL上下文或None
        """
        if self.proxy_type == 'static':
            return self.proxy.get_ssl_context()
        return None
    
    def get_verify(self) -> Union[bool, str]:
        """
        获取requests的verify参数
        
        Returns:
            verify参数值
        """
        if self.proxy_type == 'static':
            return self.proxy.get_requests_verify()
        return False
    
    def mark_success(self):
        """标记代理使用成功（仅对动态代理池有效）"""
        if self.proxy_type == 'dynamic' and hasattr(self.proxy, 'mark_success'):
            proxy_obj = self.proxy.get_proxy()
            if proxy_obj:
                self.proxy.mark_success(proxy_obj)
    
    def mark_failure(self):
        """标记代理使用失败（仅对动态代理池有效）"""
        if self.proxy_type == 'dynamic' and hasattr(self.proxy, 'mark_failure'):
            proxy_obj = self.proxy.get_proxy()
            if proxy_obj:
                self.proxy.mark_failure(proxy_obj)
    
    def test(self, test_url: str = 'https://httpbin.org/ip') -> bool:
        """
        测试代理
        
        Args:
            test_url: 测试URL
        
        Returns:
            是否可用
        """
        if self.proxy_type == 'static':
            return self.proxy.test(test_url)
        elif self.proxy_type == 'dynamic':
            # 测试动态代理池中的一个代理
            proxies = self.get_proxies()
            if proxies:
                try:
                    import requests
                    response = requests.get(test_url, proxies=proxies, timeout=10, verify=False)
                    response.raise_for_status()
                    logger.info("代理测试成功")
                    return True
                except Exception as e:
                    logger.error(f"代理测试失败: {e}")
                    return False
        return False


def create_proxy(proxy_config: Union[str, dict, None], 
                 ssl_cert_path: Optional[str] = None) -> Optional[ProxyAdapter]:
    """
    创建代理适配器（工厂函数）
    
    Args:
        proxy_config: 代理配置，可以是:
            - 字符串: 静态代理URL
            - 字典: 代理管理器配置
            - None: 不使用代理
        ssl_cert_path: SSL证书文件路径（当proxy_config是字符串时使用）
    
    Returns:
        ProxyAdapter实例或None
    
    Examples:
        >>> # 静态代理（带SSL证书）
        >>> adapter = create_proxy(
        ...     'http://user:pass@brd.superproxy.io:33335',
        ...     ssl_cert_path='cert/ca-certificate.crt'
        ... )
        >>> 
        >>> # 代理池配置
        >>> adapter = create_proxy({
        ...     'enabled': True,
        ...     'pool_type': 'file',
        ...     'proxy_file': 'proxies.txt'
        ... })
    """
    if proxy_config is None:
        return None
    
    if isinstance(proxy_config, str):
        # 静态代理（支持SSL证书）
        ssl_cert = ssl_cert_path or os.getenv('PROXY_SSL_CERT')
        return ProxyAdapter(proxy_config, ssl_cert_path=ssl_cert)
    
    if isinstance(proxy_config, dict):
        # 动态代理池
        from crawler.proxy_manager import ProxyManager
        pm = ProxyManager(proxy_config)
        return ProxyAdapter(pm)
    
    return None

