"""
对象存储管理模块
支持AWS S3和兼容S3的对象存储服务（如七牛云S3兼容模式、MinIO等）
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Protocol, runtime_checkable

if TYPE_CHECKING:
    from botocore.client import BaseClient

from utils.logger import get_logger

logger = get_logger("StorageManager")


@runtime_checkable
class StorageManagerProtocol(Protocol):
    """存储管理器协议接口"""

    def upload_file(
        self,
        local_path: str | Path,
        s3_key: str | None = None,
        extra_args: dict[str, Any] | None = None,
    ) -> bool:
        """上传文件"""
        ...

    def upload_fileobj(
        self, file_obj: BinaryIO, s3_key: str, extra_args: dict[str, Any] | None = None
    ) -> bool:
        """上传文件对象"""
        ...

    def download_file(self, s3_key: str, local_path: str | Path) -> bool:
        """下载文件"""
        ...

    def delete_file(self, s3_key: str) -> bool:
        """删除文件"""
        ...

    def file_exists(self, s3_key: str) -> bool:
        """检查文件是否存在"""
        ...

    def get_file_url(self, s3_key: str, expires_in: int = 3600) -> str | None:
        """生成文件的预签名URL"""
        ...

    def list_files(self, prefix: str = "", max_keys: int = 1000) -> list:
        """列出文件"""
        ...


class S3Manager:
    """S3存储管理器"""

    def __init__(self, config: dict):
        """
        初始化S3管理器

        Args:
            config: S3配置
        """
        self.config = config
        self.bucket_name = config.get("bucket_name")
        self.prefix = config.get("prefix", "")
        self.encrypt = config.get("encrypt", True)

        # 初始化S3客户端
        self.s3_client: BaseClient | None = None
        self.s3_resource: Any | None = None
        self._init_client()

    def _init_client(self):
        """初始化S3客户端"""
        try:
            import boto3
            from botocore.config import Config as BotoConfig

            aws_access_key_id = self.config.get("aws_access_key_id")
            aws_secret_access_key = self.config.get("aws_secret_access_key")
            region_name = self.config.get("region_name", "us-east-1")
            endpoint_url = self.config.get("endpoint_url")  # 用于兼容其他S3服务

            # 配置
            boto_config = BotoConfig(
                region_name=region_name,
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            )

            # 创建客户端
            session_kwargs = {
                "aws_access_key_id": aws_access_key_id,
                "aws_secret_access_key": aws_secret_access_key,
                "region_name": region_name,
                "config": boto_config,
            }

            if endpoint_url:
                session_kwargs["endpoint_url"] = endpoint_url

            self.s3_client = boto3.client("s3", **session_kwargs)
            self.s3_resource = boto3.resource("s3", **session_kwargs)

            # 验证桶是否存在
            if self.bucket_name:
                self._ensure_bucket_exists()

            logger.info(f"S3客户端初始化成功: {self.bucket_name}")
        except Exception as e:
            logger.error(f"S3客户端初始化失败: {e}")
            raise

    def _ensure_bucket_exists(self):
        """确保桶存在"""
        if self.s3_client is None:
            raise RuntimeError("S3客户端未初始化")
        try:
            from botocore.exceptions import ClientError

            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.debug(f"S3桶存在: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                logger.warning(f"S3桶不存在: {self.bucket_name}")
            else:
                logger.error(f"检查S3桶失败: {e}")
                raise

    def _get_full_key(self, key: str) -> str:
        """
        获取完整的对象键（包含前缀）

        Args:
            key: 对象键

        Returns:
            完整的键
        """
        if self.prefix:
            return f"{self.prefix.rstrip('/')}/{key.lstrip('/')}"
        return key

    def upload_file(
        self,
        local_path: str | Path,
        s3_key: str | None = None,
        extra_args: dict[str, Any] | None = None,
    ) -> bool:
        """
        上传文件到S3

        Args:
            local_path: 本地文件路径
            s3_key: S3对象键，如果为None则使用文件名
            extra_args: 额外参数

        Returns:
            是否成功
        """
        if self.s3_client is None:
            raise RuntimeError("S3客户端未初始化")
        try:
            from botocore.exceptions import ClientError

            local_path = Path(local_path)

            if not local_path.exists():
                logger.error(f"文件不存在: {local_path}")
                return False

            # 如果没有指定S3键，使用文件名
            if s3_key is None:
                s3_key = local_path.name

            s3_key_str = self._get_full_key(s3_key)

            # 准备额外参数
            extra_args = extra_args or {}

            # 添加加密
            if self.encrypt and "ServerSideEncryption" not in extra_args:
                extra_args["ServerSideEncryption"] = "AES256"

            # 上传文件
            self.s3_client.upload_file(
                str(local_path), self.bucket_name, s3_key_str, ExtraArgs=extra_args
            )

            logger.info(f"文件上传成功: {local_path} -> s3://{self.bucket_name}/{s3_key_str}")
            return True
        except ClientError as e:
            logger.error(f"文件上传失败: {e}")
            return False

    def upload_fileobj(
        self, file_obj: BinaryIO, s3_key: str, extra_args: dict[str, Any] | None = None
    ) -> bool:
        """
        上传文件对象到S3

        Args:
            file_obj: 文件对象
            s3_key: S3对象键
            extra_args: 额外参数

        Returns:
            是否成功
        """
        if self.s3_client is None:
            raise RuntimeError("S3客户端未初始化")
        try:
            from botocore.exceptions import ClientError

            s3_key_str = self._get_full_key(s3_key)

            # 准备额外参数
            extra_args_dict = extra_args or {}

            # 添加加密
            if self.encrypt and "ServerSideEncryption" not in extra_args_dict:
                extra_args_dict["ServerSideEncryption"] = "AES256"

            # 上传文件对象
            self.s3_client.upload_fileobj(
                file_obj, self.bucket_name, s3_key_str, ExtraArgs=extra_args_dict
            )

            logger.info(f"文件对象上传成功: s3://{self.bucket_name}/{s3_key_str}")
            return True
        except ClientError as e:
            logger.error(f"文件对象上传失败: {e}")
            return False

    def download_file(self, s3_key: str, local_path: str | Path) -> bool:
        """
        从S3下载文件

        Args:
            s3_key: S3对象键
            local_path: 本地保存路径

        Returns:
            是否成功
        """
        if self.s3_client is None:
            raise RuntimeError("S3客户端未初始化")
        try:
            from botocore.exceptions import ClientError

            s3_key_str = self._get_full_key(s3_key)
            local_path = Path(local_path)

            # 确保目录存在
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # 下载文件
            self.s3_client.download_file(self.bucket_name, s3_key_str, str(local_path))

            logger.info(f"文件下载成功: s3://{self.bucket_name}/{s3_key_str} -> {local_path}")
            return True
        except ClientError as e:
            logger.error(f"文件下载失败: {e}")
            return False

    def download_fileobj(self, s3_key: str, file_obj: BinaryIO) -> bool:
        """
        从S3下载文件到文件对象

        Args:
            s3_key: S3对象键
            file_obj: 文件对象

        Returns:
            是否成功
        """
        if self.s3_client is None:
            raise RuntimeError("S3客户端未初始化")
        try:
            from botocore.exceptions import ClientError

            s3_key_str = self._get_full_key(s3_key)

            # 下载到文件对象
            self.s3_client.download_fileobj(self.bucket_name, s3_key_str, file_obj)

            logger.info(f"文件对象下载成功: s3://{self.bucket_name}/{s3_key_str}")
            return True
        except ClientError as e:
            logger.error(f"文件对象下载失败: {e}")
            return False

    def delete_file(self, s3_key: str) -> bool:
        """
        删除S3文件

        Args:
            s3_key: S3对象键

        Returns:
            是否成功
        """
        if self.s3_client is None:
            raise RuntimeError("S3客户端未初始化")
        try:
            from botocore.exceptions import ClientError

            s3_key_str = self._get_full_key(s3_key)

            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key_str)

            logger.info(f"文件删除成功: s3://{self.bucket_name}/{s3_key_str}")
            return True
        except ClientError as e:
            logger.error(f"文件删除失败: {e}")
            return False

    def file_exists(self, s3_key: str) -> bool:
        """
        检查文件是否存在

        Args:
            s3_key: S3对象键

        Returns:
            是否存在
        """
        if self.s3_client is None:
            raise RuntimeError("S3客户端未初始化")
        try:
            from botocore.exceptions import ClientError

            s3_key_str = self._get_full_key(s3_key)

            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key_str)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error(f"检查文件存在失败: {e}")
            raise

    def list_files(self, prefix: str = "", max_keys: int = 1000) -> list:
        """
        列出文件

        Args:
            prefix: 前缀
            max_keys: 最大返回数

        Returns:
            文件键列表
        """
        if self.s3_client is None:
            raise RuntimeError("S3客户端未初始化")
        try:
            from botocore.exceptions import ClientError

            full_prefix = self._get_full_key(prefix) if prefix else self.prefix

            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=full_prefix, MaxKeys=max_keys
            )

            if "Contents" not in response:
                return []

            return [obj["Key"] for obj in response["Contents"]]
        except ClientError as e:
            logger.error(f"列出文件失败: {e}")
            return []

    def get_file_url(self, s3_key: str, expires_in: int = 3600) -> str | None:
        """
        生成文件的预签名URL

        Args:
            s3_key: S3对象键
            expires_in: 过期时间（秒）

        Returns:
            预签名URL
        """
        if self.s3_client is None:
            raise RuntimeError("S3客户端未初始化")
        try:
            from botocore.exceptions import ClientError

            s3_key_str = self._get_full_key(s3_key)

            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key_str},
                ExpiresIn=expires_in,
            )

            return str(url)
        except ClientError as e:
            logger.error(f"生成预签名URL失败: {e}")
            return None

    def get_file_size(self, s3_key: str) -> int | None:
        """
        获取文件大小

        Args:
            s3_key: S3对象键

        Returns:
            文件大小（字节）
        """
        if self.s3_client is None:
            raise RuntimeError("S3客户端未初始化")
        try:
            from botocore.exceptions import ClientError

            s3_key_str = self._get_full_key(s3_key)

            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key_str)

            return int(response["ContentLength"])
        except ClientError as e:
            logger.error(f"获取文件大小失败: {e}")
            return None

    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """
        复制文件

        Args:
            source_key: 源文件键
            dest_key: 目标文件键

        Returns:
            是否成功
        """
        if self.s3_client is None:
            raise RuntimeError("S3客户端未初始化")
        try:
            from botocore.exceptions import ClientError

            source_key_str = self._get_full_key(source_key)
            dest_key_str = self._get_full_key(dest_key)

            copy_source = {"Bucket": self.bucket_name, "Key": source_key_str}

            self.s3_client.copy_object(
                CopySource=copy_source, Bucket=self.bucket_name, Key=dest_key_str
            )

            logger.info(f"文件复制成功: {source_key_str} -> {dest_key_str}")
            return True
        except ClientError as e:
            logger.error(f"文件复制失败: {e}")
            return False


def create_storage_manager(config: dict) -> StorageManagerProtocol:
    """
    创建存储管理器（工厂函数）

    Args:
        config: 存储配置，必须包含 `type` 字段指定存储类型：
            - "s3": AWS S3或兼容S3的对象存储（包括七牛云S3兼容模式）

    Returns:
        存储管理器实例

    Examples:
        >>> # AWS S3配置
        >>> s3_config = {
        ...     "type": "s3",
        ...     "aws_access_key_id": "your_key",
        ...     "aws_secret_access_key": "your_secret",
        ...     "bucket_name": "your-bucket",
        ...     "region_name": "us-east-1",
        ... }
        >>> manager = create_storage_manager(s3_config)
        >>>
        >>> # 七牛云S3兼容模式配置
        >>> qiniu_s3_config = {
        ...     "type": "s3",
        ...     "aws_access_key_id": "your_qiniu_access_key",
        ...     "aws_secret_access_key": "your_qiniu_secret_key",
        ...     "bucket_name": "your_bucket",
        ...     "region_name": "cn-east-1",
        ...     "endpoint_url": "https://s3.cn-east-1.qiniucs.com",
        ... }
        >>> manager = create_storage_manager(qiniu_s3_config)
    """
    storage_type = config.get("type", "s3").lower()

    if storage_type == "s3":
        return S3Manager(config)
    else:
        raise ValueError(f"不支持的存储类型: {storage_type}，支持的类型: s3")
