# 🚀 快速开始指南

本指南帮助你在 5 分钟内启动 PropertyGuru 智能搜索引擎。

## 📋 前置要求

- Docker 20.10+
- Docker Compose v2.0+

## 🎯 快速部署（3 种方式）

### 方式 1: 使用部署脚本（推荐）

```bash
# 1. 进入项目目录
cd /home/ling/Crawler/propertyguru-auto-searcher

# 2. 运行部署脚本
./scripts/deploy.sh

# 3. 访问服务
# http://localhost:8080
```

### 方式 2: 使用 Makefile

```bash
# 1. 构建并启动
make build
make up

# 2. 查看服务状态
make ps

# 3. 测试 API
make test
```

### 方式 3: 使用 Docker Compose

```bash
# 1. 启动服务
docker compose up -d

# 2. 查看日志
docker compose logs -f searcher

# 3. 检查健康状态
curl http://localhost:8080/health
```

## ✅ 验证部署

### 1. 检查服务状态

```bash
# 查看运行中的容器
docker compose ps

# 应该看到两个服务:
# - property-postgres (健康状态: healthy)
# - property-searcher (健康状态: healthy)
```

### 2. 测试健康检查

```bash
curl http://localhost:8080/health
```

预期输出:
```json
{
  "status": "healthy",
  "service": "property-search-engine"
}
```

### 3. 测试搜索 API

```bash
curl -X POST http://localhost:8080/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "3 bedroom condo near MRT under $1M",
    "options": {
      "top_k": 5,
      "semantic": true
    }
  }'
```

### 4. 访问 Web UI

在浏览器中打开: http://localhost:8080

## 📊 常用命令

### 查看日志

```bash
# 查看所有服务日志
docker compose logs

# 只查看搜索引擎日志
docker compose logs -f searcher

# 只查看数据库日志
docker compose logs -f postgres

# 或使用 Makefile
make logs
make logs-searcher
make logs-postgres
```

### 进入容器

```bash
# 进入搜索引擎容器
docker exec -it property-searcher sh

# 进入数据库容器
docker exec -it property-postgres psql -U property_user -d property_search

# 或使用 Makefile
make shell
make db-shell
```

### 重启服务

```bash
# 重启所有服务
docker compose restart

# 重启特定服务
docker compose restart searcher

# 或使用 Makefile
make restart
```

### 停止服务

```bash
# 停止服务（保留容器）
docker compose stop

# 停止并删除容器（保留数据）
docker compose down

# 停止并删除容器和数据
docker compose down -v

# 或使用 Makefile
make stop
make down
make down-v
```

## 🔧 配置调整

### 修改端口

如果端口冲突，修改 `docker-compose.yml`:

```yaml
services:
  searcher:
    ports:
      - "8081:8080"  # 改为 8081
  
  postgres:
    ports:
      - "5433:5432"  # 改为 5433
```

### 修改数据库密码

1. 编辑 `.env` 文件（如果不存在，从 `config.example.env` 复制）:

```bash
cp config.example.env .env
vim .env
```

2. 修改密码:

```bash
PG_PASSWORD=your_strong_password_here
```

3. 重新启动:

```bash
docker compose down -v
docker compose up -d
```

### 调整排序权重

修改 `.env` 或 `docker-compose.yml`:

```yaml
environment:
  RANK_WEIGHT_TEXT: 0.5      # 文本相关度
  RANK_WEIGHT_PRICE: 0.3     # 价格匹配度
  RANK_WEIGHT_RECENCY: 0.2   # 新鲜度
```

## 💾 数据备份与恢复

### 备份数据库

```bash
# 使用备份脚本
./scripts/backup.sh

# 手动备份
docker exec property-postgres pg_dump -U property_user property_search > backup.sql

# 使用 Makefile
make db-backup
```

### 恢复数据库

```bash
# 使用恢复脚本（交互式）
./scripts/restore.sh

# 恢复指定备份
./scripts/restore.sh backups/property_search_20240101.sql.gz

# 手动恢复
cat backup.sql | docker exec -i property-postgres psql -U property_user -d property_search

# 使用 Makefile
make db-restore FILE=backup.sql
```

### 列出所有备份

```bash
# 使用脚本
./scripts/backup.sh --list

# 手动查看
ls -lh backups/
```

## 🐛 故障排除

### 问题 1: 服务启动失败

```bash
# 查看详细日志
docker compose logs

# 检查容器状态
docker compose ps

# 检查端口占用
sudo netstat -tlnp | grep -E '8080|5432'
```

### 问题 2: 数据库连接失败

```bash
# 检查数据库是否就绪
docker exec property-postgres pg_isready -U property_user

# 进入数据库检查
docker exec -it property-postgres psql -U property_user -d property_search

# 查看连接设置
docker exec property-postgres psql -U property_user -d property_search -c "SHOW max_connections;"
```

### 问题 3: 搜索无结果

```bash
# 检查数据库是否有数据
docker exec property-postgres psql -U property_user -d property_search -c "SELECT COUNT(*) FROM listing_info;"

# 如果没有数据，需要先运行爬虫导入数据
# 参考主 README.md 中的 "与爬虫项目集成" 部分
```

### 问题 4: 内存不足

修改 `docker-compose.yml` 降低资源限制:

```yaml
deploy:
  resources:
    limits:
      memory: 1G    # 减少内存限制
```

### 问题 5: 镜像构建慢

```bash
# 使用国内镜像源
# 编辑 Dockerfile，在开头添加:
# RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

# 或使用预构建的镜像（如果有）
docker pull your-registry.com/property-searcher:latest
```

## 🔄 更新服务

### 拉取最新代码

```bash
# 1. 停止服务
docker compose down

# 2. 更新代码
git pull

# 3. 重新构建并启动
docker compose up -d --build

# 或使用 Makefile
make reload
```

### 更新数据库架构

```bash
# 1. 备份当前数据
./scripts/backup.sh

# 2. 应用新的 SQL 脚本
cat sql/migration_v2.sql | docker exec -i property-postgres psql -U property_user -d property_search

# 3. 重启服务
docker compose restart searcher
```

## 📈 性能优化

### 1. 增加数据库连接池

```yaml
environment:
  PG_MAX_CONNECTIONS: 50
  PG_MAX_IDLE_CONNECTIONS: 10
```

### 2. 启用查询缓存（需要集成 Redis）

参考 `docker-compose.prod.yml` 中的 Redis 配置。

### 3. 调整 PostgreSQL 配置

编辑 `config/postgresql.conf` 根据服务器资源调整参数。

## 🚀 生产环境部署

参考 [DOCKER.md](./DOCKER.md) 中的生产环境部署章节。

简要步骤:

```bash
# 1. 创建生产配置
cp .env.production.example .env.production
vim .env.production  # 修改密码等敏感信息

# 2. 使用生产配置启动
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 或使用部署脚本
./scripts/deploy.sh --prod
```

## 📚 更多资源

- [完整文档](./README.md)
- [Docker 详细指南](./DOCKER.md)
- [API 文档](./README.md#api-文档)
- [与爬虫集成](./README.md#与爬虫项目集成)

## 🆘 获取帮助

遇到问题？

1. 查看日志: `docker compose logs`
2. 检查故障排除章节
3. 查看 [DOCKER.md](./DOCKER.md) 详细文档
4. 提交 Issue

## 📝 下一步

现在服务已经运行，你可以:

1. **导入数据**: 使用爬虫项目导入房源数据
2. **测试搜索**: 尝试各种自然语言查询
3. **查看 Web UI**: 浏览前端界面
4. **集成到你的应用**: 使用 API 集成搜索功能
5. **配置监控**: 参考生产环境配置添加 Prometheus/Grafana

祝你使用愉快！🎉

