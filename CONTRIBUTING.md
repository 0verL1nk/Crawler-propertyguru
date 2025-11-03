# 贡献指南

感谢你对项目的贡献！本文档提供了代码质量标准和开发流程。

## 代码质量标准

### 1. 代码格式化

项目使用以下工具自动格式化代码：

- **Black**: Python代码格式化器
- **isort**: 导入语句排序
- **Ruff**: 快速linter和代码格式化

运行格式化：
```bash
make format
# 或
./scripts/format.sh
```

### 2. 静态检查

项目使用以下工具进行静态检查：

- **Ruff**: 快速linter（替代flake8）
- **Flake8**: 代码风格检查
- **Mypy**: 类型检查

运行检查：
```bash
make check
# 或
make lint
make type-check
```

### 3. Pre-commit Hooks

安装pre-commit hooks以自动检查代码：
```bash
make pre-commit-install
```

这将在每次提交前自动运行：
- 代码格式化
- Lint检查
- 类型检查

### 4. 开发流程

1. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **开发代码**
   - 编写代码
   - 添加注释和文档字符串
   - 遵循PEP 8风格指南

3. **运行检查**
   ```bash
   make check
   ```

4. **格式化代码**
   ```bash
   make format
   ```

5. **运行测试**
   ```bash
   make test
   ```

6. **提交代码**
   ```bash
   git add .
   git commit -m "feat: 添加新功能"
   ```

## 代码风格

### 类型注解

尽可能使用类型注解：

```python
from typing import Optional, List, Dict

def process_data(data: List[Dict[str, str]]) -> Optional[str]:
    """处理数据"""
    if not data:
        return None
    return data[0].get('key')
```

### 文档字符串

所有公共函数和类都应该有文档字符串：

```python
def fetch_url(url: str, timeout: int = 30) -> Optional[str]:
    """
    获取URL内容
    
    Args:
        url: 目标URL
        timeout: 超时时间（秒）
    
    Returns:
        网页内容或None
    """
    ...
```

### 命名规范

- **函数和变量**: `snake_case`
- **类**: `PascalCase`
- **常量**: `UPPER_SNAKE_CASE`
- **私有方法**: `_leading_underscore`

### 导入顺序

1. 标准库
2. 第三方库
3. 本地模块

使用isort自动排序。

## 测试

- 所有新功能都应该有测试
- 测试文件放在 `tests/` 目录
- 测试函数名以 `test_` 开头

运行测试：
```bash
make test
make test-cov  # 带覆盖率报告
```

## 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `style:` 代码格式（不影响功能）
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具相关

示例：
```
feat: 添加远程浏览器API支持
fix: 修复代理SSL证书加载问题
docs: 更新README使用说明
```

## 环境变量

敏感信息必须使用环境变量，不要硬编码：

```python
# ✅ 正确
auth = os.getenv('BROWSER_AUTH')

# ❌ 错误
auth = 'brd-customer-xxx:password'
```

## 常见问题

### Mypy类型检查失败

如果某些第三方库缺少类型存根，可以：
1. 在 `pyproject.toml` 的 `[tool.mypy.overrides]` 中添加忽略
2. 使用 `# type: ignore` 注释（不推荐）

### Ruff检查过于严格

在 `pyproject.toml` 的 `[tool.ruff]` 或 `[tool.ruff.per-file-ignores]` 中调整配置。

### Pre-commit失败

可以手动运行：
```bash
pre-commit run --all-files
```

或跳过hooks（不推荐）：
```bash
git commit --no-verify
```

