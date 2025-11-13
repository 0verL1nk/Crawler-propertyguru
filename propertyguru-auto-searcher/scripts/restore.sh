#!/bin/bash
# PostgreSQL 数据库恢复脚本

set -e

# 配置
BACKUP_DIR="./backups"
CONTAINER_NAME="property-postgres"
DB_USER="property_user"
DB_NAME="property_search"

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

# 列出可用备份
list_backups() {
    log_info "可用的备份文件:"
    echo ""
    
    local i=1
    local -a backups
    
    while IFS= read -r backup; do
        SIZE=$(du -h "$backup" | cut -f1)
        DATE=$(stat -c %y "$backup" | cut -d' ' -f1,2 | cut -d'.' -f1)
        echo "  [$i] $(basename "$backup") ($SIZE) - $DATE"
        backups+=("$backup")
        ((i++))
    done < <(find "$BACKUP_DIR" -name "property_search_*.sql.gz" -type f | sort -r)
    
    echo ""
    
    if [ ${#backups[@]} -eq 0 ]; then
        log_error "未找到备份文件"
        exit 1
    fi
    
    # 返回备份列表
    printf '%s\n' "${backups[@]}"
}

# 选择备份文件
select_backup() {
    local backups=($(list_backups))
    local count=${#backups[@]}
    
    if [ $count -eq 0 ]; then
        exit 1
    fi
    
    echo -n "请选择要恢复的备份编号 [1-$count] (或输入完整路径): "
    read -r choice
    
    if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "$count" ]; then
        BACKUP_FILE="${backups[$((choice-1))]}"
    elif [ -f "$choice" ]; then
        BACKUP_FILE="$choice"
    else
        log_error "无效的选择"
        exit 1
    fi
    
    log_info "选择的备份文件: $BACKUP_FILE"
}

# 确认恢复操作
confirm_restore() {
    log_warn "警告: 此操作将覆盖当前数据库中的所有数据！"
    echo -n "确认继续? (输入 'yes' 继续): "
    read -r confirmation
    
    if [ "$confirmation" != "yes" ]; then
        log_info "操作已取消"
        exit 0
    fi
}

# 创建当前数据库快照
create_snapshot() {
    log_info "创建当前数据库快照..."
    
    SNAPSHOT_FILE="${BACKUP_DIR}/pre_restore_$(date +%Y%m%d_%H%M%S).sql"
    docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$DB_NAME" > "$SNAPSHOT_FILE"
    gzip "$SNAPSHOT_FILE"
    
    log_info "✓ 快照已保存: ${SNAPSHOT_FILE}.gz"
}

# 执行恢复
do_restore() {
    log_info "开始恢复数据库..."
    
    # 解压备份文件（如果需要）
    local restore_file="$BACKUP_FILE"
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        log_info "解压备份文件..."
        restore_file="${BACKUP_FILE%.gz}"
        gunzip -c "$BACKUP_FILE" > "$restore_file"
    fi
    
    # 停止应用连接
    log_info "停止搜索引擎服务..."
    docker compose stop searcher || true
    
    # 终止现有连接
    log_info "终止数据库连接..."
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d postgres -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
        || true
    
    # 删除并重建数据库
    log_info "重建数据库..."
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    
    # 恢复数据
    log_info "恢复数据..."
    cat "$restore_file" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME"
    
    # 清理临时文件
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        rm -f "$restore_file"
    fi
    
    # 重启搜索引擎
    log_info "重启搜索引擎服务..."
    docker compose start searcher
    
    log_info "✓ 数据库恢复完成"
}

# 验证恢复
verify_restore() {
    log_info "验证数据库..."
    
    # 检查数据库连接
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &>/dev/null; then
        log_info "✓ 数据库连接正常"
    else
        log_error "✗ 数据库连接失败"
        exit 1
    fi
    
    # 检查表是否存在
    local table_count=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
    
    log_info "✓ 数据库包含 $table_count 个表"
    
    # 检查数据量
    local listing_count=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM listing_info;" || echo "0")
    
    log_info "✓ listing_info 表包含 $listing_count 条记录"
}

# 主函数
main() {
    log_info "=========================================="
    log_info "  PostgreSQL 数据库恢复"
    log_info "=========================================="
    echo ""
    
    check_container
    
    if [ -n "${1:-}" ] && [ -f "$1" ]; then
        BACKUP_FILE="$1"
        log_info "使用指定的备份文件: $BACKUP_FILE"
    else
        select_backup
    fi
    
    confirm_restore
    create_snapshot
    do_restore
    verify_restore
    
    echo ""
    log_info "=========================================="
    log_info "  恢复完成"
    log_info "=========================================="
    echo ""
}

# 处理命令行参数
case "${1:-}" in
    --list|-l)
        list_backups > /dev/null
        exit 0
        ;;
    --help|-h)
        echo "用法: $0 [备份文件路径]"
        echo ""
        echo "选项:"
        echo "  无参数          交互式选择备份文件"
        echo "  <文件路径>      恢复指定的备份文件"
        echo "  --list          列出所有可用备份"
        echo "  --help          显示此帮助信息"
        echo ""
        echo "示例:"
        echo "  $0                                    # 交互式恢复"
        echo "  $0 backups/property_search_20240101.sql.gz  # 恢复指定文件"
        exit 0
        ;;
esac

# 运行主函数
main "$@"

