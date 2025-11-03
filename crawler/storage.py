"""
对象存储管理模块
支持AWS S3和七牛云对象存储
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


class QiniuManager:
    """七牛云存储管理器"""

    def __init__(self, config: dict):
        """
        初始化七牛云管理器

        Args:
            config: 七牛云配置
                - access_key: 访问密钥
                - secret_key: 秘密密钥
                - bucket_name: 存储空间名称
                - bucket_domain: 存储空间域名（用于生成下载URL）
                - prefix: 路径前缀（可选）
        """
        try:
            from qiniu import Auth
        except ImportError as err:
            raise ImportError("请安装 qiniu 库: pip install qiniu") from err

        self.config = config
        self.access_key = config.get("access_key")
        self.secret_key = config.get("secret_key")
        self.bucket_name = config.get("bucket_name")
        self.bucket_domain = config.get("bucket_domain")  # 用于生成下载URL
        self.prefix = config.get("prefix", "")

        if not self.access_key or not self.secret_key:
            raise ValueError("七牛云访问密钥和秘密密钥不能为空")

        if not self.bucket_name:
            raise ValueError("七牛云存储空间名称不能为空")

        # 初始化认证对象
        self.auth = Auth(self.access_key, self.secret_key)

        logger.info(f"七牛云客户端初始化成功: {self.bucket_name}")

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
        上传文件到七牛云

        Args:
            local_path: 本地文件路径
            s3_key: 对象键，如果为None则使用文件名
            extra_args: 额外参数（可包含 expires 过期时间，单位秒）

        Returns:
            是否成功
        """
        try:
            from qiniu import put_file_v2

            local_path = Path(local_path)

            if not local_path.exists():
                logger.error(f"文件不存在: {local_path}")
                return False

            # 如果没有指定键，使用文件名
            if s3_key is None:
                s3_key = local_path.name

            s3_key_str = self._get_full_key(s3_key)

            # 生成上传 Token，可以指定过期时间
            expires = extra_args.get("expires", 3600) if extra_args else 3600
            token = self.auth.upload_token(self.bucket_name, s3_key_str, expires)

            # 上传文件
            ret, info = put_file_v2(token, s3_key_str, str(local_path), version="v2")

            if info.status_code == 200:
                logger.info(
                    f"文件上传成功: {local_path} -> qiniu://{self.bucket_name}/{s3_key_str}"
                )
                return True
            else:
                logger.error(f"文件上传失败: {info}")
                return False
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return False

    def upload_fileobj(
        self, file_obj: BinaryIO, s3_key: str, extra_args: dict[str, Any] | None = None
    ) -> bool:
        """
        上传文件对象到七牛云

        Args:
            file_obj: 文件对象（BinaryIO）
            s3_key: 对象键
            extra_args: 额外参数（可包含 expires 过期时间，单位秒）

        Returns:
            是否成功
        """
        try:
            from qiniu import put_data

            s3_key_str = self._get_full_key(s3_key)

            # 生成上传 Token
            expires = extra_args.get("expires", 3600) if extra_args else 3600
            token = self.auth.upload_token(self.bucket_name, s3_key_str, expires)

            # 读取文件对象内容
            file_obj.seek(0)  # 确保从文件开头读取
            data = file_obj.read()

            # 上传数据
            ret, info = put_data(token, s3_key_str, data)

            if info.status_code == 200:
                logger.info(f"文件对象上传成功: qiniu://{self.bucket_name}/{s3_key_str}")
                return True
            else:
                logger.error(f"文件对象上传失败: {info}")
                return False
        except Exception as e:
            logger.error(f"文件对象上传失败: {e}")
            return False

    def download_file(self, s3_key: str, local_path: str | Path) -> bool:
        """
        从七牛云下载文件

        Args:
            s3_key: 对象键
            local_path: 本地保存路径

        Returns:
            是否成功
        """
        try:
            import requests

            s3_key_str = self._get_full_key(s3_key)
            local_path = Path(local_path)

            # 确保目录存在
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # 生成下载URL
            if not self.bucket_domain:
                raise ValueError("bucket_domain 未配置，无法下载文件")

            base_url = f"http://{self.bucket_domain}/{s3_key_str}"
            private_url = self.auth.private_download_url(base_url, expires=3600)

            # 下载文件
            response = requests.get(private_url, timeout=30)
            response.raise_for_status()

            # 保存文件
            with local_path.open("wb") as f:
                f.write(response.content)

            logger.info(f"文件下载成功: qiniu://{self.bucket_name}/{s3_key_str} -> {local_path}")
            return True
        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return False

    def delete_file(self, s3_key: str) -> bool:
        """
        删除七牛云文件

        Args:
            s3_key: 对象键

        Returns:
            是否成功
        """
        try:
            from qiniu import BucketManager

            s3_key_str = self._get_full_key(s3_key)

            bucket_manager = BucketManager(self.auth)
            ret, info = bucket_manager.delete(self.bucket_name, s3_key_str)

            if info.status_code == 200:
                logger.info(f"文件删除成功: qiniu://{self.bucket_name}/{s3_key_str}")
                return True
            else:
                logger.error(f"文件删除失败: {info}")
                return False
        except Exception as e:
            logger.error(f"文件删除失败: {e}")
            return False

    def file_exists(self, s3_key: str) -> bool:
        """
        检查文件是否存在

        Args:
            s3_key: 对象键

        Returns:
            是否存在
        """
        try:
            from qiniu import BucketManager

            s3_key_str = self._get_full_key(s3_key)

            bucket_manager = BucketManager(self.auth)
            ret, info = bucket_manager.stat(self.bucket_name, s3_key_str)

            return bool(info.status_code == 200)
        except Exception:
            return False

    def get_file_url(self, s3_key: str, expires_in: int = 3600) -> str | None:
        """
        生成文件的私有下载URL

        Args:
            s3_key: 对象键
            expires_in: 过期时间（秒）

        Returns:
            私有下载URL
        """
        try:
            s3_key_str = self._get_full_key(s3_key)

            if not self.bucket_domain:
                logger.warning("bucket_domain 未配置，无法生成下载URL")
                return None

            base_url = f"http://{self.bucket_domain}/{s3_key_str}"
            private_url = self.auth.private_download_url(base_url, expires=expires_in)

            return str(private_url)
        except Exception as e:
            logger.error(f"生成下载URL失败: {e}")
            return None

    def list_files(self, prefix: str = "", max_keys: int = 1000) -> list:
        """
        列出文件

        Args:
            prefix: 前缀
            max_keys: 最大返回数

        Returns:
            文件键列表
        """
        try:
            from qiniu import BucketManager

            full_prefix = self._get_full_key(prefix) if prefix else self.prefix

            bucket_manager = BucketManager(self.auth)
            # 七牛云的 list_files 方法需要提供 marker 参数进行分页
            # 这里简化处理，只获取第一页
            ret, info = bucket_manager.list_files(
                self.bucket_name, prefix=full_prefix, limit=max_keys
            )

            if info.status_code == 200 and ret:
                return [item["key"] for item in ret.get("items", [])]
            return []
        except Exception as e:
            logger.error(f"列出文件失败: {e}")
            return []

    def get_file_size(self, s3_key: str) -> int | None:
        """
        获取文件大小

        Args:
            s3_key: 对象键

        Returns:
            文件大小（字节）
        """
        try:
            from qiniu import BucketManager

            s3_key_str = self._get_full_key(s3_key)

            bucket_manager = BucketManager(self.auth)
            ret, info = bucket_manager.stat(self.bucket_name, s3_key_str)

            if info.status_code == 200 and ret:
                fsize = ret.get("fsize")
                return int(fsize) if fsize is not None else None
            return None
        except Exception as e:
            logger.error(f"获取文件大小失败: {e}")
            return None


def create_storage_manager(config: dict) -> StorageManagerProtocol:
    """
    创建存储管理器（工厂函数）

    Args:
        config: 存储配置，必须包含 `type` 字段指定存储类型：
            - "s3": AWS S3或兼容S3的对象存储
            - "qiniu": 七牛云对象存储

    Returns:
        存储管理器实例

    Examples:
        >>> # S3配置
        >>> s3_config = {
        ...     "type": "s3",
        ...     "aws_access_key_id": "your_key",
        ...     "aws_secret_access_key": "your_secret",
        ...     "bucket_name": "your-bucket",
        ... }
        >>> manager = create_storage_manager(s3_config)
        >>>
        >>> # 七牛云配置
        >>> qiniu_config = {
        ...     "type": "qiniu",
        ...     "access_key": "your_access_key",
        ...     "secret_key": "your_secret_key",
        ...     "bucket_name": "your_bucket",
        ...     "bucket_domain": "your_bucket.qiniucdn.com",
        ... }
        >>> manager = create_storage_manager(qiniu_config)
    """
    storage_type = config.get("type", "s3").lower()

    if storage_type == "s3":
        return S3Manager(config)
    elif storage_type == "qiniu":
        return QiniuManager(config)
    else:
        raise ValueError(f"不支持的存储类型: {storage_type}，支持的类型: s3, qiniu")
