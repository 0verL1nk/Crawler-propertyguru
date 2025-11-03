"""
七牛云对象存储示例
演示如何使用七牛云存储管理器
"""

from pathlib import Path

from crawler import Config, Spider
from utils.logger import get_logger

logger = get_logger("QiniuExample")


def upload_to_qiniu(spider):
    """上传文件到七牛云"""
    if not spider.s3_manager:
        logger.error("存储管理器未初始化")
        return

    # 上传文件
    local_file = Path("test.txt")
    if local_file.exists():
        success = spider.s3_manager.upload_file(local_file, "test/test.txt")
        if success:
            logger.info("文件上传成功")

            # 获取文件URL
            url = spider.s3_manager.get_file_url("test/test.txt", expires_in=3600)
            if url:
                logger.info(f"文件URL: {url}")

            # 检查文件是否存在
            exists = spider.s3_manager.file_exists("test/test.txt")
            logger.info(f"文件是否存在: {exists}")

            # 列出文件
            files = spider.s3_manager.list_files(prefix="test/")
            logger.info(f"文件列表: {files}")


def main():
    """主函数"""
    # 方式1: 使用配置文件（推荐）
    try:
        config = Config.from_yaml("config.yaml")
        # 确保配置中设置了 type: "qiniu"
        s3_config = config.get_section("s3")
        if s3_config:
            s3_config["type"] = "qiniu"
    except FileNotFoundError:
        logger.warning("config.yaml不存在，使用默认配置")
        config = {
            "s3": {
                "enabled": True,
                "type": "qiniu",
                "access_key": "YOUR_ACCESS_KEY",
                "secret_key": "YOUR_SECRET_KEY",
                "bucket_name": "your-bucket-name",
                "bucket_domain": "your-bucket.qiniucdn.com",  # 存储空间域名
                "prefix": "crawled_data/",
            },
            "crawler": {
                "concurrency": 3,
                "timeout": 30,
                "use_proxy": False,
            },
        }
        config = Config(config)

    # 创建爬虫实例
    spider = Spider(config)

    if not spider.s3_manager:
        logger.error("存储管理器未初始化，请检查配置")
        return

    # 方式2: 直接使用七牛云管理器（演示，实际使用时需要配置）
    # qiniu_config = {
    #     "access_key": "YOUR_ACCESS_KEY",
    #     "secret_key": "YOUR_SECRET_KEY",
    #     "bucket_name": "your-bucket-name",
    #     "bucket_domain": "your-bucket.qiniucdn.com",
    #     "prefix": "crawled_data/",
    # }
    # qiniu_manager = QiniuManager(qiniu_config)

    # 方式3: 使用工厂函数（演示，实际使用时需要配置）
    # storage_config = {
    #     "type": "qiniu",
    #     "access_key": "YOUR_ACCESS_KEY",
    #     "secret_key": "YOUR_SECRET_KEY",
    #     "bucket_name": "your-bucket-name",
    #     "bucket_domain": "your-bucket.qiniucdn.com",
    # }
    # storage_manager = create_storage_manager(storage_config)

    try:
        # 上传文件
        upload_to_qiniu(spider)

        # 也可以直接使用管理器
        # qiniu_manager.upload_file('local_file.txt', 's3_key.txt')

        # 下载文件
        # qiniu_manager.download_file('s3_key.txt', 'downloaded_file.txt')

        # 删除文件
        # qiniu_manager.delete_file('s3_key.txt')

        logger.info("操作完成")

    except Exception as e:
        logger.error(f"操作失败: {e}")
    finally:
        spider.close()


if __name__ == "__main__":
    main()
