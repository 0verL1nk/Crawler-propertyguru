"""
数据库使用示例
演示如何使用新的数据库抽象层（支持 MySQL, PostgreSQL, Supabase）
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# noqa: E402 - 必须在修改 sys.path 之后导入
from sqlalchemy import func  # noqa: E402

from crawler.database_factory import get_database  # noqa: E402
from crawler.orm_models import ListingInfoORM  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logger = get_logger("DatabaseExample")


def example_1_basic_usage():
    """示例1: 基本用法 - 自动从环境变量读取配置"""
    logger.info("=" * 60)
    logger.info("示例1: 基本用法")
    logger.info("=" * 60)

    # 创建数据库实例（自动从 .env 读取配置）
    db = get_database()

    # 测试连接
    if db.test_connection():
        logger.info(f"✅ 数据库连接成功，类型: {db.db_type}")
    else:
        logger.error("❌ 数据库连接失败")
        return

    # 查询数据
    with db.get_session() as session:
        # 查询前 5 条记录
        listings = session.query(ListingInfoORM).limit(5).all()

        logger.info(f"查询到 {len(listings)} 条记录：")
        for listing in listings:
            logger.info(f"  - {listing.listing_id}: {listing.title} (S${listing.price:,.0f})")

    # 关闭连接
    db.close()


def example_2_explicit_config():
    """示例2: 明确指定数据库类型和配置"""
    logger.info("=" * 60)
    logger.info("示例2: 明确指定配置")
    logger.info("=" * 60)

    # 方式1: 只指定类型，其他从环境变量读取
    db = get_database(db_type="postgresql")

    # 方式2: 完全自定义配置（示例）
    # custom_config = {
    #     "host": "localhost",
    #     "port": 5432,
    #     "username": "postgres",
    #     "password": "password",
    #     "database": "property_search",
    # }
    # db = get_database(db_type='postgresql', config=custom_config)

    logger.info(f"数据库类型: {db.db_type}")

    db.close()


def example_3_query_operations():
    """示例3: 查询操作"""
    logger.info("=" * 60)
    logger.info("示例3: 查询操作")
    logger.info("=" * 60)

    db = get_database()

    with db.get_session() as session:
        # 简单查询
        listing = session.query(ListingInfoORM).first()
        if listing:
            logger.info(f"第一条记录: {listing.title}")

        # 条件查询
        expensive_listings = (
            session.query(ListingInfoORM)
            .filter(ListingInfoORM.price > 1000000)
            .filter(ListingInfoORM.bedrooms >= 3)
            .limit(5)
            .all()
        )

        logger.info(f"找到 {len(expensive_listings)} 个高价房源（>S$1M, >=3房）")

        # 排序查询
        latest_listings = (
            session.query(ListingInfoORM).order_by(ListingInfoORM.created_at.desc()).limit(3).all()
        )

        logger.info("最新的 3 个房源：")
        for listing in latest_listings:
            logger.info(f"  - {listing.listing_id}: {listing.title}")

        # 聚合查询
        from sqlalchemy import func

        avg_price = session.query(func.avg(ListingInfoORM.price)).scalar()
        count = session.query(func.count(ListingInfoORM.id)).scalar()

        logger.info("统计信息:")
        logger.info(f"  - 总数: {count}")
        logger.info(f"  - 平均价格: S${avg_price:,.0f}" if avg_price else "  - 平均价格: N/A")

    db.close()


def example_4_insert_operations():
    """示例4: 插入操作"""
    logger.info("=" * 60)
    logger.info("示例4: 插入操作")
    logger.info("=" * 60)

    db = get_database()

    # 单条插入
    with db.get_session() as session:
        test_listing = ListingInfoORM(
            listing_id=999999,
            title="Test Listing - Example",
            price=950000,
            bedrooms=3,
            bathrooms=2,
            location="Test Location",
            is_completed=False,
        )

        session.add(test_listing)
        # 自动提交
        logger.info(f"✅ 插入测试数据: {test_listing.listing_id}")

    # 批量插入
    with db.get_session() as session:
        test_listings = [
            ListingInfoORM(
                listing_id=999990 + i,
                title=f"Test Listing {i}",
                price=900000 + i * 10000,
                bedrooms=2 + i % 3,
            )
            for i in range(3)
        ]

        session.add_all(test_listings)
        logger.info(f"✅ 批量插入 {len(test_listings)} 条测试数据")

    db.close()


def example_5_update_operations():
    """示例5: 更新操作"""
    logger.info("=" * 60)
    logger.info("示例5: 更新操作")
    logger.info("=" * 60)

    db = get_database()

    with db.get_session() as session:
        # 查找并更新
        listing = session.query(ListingInfoORM).filter_by(listing_id=999999).first()

        if listing:
            old_title = listing.title
            listing.title = "Updated Test Listing"
            listing.price = 1000000
            # 自动提交

            logger.info(f"✅ 更新记录: {old_title} → {listing.title}")
        else:
            logger.warning("未找到测试记录")

    db.close()


def example_6_delete_operations():
    """示例6: 删除操作"""
    logger.info("=" * 60)
    logger.info("示例6: 删除操作（清理测试数据）")
    logger.info("=" * 60)

    db = get_database()

    with db.get_session() as session:
        # 删除测试数据
        deleted_count = (
            session.query(ListingInfoORM)
            .filter(ListingInfoORM.listing_id >= 999990)
            .delete(synchronize_session=False)
        )

        logger.info(f"✅ 删除 {deleted_count} 条测试数据")

    db.close()


def example_7_supabase():
    """示例7: 使用 Supabase"""
    logger.info("=" * 60)
    logger.info("示例7: Supabase 连接")
    logger.info("=" * 60)

    try:
        # 需要先在 .env 中配置 Supabase 相关参数
        db = get_database(db_type="supabase")

        if db.test_connection():
            logger.info("✅ Supabase 连接成功")

            with db.get_session() as session:
                count = session.query(func.count(ListingInfoORM.id)).scalar()
                logger.info(f"Supabase 中的记录数: {count}")

        db.close()

    except Exception as e:
        logger.warning(f"Supabase 连接失败（可能未配置）: {e}")


def example_8_dual_database():
    """示例8: 双数据库配置（MySQL + PostgreSQL）"""
    logger.info("=" * 60)
    logger.info("示例8: 双数据库配置")
    logger.info("=" * 60)

    try:
        # MySQL 实例
        mysql_db = get_database(db_type="mysql")

        # PostgreSQL 实例
        pg_db = get_database(db_type="postgresql")

        # 从 MySQL 读取
        with mysql_db.get_session() as mysql_session:
            listing = mysql_session.query(ListingInfoORM).first()

            if listing:
                logger.info(f"从 MySQL 读取: {listing.title}")

                # 同步到 PostgreSQL
                with pg_db.get_session() as pg_session:
                    # 创建新对象避免 session 冲突
                    new_listing = ListingInfoORM()
                    for key, value in listing.__dict__.items():
                        if not key.startswith("_"):
                            setattr(new_listing, key, value)

                    pg_session.merge(new_listing)  # merge 而不是 add，避免主键冲突
                    logger.info(f"同步到 PostgreSQL: {listing.listing_id}")

        mysql_db.close()
        pg_db.close()

    except Exception as e:
        logger.error(f"双数据库操作失败: {e}")


def main():
    """运行所有示例"""
    try:
        # 基础示例
        example_1_basic_usage()

        # 配置示例
        example_2_explicit_config()

        # 查询操作
        example_3_query_operations()

        # 插入操作
        example_4_insert_operations()

        # 更新操作
        example_5_update_operations()

        # 删除操作（清理测试数据）
        example_6_delete_operations()

        # Supabase（如果配置了）
        # example_7_supabase()

        # 双数据库（如果都配置了）
        # example_8_dual_database()

    except Exception as e:
        logger.error(f"示例运行失败: {e}", exc_info=True)


if __name__ == "__main__":
    main()
