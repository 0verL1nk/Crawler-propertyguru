# 🐳 Docker 部署指南

本文档介绍如何使用 Docker 部署 PropertyGuru 智能搜索引擎。

## 📋 前置要求

- Docker Engine 20.10+
- Docker Compose v2.0+

### 安装 Docker (Ubuntu/Debian)

```bash
# 更新包索引
sudo apt update

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo apt install docker-compose-plugin

# 验证安装
docker --version
docker compose version
```

## 🚀 快速开始

### 方式 1: 使用 Docker Compose（推荐）

Docker Compose 会自动启动 PostgreSQL 和搜索引擎服务。

```bash
# 1. 克隆项目
cd /home/ling/Crawler/propertyguru-auto-searcher

# 2. 启动所有服务
docker compose up -d

# 3. 查看日志
docker compose logs -f searcher

# 4. 检查服务状态
docker compose ps

# 5. 测试服务
curl http://localhost:8080/health
```

服务将在以下地址可用：
- **Web UI**: http://localhost:8080
- **API**: http://localhost:8080/api/v1
- **PostgreSQL**: localhost:5432

### 方式 2: 仅构建镜像

如果你已有 PostgreSQL 数据库，只需构建搜索引擎镜像：

```bash
# 构建镜像
docker build -t property-searcher:latest .

# 运行容器（需要配置环境变量）
docker run -d \
  --name property-searcher \
  -p 8080:8080 \
  -e PG_HOST=your_postgres_host \
  -e PG_PORT=5432 \
  -e PG_USER=property_user \
  -e PG_PASSWORD=your_password \
  -e PG_DATABASE=property_search \
  property-searcher:latest
```

## 🔧 配置选项

### 环境变量

在 `docker-compose.yml` 中可以配置以下环境变量：

#### PostgreSQL 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PG_HOST` | PostgreSQL 主机地址 | `postgres` |
| `PG_PORT` | PostgreSQL 端口 | `5432` |
| `PG_USER` | 数据库用户名 | `property_user` |
| `PG_PASSWORD` | 数据库密码 | `property_password` |
| `PG_DATABASE` | 数据库名称 | `property_search` |
| `PG_SSLMODE` | SSL 模式 | `disable` |
| `PG_MAX_CONNECTIONS` | 最大连接数 | `25` |
| `PG_MAX_IDLE_CONNECTIONS` | 最大空闲连接数 | `5` |

#### 服务器配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SERVER_PORT` | 服务监听端口 | `8080` |
| `SERVER_HOST` | 服务监听地址 | `0.0.0.0` |
| `GIN_MODE` | Gin 框架模式 | `release` |

#### 搜索配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SEARCH_DEFAULT_LIMIT` | 默认返回结果数 | `20` |
| `SEARCH_MAX_LIMIT` | 最大返回结果数 | `100` |
| `RANK_WEIGHT_TEXT` | 文本相关度权重 | `0.5` |
| `RANK_WEIGHT_PRICE` | 价格匹配度权重 | `0.3` |
| `RANK_WEIGHT_RECENCY` | 新鲜度权重 | `0.2` |

### 自定义配置

创建 `.env` 文件来覆盖默认配置：

```bash
# 复制示例配置
cp config.example.env .env

# 编辑配置
vim .env
```

然后在 `docker-compose.yml` 中引用：

```yaml
services:
  searcher:
    env_file:
      - .env
```

## 📊 数据持久化

PostgreSQL 数据存储在 Docker 卷中：

```bash
# 查看卷
docker volume ls | grep postgres

# 备份数据
docker exec property-postgres pg_dump -U property_user property_search > backup.sql

# 恢复数据
cat backup.sql | docker exec -i property-postgres psql -U property_user -d property_search
```

## 🔍 故障排除

### 查看日志

```bash
# 查看所有服务日志
docker compose logs

# 查看特定服务日志
docker compose logs searcher
docker compose logs postgres

# 实时跟踪日志
docker compose logs -f searcher
```

### 进入容器

```bash
# 进入搜索引擎容器
docker exec -it property-searcher sh

# 进入 PostgreSQL 容器
docker exec -it property-postgres psql -U property_user -d property_search
```

### 常见问题

#### 1. 数据库连接失败

```bash
# 检查 PostgreSQL 是否启动
docker compose ps postgres

# 检查数据库健康状态
docker exec property-postgres pg_isready -U property_user

# 查看 PostgreSQL 日志
docker compose logs postgres
```

#### 2. 端口冲突

如果 8080 或 5432 端口已被占用，修改 `docker-compose.yml`：

```yaml
services:
  searcher:
    ports:
      - "8081:8080"  # 使用不同的主机端口
  
  postgres:
    ports:
      - "5433:5432"  # 使用不同的主机端口
```

#### 3. pgvector 扩展未安装

我们使用的是 `pgvector/pgvector:pg16` 镜像，已经预装了 pgvector 扩展。

如果遇到问题，手动创建扩展：

```bash
docker exec -it property-postgres psql -U property_user -d property_search -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### 4. 镜像构建失败

```bash
# 清理构建缓存
docker builder prune

# 重新构建（不使用缓存）
docker compose build --no-cache

# 查看详细构建日志
docker compose build --progress=plain
```

## 🔄 服务管理

### 启动服务

```bash
# 启动所有服务
docker compose up -d

# 启动特定服务
docker compose up -d searcher

# 查看启动日志
docker compose up
```

### 停止服务

```bash
# 停止所有服务
docker compose stop

# 停止特定服务
docker compose stop searcher
```

### 重启服务

```bash
# 重启所有服务
docker compose restart

# 重启特定服务
docker compose restart searcher
```

### 删除服务

```bash
# 停止并删除容器（保留数据卷）
docker compose down

# 删除容器和数据卷
docker compose down -v

# 删除容器、数据卷和镜像
docker compose down -v --rmi all
```

### 更新服务

```bash
# 重新构建并启动
docker compose up -d --build

# 仅重新构建
docker compose build

# 强制重新创建容器
docker compose up -d --force-recreate
```

## 🌐 生产环境部署

### 使用外部 PostgreSQL

如果使用外部数据库（如 Supabase、AWS RDS），修改 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  searcher:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: property-searcher
    environment:
      PG_HOST: your-db-host.supabase.co
      PG_PORT: 5432
      PG_USER: postgres
      PG_PASSWORD: ${PG_PASSWORD}  # 从环境变量读取
      PG_DATABASE: postgres
      PG_SSLMODE: require
      GIN_MODE: release
    ports:
      - "8080:8080"
    restart: unless-stopped
```

### 使用 Docker Swarm / Kubernetes

#### Docker Swarm

```bash
# 部署到 Swarm
docker stack deploy -c docker-compose.yml property

# 查看服务
docker service ls

# 扩展服务
docker service scale property_searcher=3
```

#### Kubernetes

创建 `k8s/deployment.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: property-searcher
spec:
  replicas: 3
  selector:
    matchLabels:
      app: property-searcher
  template:
    metadata:
      labels:
        app: property-searcher
    spec:
      containers:
      - name: searcher
        image: property-searcher:latest
        ports:
        - containerPort: 8080
        env:
        - name: PG_HOST
          value: "postgres-service"
        - name: PG_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
```

### 反向代理（Nginx）

```nginx
upstream property_searcher {
    server localhost:8080;
}

server {
    listen 80;
    server_name property-search.example.com;

    location / {
        proxy_pass http://property_searcher;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### HTTPS 配置（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d property-search.example.com

# 自动续期
sudo certbot renew --dry-run
```

## 📈 性能优化

### 1. 资源限制

在 `docker-compose.yml` 中添加资源限制：

```yaml
services:
  searcher:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
  
  postgres:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '2'
          memory: 2G
```

### 2. 健康检查优化

```yaml
healthcheck:
  test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8080/health"]
  interval: 10s      # 检查间隔
  timeout: 3s        # 超时时间
  retries: 3         # 重试次数
  start_period: 30s  # 启动等待时间
```

### 3. 数据库连接池

调整连接池大小以匹配容器资源：

```yaml
environment:
  PG_MAX_CONNECTIONS: 50
  PG_MAX_IDLE_CONNECTIONS: 10
```

## 🔒 安全建议

1. **不要在代码中硬编码密码**
   ```bash
   # 使用环境变量
   export PG_PASSWORD="secure_password"
   docker compose up -d
   ```

2. **限制容器权限**
   ```yaml
   security_opt:
     - no-new-privileges:true
   read_only: true
   ```

3. **使用私有镜像仓库**
   ```bash
   docker tag property-searcher:latest registry.example.com/property-searcher:latest
   docker push registry.example.com/property-searcher:latest
   ```

4. **定期更新基础镜像**
   ```bash
   docker pull golang:1.21-alpine
   docker pull alpine:latest
   docker compose build --no-cache
   ```

## 📝 监控和日志

### 1. 集成 Prometheus

添加 metrics endpoint 并配置 Prometheus：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'property-searcher'
    static_configs:
      - targets: ['property-searcher:8080']
```

### 2. 集成 ELK Stack

配置日志输出到 Elasticsearch：

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 3. 使用 Portainer 管理

```bash
docker run -d -p 9000:9000 \
  --name portainer \
  -v /var/run/docker.sock:/var/run/docker.sock \
  portainer/portainer-ce
```

访问 http://localhost:9000 进行可视化管理。

## 🧪 测试

```bash
# 健康检查
curl http://localhost:8080/health

# 搜索测试
curl -X POST http://localhost:8080/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "3 bedroom condo near MRT under $1M",
    "options": {
      "top_k": 10,
      "semantic": true
    }
  }'

# 数据库测试
docker exec property-postgres psql -U property_user -d property_search -c "SELECT COUNT(*) FROM listing_info;"
```

## 📚 参考资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [pgvector Docker 镜像](https://hub.docker.com/r/pgvector/pgvector)
- [Go Docker 最佳实践](https://docs.docker.com/language/golang/)

## 🤝 贡献

如有问题或建议，请提交 Issue！

