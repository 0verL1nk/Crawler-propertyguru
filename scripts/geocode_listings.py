#!/usr/bin/env python3
"""
批量地理编码脚本

对数据库中尚未进行地理编码的房产进行批量地理编码。
建议在爬取完成后运行此脚本，避免在爬取过程中影响速度。

使用方法:
    python scripts/geocode_listings.py [--limit N] [--force]

参数:
    --limit N    限制处理的记录数量（默认：全部）
    --force      强制重新编码已有坐标的记录
    --batch-size 批量处理大小（默认：100）
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# noqa: E402 - 必须在修改 sys.path 之后导入
from sqlalchemy import select, update  # noqa: E402

from crawler.database_factory import get_database  # noqa: E402
from crawler.orm_models import ListingInfoORM  # noqa: E402
from utils.geocoding import geocode_address  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logger = get_logger("GeocodeScript")


def geocode_listings(
    limit: int | None = None,
    force: bool = False,
    batch_size: int = 100,
) -> None:
    """
    批量地理编码数据库中的房产

    Args:
        limit: 限制处理的记录数量，None 表示全部
        force: 是否强制重新编码已有坐标的记录
        batch_size: 每批处理的记录数
    """
    logger.info("=" * 60)
    logger.info("开始批量地理编码")
    logger.info(f"限制记录数: {limit if limit else '全部'}")
    logger.info(f"强制重新编码: {force}")
    logger.info(f"批量大小: {batch_size}")
    logger.info("=" * 60)

    # 初始化数据库
    db = get_database()

    try:
        # 构造查询
        with db.get_session() as session:
            if force:
                # 强制模式：处理所有有地址的记录
                stmt = select(ListingInfoORM.listing_id, ListingInfoORM.location).where(
                    ListingInfoORM.location.isnot(None)
                )
            else:
                # 正常模式：只处理尚未编码的记录
                stmt = select(ListingInfoORM.listing_id, ListingInfoORM.location).where(
                    ListingInfoORM.location.isnot(None),
                    (ListingInfoORM.latitude.is_(None)) | (ListingInfoORM.longitude.is_(None)),
                )

            if limit:
                stmt = stmt.limit(limit)

            # 执行查询
            result = session.execute(stmt)
            listings = result.all()

        if not listings:
            logger.info("没有需要地理编码的记录")
            return

        total_count = len(listings)
        logger.info(f"找到 {total_count} 条需要地理编码的记录")

        # 统计信息
        success_count = 0
        failed_count = 0
        skipped_count = 0
        start_time = time.time()

        # 批量处理
        for i, (listing_id, location) in enumerate(listings, 1):
            try:
                logger.info(
                    f"[{i}/{total_count}] 正在处理 listing_id={listing_id}, location={location}"
                )

                # 地理编码
                latitude, longitude = geocode_address(location)

                if latitude and longitude:
                    # 更新数据库
                    with db.get_session() as session:
                        update_stmt = (
                            update(ListingInfoORM)
                            .where(ListingInfoORM.listing_id == listing_id)
                            .values(latitude=float(latitude), longitude=float(longitude))
                        )
                        session.execute(update_stmt)

                    logger.info(f"  ✓ 成功: ({latitude}, {longitude})")
                    success_count += 1
                else:
                    logger.warning("  ✗ 失败: 无法获取坐标")
                    failed_count += 1

                # 每处理一批后显示进度
                if i % batch_size == 0:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / i
                    remaining = (total_count - i) * avg_time
                    logger.info(
                        f"进度: {i}/{total_count} ({i*100//total_count}%), "
                        f"成功: {success_count}, 失败: {failed_count}, "
                        f"预计剩余时间: {remaining/60:.1f}分钟"
                    )

            except KeyboardInterrupt:
                logger.warning("收到中断信号，正在停止...")
                break
            except Exception as e:
                logger.error(f"  ✗ 处理 listing_id={listing_id} 时出错: {e}")
                failed_count += 1
                continue

        # 总结
        elapsed_total = time.time() - start_time
        logger.info("=" * 60)
        logger.info("地理编码完成")
        logger.info(f"总计: {total_count} 条记录")
        logger.info(f"成功: {success_count} 条")
        logger.info(f"失败: {failed_count} 条")
        logger.info(f"跳过: {skipped_count} 条")
        logger.info(f"总耗时: {elapsed_total/60:.1f} 分钟")
        logger.info(f"平均速度: {elapsed_total/total_count if total_count > 0 else 0:.2f} 秒/条")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"批量地理编码失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="批量地理编码数据库中的房产",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理全部未编码的记录
  python scripts/geocode_listings.py

  # 只处理前100条
  python scripts/geocode_listings.py --limit 100

  # 强制重新编码所有记录
  python scripts/geocode_listings.py --force

  # 自定义批量大小
  python scripts/geocode_listings.py --batch-size 50
        """,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制处理的记录数量（默认：全部）",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新编码已有坐标的记录",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="批量处理大小（默认：100）",
    )

    args = parser.parse_args()

    try:
        geocode_listings(
            limit=args.limit,
            force=args.force,
            batch_size=args.batch_size,
        )
    except KeyboardInterrupt:
        logger.warning("\n用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"脚本执行失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
