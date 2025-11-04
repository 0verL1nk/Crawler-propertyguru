"""
爬虫进度管理模块
用于记录爬取进度，支持断点续传
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger("CrawlProgress")


class CrawlProgress:
    """爬虫进度管理器"""

    def __init__(self, progress_file: str = "crawl_progress.json"):
        """
        初始化进度管理器

        Args:
            progress_file: 进度文件路径
        """
        self.progress_file = Path(progress_file)
        self.progress_data = self._load_progress()

    def _load_progress(self) -> dict[str, Any]:
        """加载进度文件"""
        if self.progress_file.exists():
            try:
                with self.progress_file.open(encoding="utf-8") as f:
                    raw_data: dict[str, Any] = json.load(f)
                    # 将list转换回set
                    data: dict[str, Any] = {}
                    for key, value in raw_data.items():
                        if key in ("completed_listings", "failed_listings") and isinstance(
                            value, list
                        ):
                            data[key] = set(value)
                        else:
                            data[key] = value
                    logger.info(
                        f"加载进度文件: {data.get('last_page', 0)} 页, "
                        f"{len(data.get('completed_listings', set()))} 个房源"
                    )
                    return data
            except Exception as e:
                logger.warning(f"加载进度文件失败: {e}，将创建新文件")
        return {
            "last_page": 0,
            "completed_listings": set(),
            "failed_listings": set(),
            "start_time": None,
            "last_update": None,
        }

    def save_progress(self):
        """保存进度到文件"""
        try:
            # 将set转换为list以便JSON序列化
            progress = {
                "last_page": self.progress_data.get("last_page", 0),
                "completed_listings": list(self.progress_data.get("completed_listings", set())),
                "failed_listings": list(self.progress_data.get("failed_listings", set())),
                "start_time": self.progress_data.get("start_time"),
                "last_update": self.progress_data.get("last_update"),
            }
            with self.progress_file.open("w", encoding="utf-8") as f:
                json.dump(progress, f, indent=2, ensure_ascii=False)
            logger.debug(f"进度已保存: {self.progress_file}")
        except Exception as e:
            logger.error(f"保存进度失败: {e}")

    def mark_page_completed(self, page_num: int):
        """标记页面已完成"""
        self.progress_data["last_page"] = max(self.progress_data.get("last_page", 0), page_num)
        self.progress_data["last_update"] = datetime.now().isoformat()
        self.save_progress()

    def mark_listing_completed(self, listing_id: int):
        """标记房源已完成"""
        if "completed_listings" not in self.progress_data:
            self.progress_data["completed_listings"] = set()
        self.progress_data["completed_listings"].add(listing_id)
        self.progress_data["last_update"] = datetime.now().isoformat()
        self.save_progress()

    def mark_listing_failed(self, listing_id: int):
        """标记房源失败"""
        if "failed_listings" not in self.progress_data:
            self.progress_data["failed_listings"] = set()
        self.progress_data["failed_listings"].add(listing_id)
        self.progress_data["last_update"] = datetime.now().isoformat()
        self.save_progress()

    def is_listing_completed(self, listing_id: int) -> bool:
        """检查房源是否已完成"""
        completed = self.progress_data.get("completed_listings", set())
        return listing_id in completed

    def is_listing_failed(self, listing_id: int) -> bool:
        """检查房源是否失败过"""
        failed = self.progress_data.get("failed_listings", set())
        return listing_id in failed

    def get_last_page(self) -> int:
        """获取最后完成的页码"""
        value = self.progress_data.get("last_page", 0)
        return int(value) if value is not None else 0

    def get_completed_count(self) -> int:
        """获取已完成房源数量"""
        return len(self.progress_data.get("completed_listings", set()))

    def get_failed_count(self) -> int:
        """获取失败房源数量"""
        return len(self.progress_data.get("failed_listings", set()))

    def reset(self):
        """重置进度"""
        self.progress_data = {
            "last_page": 0,
            "completed_listings": set(),
            "failed_listings": set(),
            "start_time": datetime.now().isoformat(),
            "last_update": None,
        }
        if self.progress_file.exists():
            self.progress_file.unlink()
        logger.info("进度已重置")
