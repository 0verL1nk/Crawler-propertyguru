"""
爬虫进度管理模块
用于记录爬取进度，支持断点续传
注意：completed_listings 不再保存在文件中，而是从数据库查询
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger("CrawlProgress")


class CrawlProgress:
    """爬虫进度管理器"""

    def __init__(self, progress_file: str = "crawl_progress.json", db_ops=None):
        """
        初始化进度管理器

        Args:
            progress_file: 进度文件路径
            db_ops: 数据库操作对象（可选），用于查询完成状态
        """
        self.progress_file = Path(progress_file)
        self.db_ops = db_ops
        self.progress_data = self._load_progress()

    def _load_progress(self) -> dict[str, Any]:
        """加载进度文件"""
        if self.progress_file.exists():
            try:
                with self.progress_file.open(encoding="utf-8") as f:
                    raw_data: dict[str, Any] = json.load(f)
                    # 移除 completed_listings 和 failed_listings（不再从文件加载）
                    data: dict[str, Any] = {}
                    for key, value in raw_data.items():
                        if key not in ("completed_listings", "failed_listings"):
                            data[key] = value
                    logger.info(f"加载进度文件: {data.get('last_page', 0)} 页")
                    return data
            except Exception as e:
                logger.warning(f"加载进度文件失败: {e}，将创建新文件")
        return {
            "last_page": 0,
            "start_time": None,
            "last_update": None,
        }

    def save_progress(self):
        """保存进度到文件（不保存completed_listings，从数据库查询）"""
        try:
            progress = {
                "last_page": self.progress_data.get("last_page", 0),
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

    def mark_listing_completed(self, listing_id: int):  # noqa: ARG002
        """
        标记房源已完成（不再保存到文件，数据库已有记录）
        此方法保留是为了兼容性，实际不做任何操作

        Args:
            listing_id: 房源ID（保留参数以保持接口兼容性）
        """
        # 不再保存到文件，因为数据库已经有 is_completed 字段
        # 如果需要更新进度时间，可以在这里更新
        self.progress_data["last_update"] = datetime.now().isoformat()
        # 不调用 save_progress()，避免频繁写入文件

    def mark_listing_failed(self, listing_id: int):
        """
        标记房源失败（保留兼容性，但不再保存到文件）
        此方法保留是为了兼容性，实际不做任何操作
        """
        # 不再保存到文件
        pass

    def is_listing_completed(self, listing_id: int) -> bool:
        """
        检查房源是否已完成
        优先从数据库查询，如果没有db_ops则返回False

        Args:
            listing_id: 房源ID

        Returns:
            是否完成
        """
        if self.db_ops:
            result = self.db_ops.check_listing_completed(listing_id)
            return bool(result)
        # 如果没有db_ops，返回False（不再从文件查询）
        return False

    def is_listing_failed(self, listing_id: int) -> bool:  # noqa: ARG002
        """检查房源是否失败过（保留兼容性，但不再使用）"""
        # 不再从文件查询failed_listings
        return False

    def get_last_page(self) -> int:
        """获取最后完成的页码"""
        value = self.progress_data.get("last_page", 0)
        return int(value) if value is not None else 0

    def get_completed_count(self) -> int:
        """获取已完成房源数量（从数据库查询）"""
        if self.db_ops:
            return int(self.db_ops.count_completed_listings())
        return 0

    def get_failed_count(self) -> int:
        """获取失败房源数量（不再使用）"""
        return 0

    def reset(self):
        """重置进度"""
        self.progress_data = {
            "last_page": 0,
            "start_time": datetime.now().isoformat(),
            "last_update": None,
        }
        if self.progress_file.exists():
            self.progress_file.unlink()
        logger.info("进度已重置")
