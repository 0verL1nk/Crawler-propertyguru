"""
去水印API测试（不使用代理版本）
测试通过请求头伪造IP地址是否可行
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from crawler.watermark_remover_no_proxy import WatermarkRemoverNoProxy
from utils.logger import get_logger

# 加载 .env 文件
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    # 尝试从项目根目录加载
    root_env = Path(__file__).parent.parent.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env)
    else:
        # 尝试加载当前目录的 .env
        load_dotenv()

logger = get_logger("WatermarkAPITestNoProxy")


def test_watermark_api_no_proxy():
    """
    测试去水印API（不使用代理，通过请求头伪造IP）
    """
    # 测试图片路径
    test_image_path = Path(__file__).parent / "images" / "test1.jpg"

    if not test_image_path.exists():
        logger.error(f"测试图片不存在: {test_image_path}")
        return False

    logger.info(f"使用测试图片: {test_image_path}")
    logger.info("不使用代理模式，通过请求头伪造IP地址")

    try:
        # 可选：指定伪造IP，如果不指定则每次随机生成
        fake_ip = os.getenv("FAKE_IP")  # 可以从环境变量读取
        if fake_ip:
            logger.info(f"使用指定的伪造IP: {fake_ip}")
        else:
            logger.info("将使用随机生成的伪造IP")

        remover = WatermarkRemoverNoProxy(fake_ip=fake_ip)
        output_path = (
            test_image_path.parent
            / f"{test_image_path.stem}_no_proxy_result{test_image_path.suffix}"
        )

        logger.info("=" * 60)
        logger.info("开始测试去水印API（不使用代理）")
        logger.info("=" * 60)

        result_path = remover.remove_watermark(
            image_path=test_image_path,
            output_path=output_path,
            max_wait=300,
        )

        if result_path:
            logger.info("=" * 60)
            logger.info("✅ 去水印成功！")
            logger.info(f"输入文件: {test_image_path}")
            logger.info(f"输出文件: {result_path}")
            logger.info("=" * 60)

            # 验证文件
            if Path(result_path).exists():
                file_size = Path(result_path).stat().st_size
                logger.info(f"输出文件大小: {file_size} 字节")
                return True
            else:
                logger.error(f"输出文件不存在: {result_path}")
                return False
        else:
            logger.error("=" * 60)
            logger.error("❌ 去水印失败")
            logger.error("=" * 60)
            return False

    except Exception as e:
        logger.error(f"测试过程中出错: {e}", exc_info=True)
        return False
    finally:
        # 关闭会话
        if "remover" in locals():
            remover.close()


def test_watermark_api_step_by_step_no_proxy():
    """
    分步骤测试去水印API（用于调试，不使用代理）
    """
    test_image_path = Path(__file__).parent / "images" / "test1.jpg"

    if not test_image_path.exists():
        logger.error(f"测试图片不存在: {test_image_path}")
        return False

    logger.info(f"使用测试图片: {test_image_path}")
    logger.info("分步骤测试去水印API（不使用代理，通过请求头伪造IP）")

    # 可选：指定伪造IP
    fake_ip = os.getenv("FAKE_IP")
    if fake_ip:
        logger.info(f"使用指定的伪造IP: {fake_ip}")
    else:
        logger.info("将使用随机生成的伪造IP")

    try:
        remover = WatermarkRemoverNoProxy(fake_ip=fake_ip)

        # 步骤1: 创建任务
        logger.info("-" * 60)
        logger.info("步骤1: 创建去水印任务")
        logger.info("-" * 60)
        job_id = remover.create_job(test_image_path)

        if not job_id:
            logger.error("创建任务失败")
            return False

        logger.info(f"✓ 任务创建成功，Job ID: {job_id}")

        # 步骤2: 等待任务完成
        logger.info("-" * 60)
        logger.info("步骤2: 等待任务完成")
        logger.info("-" * 60)
        result_url = remover.wait_for_completion(job_id, max_wait=300)

        if not result_url:
            logger.error("任务执行失败或超时")
            return False

        logger.info(f"✓ 任务完成，结果URL: {result_url}")

        # 步骤3: 下载结果
        logger.info("-" * 60)
        logger.info("步骤3: 下载处理结果")
        logger.info("-" * 60)
        output_path = (
            test_image_path.parent
            / f"{test_image_path.stem}_no_proxy_result{test_image_path.suffix}"
        )

        success = remover.download_result(result_url, output_path)

        if success:
            logger.info("=" * 60)
            logger.info("✅ 所有步骤成功完成！")
            logger.info(f"输出文件: {output_path}")
            logger.info("=" * 60)
            return True

        logger.error("下载结果失败")
        return False

    except Exception as e:
        logger.error(f"测试过程中出错: {e}", exc_info=True)
        return False
    finally:
        if "remover" in locals():
            remover.close()


if __name__ == "__main__":
    import sys

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--step-by-step":
        # 分步骤测试
        success = test_watermark_api_step_by_step_no_proxy()
    else:
        # 完整流程测试
        success = test_watermark_api_no_proxy()

    # 退出码
    sys.exit(0 if success else 1)
