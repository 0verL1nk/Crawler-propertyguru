"""
图片去水印API封装
基于 magiceraser.org API
"""

import os
import time
import requests
from pathlib import Path
from typing import Union, Optional, Dict, Any
from dotenv import load_dotenv
from utils.logger import get_logger
from utils.proxy import ProxyAdapter

# 加载环境变量
load_dotenv()

logger = get_logger("WatermarkRemover")


class WatermarkRemover:
    """图片去水印工具类"""
    
    BASE_URL = "https://api.magiceraser.org"
    
    def __init__(self, product_serial: str = None, product_code: str = None, 
                 authorization: str = None, proxy: Union[str, ProxyAdapter] = None):
        """
        初始化去水印工具
        
        Args:
            product_serial: 产品序列号，如不提供则从环境变量 WATERMARK_REMOVER_PRODUCT_SERIAL 读取
            product_code: 产品代码，如不提供则从环境变量 WATERMARK_REMOVER_PRODUCT_CODE 读取
            authorization: 授权令牌，如不提供则从环境变量 WATERMARK_REMOVER_AUTHORIZATION 读取
            proxy: 代理，可以是:
                - 字符串: 静态代理URL，如 'http://user:pass@host:port'
                - ProxyAdapter实例: 支持静态代理和代理池
                - None: 从环境变量 PROXY_URL 读取，如无则不使用代理
        
        Examples:
            >>> # 从环境变量自动加载配置
            >>> remover = WatermarkRemover()
            >>> 
            >>> # 手动指定代理
            >>> remover = WatermarkRemover(
            ...     proxy='http://user:pass@brd.superproxy.io:33335'
            ... )
            >>> 
            >>> # 使用代理适配器
            >>> from utils.proxy import ProxyAdapter
            >>> adapter = ProxyAdapter('http://user:pass@host:port')
            >>> remover = WatermarkRemover(proxy=adapter)
        """
        # 从环境变量或参数获取配置
        self.product_serial = product_serial or os.getenv(
            'WATERMARK_REMOVER_PRODUCT_SERIAL',
            'd92a85a2-7f15-40d0-975d-518d1610eb71'  # 默认值
        )
        self.product_code = product_code or os.getenv(
            'WATERMARK_REMOVER_PRODUCT_CODE',
            '067003'  # 默认值
        )
        self.authorization = authorization or os.getenv(
            'WATERMARK_REMOVER_AUTHORIZATION',
            ''
        )
        
        # 配置代理适配器
        if proxy is None:
            # 尝试从环境变量读取代理
            proxy = os.getenv('PROXY_URL')
        
        if isinstance(proxy, str):
            self.proxy_adapter = ProxyAdapter(proxy)
        elif isinstance(proxy, ProxyAdapter):
            self.proxy_adapter = proxy
        else:
            self.proxy_adapter = ProxyAdapter(None)
        
        # 创建会话
        self.session = requests.Session()
        
        # 设置会话代理
        proxies = self.proxy_adapter.get_proxies()
        if proxies:
            self.session.proxies.update(proxies)
    
    def _get_proxy_dict(self) -> Optional[Dict[str, str]]:
        """
        获取代理字典
        
        Returns:
            代理字典
        """
        return self.proxy_adapter.get_proxies()
    
    def _get_headers(self, content_type: str = None) -> Dict[str, str]:
        """
        获取请求头
        
        Args:
            content_type: 内容类型
        
        Returns:
            请求头字典
        """
        headers = {
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Ch-Ua": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Product-Serial": self.product_serial,
            "Product-Code": self.product_code,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
            "Accept": "*/*",
            "Origin": "https://magiceraser.org",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://magiceraser.org/",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Priority": "u=1, i"
        }
        
        if self.authorization:
            headers["Authorization"] = self.authorization
        
        if content_type:
            headers["Content-Type"] = content_type
        
        return headers
    
    def create_job(self, image_path: Union[str, Path]) -> Optional[str]:
        """
        创建去水印任务
        
        Args:
            image_path: 图片文件路径
        
        Returns:
            job_id 或 None
        """
        try:
            image_path = Path(image_path)
            
            if not image_path.exists():
                logger.error(f"图片文件不存在: {image_path}")
                return None
            
            # 准备文件
            with open(image_path, 'rb') as f:
                files = {
                    'original_image_file': (
                        image_path.name,
                        f,
                        'image/jpeg' if image_path.suffix.lower() in ['.jpg', '.jpeg'] else 'image/png'
                    )
                }
                
                # 发送请求
                url = f"{self.BASE_URL}/api/magiceraser/v3/ai-image-watermark-remove-auto/create-job"
                headers = self._get_headers()
                # 不设置 Content-Type，让 requests 自动处理 multipart/form-data
                headers.pop('Content-Type', None)
                
                logger.info(f"正在创建去水印任务: {image_path.name}")
                
                # 使用适配器的SSL验证设置
                verify = self.proxy_adapter.get_verify() if self.proxy_adapter else False
                
                response = self.session.post(
                    url,
                    files=files,
                    headers=headers,
                    timeout=60,
                    verify=verify
                )
                
                response.raise_for_status()
                result = response.json()
                
                # 解析响应
                if result.get('code') == 100000:
                    job_id = result.get('result', {}).get('job_id')
                    logger.info(f"任务创建成功，job_id: {job_id}")
                    return job_id
                else:
                    logger.error(f"任务创建失败: {result.get('message')}")
                    return None
                    
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            return None
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            job_id: 任务ID
        
        Returns:
            任务状态信息
        """
        try:
            url = f"{self.BASE_URL}/api/magiceraser/v2/ai-remove-object/get-job/{job_id}"
            headers = self._get_headers()
            
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return {}
    
    def wait_for_completion(self, job_id: str, max_wait: int = 300, 
                          check_interval: int = 3) -> Optional[str]:
        """
        等待任务完成
        
        Args:
            job_id: 任务ID
            max_wait: 最大等待时间（秒）
            check_interval: 检查间隔（秒）
        
        Returns:
            处理后的图片URL 或 None
        """
        logger.info(f"等待任务完成: {job_id}")
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            result = self.get_job_status(job_id)
            code = result.get('code')
            
            if code == 100000:
                # 任务完成
                output_urls = result.get('result', {}).get('output_url', [])
                if output_urls:
                    output_url = output_urls[0]
                    logger.info(f"任务完成！输出URL: {output_url}")
                    return output_url
                else:
                    logger.error("任务完成但未获取到输出URL")
                    return None
                    
            elif code == 300006:
                # 处理中
                message = result.get('message', {}).get('zh', '处理中...')
                logger.info(f"任务状态: {message}")
                time.sleep(check_interval)
                
            else:
                # 其他错误
                message = result.get('message', {})
                logger.error(f"任务失败: {message}")
                return None
        
        logger.error(f"等待超时（{max_wait}秒）")
        return None
    
    def download_result(self, url: str, save_path: Union[str, Path]) -> bool:
        """
        下载处理后的图片
        
        Args:
            url: 图片URL
            save_path: 保存路径
        
        Returns:
            是否成功
        """
        try:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"正在下载图片: {url}")
            
            verify = self.proxy_adapter.get_verify() if self.proxy_adapter else False
            response = self.session.get(url, timeout=60, verify=verify)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"图片已保存: {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
            return False
    
    def remove_watermark(self, image_path: Union[str, Path], 
                        output_path: Union[str, Path] = None,
                        max_wait: int = 300) -> Optional[str]:
        """
        去除图片水印（完整流程）
        
        Args:
            image_path: 输入图片路径
            output_path: 输出图片路径，如不指定则在原文件名后加 _no_watermark
            max_wait: 最大等待时间（秒）
        
        Returns:
            输出图片路径 或 None
        """
        try:
            image_path = Path(image_path)
            
            # 设置输出路径
            if output_path is None:
                output_path = image_path.parent / f"{image_path.stem}_no_watermark{image_path.suffix}"
            else:
                output_path = Path(output_path)
            
            logger.info(f"开始去除水印: {image_path.name}")
            
            # 1. 创建任务
            job_id = self.create_job(image_path)
            if not job_id:
                return None
            
            # 2. 等待完成
            result_url = self.wait_for_completion(job_id, max_wait=max_wait)
            if not result_url:
                return None
            
            # 3. 下载结果
            if self.download_result(result_url, output_path):
                logger.info(f"去水印完成！保存至: {output_path}")
                return str(output_path)
            else:
                return None
                
        except Exception as e:
            logger.error(f"去水印失败: {e}")
            return None
    
    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()


# 便捷函数
def remove_watermark(image_path: Union[str, Path], 
                    output_path: Union[str, Path] = None,
                    product_serial: str = None,
                    product_code: str = None,
                    authorization: str = None,
                    proxy: Union[str, ProxyAdapter] = None) -> Optional[str]:
    """
    去除图片水印（便捷函数）
    
    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径
        product_serial: 产品序列号（可选，默认从环境变量读取）
        product_code: 产品代码（可选，默认从环境变量读取）
        authorization: 授权令牌（可选，默认从环境变量读取）
        proxy: 代理配置（可选，默认从环境变量读取）
    
    Returns:
        输出图片路径 或 None
    
    Examples:
        >>> # 使用环境变量配置
        >>> result = remove_watermark("input.jpg", "output.jpg")
        >>> 
        >>> # 手动指定配置
        >>> result = remove_watermark(
        ...     "input.jpg",
        ...     "output.jpg",
        ...     proxy='http://user:pass@host:port'
        ... )
        >>> 
        >>> if result:
        ...     print(f"成功: {result}")
    """
    remover = WatermarkRemover(
        product_serial=product_serial,
        product_code=product_code,
        authorization=authorization,
        proxy=proxy
    )
    
    try:
        return remover.remove_watermark(image_path, output_path)
    finally:
        remover.close()

