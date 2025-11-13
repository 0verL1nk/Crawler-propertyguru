# 对象存储支持

本框架支持多种对象存储服务，包括 AWS S3 和七牛云。

## 支持的存储类型

- **S3**: AWS S3 或兼容 S3 的对象存储（如 MinIO）
- **Qiniu**: 七牛云对象存储

## 配置方式

### S3 配置

在 `config.yaml` 中配置：

```yaml
s3:
  enabled: true
  type: "s3"
  aws_access_key_id: "your_access_key"
  aws_secret_access_key: "your_secret_key"
  bucket_name: "your-bucket-name"
  region_name: "us-east-1"
  endpoint_url: ""  # 可选，用于兼容其他S3服务
  prefix: "crawled_data/"
  encrypt: true
```

### 七牛云配置

在 `config.yaml` 中配置：

```yaml
s3:
  enabled: true
  type: "qiniu"
  access_key: "your_access_key"
  secret_key: "your_secret_key"
  bucket_name: "your-bucket-name"
  bucket_domain: "your-bucket.qiniucdn.com"  # 存储空间域名，用于生成下载URL
  prefix: "crawled_data/"
```

## 使用方法

### 方式1: 通过爬虫框架自动初始化

```python
from crawler import Config, Spider

# 从配置文件加载（会自动创建存储管理器）
config = Config.from_yaml("config.yaml")
spider = Spider(config)

# 使用存储管理器
if spider.s3_manager:
    spider.s3_manager.upload_file("local_file.txt", "remote_file.txt")
```

### 方式2: 直接使用存储管理器

```python
from crawler.storage import S3Manager, QiniuManager, create_storage_manager

# 使用 S3
s3_config = {
    "type": "s3",
    "aws_access_key_id": "your_key",
    "aws_secret_access_key": "your_secret",
    "bucket_name": "your-bucket",
}
s3_manager = create_storage_manager(s3_config)

# 使用七牛云
qiniu_config = {
    "type": "qiniu",
    "access_key": "your_access_key",
    "secret_key": "your_secret_key",
    "bucket_name": "your-bucket",
    "bucket_domain": "your-bucket.qiniucdn.com",
}
qiniu_manager = create_storage_manager(qiniu_config)

# 或者直接创建
qiniu_manager = QiniuManager(qiniu_config)
```

## API 接口

所有存储管理器都实现了统一的接口：

### 上传文件

```python
# 上传本地文件
success = manager.upload_file("local_file.txt", "remote_file.txt")

# 上传文件对象
with open("local_file.txt", "rb") as f:
    success = manager.upload_fileobj(f, "remote_file.txt")
```

### 下载文件

```python
# 下载到本地文件
success = manager.download_file("remote_file.txt", "local_file.txt")

# 下载到文件对象
with open("local_file.txt", "wb") as f:
    success = manager.download_fileobj("remote_file.txt", f)
```

### 删除文件

```python
success = manager.delete_file("remote_file.txt")
```

### 检查文件是否存在

```python
exists = manager.file_exists("remote_file.txt")
```

### 获取文件URL

```python
# 生成预签名URL（S3）或私有下载URL（七牛云）
url = manager.get_file_url("remote_file.txt", expires_in=3600)
```

### 列出文件

```python
files = manager.list_files(prefix="folder/", max_keys=100)
```

### 获取文件大小

```python
size = manager.get_file_size("remote_file.txt")  # 返回字节数
```

## 七牛云特殊说明

1. **bucket_domain**: 必须配置存储空间域名，用于生成下载URL
2. **上传Token过期时间**: 可以通过 `extra_args` 参数指定：
   ```python
   manager.upload_file("file.txt", "key.txt", extra_args={"expires": 7200})
   ```
3. **私有下载URL**: 七牛云会自动生成带签名的私有下载URL

## 示例

查看示例文件：
- `examples/s3_example.py` - S3 存储示例
- `examples/qiniu_example.py` - 七牛云存储示例

## 依赖安装

```bash
# 安装 S3 支持（AWS S3）
pip install boto3

# 安装七牛云支持
pip install qiniu

# 或使用 uv
uv sync  # 会自动安装所有依赖
```
