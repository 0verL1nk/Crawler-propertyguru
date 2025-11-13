# 🐳 Docker 相关文件清单

本文档列出了所有 Docker 相关的配置文件及其用途。

## 📁 核心文件

### 1. `Dockerfile`
**用途**: 应用镜像构建文件

**特性**:
- 多阶段构建（构建阶段 + 运行阶段）
- 基于 Alpine Linux，镜像体积小
- 使用非 root 用户运行
- 包含健康检查
- 优化的 Go 编译参数

**构建命令**:
```bash
docker build -t property-searcher:latest .
```

---

### 2. `.dockerignore`
**用途**: 排除不需要复制到镜像中的文件

**排除内容**:
- Git 文件
- 文档和说明
- 环境配置文件
- 构建产物
- 开发工具配置
- 临时文件

---

### 3. `docker-compose.yml`
**用途**: 开发/测试环境服务编排

**包含服务**:
- PostgreSQL (pgvector/pgvector:pg16)
- 搜索引擎服务 (property-searcher)

**特性**:
- 自动健康检查
- 数据持久化
- 网络隔离
- 日志管理

**启动命令**:
```bash
docker compose up -d
```

---

### 4. `docker-compose.prod.yml`
**用途**: 生产环境服务编排

**额外包含**:
- Nginx 反向代理
- Redis 缓存
- Prometheus 监控
- Grafana 可视化

**特性**:
- 资源限制
- 安全加固
- 滚动更新
- 高可用配置
- 完整的监控栈

**启动命令**:
```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## 📋 脚本文件

### 5. `scripts/deploy.sh`
**用途**: 一键部署脚本

**功能**:
- ✅ 检查环境要求
- ✅ 创建必要目录
- ✅ 构建 Docker 镜像
- ✅ 启动服务
- ✅ 健康检查
- ✅ 显示访问信息

**使用方法**:
```bash
./scripts/deploy.sh           # 开发环境
./scripts/deploy.sh --prod    # 生产环境
```

---

### 6. `scripts/backup.sh`
**用途**: 数据库自动备份脚本

**功能**:
- 📦 备份 PostgreSQL 数据库
- 🗜️ 自动压缩备份文件
- 🔍 验证备份完整性
- 🧹 清理过期备份（默认 30 天）
- 📋 列出所有备份

**使用方法**:
```bash
./scripts/backup.sh         # 执行备份
./scripts/backup.sh --list  # 列出备份
```

**定时备份** (crontab):
```bash
# 每天凌晨 2 点备份
0 2 * * * /path/to/scripts/backup.sh
```

---

### 7. `scripts/restore.sh`
**用途**: 数据库恢复脚本

**功能**:
- 🔄 交互式选择备份
- 📸 恢复前创建快照
- ⚠️ 安全确认机制
- ✅ 恢复后验证

**使用方法**:
```bash
./scripts/restore.sh                    # 交互式恢复
./scripts/restore.sh backup.sql.gz     # 恢复指定文件
```

---

### 8. `Makefile`
**用途**: 简化 Docker 操作的快捷命令

**可用命令**:

| 命令 | 功能 |
|------|------|
| `make help` | 显示所有命令 |
| `make build` | 构建镜像 |
| `make up` | 启动服务 |
| `make down` | 停止服务 |
| `make logs` | 查看日志 |
| `make shell` | 进入容器 |
| `make db-shell` | 进入数据库 |
| `make test` | 测试 API |
| `make db-backup` | 备份数据库 |
| `make db-restore` | 恢复数据库 |
| `make health` | 健康检查 |
| `make clean` | 清理资源 |

---

## ⚙️ 配置文件

### 9. `config/nginx/nginx.conf`
**用途**: Nginx 主配置文件

**包含**:
- Worker 进程配置
- 日志格式
- Gzip 压缩
- 安全头设置
- 上游服务器配置

---

### 10. `config/nginx/conf.d/default.conf`
**用途**: Nginx 站点配置

**包含**:
- HTTP/HTTPS 服务器配置
- API 路由代理
- 静态文件缓存
- 超时和缓冲设置
- SSL 配置示例

---

### 11. `config/postgresql.conf`
**用途**: PostgreSQL 性能优化配置

**优化项**:
- 内存设置 (8GB 服务器)
- 连接池配置
- 查询优化
- WAL 设置
- 自动清理
- pgvector 优化

**使用方法**:
在 `docker-compose.prod.yml` 中挂载:
```yaml
volumes:
  - ./config/postgresql.conf:/etc/postgresql/postgresql.conf:ro
```

---

### 12. `config/prometheus/prometheus.yml`
**用途**: Prometheus 监控配置

**监控目标**:
- PostgreSQL
- 搜索引擎服务
- Nginx
- Redis
- 系统指标 (Node Exporter)
- 容器指标 (cAdvisor)

---

## 📚 文档文件

### 13. `DOCKER.md`
**用途**: Docker 详细部署指南

**内容**:
- 前置要求
- 快速开始
- 配置选项
- 故障排除
- 生产环境部署
- 性能优化
- 安全建议
- 监控和日志

**约 400+ 行的完整文档**

---

### 14. `QUICKSTART.md`
**用途**: 5 分钟快速开始指南

**内容**:
- 3 种快速部署方式
- 验证部署步骤
- 常用命令速查
- 快速故障排除
- 下一步行动指南

**约 300+ 行的精简指南**

---

### 15. `DOCKER_FILES.md` (本文件)
**用途**: Docker 文件清单和说明

---

## 🔄 CI/CD 文件

### 16. `.github/workflows/docker-build.yml`
**用途**: GitHub Actions 工作流

**功能**:
- ✅ 代码检查和测试
- ✅ Docker 镜像构建
- ✅ Docker Compose 集成测试
- ✅ 自动发布到 Docker Hub

**触发条件**:
- Push 到 main/develop 分支
- 创建版本标签 (v*.*.*)
- Pull Request

---

## 📊 文件结构总览

```
propertyguru-auto-searcher/
├── Dockerfile                          # 核心镜像构建文件
├── .dockerignore                       # Docker 忽略文件
├── docker-compose.yml                  # 开发环境编排
├── docker-compose.prod.yml             # 生产环境编排
├── Makefile                            # 快捷命令
│
├── scripts/
│   ├── deploy.sh                       # 部署脚本
│   ├── backup.sh                       # 备份脚本
│   └── restore.sh                      # 恢复脚本
│
├── config/
│   ├── nginx/
│   │   ├── nginx.conf                  # Nginx 主配置
│   │   └── conf.d/
│   │       └── default.conf            # 站点配置
│   ├── postgresql.conf                 # PostgreSQL 优化
│   └── prometheus/
│       └── prometheus.yml              # 监控配置
│
├── .github/
│   └── workflows/
│       └── docker-build.yml            # CI/CD 工作流
│
└── docs/ (文档)
    ├── DOCKER.md                       # 详细 Docker 指南
    ├── QUICKSTART.md                   # 快速开始指南
    └── DOCKER_FILES.md                 # 本文件
```

---

## 🚀 使用建议

### 开发环境

1. **快速开始**:
   ```bash
   make up
   ```

2. **查看日志**:
   ```bash
   make logs
   ```

3. **测试 API**:
   ```bash
   make test
   ```

### 生产环境

1. **使用部署脚本**:
   ```bash
   ./scripts/deploy.sh --prod
   ```

2. **手动部署**:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

3. **监控**:
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000

### 数据管理

1. **定期备份**:
   ```bash
   # 添加到 crontab
   0 2 * * * /path/to/scripts/backup.sh
   ```

2. **恢复数据**:
   ```bash
   ./scripts/restore.sh
   ```

---

## 📝 最佳实践

### 1. 安全
- ✅ 使用 `.env` 文件管理敏感信息
- ✅ 不要在代码中硬编码密码
- ✅ 使用非 root 用户运行容器
- ✅ 定期更新基础镜像

### 2. 性能
- ✅ 使用多阶段构建减小镜像体积
- ✅ 配置资源限制
- ✅ 启用 Gzip 压缩
- ✅ 使用连接池

### 3. 可靠性
- ✅ 配置健康检查
- ✅ 自动重启策略
- ✅ 数据持久化
- ✅ 定期备份

### 4. 可维护性
- ✅ 使用标准化的文件名和路径
- ✅ 编写清晰的注释
- ✅ 版本化配置文件
- ✅ 完善的文档

---

## 🔗 相关链接

- [主 README](./README.md)
- [Docker 详细指南](./DOCKER.md)
- [快速开始](./QUICKSTART.md)
- [API 文档](./README.md#api-文档)

---

## 🆘 获取帮助

如果你对任何文件有疑问:

1. 查看该文件的内联注释
2. 阅读对应的文档 (DOCKER.md 或 QUICKSTART.md)
3. 运行 `make help` 查看可用命令
4. 提交 Issue

---

**最后更新**: 2024-11-07
**维护者**: PropertyGuru Team

