# 测试文档

本目录包含项目的单元测试，使用 pytest 框架编写。

## 测试结构

```
tests/
├── __init__.py
├── conftest.py              # 公共 fixtures 和配置
├── test_browser.py          # 浏览器模块测试
├── test_watermark_remover.py # 去水印模块测试
├── test_proxy.py            # 代理IP模块测试
└── images/
    └── test1.jpg            # 测试图片
```

## 运行测试

### 运行所有测试

```bash
# 使用 pytest
pytest

# 或使用 make
make test
```

### 运行特定测试文件

```bash
# 浏览器测试
pytest tests/test_browser.py

# 去水印测试
pytest tests/test_watermark_remover.py

# 代理测试
pytest tests/test_proxy.py
```

### 运行特定测试类或方法

```bash
# 运行特定测试类
pytest tests/test_browser.py::TestRemoteBrowser

# 运行特定测试方法
pytest tests/test_browser.py::TestRemoteBrowser::test_init_with_auth
```

### 详细输出

```bash
# 显示详细输出
pytest -v

# 显示更详细的输出
pytest -vv

# 显示打印输出
pytest -s
```

### 覆盖率报告

```bash
# 需要先安装 pytest-cov
# uv sync --group dev

# 运行测试并生成覆盖率报告
pytest --cov=crawler --cov=utils --cov-report=html --cov-report=term
```

## 测试说明

### 浏览器测试 (test_browser.py)

测试 `RemoteBrowser` 类的功能：

- ✅ 初始化（从参数或环境变量）
- ✅ 连接远程浏览器
- ✅ 导航到URL
- ✅ 查找元素
- ✅ 执行JavaScript
- ✅ 执行CDP命令
- ✅ 等待验证码解决
- ✅ 文件下载
- ✅ 截图功能
- ✅ 上下文管理器

### 去水印测试 (test_watermark_remover.py)

测试 `WatermarkRemover` 类的功能：

- ✅ 初始化（从参数或环境变量）
- ✅ 代理配置
- ✅ 创建去水印任务
- ✅ 获取任务状态
- ✅ 等待任务完成
- ✅ 完整流程测试（创建任务 -> 等待完成）

### 代理IP测试 (test_proxy.py)

测试代理相关模块：

- ✅ `ResidentialProxy` 类
  - 初始化（基本代理、认证、SSL证书）
  - 获取代理字典
  - SSL上下文管理
  - 代理可用性测试
- ✅ `ProxyAdapter` 类
  - 静态代理适配
  - 动态代理适配（ProxyManager）
  - SSL证书支持
  - 成功/失败标记
- ✅ `ProxyManager` 类
  - 从文件加载代理
  - 从API加载代理
  - 获取代理
  - 标记成功/失败
  - 代理统计
- ✅ `Proxy` 类
  - 初始化
  - 代理字典生成

## Fixtures

公共 fixtures 定义在 `conftest.py` 中：

- `mock_env_vars`: 模拟环境变量
- `test_image_path`: 测试图片路径
- `mock_selenium_driver`: 模拟 Selenium WebDriver
- `mock_connection`: 模拟 Selenium Connection
- `mock_requests_response`: 模拟 requests.Response
- `mock_proxy_manager`: 模拟 ProxyManager
- `temp_proxy_file`: 临时代理文件
- `sample_config`: 示例配置字典

## 注意事项

1. **外部依赖**: 测试使用 `unittest.mock` 模拟外部依赖（如 Selenium、requests），不需要实际连接外部服务

2. **环境变量**: 测试会自动设置必要的环境变量，不会影响实际环境

3. **测试图片**: 确保 `tests/images/test1.jpg` 存在，否则部分测试会被跳过

4. **代理测试**: 代理测试不需要真实的代理服务器，使用 mock 对象模拟

5. **浏览器测试**: 浏览器测试使用 mock 对象，不会实际启动浏览器

## 编写新测试

添加新测试时，请遵循以下规范：

1. 测试文件命名：`test_*.py`
2. 测试类命名：`Test*`
3. 测试方法命名：`test_*`
4. 使用 pytest fixtures 共享测试资源
5. 使用 `unittest.mock` 模拟外部依赖
6. 每个测试应该独立，不依赖其他测试的执行顺序

## 示例

```python
import pytest
from unittest.mock import Mock, patch
from crawler.browser import RemoteBrowser

class TestMyFeature:
    def test_something(self):
        """测试某个功能"""
        # 测试代码
        assert True
```
