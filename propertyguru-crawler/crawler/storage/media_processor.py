"""
媒体处理模块
处理图片/视频下载、去水印、上传S3的异步流程
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import aiohttp

from utils.logger import get_logger
from utils.proxy import ProxyAdapter

from ..models import MediaItem

if TYPE_CHECKING:
    from ..storage import StorageManagerProtocol
    from ..utils.watermark_remover import WatermarkRemover

logger = get_logger("MediaProcessor")


class MediaProcessor:
    """媒体处理器"""

    def __init__(
        self,
        storage_manager: StorageManagerProtocol,
        watermark_remover: WatermarkRemover | None = None,
        proxy_url: str | None = None,
        proxy_manager: Any | None = None,
        process_immediately: bool = True,
    ):
        """
        初始化媒体处理器

        Args:
            storage_manager: 存储管理器实例
            watermark_remover: 去水印工具实例（可选）
            proxy_url: 代理URL（用于下载图片，静态代理）
            proxy_manager: 代理管理器实例（用于动态获取直连IP代理）
            process_immediately: 是否立即进行去水印处理
                True: 立即进行去水印并上传S3
                False: 只保存原始URL到数据库，后续再批量处理去水印
        """
        self.storage_manager = storage_manager
        self.watermark_remover = watermark_remover
        self.proxy_url = proxy_url
        self.proxy_manager = proxy_manager
        self.process_immediately = process_immediately
        self.temp_dir = Path(tempfile.gettempdir()) / "propertyguru_media"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # 创建线程池用于并行执行去水印任务（同步API的异步化）
        self.executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="watermark")

        # 下载并发控制：限制同时下载的图片数量（避免过多并发导致卡住）
        self.download_semaphore = asyncio.Semaphore(5)  # 最多同时下载5张图片

        if not process_immediately:
            logger.info("已配置为跳过去水印处理，只保存原始URL到数据库")

    def _generate_temp_filename(
        self, url: str, listing_id: int | None = None, position: int | None = None
    ) -> str:
        """生成临时文件名"""
        parsed = urlparse(url)
        original_filename = Path(parsed.path).name or "image.jpg"
        stem = Path(original_filename).stem
        suffix = Path(original_filename).suffix
        unique_id = uuid.uuid4().hex[:8]

        if listing_id is not None and position is not None:
            return f"{stem}_{listing_id}_{position}_{unique_id}{suffix}"
        return f"{stem}_{unique_id}{suffix}"

    def _get_proxy_from_manager(self, last_proxy_obj: Any | None) -> tuple[str | None, Any | None]:
        """从代理管理器获取代理"""
        if not self.proxy_manager:
            return None, None

        try:
            if last_proxy_obj:
                self.proxy_manager.mark_failure(last_proxy_obj)
                logger.debug("已标记代理失败，获取新代理")

            proxy_obj = self.proxy_manager.get_proxy()
            if proxy_obj:
                proxy_dict = proxy_obj.get_proxy_dict()
                proxy = proxy_dict.get("http") or proxy_dict.get("https")
                logger.debug(f"使用直连IP代理: {proxy_obj.ip}:{proxy_obj.port}")
                return proxy, proxy_obj
        except Exception as e:
            logger.warning(f"从代理管理器获取代理失败: {e}")

        return None, None

    def _get_proxy_from_url(self) -> str | None:
        """从静态代理URL获取代理"""
        if not self.proxy_url:
            return None

        try:
            proxy_adapter = ProxyAdapter(self.proxy_url)
            proxies = proxy_adapter.get_proxies()
            if proxies:
                return proxies.get("http") or proxies.get("https")
        except Exception as e:
            logger.warning(f"从静态代理URL获取代理失败: {e}")

        return None

    async def _download_with_aiohttp(self, url: str, proxy: str | None, temp_path: Path) -> None:
        """使用 aiohttp 下载文件"""
        timeout = aiohttp.ClientTimeout(total=60)
        connector = aiohttp.TCPConnector(limit=10)

        async with (
            aiohttp.ClientSession(timeout=timeout, connector=connector) as session,
            session.get(url, proxy=proxy) as response,
        ):
            # 检查状态码，503等服务器错误需要重试
            if response.status >= 500:
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=response.reason or "Server Error",
                )

            response.raise_for_status()

            # 保存文件
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            with temp_path.open("wb") as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)

    def download_image_from_browser(
        self,
        img_element: Any,
        driver: Any,
        temp_path: Path | None = None,
        listing_id: int | None = None,
        position: int | None = None,
    ) -> Path | None:
        """
        从浏览器元素直接获取图片（避免重新下载）

        Args:
            img_element: Selenium WebElement 图片元素
            driver: Selenium WebDriver 实例
            temp_path: 临时保存路径（可选）
            listing_id: 房源ID（用于生成唯一文件名）
            position: 位置索引（用于生成唯一文件名）

        Returns:
            保存的文件路径，失败返回None
        """
        try:
            if temp_path is None:
                # 从URL提取文件名，并添加唯一标识避免并发冲突
                src = img_element.get_attribute("src") or ""
                parsed = urlparse(src if src.startswith("http") else "http://example.com/image.jpg")
                original_filename = Path(parsed.path).name or "image.jpg"

                if listing_id is not None and position is not None:
                    stem = Path(original_filename).stem
                    suffix = Path(original_filename).suffix
                    unique_id = uuid.uuid4().hex[:8]
                    filename = f"{stem}_{listing_id}_{position}_{unique_id}{suffix}"
                else:
                    stem = Path(original_filename).stem
                    suffix = Path(original_filename).suffix
                    unique_id = uuid.uuid4().hex[:8]
                    filename = f"{stem}_{unique_id}{suffix}"

                temp_path = self.temp_dir / filename

            # 方法1: 如果图片是base64，直接获取
            src = img_element.get_attribute("src") or ""
            if src.startswith("data:image"):
                # base64图片，直接解码保存
                import base64

                header, encoded = src.split(",", 1)
                image_data = base64.b64decode(encoded)
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                with temp_path.open("wb") as f:
                    f.write(image_data)
                logger.info(f"从浏览器获取base64图片成功: {temp_path}")
                return temp_path

            # 方法2: 使用canvas将图片转换为base64（保留原始格式）
            script = """
            var img = arguments[0];
            var canvas = document.createElement('canvas');
            var ctx = canvas.getContext('2d');
            canvas.width = img.naturalWidth || img.width;
            canvas.height = img.naturalHeight || img.height;
            ctx.drawImage(img, 0, 0);
            // 根据原图格式选择输出格式，默认jpg（体积更小）
            var format = 'image/jpeg';
            if (img.src && img.src.includes('.png')) {
                format = 'image/png';
            }
            return canvas.toDataURL(format, 0.95);
            """
            try:
                base64_data = driver.execute_script(script, img_element)
                if base64_data and base64_data.startswith("data:image"):
                    import base64

                    header, encoded = base64_data.split(",", 1)
                    image_data = base64.b64decode(encoded)
                    temp_path.parent.mkdir(parents=True, exist_ok=True)
                    with temp_path.open("wb") as f:
                        f.write(image_data)
                    logger.info(f"从浏览器获取图片成功: {temp_path}")
                    return temp_path
            except Exception as e:
                logger.debug(f"使用canvas获取图片失败: {e}")

            return None

        except Exception as e:
            logger.error(f"从浏览器获取图片失败: {e}")
            return None

    async def download_image(
        self,
        url: str,
        temp_path: Path | None = None,
        listing_id: int | None = None,
        position: int | None = None,
    ) -> Path | None:
        """
        使用动态代理异步下载图片

        Args:
            url: 图片URL
            temp_path: 临时保存路径（可选）
            listing_id: 房源ID（用于生成唯一文件名）
            position: 位置索引（用于生成唯一文件名）

        Returns:
            下载的文件路径，失败返回None
        """
        if temp_path is None:
            filename = self._generate_temp_filename(url, listing_id, position)
            temp_path = self.temp_dir / filename

        max_retries = 3
        last_proxy_obj = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"重试下载图片 (尝试 {attempt + 1}/{max_retries}): {url}")
                else:
                    logger.info(f"开始下载图片: {url}")

                result, last_proxy_obj = await self._download_with_retry(
                    url, temp_path, last_proxy_obj
                )
                if result:
                    return result

            except (aiohttp.ClientError, aiohttp.ClientResponseError) as e:
                should_retry = self._handle_download_error(e, attempt, max_retries, url)
                if should_retry:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                return None

            except Exception as e:
                logger.error(f"下载图片失败: {url}, 错误: {e}")
                return None

        return None

    def remove_watermark(self, image_path: Path) -> Path | None:
        """
        调用去水印API处理图片

        Args:
            image_path: 图片文件路径

        Returns:
            处理后的图片路径，失败返回None
        """
        if not self.watermark_remover:
            logger.warning("未配置去水印工具，跳过去水印步骤")
            return image_path

        try:
            # 检查文件是否存在
            if not image_path.exists():
                logger.error(f"图片文件不存在，无法去水印: {image_path}")
                return None

            logger.info(f"开始去除水印: {image_path.name}")

            # 生成输出路径
            output_path = image_path.parent / f"{image_path.stem}_no_watermark{image_path.suffix}"

            # 调用去水印API
            result_path = self.watermark_remover.remove_watermark(
                image_path, output_path=output_path
            )

            if result_path:
                logger.info(f"去水印完成: {result_path}")
                # 删除原图（确保文件存在且是文件而不是目录）
                if image_path.exists() and image_path.is_file():
                    try:
                        image_path.unlink()
                    except Exception as e:
                        logger.warning(f"删除原图失败: {image_path}, 错误: {e}")
                return Path(result_path)
            else:
                logger.warning(f"去水印失败，使用原图: {image_path}")
                return image_path

        except Exception as e:
            logger.error(f"去水印失败: {e}")
            return image_path  # 失败时返回原图

    def _generate_s3_key(self, image_url: str, listing_id: int, position: int) -> str:
        """生成S3 key"""
        parsed = urlparse(image_url)
        original_filename = Path(parsed.path).name or f"image_{listing_id}_{position}.jpg"
        original_stem = Path(original_filename).stem
        original_suffix = Path(original_filename).suffix
        s3_filename = f"{original_stem}_no_watermark{original_suffix}"
        return f"propertyguru/{listing_id}/{s3_filename}"

    def _get_s3_url(self, s3_key: str) -> str:
        """获取S3 URL"""
        s3_url = self.storage_manager.get_file_url(s3_key, expires_in=31536000)  # 1年
        if not s3_url and hasattr(self.storage_manager, "bucket_name"):
            bucket_name = self.storage_manager.bucket_name
            s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
        return s3_url or s3_key

    def _handle_download_error(
        self, e: Exception, attempt: int, max_retries: int, url: str
    ) -> bool:
        """处理下载错误，返回是否应该重试"""
        error_msg = str(e)
        status_code = getattr(e, "status", None)

        if status_code:
            logger.warning(
                f"下载图片失败 (尝试 {attempt + 1}/{max_retries}): {url}, "
                f"状态码: {status_code}, 错误: {error_msg}"
            )
        else:
            logger.warning(
                f"下载图片失败 (尝试 {attempt + 1}/{max_retries}): {url}, 错误: {error_msg}"
            )

        if attempt < max_retries - 1:
            return True  # 应该重试

        logger.error(f"下载图片失败，已重试 {max_retries} 次: {url}, 错误: {error_msg}")
        return False  # 不应该重试

    async def _download_with_retry(
        self, url: str, temp_path: Path, last_proxy_obj: Any | None
    ) -> tuple[Path | None, Any | None]:
        """执行单次下载尝试，返回 (结果路径, 更新后的代理对象)"""
        # 获取代理
        proxy, proxy_obj = self._get_proxy_from_manager(last_proxy_obj)
        if proxy_obj:
            last_proxy_obj = proxy_obj

        if not proxy:
            proxy = self._get_proxy_from_url()

        # 使用信号量控制并发下载数量
        async with self.download_semaphore:
            await self._download_with_aiohttp(url, proxy, temp_path)

        logger.info(f"图片下载成功: {temp_path}")
        return temp_path, last_proxy_obj

    def upload_to_s3(self, file_path: Path, s3_key: str) -> bool:
        """
        上传文件到S3

        Args:
            file_path: 本地文件路径
            s3_key: S3对象键

        Returns:
            是否成功
        """
        try:
            logger.info(f"开始上传到S3: {s3_key}")

            success = self.storage_manager.upload_file(file_path, s3_key=s3_key)

            if success:
                logger.info(f"上传S3成功: {s3_key}")
                # 删除临时文件
                if file_path.exists():
                    file_path.unlink()
            else:
                logger.error(f"上传S3失败: {s3_key}")

            return success

        except Exception as e:
            logger.error(f"上传S3失败: {e}")
            return False

    async def _get_image_from_browser_or_download(
        self,
        image_url: str,
        listing_id: int,
        position: int,
        img_element: Any | None,
        browser_driver: Any | None,
    ) -> Path | None:
        """从浏览器获取图片或下载图片"""
        if img_element and browser_driver:
            try:
                temp_path = self.download_image_from_browser(
                    img_element, browser_driver, listing_id=listing_id, position=position
                )
                if temp_path:
                    logger.info(f"成功从浏览器获取图片: {image_url}")
                    return temp_path
            except Exception as e:
                logger.debug(f"从浏览器获取图片失败，将使用下载方式: {e}")

        return await self.download_image(image_url, listing_id=listing_id, position=position)

    async def _process_watermark_removal(self, temp_path: Path) -> Path | None:
        """处理去水印"""
        if not temp_path.exists():
            logger.error(f"图片文件不存在，无法去水印: {temp_path}")
            return None

        loop = asyncio.get_event_loop()
        processed_path = await loop.run_in_executor(self.executor, self.remove_watermark, temp_path)

        if processed_path is None or not processed_path.exists():
            logger.error(f"去水印后的文件不存在: {processed_path}")
            return None

        return processed_path

    def _check_watermark_removed(self, original_path: Path, processed_path: Path | None) -> bool:
        """
        判断去水印是否成功

        Args:
            original_path: 原始图片路径
            processed_path: 处理后的图片路径

        Returns:
            是否去水印成功
        """
        if not processed_path or not processed_path.exists():
            return False

        # 如果路径不同，说明生成了新文件（去水印成功）
        if processed_path != original_path:
            return True

        # 如果路径相同，检查是否有去水印工具配置
        if self.watermark_remover:
            # 有工具但返回原图，说明去水印失败
            return False

        # 没有工具，不算失败也不算成功
        return False

    def _upload_processed_image(
        self, processed_path: Path, image_url: str, listing_id: int, position: int
    ) -> tuple[str | None, str | None, bool]:
        """
        上传处理后的图片到S3

        Args:
            processed_path: 处理后的图片路径
            image_url: 原始图片URL
            listing_id: 房源ID
            position: 位置索引

        Returns:
            (s3_url, s3_key, success) 元组
        """
        s3_key = self._generate_s3_key(image_url, listing_id, position)
        success = self.upload_to_s3(processed_path, s3_key)
        if success:
            s3_url = self._get_s3_url(s3_key)
            return s3_url, s3_key, True
        else:
            logger.warning(f"去水印成功但上传S3失败: {image_url}")
            return None, None, False

    def _cleanup_failed_image(self, processed_path: Path | None) -> None:
        """清理去水印失败的临时文件"""
        if processed_path and processed_path.exists():
            try:
                processed_path.unlink()
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")

    async def process_image(
        self,
        image_url: str,
        listing_id: int,
        position: int,
        img_element: Any | None = None,
        browser_driver: Any | None = None,
    ) -> MediaItem | None:
        """
        处理单张图片（下载、去水印、上传S3）
        根据process_immediately配置决定是否立即进行去水印处理

        Args:
            image_url: 图片URL
            listing_id: 房源ID
            position: 位置索引
            img_element: 浏览器中的图片元素（可选，用于直接从浏览器获取）
            browser_driver: 浏览器驱动实例（可选，用于从浏览器获取图片）

        Returns:
            MediaItem对象，失败返回None
        """
        try:
            # 如果配置为不立即处理，只保存原始URL
            if not self.process_immediately:
                return MediaItem(
                    listing_id=listing_id,
                    media_type="image",
                    original_url=image_url,
                    media_url=None,
                    s3_key=None,
                    watermark_removed=False,
                    position=position,
                )

            # 1. 获取图片
            temp_path = await self._get_image_from_browser_or_download(
                image_url, listing_id, position, img_element, browser_driver
            )
            if not temp_path:
                return None

            # 2. 去水印
            original_path = temp_path
            processed_path = await self._process_watermark_removal(temp_path)
            watermark_removed = self._check_watermark_removed(original_path, processed_path)

            # 3. 只有去水印成功才上传到S3
            s3_url = None
            s3_key = None
            if watermark_removed and processed_path:
                s3_url, s3_key, upload_success = self._upload_processed_image(
                    processed_path, image_url, listing_id, position
                )
                if not upload_success:
                    watermark_removed = False  # 上传失败，标记为未成功
            else:
                # 去水印失败，清理临时文件
                self._cleanup_failed_image(processed_path)
                logger.warning(f"去水印失败，不上传S3: {image_url}")

            # 4. 返回MediaItem（无论是否成功都保存记录，包含原始URL以便后续补偿）
            return MediaItem(
                listing_id=listing_id,
                media_type="image",
                original_url=image_url,
                media_url=s3_url,
                s3_key=s3_key,
                watermark_removed=watermark_removed,
                position=position,
            )

        except Exception as e:
            logger.error(f"处理图片失败: {image_url}, 错误: {e}")
            return None

    async def process_video(
        self, video_url: str, listing_id: int, position: int
    ) -> MediaItem | None:
        """
        处理视频（下载、上传S3，视频不去水印）

        Args:
            video_url: 视频URL
            listing_id: 房源ID
            position: 位置索引

        Returns:
            MediaItem对象，失败返回None
        """
        try:
            # 1. 下载视频（使用图片下载方法，通用，使用唯一文件名）
            temp_path = await self.download_image(
                video_url, listing_id=listing_id, position=position
            )
            if not temp_path:
                return None

            # 2. 生成S3 key
            parsed = urlparse(video_url)
            filename = Path(parsed.path).name or f"video_{listing_id}_{position}.mp4"
            s3_key = f"propertyguru/{listing_id}/{filename}"

            # 3. 上传到S3
            success = self.upload_to_s3(temp_path, s3_key)
            if not success:
                return None

            # 4. 获取S3 URL
            s3_url = self.storage_manager.get_file_url(s3_key, expires_in=31536000)
            if not s3_url and hasattr(self.storage_manager, "bucket_name"):
                bucket_name = self.storage_manager.bucket_name
                s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"

            return MediaItem(
                listing_id=listing_id,
                media_type="video",
                original_url=video_url,
                media_url=s3_url or s3_key,
                s3_key=s3_key,
                watermark_removed=False,  # 视频不去水印
                position=position,
            )

        except Exception as e:
            logger.error(f"处理视频失败: {video_url}, 错误: {e}")
            return None

    async def process_media_list(
        self, media_urls: list[tuple], listing_id: int, browser_driver: Any | None = None
    ) -> list[MediaItem]:
        """
        批量处理媒体文件（异步）
        注意：现在不处理视频，只处理图片

        Args:
            media_urls: [(media_type, url), ...] 列表，视频会被自动跳过
            listing_id: 房源ID

        Returns:
            MediaItem对象列表（只包含图片）
        """
        tasks = []

        for position, media_info in enumerate(media_urls):
            # media_info 可能是 (type, url) 或 (type, url, element)
            if len(media_info) == 3:
                media_type, url, img_element = media_info
            else:
                media_type, url = media_info
                img_element = None

            if media_type == "image":
                task = self.process_image(
                    url,
                    listing_id,
                    position,
                    img_element=img_element,
                    browser_driver=browser_driver,
                )
            elif media_type == "video":
                # 跳过视频处理（现在不保存视频）
                logger.debug(f"跳过视频处理: {url}")
                continue
            else:
                logger.warning(f"未知的媒体类型: {media_type}")
                continue

            tasks.append(task)

        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤成功的结果
        media_items: list[MediaItem] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"处理媒体失败: {result}")
            elif isinstance(result, MediaItem):
                media_items.append(result)

        logger.debug(f"处理完成: {len(media_items)}/{len(media_urls)} 个媒体文件")
        return media_items
