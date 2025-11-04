"""
去水印API测试
使用直连代理测试去水印接口
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from crawler.watermark_remover import WatermarkRemover
from utils.logger import get_logger
from utils.proxy import ProxyAdapter

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

logger = get_logger("WatermarkAPITest")


def _get_direct_proxy_url() -> str | None:
    """获取直连代理URL，优先从环境变量，其次从配置文件"""
    direct_proxy_url = os.getenv("PROXY_DIRECT_URL")
    if direct_proxy_url:
        return direct_proxy_url

    # 如果没有配置直连代理URL，尝试使用 ProxyManager 获取
    try:
        from crawler.config import Config
        from crawler.proxy_manager import ProxyManager

        config_file = Path(__file__).parent.parent / "config.yaml"
        config = Config.from_yaml(str(config_file)) if config_file.exists() else None
        if config:
            proxy_config = config.get_section("proxy")
            if proxy_config and proxy_config.get("pool_type") == "direct_api":
                proxy_manager = ProxyManager(proxy_config)
                proxy = proxy_manager.get_proxy()
                if proxy:
                    proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.ip}:{proxy.port}"
                    logger.info(f"从代理池获取直连代理: {proxy.ip}:{proxy.port}")
                    return proxy_url
    except Exception as e:
        logger.warning(f"无法从代理池获取代理: {e}")

    return None


def _create_watermark_remover_with_proxy(direct_proxy_url: str) -> WatermarkRemover:
    """创建带代理的去水印工具"""
    proxy_adapter = ProxyAdapter(direct_proxy_url)
    remover = WatermarkRemover(proxy=proxy_adapter)

    # 验证代理配置
    proxies = remover.proxy_adapter.get_proxies()
    if proxies:
        logger.info("✓ 确认：已配置代理")
    else:
        logger.warning("未检测到代理配置")

    return remover


def _verify_result_file(result_path: str) -> bool:
    """验证结果文件是否存在并打印信息"""
    if Path(result_path).exists():
        file_size = Path(result_path).stat().st_size
        logger.info(f"输出文件大小: {file_size} 字节")
        logger.info("=" * 60)
        return True

    logger.error(f"输出文件不存在: {result_path}")
    return False


def test_watermark_api_without_proxy():
    """
    测试去水印API（使用直连代理）
    """
    # 测试图片路径
    test_image_path = Path(__file__).parent / "images" / "test1.jpg"

    if not test_image_path.exists():
        logger.error(f"测试图片不存在: {test_image_path}")
        return False

    logger.info(f"使用测试图片: {test_image_path}")

    # 获取直连代理
    direct_proxy_url = _get_direct_proxy_url()
    if not direct_proxy_url:
        logger.error("未配置直连代理（PROXY_DIRECT_URL 或 ProxyManager）")
        return False

    logger.info(
        f"使用直连代理: {direct_proxy_url.split('@')[1] if '@' in direct_proxy_url else '已配置'}"
    )

    try:
        remover = _create_watermark_remover_with_proxy(direct_proxy_url)
        output_path = (
            test_image_path.parent / f"{test_image_path.stem}_result{test_image_path.suffix}"
        )

        logger.info("=" * 60)
        logger.info("开始测试去水印API")
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

            return _verify_result_file(result_path)
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


def test_watermark_api_step_by_step():
    """
    分步骤测试去水印API（用于调试，使用直连代理）
    """
    test_image_path = Path(__file__).parent / "images" / "test1.jpg"

    if not test_image_path.exists():
        logger.error(f"测试图片不存在: {test_image_path}")
        return False

    logger.info(f"使用测试图片: {test_image_path}")
    logger.info("分步骤测试去水印API（使用直连代理）")

    # 获取直连代理
    direct_proxy_url = _get_direct_proxy_url()
    if not direct_proxy_url:
        logger.error("未配置直连代理（PROXY_DIRECT_URL 或 ProxyManager）")
        return False

    logger.info(
        f"使用直连代理: {direct_proxy_url.split('@')[1] if '@' in direct_proxy_url else '已配置'}"
    )

    try:
        remover = _create_watermark_remover_with_proxy(direct_proxy_url)

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
            test_image_path.parent / f"{test_image_path.stem}_result{test_image_path.suffix}"
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
        success = test_watermark_api_step_by_step()
    else:
        # 完整流程测试
        success = test_watermark_api_without_proxy()

    # 退出码
    sys.exit(0 if success else 1)
