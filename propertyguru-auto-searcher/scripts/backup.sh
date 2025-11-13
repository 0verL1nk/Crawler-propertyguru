#!/bin/bash
# PostgreSQL 数据库备份脚本

set -e

# 配置
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/property_search_${TIMESTAMP}.sql"
CONTAINER_NAME="property-postgres"
DB_USER="property_user"
DB_NAME="property_search"
RETENTION_DAYS=30

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 检查容器是否运行
check_container() {
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        log_error "容器 $CONTAINER_NAME 未运行"
        exit 1
    fi
}

# 创建备份目录
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_info "创建备份目录: $BACKUP_DIR"
    fi
}

# 执行备份
do_backup() {
    log_info "开始备份数据库..."
    log_info "备份文件: $BACKUP_FILE"
    
    # 使用 pg_dump 备份
    docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"
    
    # 压缩备份文件
    gzip "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"
    
    # 检查备份文件
    if [ -f "$BACKUP_FILE" ]; then
        SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log_info "✓ 备份完成: $BACKUP_FILE (大小: $SIZE)"
    else
        log_error "✗ 备份失败"
        exit 1
    fi
}

# 清理旧备份
cleanup_old_backups() {
    log_info "清理 $RETENTION_DAYS 天前的备份..."
    
    find "$BACKUP_DIR" -name "property_search_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    
    REMAINING=$(find "$BACKUP_DIR" -name "property_search_*.sql.gz" | wc -l)
    log_info "✓ 当前保留 $REMAINING 个备份文件"
}

# 列出所有备份
list_backups() {
    log_info "现有备份列表:"
    echo ""
    find "$BACKUP_DIR" -name "property_search_*.sql.gz" -type f -exec ls -lh {} \; | \
        awk '{print $9, "("$5")", $6, $7, $8}'
}

# 验证备份
verify_backup() {
    log_info "验证备份文件..."
    
    # 检查 gzip 文件完整性
    if gzip -t "$BACKUP_FILE" 2>/dev/null; then
        log_info "✓ 备份文件完整性验证通过"
    else
        log_error "✗ 备份文件损坏"
        exit 1
    fi
}

# 上传到远程存储（可选）
upload_to_remote() {
    if [ -n "${BACKUP_REMOTE_PATH:-}" ]; then
        log_info "上传备份到远程存储: $BACKUP_REMOTE_PATH"
        # 示例: rsync, scp, aws s3, etc.
        # rsync -avz "$BACKUP_FILE" "$BACKUP_REMOTE_PATH/"
        log_warn "远程上传功能需要配置"
    fi
}

# 主函数
main() {
    log_info "=========================================="
    log_info "  PostgreSQL 数据库备份"
    log_info "=========================================="
    echo ""
    
    check_container
    create_backup_dir
    do_backup
    verify_backup
    cleanup_old_backups
    upload_to_remote
    
    echo ""
    log_info "=========================================="
    log_info "  备份完成"
    log_info "=========================================="
    echo ""
    list_backups
}

# 处理命令行参数
case "${1:-}" in
    --list|-l)
        list_backups
        exit 0
        ;;
    --help|-h)
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  无参数    执行备份"
        echo "  --list    列出所有备份"
        echo "  --help    显示此帮助信息"
        echo ""
        echo "环境变量:"
        echo "  BACKUP_REMOTE_PATH  远程备份路径（可选）"
        echo "  RETENTION_DAYS      备份保留天数（默认: 30）"
        exit 0
        ;;
esac

# 运行主函数
main

