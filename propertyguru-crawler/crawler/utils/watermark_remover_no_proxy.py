"""
图片去水印API封装（不使用代理版本）
基于 magiceraser.org API
通过请求头伪造IP地址
"""

from __future__ import annotations

import os
import random
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from utils.logger import get_logger

# 加载环境变量
load_dotenv()

logger = get_logger("WatermarkRemoverNoProxy")


def _generate_fake_ip() -> str:
    """生成随机的伪造IP地址"""
    return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"


class WatermarkRemoverNoProxy:
    """图片去水印工具类（不使用代理，通过请求头伪造IP）"""

    BASE_URL = "https://api.magiceraser.org"

    def __init__(
        self,
        product_serial: str | None = None,
        product_code: str | None = None,
        authorization: str | None = None,
        fake_ip: str | None = None,
    ):
        """
        初始化去水印工具（不使用代理）

        Args:
            product_serial: 产品序列号，如不提供则从环境变量 WATERMARK_REMOVER_PRODUCT_SERIAL 读取
            product_code: 产品代码，如不提供则从环境变量 WATERMARK_REMOVER_PRODUCT_CODE 读取
            authorization: 授权令牌，如不提供则从环境变量 WATERMARK_REMOVER_AUTHORIZATION 读取
            fake_ip: 伪造的IP地址，如不提供则随机生成

        Examples:
            >>> # 从环境变量自动加载配置
            >>> remover = WatermarkRemoverNoProxy()
            >>>
            >>> # 手动指定伪造IP
            >>> remover = WatermarkRemoverNoProxy(fake_ip="123.45.67.89")
        """
        # 从环境变量或参数获取配置
        self.product_serial = product_serial or os.getenv(
            "WATERMARK_REMOVER_PRODUCT_SERIAL",
            "d92a85a2-7f15-40d0-975d-518d1610eb71",  # 默认值
        )
        self.product_code = product_code or os.getenv(
            "WATERMARK_REMOVER_PRODUCT_CODE",
            "067003",  # 默认值
        )
        self.authorization = authorization or os.getenv("WATERMARK_REMOVER_AUTHORIZATION", "")

        # 设置伪造IP（每次请求都会使用，如果为None则每次随机生成）
        self.fake_ip = fake_ip

        # 创建会话
        self.session = requests.Session()

        # 配置会话以支持大文件上传
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info("不使用代理模式，通过请求头伪造IP地址")

    def _get_headers(self, content_type: str | None = None) -> dict[str, str]:
        """
        获取请求头（包含伪造IP的字段）

        Args:
            content_type: 内容类型

        Returns:
            请求头字典
        """
        # 生成或使用伪造IP
        fake_ip = self.fake_ip or _generate_fake_ip()

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
            "Priority": "u=1, i",
            # 伪造IP的请求头（注意：这些头通常不会真正改变服务端看到的IP，真实IP来自TCP连接）
            "X-Forwarded-For": fake_ip,
            "X-Real-IP": fake_ip,
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "api.magiceraser.org",
            "CF-Connecting-IP": fake_ip,  # Cloudflare使用的头
            "True-Client-IP": fake_ip,  # 某些CDN使用的头
        }

        if self.authorization:
            headers["Authorization"] = self.authorization

        if content_type:
            headers["Content-Type"] = content_type

        logger.debug(f"使用伪造IP: {fake_ip}")

        return headers  # type: ignore[return-value]

    def _prepare_file_for_upload(self, image_path: Path) -> tuple[BytesIO, str, int]:
        """准备文件用于上传，返回 (file_buffer, content_type, file_size)"""
        with image_path.open("rb") as f:
            file_content = f.read()

        content_type = (
            "image/jpeg" if image_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
        )

        file_buffer = BytesIO(file_content)
        file_buffer.seek(0)
        file_size = len(file_content)

        logger.info(f"图片大小: {file_size / 1024 / 1024:.2f} MB")
        return file_buffer, content_type, file_size

    def _calculate_timeout(self, file_size: int) -> tuple[int, float]:
        """计算请求超时时间，返回 (连接超时, 读取超时)"""
        read_timeout = max(120, file_size / 1024 / 10)
        timeout = (10, min(read_timeout, 300))
        logger.debug(f"请求超时设置: 连接={timeout[0]}s, 读取={timeout[1]:.1f}s")
        return timeout

    def _send_create_job_request(
        self, files: dict, headers: dict, timeout: tuple[int, float]
    ) -> str | None:
        """发送创建任务请求"""
        url = f"{self.BASE_URL}/api/magiceraser/v3/ai-image-watermark-remove-auto/create-job"
        logger.debug("不使用代理，直接连接")

        response = self.session.post(
            url, files=files, headers=headers, timeout=timeout, verify=True, proxies=None
        )

        response.raise_for_status()
        result = response.json()

        if result.get("code") == 100000:
            job_id = result.get("result", {}).get("job_id")
            if isinstance(job_id, str):
                logger.info(f"任务创建成功，job_id: {job_id}")
                return job_id
            logger.error("任务创建失败: job_id 不是字符串")
            return None

        logger.error(f"任务创建失败: {result.get('message')}")
        return None

    def create_job(self, image_path: str | Path) -> str | None:
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

            file_buffer, content_type, file_size = self._prepare_file_for_upload(image_path)

            try:
                files = {
                    "original_image_file": (
                        image_path.name,
                        file_buffer,
                        content_type,
                    )
                }

                headers = self._get_headers()
                headers.pop("Content-Type", None)

                logger.info(f"正在创建去水印任务: {image_path.name}")

                timeout = self._calculate_timeout(file_size)
                return self._send_create_job_request(files, headers, timeout)
            finally:
                file_buffer.close()

        except requests.exceptions.Timeout as e:
            logger.error(f"创建任务超时: {e}")
            logger.error("建议：检查网络连接或增加超时时间")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"创建任务连接失败: {e}")
            logger.error("建议：检查网络连接")
            return None
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            import traceback

            logger.debug(f"详细错误信息: {traceback.format_exc()}")
            return None

    def get_job_status(self, job_id: str) -> dict[str, Any]:
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

            response = self.session.get(url, headers=headers, timeout=30, verify=True, proxies=None)
            response.raise_for_status()

            result: dict[str, Any] = response.json()
            return result

        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return {}

    def wait_for_completion(
        self, job_id: str, max_wait: int = 300, check_interval: int = 3
    ) -> str | None:
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
            code = result.get("code")

            if code == 100000:
                # 任务完成
                output_urls = result.get("result", {}).get("output_url", [])
                if output_urls and isinstance(output_urls, list) and len(output_urls) > 0:
                    output_url = output_urls[0]
                    if isinstance(output_url, str):
                        logger.info(f"任务完成！输出URL: {output_url}")
                        return output_url
                    logger.error("输出URL不是字符串")
                    return None
                else:
                    logger.error("任务完成但未获取到输出URL")
                    return None

            elif code == 300006:
                # 处理中
                message = result.get("message", {}).get("zh", "处理中...")
                logger.info(f"任务状态: {message}")
                time.sleep(check_interval)

            else:
                # 其他错误
                message = result.get("message", {})
                logger.error(f"任务失败: {message}")
                return None

        logger.error(f"等待超时（{max_wait}秒）")
        return None

    def download_result(self, url: str, save_path: str | Path) -> bool:
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

            headers = self._get_headers()

            response = self.session.get(url, headers=headers, timeout=60, verify=True, proxies=None)
            response.raise_for_status()

            with Path(save_path).open("wb") as f:
                f.write(response.content)

            logger.info(f"图片已保存: {save_path}")
            return True

        except Exception as e:
            logger.error(f"下载图片失败: {e}")
            return False

    def remove_watermark(
        self,
        image_path: str | Path,
        output_path: str | Path | None = None,
        max_wait: int = 300,
    ) -> str | None:
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
                output_path = (
                    image_path.parent / f"{image_path.stem}_no_watermark{image_path.suffix}"
                )
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
def remove_watermark_no_proxy(
    image_path: str | Path,
    output_path: str | Path | None = None,
    product_serial: str | None = None,
    product_code: str | None = None,
    authorization: str | None = None,
    fake_ip: str | None = None,
) -> str | None:
    """
    去除图片水印（便捷函数，不使用代理）

    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径
        product_serial: 产品序列号（可选，默认从环境变量读取）
        product_code: 产品代码（可选，默认从环境变量读取）
        authorization: 授权令牌（可选，默认从环境变量读取）
        fake_ip: 伪造的IP地址（可选，默认随机生成）

    Returns:
        输出图片路径 或 None

    Examples:
        >>> # 使用环境变量配置
        >>> result = remove_watermark_no_proxy("input.jpg", "output.jpg")
        >>>
        >>> # 手动指定伪造IP
        >>> result = remove_watermark_no_proxy(
        ...     "input.jpg",
        ...     "output.jpg",
        ...     fake_ip="123.45.67.89"
        ... )
        >>>
        >>> if result:
        ...     print(f"成功: {result}")
    """
    remover = WatermarkRemoverNoProxy(
        product_serial=product_serial,
        product_code=product_code,
        authorization=authorization,
        fake_ip=fake_ip,
    )

    try:
        return remover.remove_watermark(image_path, output_path)
    finally:
        remover.close()
