"""
页面解析器
用于解析PropertyGuru网站的列表页和详情页
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

if TYPE_CHECKING:
    from selenium.webdriver.remote.webelement import WebElement

from utils.logger import get_logger

from .models import FAQ, ListingInfo, MortgageInfo, PropertyDetails

logger = get_logger("Parsers")


class TextNotEmpty:
    """自定义等待条件：等待元素有非空文本"""

    def __init__(self, element: WebElement):
        self.element = element

    def __call__(self, _driver):
        try:
            text = self.element.text.strip()
            return text if text else False
        except Exception:
            return False


class ListingPageParser:
    """列表页解析器"""

    def __init__(self, browser):
        """
        初始化解析器

        Args:
            browser: RemoteBrowser实例
        """
        self.browser = browser
        self.wait = browser.wait(timeout=10) if browser.driver else None

    def get_max_pages(self) -> int | None:
        """
        获取最大页数

        Returns:
            最大页数，如果无法获取则返回None
        """
        try:
            # 查找分页器 ul da-id="hui-pagination"
            pagination = self.browser.find_element(By.CSS_SELECTOR, 'ul[da-id="hui-pagination"]')
            if not pagination:
                logger.warning("未找到分页器")
                return None

            # 找到所有 li class="pageitem"
            page_items = pagination.find_elements(By.CSS_SELECTOR, "li.pageitem")
            if not page_items:
                logger.warning("未找到分页项")
                return None

            # 倒数第三个li就是最大页数
            if len(page_items) >= 3:
                last_page_item = page_items[-3]
                page_text = last_page_item.text.strip()
                try:
                    max_page = int(page_text)
                    logger.info(f"获取到最大页数: {max_page}")
                    return max_page
                except ValueError:
                    logger.error(f"无法解析页数: {page_text}")
                    return None
            else:
                logger.warning(f"分页项数量不足: {len(page_items)}")
                return 1  # 只有一页

        except Exception as e:
            logger.error(f"获取最大页数失败: {e}")
            return None

    def extract_listing_cards(self) -> list[WebElement]:
        """
        提取所有房产卡片元素

        Returns:
            房产卡片元素列表
        """
        try:
            # 查找 search-result-root
            root = self.browser.find_element(By.CSS_SELECTOR, "div.search-result-root")
            if not root:
                logger.warning("未找到搜索结果根元素")
                return []

            # 查找所有 da-id="parent-listing-card-v2-regular" 的div
            cards: list[WebElement] = root.find_elements(
                By.CSS_SELECTOR, 'div[da-id="parent-listing-card-v2-regular"]'
            )
            logger.info(f"找到 {len(cards)} 个房产卡片")
            return cards

        except Exception as e:
            logger.error(f"提取房产卡片失败: {e}")
            return []

    def _extract_listing_id(self, card: WebElement) -> int | None:
        """提取房源ID"""
        listing_id_str = card.get_attribute("da-listing-id")
        if not listing_id_str:
            logger.warning("未找到listing_id属性")
            return None
        try:
            return int(listing_id_str)
        except ValueError:
            logger.warning(f"无效的listing_id: {listing_id_str}")
            return None

    def _extract_detail_url(self, card: WebElement) -> str | None:
        """提取详情页URL"""
        try:
            footer_links = card.find_elements(By.CSS_SELECTOR, "a.card-footer")
            if not footer_links:
                return None
            footer_link = footer_links[0]
            detail_url = footer_link.get_attribute("href")
            if detail_url:
                return urljoin("https://www.propertyguru.com.sg", detail_url)
        except Exception:
            pass
        return None

    def _wait_for_text(self, element: WebElement, _timeout: int = 5) -> str | None:
        """等待元素有文本内容"""
        if not self.wait:
            # 如果没有wait对象，直接返回当前文本
            return element.text.strip() or None
        try:
            text = self.wait.until(TextNotEmpty(element))
            return text if text else None
        except Exception:
            # 超时后返回当前文本（可能为空）
            return element.text.strip() or None

    def _extract_price(self, card: WebElement) -> Decimal | None:
        """提取价格"""
        try:
            # 滚动到元素位置以确保渲染
            import contextlib

            with contextlib.suppress(Exception):
                self.browser.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", card
                )

            # 根据文档：<div class="listing-price" da-id="listing-card-v2-price">S$ 708,000</div>
            price_elems = card.find_elements(By.CSS_SELECTOR, '[da-id="listing-card-v2-price"]')
            if not price_elems:
                logger.debug("未找到价格元素")
                return None
            price_elem = price_elems[0]

            # 等待元素有文本内容
            price_text = self._wait_for_text(price_elem)
            if not price_text:
                logger.debug("价格元素文本为空")
                return None

            logger.debug(f"价格文本: {price_text}")
            # 提取数字（去除 S$ 和逗号）
            price_match = re.search(r"[\d,]+", price_text.replace(",", ""))
            if price_match:
                price_value = Decimal(price_match.group().replace(",", ""))
                logger.debug(f"提取的价格: {price_value}")
                return price_value
            logger.debug(f"价格文本中未找到数字: {price_text}")
        except Exception as e:
            logger.debug(f"提取价格失败: {e}")
        return None

    def _extract_price_per_sqft(self, card: WebElement) -> Decimal | None:
        """提取每平方英尺价格"""
        try:
            # 根据文档：<p class="hui-typography pg-font-body-xs listing-ppa" da-id="listing-card-v2-psf">S$ 707.29 psf</p>
            psf_elems = card.find_elements(By.CSS_SELECTOR, '[da-id="listing-card-v2-psf"]')
            if not psf_elems:
                logger.debug("未找到每平方英尺价格元素")
                return None
            psf_elem = psf_elems[0]

            # 等待元素有文本内容
            psf_text = self._wait_for_text(psf_elem)
            if not psf_text:
                logger.debug("每平方英尺价格元素文本为空")
                return None

            logger.debug(f"每平方英尺价格文本: {psf_text}")
            # 提取数字（去除 S$ 和 psf）
            psf_match = re.search(r"[\d.]+", psf_text)
            if psf_match:
                psf_value = Decimal(psf_match.group())
                logger.debug(f"提取的每平方英尺价格: {psf_value}")
                return psf_value
            logger.debug(f"每平方英尺价格文本中未找到数字: {psf_text}")
        except Exception as e:
            logger.debug(f"提取每平方英尺价格失败: {e}")
        return None

    def _extract_text_field(
        self, card: WebElement, selector: str, tag: str | None = None
    ) -> str | None:
        """提取文本字段的通用方法"""
        try:
            # 滚动到元素位置以确保渲染
            import contextlib

            with contextlib.suppress(Exception):
                self.browser.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", card
                )

            # 使用 find_elements 避免等待，立即返回
            elems = card.find_elements(By.CSS_SELECTOR, selector)
            if not elems:
                logger.debug(f"未找到元素: {selector}")
                return None
            elem = elems[0]
            if tag:
                tag_elems = elem.find_elements(By.TAG_NAME, tag)
                if not tag_elems:
                    logger.debug(f"未找到 {tag} 标签在 {selector} 中")
                    return None
                elem = tag_elems[0]

            # 等待元素有文本内容
            text = self._wait_for_text(elem)

            logger.debug(f"提取文本 ({selector}): {text[:50] if text else '空'}")
            return text if text else None
        except Exception as e:
            logger.debug(f"提取文本字段失败 ({selector}): {e}")
        return None

    def _extract_int_field(self, card: WebElement, selector: str) -> int | None:
        """提取整数字段"""
        try:
            elems = card.find_elements(By.CSS_SELECTOR, selector)
            if not elems:
                return None
            elem = elems[0]
            p_elems = elem.find_elements(By.TAG_NAME, "p")
            if not p_elems:
                return None

            # 等待元素有文本内容
            text = self._wait_for_text(p_elems[0])
            return int(text) if text else None
        except Exception:
            pass
        return None

    def _extract_decimal_field(self, card: WebElement, selector: str) -> Decimal | None:
        """提取小数字段（带逗号分隔符，如面积）"""
        try:
            # 根据文档：<div da-id="listing-card-v2-area" class="info-item d-flex hstack gap-1"><p class="hui-typography pg-font-body-xs">1,001 sqft</p></div>
            elems = card.find_elements(By.CSS_SELECTOR, selector)
            if not elems:
                logger.debug(f"未找到元素: {selector}")
                return None
            elem = elems[0]
            p_elems = elem.find_elements(By.TAG_NAME, "p")
            if not p_elems:
                logger.debug(f"未找到 p 标签在 {selector} 中")
                return None

            # 等待元素有文本内容
            area_text = self._wait_for_text(p_elems[0])
            if not area_text:
                logger.debug(f"面积文本为空 ({selector})")
                return None

            logger.debug(f"面积文本 ({selector}): {area_text}")
            # 提取数字（去除逗号和单位如 sqft）
            area_match = re.search(r"[\d,]+", area_text.replace(",", ""))
            if area_match:
                area_value = Decimal(area_match.group().replace(",", ""))
                logger.debug(f"提取的面积: {area_value}")
                return area_value
            logger.debug(f"面积文本中未找到数字: {area_text}")
        except Exception as e:
            logger.debug(f"提取小数字段失败 ({selector}): {e}")
        return None

    def _extract_build_year(self, card: WebElement) -> int | None:
        """提取建造年份"""
        try:
            year_elems = card.find_elements(By.CSS_SELECTOR, '[da-id="listing-card-v2-build-year"]')
            if not year_elems:
                return None
            year_elem = year_elems[0]
            p_elems = year_elem.find_elements(By.TAG_NAME, "p")
            if not p_elems:
                return None

            # 等待元素有文本内容
            year_text = self._wait_for_text(p_elems[0])
            if not year_text:
                return None

            year_match = re.search(r"\d{4}", year_text)
            if year_match:
                return int(year_match.group())
        except Exception:
            pass
        return None

    def _extract_mrt_info(self, card: WebElement) -> tuple[str | None, int | None]:
        """提取MRT信息"""
        try:
            mrt_elems = card.find_elements(By.CSS_SELECTOR, '[da-id="listing-card-v2-mrt"]')
            if not mrt_elems:
                return None, None
            mrt_elem = mrt_elems[0]
            span_elems = mrt_elem.find_elements(By.CSS_SELECTOR, "span.listing-location-value")
            if not span_elems:
                return None, None

            # 等待元素有文本内容
            mrt_text = self._wait_for_text(span_elems[0])
            if not mrt_text:
                return None, None

            mrt_distance_m = None
            mrt_match = re.search(r"\((\d+)\s*m\)", mrt_text)
            if mrt_match:
                mrt_distance_m = int(mrt_match.group(1))

            mrt_station = None
            station_match = re.search(r"from\s+(.+)", mrt_text)
            if station_match:
                mrt_station = station_match.group(1).strip()

            return mrt_station, mrt_distance_m
        except Exception:
            pass
        return None, None

    def parse_listing_card(self, card: WebElement) -> ListingInfo | None:
        """
        解析单个房产卡片

        Args:
            card: 房产卡片元素

        Returns:
            ListingInfo对象，如果解析失败返回None
        """
        try:
            logger.debug("开始提取 listing_id...")
            listing_id = self._extract_listing_id(card)
            if not listing_id:
                logger.debug("listing_id 提取失败，返回 None")
                return None
            logger.debug(f"listing_id: {listing_id}")

            logger.debug("开始提取 detail_url...")
            detail_url = self._extract_detail_url(card)
            logger.debug(f"detail_url: {detail_url}")

            logger.debug("开始提取 price...")
            price = self._extract_price(card)
            logger.debug(f"price: {price}")

            logger.debug("开始提取 price_per_sqft...")
            price_per_sqft = self._extract_price_per_sqft(card)
            logger.debug(f"price_per_sqft: {price_per_sqft}")

            logger.debug("开始提取 title...")
            # 根据文档：<h3 class="hui-typography pg-font-label-m listing-type-text" da-id="listing-card-v2-title">619D Punggol Drive</h3>
            title = self._extract_text_field(card, '[da-id="listing-card-v2-title"]', tag="h3")
            if not title:
                # 如果没有 h3，尝试直接取文本
                title_elems = card.find_elements(By.CSS_SELECTOR, '[da-id="listing-card-v2-title"]')
                if title_elems:
                    title = title_elems[0].text.strip()
            logger.debug(f"title: {title}")

            logger.debug("开始提取 location...")
            # 根据文档：<p class="hui-typography pg-font-body-xs listing-address">619D Punggol Drive</p>
            # location 不在 title 元素内，应该直接在卡片下查找
            location = self._extract_text_field(card, "p.listing-address")
            logger.debug(f"location: {location}")

            logger.debug("开始提取 bedrooms...")
            bedrooms = self._extract_int_field(card, '[da-id="listing-card-v2-bedrooms"]')
            logger.debug(f"bedrooms: {bedrooms}")

            logger.debug("开始提取 bathrooms...")
            bathrooms = self._extract_int_field(card, '[da-id="listing-card-v2-bathrooms"]')
            logger.debug(f"bathrooms: {bathrooms}")

            logger.debug("开始提取 area_sqft...")
            area_sqft = self._extract_decimal_field(card, '[da-id="listing-card-v2-area"]')
            logger.debug(f"area_sqft: {area_sqft}")

            logger.debug("开始提取 unit_type...")
            unit_type = self._extract_text_field(
                card, '[da-id="listing-card-v2-unit-type"]', tag="p"
            )
            logger.debug(f"unit_type: {unit_type}")

            logger.debug("开始提取 tenure...")
            tenure = self._extract_text_field(card, '[da-id="listing-card-v2-tenure"]', tag="p")
            logger.debug(f"tenure: {tenure}")

            logger.debug("开始提取 build_year...")
            build_year = self._extract_build_year(card)
            logger.debug(f"build_year: {build_year}")

            logger.debug("开始提取 mrt_info...")
            mrt_station, mrt_distance_m = self._extract_mrt_info(card)
            logger.debug(f"mrt_station: {mrt_station}, mrt_distance_m: {mrt_distance_m}")

            logger.debug("开始提取 listed_age...")
            # 根据文档：<ul class="listing-recency" da-id="listing-card-v2-recency"><div class="info-item d-flex hstack gap-1"><div class="hui-svgicon..."></div><span class="hui-typography pg-font-caption-xs">Listed on Nov 03, 2025 (18m ago)</span></div></ul>
            # 需要在 ul 下找 span
            listed_age = self._extract_text_field(card, '[da-id="listing-card-v2-recency"] span')
            logger.debug(f"listed_age: {listed_age}")

            logger.debug("开始创建 ListingInfo 对象...")

            return ListingInfo(
                listing_id=listing_id,
                title=title,
                price=price,
                price_per_sqft=price_per_sqft,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                area_sqft=area_sqft,
                unit_type=unit_type,
                tenure=tenure,
                build_year=build_year,
                mrt_station=mrt_station,
                mrt_distance_m=mrt_distance_m,
                location=location,
                listed_age=listed_age,
                url=detail_url,
            )

        except Exception as e:
            logger.error(f"解析房产卡片失败: {e}")
            return None


class DetailPageParser:
    """详情页解析器"""

    def __init__(self, browser):
        """
        初始化解析器

        Args:
            browser: RemoteBrowser实例
        """
        self.browser = browser
        self.wait = browser.wait(timeout=30)

    def _dismiss_cookie_banner(self):
        """关闭 Cookie 横幅（如果存在）"""
        try:
            # 查找各种可能的 cookie banner 关闭按钮
            # 优先级：先查找最精确的选择器
            cookie_selectors = [
                ".cookie-banner-action button.btn-dark",  # 精确匹配：<div class="cookie-banner-action"><button class="actionable btn btn-dark">Accept</button></div>
                ".cookie-banner-action button",  # 更通用的匹配
                'button[aria-label*="accept"]',
                'button[aria-label*="Accept"]',
                'button[aria-label*="同意"]',
                ".cookie-banner button",
                ".cookie-banner-section-root button",
                '[class*="cookie"] button[class*="accept"]',
                '[class*="cookie"] button[class*="close"]',
            ]

            for selector in cookie_selectors:
                try:
                    buttons = self.browser.find_elements(By.CSS_SELECTOR, selector)
                    if buttons:
                        # 使用 JavaScript 点击避免遮挡问题
                        self.browser.execute_script("arguments[0].click();", buttons[0])
                        logger.debug(f"已关闭 Cookie 横幅（使用选择器: {selector}）")
                        # 等待一下让横幅消失
                        import time

                        time.sleep(0.5)
                        return True
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"关闭 Cookie 横幅失败: {e}")
        return False

    def _click_modal_button(self, button_selector: str, modal_selector: str) -> bool:
        """
        点击按钮打开模态框并等待加载

        Args:
            button_selector: 按钮选择器
            modal_selector: 模态框内容选择器

        Returns:
            是否成功
        """
        try:
            # 先关闭可能的 Cookie 横幅
            self._dismiss_cookie_banner()

            # 等待按钮出现并可见
            try:
                button = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
                )
            except Exception:
                # 如果按钮不可点击，尝试等待它出现
                try:
                    button = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, button_selector))
                    )
                except Exception:
                    logger.debug(f"按钮未出现: {button_selector}")
                    return False

            # 滚动到按钮位置
            self.browser.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button
            )

            # 等待一下确保滚动完成
            import time

            time.sleep(0.3)

            # 再次尝试关闭 Cookie 横幅（可能在滚动后出现）
            self._dismiss_cookie_banner()

            # 使用 JavaScript 点击避免被其他元素遮挡
            self.browser.execute_script("arguments[0].click();", button)

            # 等待模态框内容加载
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, modal_selector)))

            return True

        except Exception as e:
            logger.debug(f"点击模态框按钮失败: {e}")
            return False

    def _find_close_icon_parent(self, close_icon) -> Any | None:
        """查找关闭图标的可点击父元素"""
        import contextlib

        try:
            return close_icon.find_element(By.XPATH, "./ancestor::button[1]")
        except Exception:
            try:
                return close_icon.find_element(By.XPATH, "./ancestor::div[@role='button'][1]")
            except Exception:
                try:
                    return close_icon.find_element(
                        By.XPATH, "./ancestor::div[contains(@class, 'close')][1]"
                    )
                except Exception:
                    with contextlib.suppress(Exception):
                        return close_icon.find_element(By.XPATH, "./parent::*")
        return None

    def _try_close_by_icon(self) -> bool:
        """尝试通过交叉图标关闭模态框"""
        import time

        try:
            close_icons = self.browser.find_elements(
                By.CSS_SELECTOR, 'div.hui-svgicon--crossed-small-o[da-id="svg-icon"]'
            )
            if not close_icons:
                return False

            close_icon = close_icons[0]
            parent = self._find_close_icon_parent(close_icon)

            if parent:
                self.browser.execute_script("arguments[0].click();", parent)
                logger.debug("已关闭模态框（通过交叉图标父元素）")
                time.sleep(0.3)
                return True

            self.browser.execute_script("arguments[0].click();", close_icon)
            logger.debug("已关闭模态框（直接点击交叉图标）")
            time.sleep(0.3)
            return True
        except Exception as e:
            logger.debug(f"查找交叉图标关闭按钮失败: {e}")
            return False

    def _try_close_by_selectors(self) -> bool:
        """尝试通过常见选择器关闭模态框"""
        import time

        close_selectors = [
            'button[aria-label*="close"]',
            'button[aria-label*="Close"]',
            ".modal-header .close",
            '[data-dismiss="modal"]',
            ".modal button.close",
            ".modal-header button",
            "button.close",
        ]

        for selector in close_selectors:
            try:
                close_elements = self.browser.find_elements(By.CSS_SELECTOR, selector)
                if close_elements:
                    self.browser.execute_script("arguments[0].click();", close_elements[0])
                    logger.debug(f"已关闭模态框（使用选择器: {selector}）")
                    time.sleep(0.3)
                    return True
            except Exception:
                continue

        return False

    def _try_close_by_escape(self) -> None:
        """尝试通过ESC键关闭模态框"""
        import time

        logger.debug("未找到关闭按钮，尝试按ESC键")
        self.browser.execute_script(
            "document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));"
        )
        time.sleep(0.3)

    def _close_modal(self):
        """关闭当前打开的模态框"""
        try:
            if self._try_close_by_icon():
                return

            if self._try_close_by_selectors():
                return

            self._try_close_by_escape()
        except Exception as e:
            logger.debug(f"关闭模态框失败: {e}")

    def _extract_table_property_details(self, property_details_dict: dict):
        """从表格中提取Property details"""
        try:
            table = self.browser.find_element(By.CSS_SELECTOR, '[da-id="property-details"] table')
            rows = table.find_elements(By.CSS_SELECTOR, "tr.row")

            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, "td.meta-table__item-wrapper")
                for cell in cells:
                    try:
                        item_wrapper = cell.find_element(
                            By.CSS_SELECTOR, ".meta-table__item__wrapper"
                        )
                        icon = item_wrapper.find_element(By.CSS_SELECTOR, 'img[da-id="svg-icon"]')
                        value_elem = item_wrapper.find_element(
                            By.CSS_SELECTOR, '[da-id="metatable-item"]'
                        )

                        alt = icon.get_attribute("alt") or ""
                        text = value_elem.text.strip()
                        self._add_to_property_dict(property_details_dict, alt, text)
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"从表格提取Property details失败: {e}")

    def _extract_modal_property_details(self, property_details_dict: dict):
        """从模态框中提取Property details"""
        modal_opened = False
        try:
            see_more_btn = self.browser.find_element(
                By.CSS_SELECTOR, '[da-id="meta-table-see-more-btn"]'
            )
            if not see_more_btn or not self._click_modal_button(
                '[da-id="meta-table-see-more-btn"]', '[da-id="property-details-modal-body"]'
            ):
                return

            modal_opened = True
            modal_body = self.browser.find_element(
                By.CSS_SELECTOR, '[da-id="property-details-modal-body"]'
            )
            wrappers = modal_body.find_elements(By.CSS_SELECTOR, ".property-modal-body-wrapper")

            for wrapper in wrappers:
                try:
                    icon = wrapper.find_element(By.CSS_SELECTOR, "img.property-modal-body-icon")
                    value_elem = wrapper.find_element(
                        By.CSS_SELECTOR, '[da-id="property-modal-value"]'
                    )

                    alt = icon.get_attribute("alt") or ""
                    text = value_elem.text.strip()
                    self._add_to_property_dict(property_details_dict, alt, text)
                except Exception as e:
                    logger.debug(f"解析modal wrapper失败: {e}")
                    continue

        except Exception as e:
            logger.debug(f"提取模态框Property details失败: {e}")
        finally:
            # 确保模态框被关闭
            if modal_opened:
                self._close_modal()

    def _add_to_property_dict(self, property_details_dict: dict, alt: str, text: str):
        """向property_details_dict添加数据"""
        if alt in property_details_dict:
            if isinstance(property_details_dict[alt], list):
                property_details_dict[alt].append(text)
            else:
                property_details_dict[alt] = [property_details_dict[alt], text]
        else:
            property_details_dict[alt] = text

    def extract_property_details(self) -> PropertyDetails | None:
        """
        提取Property details信息

        Returns:
            PropertyDetails对象
        """
        try:
            listing_id = self._extract_listing_id_from_url()
            if not listing_id:
                return None

            details = PropertyDetails(listing_id=listing_id)
            property_details_dict: dict[str, Any] = {}

            self._extract_table_property_details(property_details_dict)
            self._extract_modal_property_details(property_details_dict)

            details.property_details = property_details_dict
            return details

        except Exception as e:
            logger.error(f"提取Property details失败: {e}")
            return None

    def _extract_basic_description(self, widget) -> tuple[str | None, str | None]:
        """提取基本描述（标题和描述）"""
        title = None
        try:
            title_elem = widget.find_element(By.CSS_SELECTOR, "h3.subtitle")
            title = title_elem.text.strip()
        except Exception:
            pass

        description = None
        try:
            desc_elem = widget.find_element(By.CSS_SELECTOR, "div.description")
            description = desc_elem.text.strip()
        except Exception:
            pass

        return title, description

    def _extract_full_description_from_modal(self) -> tuple[str | None, str | None]:
        """从模态框提取完整描述"""
        modal_opened = True  # 调用此方法时模态框已经打开
        try:
            modal_body = self.browser.find_element(By.CSS_SELECTOR, "div.description-modal-body")

            title = None
            try:
                subtitle = modal_body.find_element(By.CSS_SELECTOR, "h3.subtitle")
                title = subtitle.text.strip()
            except Exception:
                pass

            description = modal_body.text.strip()
            if title and description.startswith(title):
                description = description[len(title) :].strip()

            return title, description
        except Exception as e:
            logger.error(f"提取完整描述失败: {e}")
            return None, None
        finally:
            # 确保模态框被关闭
            if modal_opened:
                self._close_modal()

    def extract_property_description(self) -> tuple[str | None, str | None]:
        """
        提取About this property描述

        Returns:
            (title, description) 元组
        """
        try:
            # 使用 find_elements 检查元素是否存在
            widgets = self.browser.find_elements(By.CSS_SELECTOR, '[da-id="description-widget"]')
            if not widgets:
                logger.debug("未找到 description-widget 元素")
                return None, None
            widget = widgets[0]

            title, description = self._extract_basic_description(widget)

            if self._click_modal_button(
                '[da-id="description-widget-show-more-lnk"]', "div.description-modal-body"
            ):
                modal_title, modal_description = self._extract_full_description_from_modal()
                if modal_title:
                    title = modal_title
                if modal_description:
                    description = modal_description

            return title, description

        except Exception as e:
            logger.error(f"提取描述失败: {e}")
            return None, None

    def extract_amenities(self) -> list[str]:
        """
        提取Amenities列表

        Returns:
            Amenities名称列表
        """
        amenities: list[str] = []
        try:
            # 使用 find_elements 检查元素是否存在
            widgets = self.browser.find_elements(By.CSS_SELECTOR, '[da-id="property-amenities"]')
            if not widgets:
                logger.debug("未找到 property-amenities 元素")
                return amenities
            widget = widgets[0]

            # 先提取可见的amenities
            items = widget.find_elements(By.CSS_SELECTOR, '[da-id="facilities-amenities-data"]')
            for item in items:
                value_elem = item.find_element(
                    By.CSS_SELECTOR, "p.property-amenities__row-item__value"
                )
                amenities.append(value_elem.text.strip())

            # 尝试点击"See all"获取完整列表
            modal_opened = False
            try:
                # 先检查按钮是否存在
                see_all_btns = widget.find_elements(
                    By.CSS_SELECTOR, '[da-id="amenities-see-all-btn"]'
                )
                if see_all_btns and self._click_modal_button(
                    '[da-id="amenities-see-all-btn"]', '[da-id="facilities-amenities-modal-data"]'
                ):
                    modal_opened = True
                    modal_body = self.browser.find_element(
                        By.CSS_SELECTOR, '[da-id="facilities-amenities-modal-data"]'
                    )
                    modal_items = modal_body.find_elements(
                        By.CSS_SELECTOR, "p.amenities-facilties-modal-body-value"
                    )

                    amenities = []
                    for item in modal_items:
                        amenities.append(item.text.strip())

            except Exception as e:
                logger.debug(f"点击 amenities See all 按钮失败: {e}")
                pass  # 如果没有"See all"按钮，使用已提取的
            finally:
                # 确保模态框被关闭
                if modal_opened:
                    self._close_modal()

            return amenities

        except Exception as e:
            logger.error(f"提取Amenities失败: {e}")
            return amenities

    def extract_facilities(self) -> list[str]:
        """
        提取Common facilities列表

        Returns:
            Facilities名称列表
        """
        facilities: list[str] = []
        try:
            # 使用 find_elements 检查元素是否存在
            widgets = self.browser.find_elements(By.CSS_SELECTOR, '[da-id="property-facilities"]')
            if not widgets:
                logger.debug("未找到 property-facilities 元素")
                return facilities
            widget = widgets[0]

            # 先提取可见的facilities
            items = widget.find_elements(By.CSS_SELECTOR, '[da-id="facilities-amenities-data"]')
            for item in items:
                value_elem = item.find_element(
                    By.CSS_SELECTOR, "p.property-amenities__row-item__value"
                )
                facilities.append(value_elem.text.strip())

            # 尝试点击"See all"获取完整列表
            modal_opened = False
            try:
                # 先检查按钮是否存在
                see_all_btns = widget.find_elements(
                    By.CSS_SELECTOR, '[da-id="facilities-see-all-btn"]'
                )
                if see_all_btns and self._click_modal_button(
                    '[da-id="facilities-see-all-btn"]', '[da-id="facilities-amenities-modal-data"]'
                ):
                    modal_opened = True
                    modal_body = self.browser.find_element(
                        By.CSS_SELECTOR, '[da-id="facilities-amenities-modal-data"]'
                    )
                    modal_items = modal_body.find_elements(
                        By.CSS_SELECTOR, "p.amenities-facilties-modal-body-value"
                    )

                    facilities = []
                    for item in modal_items:
                        facilities.append(item.text.strip())

            except Exception as e:
                logger.debug(f"点击 facilities See all 按钮失败: {e}")
                pass  # 如果没有"See all"按钮，使用已提取的
            finally:
                # 确保模态框被关闭
                if modal_opened:
                    self._close_modal()

            return facilities

        except Exception as e:
            logger.error(f"提取Facilities失败: {e}")
            return facilities

    def _extract_decimal_from_text(self, text: str) -> Decimal | None:
        """从文本中提取小数"""
        try:
            match = re.search(r"[\d,]+\.?\d*", text.replace(",", ""))
            if match:
                return Decimal(match.group())
        except Exception:
            pass
        return None

    def _extract_monthly_payment(self, section, mortgage: MortgageInfo):
        """提取每月还款额"""
        try:
            monthly_elem = section.find_element(
                By.CSS_SELECTOR, '[da-id="mortgage-calculator-monthly-breakdown-value"]'
            )
            monthly_text = monthly_elem.text.strip()
            value = self._extract_decimal_from_text(monthly_text)
            if value:
                mortgage.monthly_repayment = value
        except Exception:
            pass

    def _extract_principal_and_interest(self, section, mortgage: MortgageInfo):
        """提取本金和利息"""
        try:
            principal_elem = section.find_element(
                By.CSS_SELECTOR, '[da-id="mortgage-calculator-monthly-pricipal-text"]'
            )
            principal_text = principal_elem.text.strip()
            value = self._extract_decimal_from_text(principal_text)
            if value:
                mortgage.principal = value

            interest_elem = section.find_element(
                By.CSS_SELECTOR, '[da-id="mortgage-calculator-monthly-interest-text"]'
            )
            interest_text = interest_elem.text.strip()
            value = self._extract_decimal_from_text(interest_text)
            if value:
                mortgage.interest = value
        except Exception:
            pass

    def _extract_downpayment(self, section, mortgage: MortgageInfo):
        """提取首付款"""
        try:
            downpayment_elem = section.find_element(
                By.CSS_SELECTOR, '[da-id="mortgage-calculator-upfront-downpayment-value"]'
            )
            downpayment_text = downpayment_elem.text.strip()
            value = self._extract_decimal_from_text(downpayment_text)
            if value:
                mortgage.downpayment = value
        except Exception:
            pass

    def _extract_form_fields(self, section, mortgage: MortgageInfo):
        """从表单中提取字段"""
        try:
            price_input = section.find_element(
                By.CSS_SELECTOR, '[da-id="mortgage-calculator-property-price-input"]'
            )
            price_value = price_input.get_attribute("value")
            if price_value:
                mortgage.property_price = Decimal(price_value.replace(",", ""))

            loan_input = section.find_element(
                By.CSS_SELECTOR, '[da-id="mortgage-calculator-loan-amount-input"]'
            )
            loan_value = loan_input.get_attribute("value")
            if loan_value:
                mortgage.loan_amount = Decimal(loan_value.replace(",", ""))

            rate_input = section.find_element(
                By.CSS_SELECTOR, '[da-id="mortgage-calculator-interest-rate-input"]'
            )
            rate_value = rate_input.get_attribute("value")
            if rate_value:
                mortgage.interest_rate = Decimal(rate_value)

            tenure_input = section.find_element(
                By.CSS_SELECTOR, '[da-id="mortgage-calculator-loan-tenure-input"]'
            )
            tenure_value = tenure_input.get_attribute("value")
            if tenure_value:
                mortgage.loan_tenure_years = int(tenure_value)

            if mortgage.property_price and mortgage.loan_amount:
                mortgage.loan_to_value_percent = (
                    mortgage.loan_amount / mortgage.property_price * 100
                )
        except Exception:
            pass

    def extract_affordability(self) -> MortgageInfo | None:
        """
        提取Affordability信息

        Returns:
            MortgageInfo对象
        """
        try:
            listing_id = self._extract_listing_id_from_url()
            if not listing_id:
                return None

            mortgage = MortgageInfo(listing_id=listing_id)

            section = self.browser.find_element(
                By.CSS_SELECTOR, '[da-id="mortgage-calculator-section"]'
            )
            if not section:
                return None

            self._extract_monthly_payment(section, mortgage)
            self._extract_principal_and_interest(section, mortgage)
            self._extract_downpayment(section, mortgage)
            self._extract_form_fields(section, mortgage)

            return mortgage

        except Exception as e:
            logger.error(f"提取Affordability失败: {e}")
            return None

    def _extract_faq_answer(self, item) -> str | None:
        """提取FAQ答案"""
        try:
            answer_elem = item.find_element(By.CSS_SELECTOR, '[da-id="faq-widget-answer-item"]')
            answer_text: str = answer_elem.text.strip()
            return answer_text
        except Exception:
            return self._extract_faq_answer_by_clicking(item)

    def _extract_faq_answer_by_clicking(self, item) -> str | None:
        """通过点击按钮提取FAQ答案"""
        try:
            button = item.find_element(By.CSS_SELECTOR, "button.accordion-button")
            if "collapsed" in button.get_attribute("class"):
                button.click()
                self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, '[da-id="faq-widget-answer-item"]')
                    )
                )
                answer_elem = item.find_element(By.CSS_SELECTOR, '[da-id="faq-widget-answer-item"]')
                answer_text: str = answer_elem.text.strip()
                return answer_text
        except Exception:
            pass
        return None

    def _parse_faq_item(self, item, listing_id: int, idx: int) -> FAQ | None:
        """解析单个FAQ项"""
        try:
            question_elem = item.find_element(
                By.CSS_SELECTOR, '[da-id="faq-widget-questions-item"] .faq__item__question-text'
            )
            question = question_elem.text.strip()

            if not question:
                return None

            answer = self._extract_faq_answer(item)

            return FAQ(
                listing_id=listing_id,
                question=question,
                answer=answer,
                position=idx,
            )
        except Exception as e:
            logger.debug(f"解析FAQ项失败: {e}")
            return None

    def extract_faqs(self) -> list[FAQ]:
        """
        提取FAQs

        Returns:
            FAQ对象列表
        """
        faqs: list[FAQ] = []
        try:
            faq_root = self.browser.find_element(By.CSS_SELECTOR, '[da-id="faq-widget"]')
            if not faq_root:
                return faqs

            listing_id = self._extract_listing_id_from_url()
            if not listing_id:
                return faqs

            faq_items = faq_root.find_elements(By.CSS_SELECTOR, ".faq__item")
            for idx, item in enumerate(faq_items):
                faq = self._parse_faq_item(item, listing_id, idx)
                if faq:
                    faqs.append(faq)

            return faqs

        except Exception as e:
            logger.error(f"提取FAQs失败: {e}")
            return faqs

    def _scroll_to_button_center(self, button) -> None:
        """滚动到按钮位置，使其居中显示"""
        import time

        try:
            button_location = button.location_once_scrolled_into_view
            button_size = button.size
            viewport_height = self.browser.driver.execute_script("return window.innerHeight;")
            button_top = button_location["y"]
            target_scroll = button_top - (viewport_height / 2) + (button_size["height"] / 2)

            self.browser.driver.execute_script(f"window.scrollTo(0, {target_scroll});")
            time.sleep(0.3)

            self.browser.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'instant', block: 'center', inline: 'nearest'});",
                button,
            )
            time.sleep(0.3)

            self.browser.driver.execute_script("window.scrollBy(0, 150);")
            time.sleep(0.2)

            logger.debug(f"已滚动到按钮位置，按钮Y坐标: {button_top}, 视口高度: {viewport_height}")
        except Exception as e:
            logger.debug(f"滚动到按钮时出错（可忽略）: {e}")
            try:
                self.browser.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", button
                )
                time.sleep(0.5)
            except Exception:
                pass

    def _click_button_with_retry(self, button) -> bool:
        """尝试点击按钮，失败时重试"""
        import time

        try:
            self.browser.driver.execute_script("arguments[0].click();", button)
            logger.info("使用JavaScript点击方式点击按钮")
            return True
        except Exception as js_error:
            logger.debug(f"JavaScript点击失败，尝试普通点击: {js_error}")
            try:
                self.browser.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", button
                )
                time.sleep(0.5)
                button.click()
                logger.debug("使用普通点击方式点击按钮")
                return True
            except Exception as e:
                logger.error(f"所有点击方式都失败: {e}")
                raise

    def _wait_and_scroll_media_grid(self, short_wait) -> None:
        """等待媒体网格出现并滚动到底部加载所有图片"""
        import time

        logger.debug("等待媒体网格容器出现...")
        try:
            short_wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[da-id="media-gallery-l1-grid"]'))
            )
            logger.info("媒体网格容器已出现")
        except Exception as e:
            logger.warning(f"等待媒体网格容器超时（可能已存在）: {e}")

        time.sleep(0.5)

        try:
            media_grid = self.browser.find_element(
                By.CSS_SELECTOR, '[da-id="media-gallery-l1-grid"]'
            )
            if media_grid:
                self.browser.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    media_grid,
                )
                time.sleep(0.5)

                self.browser.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'end'});", media_grid
                )
                time.sleep(1.0)

                logger.debug("已滚动到媒体网格底部，等待图片加载完成")
        except Exception as e:
            logger.debug(f"滚动媒体网格时出错（可忽略）: {e}")

        try:
            short_wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[da-id="media-gallery-l1-grid"] [da-id="media-item"]')
                )
            )
            logger.debug("媒体网格内容已加载")
        except Exception:
            logger.debug("等待媒体项超时，但继续执行（可能内容已存在）")

    def _click_view_more_media(self):
        """点击"Show all media"按钮，并等待所有图片加载完成"""
        try:
            logger.debug("查找 'Show all media' 按钮...")
            buttons = self.browser.find_elements(
                By.CSS_SELECTOR, '[da-id="media-gallery-view-more"]'
            )

            if not buttons:
                logger.debug("未找到 'Show all media' 按钮，可能不需要展开")
                return

            from selenium.webdriver.support.wait import WebDriverWait

            short_wait = WebDriverWait(self.browser.driver, timeout=5)
            view_more_btn = short_wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[da-id="media-gallery-view-more"]'))
            )

            if view_more_btn:
                logger.info("找到 'Show all media' 按钮，准备点击")
                self._scroll_to_button_center(view_more_btn)
                self._click_button_with_retry(view_more_btn)
                self._wait_and_scroll_media_grid(short_wait)

        except Exception as e:
            logger.debug(f"未找到或无法点击 'Show all media' 按钮（可能不需要）: {e}")

    def _extract_images(
        self, selector: str | None = None, parent_element: WebElement | None = None
    ) -> list[tuple[str, str, WebElement]]:
        """提取图片URL和元素（用于后续从浏览器直接获取图片数据）"""
        media_urls = []
        try:
            if parent_element:
                if selector:
                    images = parent_element.find_elements(By.CSS_SELECTOR, selector)
                else:
                    images = parent_element.find_elements(
                        By.CSS_SELECTOR, '[da-id="media-gallery-images"]'
                    )
            else:
                if selector:
                    images = self.browser.find_elements(By.CSS_SELECTOR, selector)
                else:
                    images = self.browser.find_elements(
                        By.CSS_SELECTOR, '[da-id="media-gallery-images"]'
                    )
            for img in images:
                src = img.get_attribute("src")
                if src:
                    # 返回元组包含 (类型, URL, 元素)，元素用于后续从浏览器获取图片
                    # 注意：元素需要保持有效，在提取后立即使用
                    media_urls.append(("image", src, img))
        except Exception:
            pass
        return media_urls

    def _extract_videos(self) -> list[tuple[str, str]]:
        """提取视频URL"""
        media_urls = []
        try:
            videos = self.browser.find_elements(By.CSS_SELECTOR, '[da-id="media-gallery-videos"]')
            for video in videos:
                src = video.get_attribute("src")
                if not src:
                    try:
                        source = video.find_element(By.TAG_NAME, "source")
                        if source:
                            src = source.get_attribute("src")
                    except Exception:
                        pass
                if src:
                    media_urls.append(("video", src))
        except Exception:
            pass
        return media_urls

    def _extract_floor_plans(
        self, selector: str | None = None, parent_element: WebElement | None = None
    ) -> list[tuple[str, str]]:
        """提取平面图URL"""
        media_urls = []
        try:
            if parent_element:
                if selector:
                    floor_plans = parent_element.find_elements(By.CSS_SELECTOR, selector)
                else:
                    floor_plans = parent_element.find_elements(
                        By.CSS_SELECTOR, 'img.floorPlans[da-id="media-gallery-floorPlans"]'
                    )
            else:
                if selector:
                    floor_plans = self.browser.find_elements(By.CSS_SELECTOR, selector)
                else:
                    floor_plans = self.browser.find_elements(
                        By.CSS_SELECTOR, 'img.floorPlans[da-id="media-gallery-floorPlans"]'
                    )
            for plan in floor_plans:
                src = plan.get_attribute("src")
                if src:
                    media_urls.append(("image", src))
        except Exception:
            pass
        return media_urls

    def _extract_from_grid(self) -> list[tuple[str, str] | tuple[str, str, WebElement]]:
        """从grid中提取媒体"""
        media_urls: list[tuple[str, str] | tuple[str, str, WebElement]] = []
        try:
            grid = self.browser.find_element(By.CSS_SELECTOR, ".media-gallery-image-grid")
            # 图片包含元素
            media_urls.extend(
                self._extract_images('img[da-id="media-gallery-images"]', parent_element=grid)
            )
            media_urls.extend(
                self._extract_floor_plans(
                    'img.floorPlans[da-id="media-gallery-floorPlans"]', parent_element=grid
                )
            )
        except Exception:
            pass
        return media_urls

    def extract_media_urls(self) -> list[tuple[str, str] | tuple[str, str, WebElement]]:
        """
        提取媒体URL列表

        Returns:
            [(media_type, url) 或 (media_type, url, element), ...] 列表
            media_type为'image'或'video'，图片可能包含元素用于直接从浏览器获取
        """
        media_urls: list[tuple[str, str] | tuple[str, str, WebElement]] = []
        try:
            self._click_view_more_media()

            # 图片包含元素，可以直接传递
            media_urls.extend(self._extract_images())
            # 视频和平面图不包含元素
            media_urls.extend(self._extract_videos())
            media_urls.extend(self._extract_floor_plans())

            if not media_urls:
                media_urls.extend(self._extract_from_grid())

            logger.info(f"提取到 {len(media_urls)} 个媒体URL")
            return media_urls

        except Exception as e:
            logger.error(f"提取媒体URL失败: {e}")
            return media_urls

    def _extract_listing_id_from_url(self) -> int | None:
        """
        从当前URL提取listing_id

        Returns:
            listing_id，如果无法提取返回None
        """
        try:
            current_url = self.browser.driver.current_url
            # URL格式可能是: https://www.propertyguru.com.sg/property-for-sale/.../listing_id
            # 或者包含listing_id参数
            match = re.search(r"/(\d+)(?:/|$|\?)", current_url)
            if match:
                return int(match.group(1))
            return None
        except Exception:
            return None
