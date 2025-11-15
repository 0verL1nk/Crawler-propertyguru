"""__NEXT_DATA__ 详情页 JSON 解析器"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from crawler.models import PropertyDetails
from utils.logger import get_logger

logger = get_logger("DetailJsonParser")


class DetailJsonParser:
    """将 __NEXT_DATA__ JSON 转换为 PropertyDetails 与媒体数据的解析器"""

    def __init__(self, next_data: dict[str, Any] | None):
        self.raw = next_data or {}
        props = self.raw.get("props") or {}
        self.page_props = props.get("pageProps") or {}
        self.page_data = self.page_props.get("pageData") or {}
        self.data = self.page_data.get("data") or {}

    def build_property_details(self) -> PropertyDetails | None:
        """解析 PropertyDetails 结构"""
        listing_id = self._extract_listing_id()
        if not listing_id:
            logger.warning("__NEXT_DATA__ 中未找到 listing_id，无法构建 PropertyDetails")
            return None

        details = PropertyDetails(listing_id=listing_id)
        details.property_details = self._parse_property_detail_items()

        description_title, description = self._parse_description()
        details.description_title = description_title
        details.description = description

        details.amenities = self._parse_text_list("amenitiesData")
        details.facilities = self._parse_text_list("facilitiesData")
        return details

    def parse_media_urls(self) -> list[tuple[str, str]]:
        """从 mediaExplorerData 中提取媒体 URL 列表"""
        media_data = (self.data.get("mediaExplorerData") or {}).get("mediaGroups") or {}
        media_urls: list[tuple[str, str]] = []

        def append_media(items: list[dict[str, Any]] | None, media_type: str) -> None:
            if not items:
                return
            for item in items:
                src = item.get("src")
                if not src:
                    src_list = item.get("srcList") or []
                    if src_list:
                        src = src_list[0]
                if src:
                    media_urls.append((media_type, src))

        append_media((media_data.get("images") or {}).get("items"), "image")
        append_media((media_data.get("floorPlans") or {}).get("items"), "image")
        # 暂不抓取视频/虚拟看房，避免产生额外处理逻辑
        return media_urls

    def parse_all(self) -> dict[str, Any]:
        """一次性解析 PropertyDetails 与媒体数据"""
        details = self.build_property_details()
        media_urls = self.parse_media_urls()
        amenities = details.amenities if details else None
        facilities = details.facilities if details else None
        return {
            "property_details": details,
            "amenities": amenities or [],
            "facilities": facilities or [],
            "media_urls": media_urls,
        }

    def _extract_listing_id(self) -> int | None:
        """尝试从多个路径中提取 listing_id"""
        candidate_sources = [
            (self.data.get("listingData") or {}).get("listingId"),
            (self.data.get("listingDetail") or {}).get("listingId"),
            (self.data.get("dataCachingContext") or {}).get("listingId"),
            (self.page_data.get("listingData") or {}).get("listingId"),
            self.page_data.get("listingId"),
            self.page_props.get("listingId"),
        ]

        for value in candidate_sources:
            normalized = self._normalize_listing_id(value)
            if normalized:
                return normalized

        # 兜底：在 data 节点里深度搜索 listingId 字段
        return self._deep_search_listing_id(self.data)

    def _normalize_listing_id(self, value: Any) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    def _deep_search_listing_id(self, node: Any) -> int | None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"listingId", "listing_id", "unifiedListingId"}:
                    normalized = self._normalize_listing_id(value)
                    if normalized:
                        return normalized
                found = self._deep_search_listing_id(value)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = self._deep_search_listing_id(item)
                if found:
                    return found
        return None

    def _parse_property_detail_items(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        metatable = (self.data.get("detailsData") or {}).get("metatable") or {}
        items = metatable.get("items") or []

        for idx, item in enumerate(items, start=1):
            key = item.get("icon") or item.get("label") or f"field_{idx}"
            value = self._clean_text(item.get("value"))
            if not value:
                continue
            self._append_property_detail_value(result, key, value)

        return result

    def _append_property_detail_value(self, container: dict[str, Any], key: str, value: str) -> None:
        existing = container.get(key)
        if existing is None:
            container[key] = value
        elif isinstance(existing, list):
            existing.append(value)
        else:
            container[key] = [existing, value]

    def _parse_description(self) -> tuple[str | None, str | None]:
        block = self.data.get("descriptionBlockData") or {}
        title = self._clean_text(block.get("subtitle")) or self._clean_text(block.get("title"))
        description_html = block.get("description")
        description = self._clean_html(description_html)
        return title, description

    def _parse_text_list(self, section_key: str) -> list[str] | None:
        section = self.data.get(section_key) or {}
        items = section.get("data") or []
        values = [self._clean_text(item.get("text")) for item in items]
        filtered = [value for value in values if value]
        return filtered or None

    def _clean_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _clean_html(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        soup = BeautifulSoup(value, "lxml")
        text = soup.get_text(separator="\n")
        text = re.sub(r"\n{2,}", "\n", text)
        text = text.strip()
        return text or None
