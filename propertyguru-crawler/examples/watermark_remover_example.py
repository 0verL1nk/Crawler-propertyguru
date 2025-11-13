"""
图片去水印示例
演示如何使用 WatermarkRemover 去除图片水印
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from crawler.watermark_remover import WatermarkRemover, remove_watermark  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logger = get_logger("WatermarkRemoverExample")


def example_1_simple():
    """示例1: 最简单的用法（使用环境变量配置）"""
    logger.info("=" * 60)
    logger.info("示例1: 使用环境变量配置")
    logger.info("=" * 60)

    # 准备测试图片路径
    input_image = "data/test_image.jpg"  # 请替换为实际图片路径
    output_image = "data/test_image_no_watermark.jpg"

    # 检查图片是否存在
    if not Path(input_image).exists():
        logger.warning(f"测试图片不存在: {input_image}")
        logger.info("请准备一张带水印的图片并更新路径")
        return

    # 使用便捷函数（所有配置从环境变量读取）
    result = remove_watermark(input_image, output_image)

    if result:
        logger.info(f"✅ 成功！输出文件: {result}")
    else:
        logger.error("❌ 失败")


def example_2_with_proxy():
    """示例2: 使用动态代理（推荐用于大规模处理）"""
    logger.info("\n" + "=" * 60)
    logger.info("示例2: 使用动态住宅代理")
    logger.info("=" * 60)

    input_image = "data/test_image.jpg"

    if not Path(input_image).exists():
        logger.warning(f"测试图片不存在: {input_image}")
        return

    # 从环境变量获取动态代理（推荐）
    # 每次请求自动切换IP，避免被封禁
    proxy_url = os.getenv("PROXY_URL")

    if not proxy_url:
        logger.warning("未配置 PROXY_URL，将从环境变量或默认配置读取")
        logger.info("建议配置动态住宅代理以支持大规模图片处理")

    # 使用便捷函数（自动使用动态代理）
    result = remove_watermark(input_image, "data/output_with_proxy.jpg", proxy=proxy_url)

    if result:
        logger.info(f"✅ 成功！输出文件: {result}")


def example_3_class_usage():
    """示例3: 使用类接口（更多控制）"""
    logger.info("\n" + "=" * 60)
    logger.info("示例3: 使用类接口进行精细控制")
    logger.info("=" * 60)

    input_image = "data/test_image.jpg"

    if not Path(input_image).exists():
        logger.warning(f"测试图片不存在: {input_image}")
        return

    # 创建去水印实例（可选配置代理）
    remover = WatermarkRemover(
        # proxy='http://user:pass@host:port'  # 可选
    )

    try:
        # 步骤1: 创建任务
        logger.info("步骤1: 创建去水印任务...")
        job_id = remover.create_job(input_image)

        if not job_id:
            logger.error("创建任务失败")
            return

        logger.info(f"任务ID: {job_id}")

        # 步骤2: 等待处理完成
        logger.info("步骤2: 等待处理完成...")
        result_url = remover.wait_for_completion(
            job_id,
            max_wait=300,
            check_interval=3,  # 最多等待5分钟  # 每3秒检查一次
        )

        if not result_url:
            logger.error("任务处理失败或超时")
            return

        logger.info(f"处理完成！结果URL: {result_url}")

        # 步骤3: 下载结果
        logger.info("步骤3: 下载处理后的图片...")
        output_path = "data/output_step_by_step.jpg"

        if remover.download_result(result_url, output_path):
            logger.info(f"✅ 全部完成！输出文件: {output_path}")
        else:
            logger.error("下载失败")

    finally:
        remover.close()


def example_4_batch_processing():
    """示例4: 批量处理多张图片（使用动态代理避免IP封禁）"""
    logger.info("\n" + "=" * 60)
    logger.info("示例4: 批量处理多张图片")
    logger.info("提示: 推荐使用动态住宅代理，避免大规模处理时IP被封")
    logger.info("=" * 60)

    # 准备图片列表
    image_files = [
        "data/image1.jpg",
        "data/image2.jpg",
        "data/image3.jpg",
    ]

    # 过滤存在的文件
    existing_files = [f for f in image_files if Path(f).exists()]

    if not existing_files:
        logger.warning("没有找到测试图片")
        return

    logger.info(f"找到 {len(existing_files)} 张图片待处理")

    # 创建去水印实例（复用连接）
    remover = WatermarkRemover()

    success_count = 0
    fail_count = 0

    try:
        for image_path in existing_files:
            logger.info(f"\n处理: {image_path}")

            output_path = (
                Path(image_path).parent / f"{Path(image_path).stem}_clean{Path(image_path).suffix}"
            )

            result = remover.remove_watermark(image_path, output_path)

            if result:
                success_count += 1
                logger.info(f"✅ 成功: {output_path}")
            else:
                fail_count += 1
                logger.error(f"❌ 失败: {image_path}")

        logger.info(f"\n批量处理完成！成功: {success_count}, 失败: {fail_count}")

    finally:
        remover.close()


def example_5_with_proxy_adapter():
    """示例5: 使用代理适配器（动态代理）"""
    logger.info("\n" + "=" * 60)
    logger.info("示例5: 使用动态代理适配器")
    logger.info("提示: 动态代理自动切换IP，适合大规模图片处理")
    logger.info("=" * 60)

    from utils.proxy import ProxyAdapter, StaticProxy

    # 从环境变量获取动态代理
    proxy_url = os.getenv("PROXY_URL")

    if not proxy_url:
        logger.error("未配置 PROXY_URL，无法使用代理")
        logger.info("请在 .env 文件中配置动态住宅代理")
        return

    # 创建动态代理实例
    dynamic_proxy = StaticProxy(proxy_url)

    # 测试代理
    logger.info("测试动态代理连接...")
    if dynamic_proxy.test():
        logger.info("✅ 代理测试通过")
    else:
        logger.error("❌ 代理测试失败")
        return

    # 创建适配器
    adapter = ProxyAdapter(dynamic_proxy)

    # 使用适配器
    input_image = "data/test_image.jpg"
    if Path(input_image).exists():
        remover = WatermarkRemover(proxy=adapter)
        try:
            result = remover.remove_watermark(input_image)
            if result:
                logger.info(f"✅ 成功: {result}")
        finally:
            remover.close()


def main():
    """主函数"""
    logger.info("图片去水印示例程序")
    logger.info("请确保在 .env 文件中配置了相关信息\n")

    # 运行示例（根据需要注释/取消注释）

    # 示例1: 最简单的用法
    example_1_simple()

    # 示例2: 使用代理
    # example_2_with_proxy()

    # 示例3: 分步骤控制
    # example_3_class_usage()

    # 示例4: 批量处理
    # example_4_batch_processing()

    # 示例5: 使用代理适配器
    # example_5_with_proxy_adapter()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("图片去水印示例程序")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📝 配置说明:")
    logger.info("  1. 复制 env.example 为 .env")
    logger.info("  2. 在 .env 中配置以下环境变量:")
    logger.info("")
    logger.info("  必要配置:")
    logger.info("    - PROXY_URL: 动态住宅代理（推荐用于大规模处理）")
    logger.info("      格式: http://user:pass@host:port")
    logger.info(
        "      示例: http://brd-customer-xxx-zone-residential_proxy1:pass@brd.superproxy.io:33335"
    )
    logger.info("")
    logger.info("  可选配置:")
    logger.info("    - WATERMARK_REMOVER_PRODUCT_SERIAL (有默认值)")
    logger.info("    - WATERMARK_REMOVER_PRODUCT_CODE (有默认值)")
    logger.info("    - WATERMARK_REMOVER_AUTHORIZATION")
    logger.info("")
    logger.info("💡 为什么推荐动态住宅代理？")
    logger.info("  ✓ 每次请求自动切换IP，避免被封禁")
    logger.info("  ✓ 适合大规模图片处理，不会触发限流")
    logger.info("  ✓ 真实用户网络环境，成功率高")
    logger.info("")

    main()
