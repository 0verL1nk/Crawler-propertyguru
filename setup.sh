#!/bin/bash
# PropertyGuru Crawler 自动安装脚本
# 适用于 Ubuntu/Debian 系统

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_error "请不要使用 root 用户运行此脚本"
        exit 1
    fi
}

# 检查系统类型
check_system() {
    log_info "检查系统类型..."
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
        log_success "系统: $OS $VER"
    else
        log_error "无法检测系统类型"
        exit 1
    fi
}

# 安装系统依赖
install_system_deps() {
    log_info "安装系统依赖..."

    # 更新包列表
    log_info "更新包列表..."
    sudo apt-get update

    # 安装基础依赖
    log_info "安装基础工具..."
    sudo apt-get install -y \
        wget \
        curl \
        git \
        unzip \
        software-properties-common \
        build-essential

    # 安装虚拟显示（用于无窗口运行有头浏览器）
    log_info "安装 Xvfb（虚拟显示）..."
    sudo apt-get install -y \
        xvfb \
        x11-xkb-utils \
        xfonts-100dpi \
        xfonts-75dpi \
        xfonts-scalable \
        xfonts-cyrillic

    log_success "系统依赖安装完成"
}

# 检查并安装 Chrome
install_chrome() {
    log_info "检查 Google Chrome..."

    if command -v google-chrome &> /dev/null; then
        CHROME_VERSION=$(google-chrome --version | awk '{print $3}')
        log_success "Google Chrome 已安装: $CHROME_VERSION"
    else
        log_info "安装 Google Chrome..."

        # 下载并安装 Chrome
        wget -q -O /tmp/google-chrome-stable_current_amd64.deb \
            https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

        sudo apt-get install -y /tmp/google-chrome-stable_current_amd64.deb || {
            log_warning "安装 Chrome 时出现依赖问题，尝试修复..."
            sudo apt-get install -f -y
        }

        rm /tmp/google-chrome-stable_current_amd64.deb

        CHROME_VERSION=$(google-chrome --version | awk '{print $3}')
        log_success "Google Chrome 安装完成: $CHROME_VERSION"
    fi
}

# 检查并安装 Python
check_python() {
    log_info "检查 Python..."

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        log_success "Python 已安装: $PYTHON_VERSION"

        # 检查 Python 版本是否满足要求 (>= 3.10)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

        if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
            log_error "Python 版本过低，需要 >= 3.10，当前: $PYTHON_VERSION"
            exit 1
        fi
    else
        log_error "Python 未安装，请先安装 Python 3.10+"
        exit 1
    fi
}

# 检查并安装 uv
install_uv() {
    log_info "检查 uv..."

    if command -v uv &> /dev/null; then
        UV_VERSION=$(uv --version | awk '{print $2}')
        log_success "uv 已安装: $UV_VERSION"
    else
        log_info "安装 uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh

        # 添加 uv 到当前 shell 的 PATH
        export PATH="$HOME/.cargo/bin:$PATH"

        if command -v uv &> /dev/null; then
            UV_VERSION=$(uv --version | awk '{print $2}')
            log_success "uv 安装完成: $UV_VERSION"
        else
            log_error "uv 安装失败"
            exit 1
        fi
    fi
}

# 安装 Python 依赖
install_python_deps() {
    log_info "安装 Python 依赖..."

    # 使用 uv 同步依赖
    uv sync

    log_success "Python 依赖安装完成"
}

# 安装额外的 Python 包
install_extra_deps() {
    log_info "安装额外的 Python 包..."

    # 安装虚拟显示支持
    uv pip install pyvirtualdisplay

    log_success "额外依赖安装完成"
}

# 配置环境
setup_environment() {
    log_info "配置环境..."

    # 创建 .env 文件（如果不存在）
    if [ ! -f .env ]; then
        log_info "创建 .env 文件..."
        cp env.example .env
        log_success ".env 文件已创建，请根据需要修改配置"
    else
        log_warning ".env 文件已存在，跳过创建"
    fi

    # 创建必要的目录
    log_info "创建必要的目录..."
    mkdir -p logs
    mkdir -p data
    mkdir -p screenshots
    mkdir -p downloads

    log_success "环境配置完成"
}

# 测试安装
test_installation() {
    log_info "测试安装..."

    # 测试导入关键模块
    log_info "测试 Python 模块..."
    uv run python -c "
import sys
try:
    import undetected_chromedriver
    import selenium
    import pyvirtualdisplay
    from crawler import browser
    print('✅ 所有关键模块导入成功')
    sys.exit(0)
except ImportError as e:
    print(f'❌ 模块导入失败: {e}')
    sys.exit(1)
" || {
        log_error "模块测试失败"
        return 1
    }

    log_success "安装测试通过"
}

# 显示安装信息
show_info() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  安装完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}系统信息:${NC}"
    echo "  - Python: $(python3 --version | awk '{print $2}')"
    echo "  - uv: $(uv --version | awk '{print $2}')"
    echo "  - Chrome: $(google-chrome --version | awk '{print $3}')"
    echo "  - Xvfb: $(which Xvfb)"
    echo ""
    echo -e "${BLUE}下一步:${NC}"
    echo "  1. 编辑 .env 文件配置你的环境变量"
    echo -e "     ${YELLOW}nano .env${NC}"
    echo ""
    echo "  2. 激活虚拟环境"
    echo -e "     ${YELLOW}source .venv/bin/activate${NC}"
    echo ""
    echo "  3. 运行测试"
    echo -e "     ${YELLOW}uv run python test_undetected.py${NC}"
    echo ""
    echo "  4. 运行爬虫"
    echo -e "     ${YELLOW}uv run python main.py --update-mode${NC}"
    echo ""
    echo -e "${BLUE}虚拟显示模式（推荐）:${NC}"
    echo "  在 .env 中设置:"
    echo -e "     ${YELLOW}BROWSER_HEADLESS=false${NC}"
    echo -e "     ${YELLOW}BROWSER_USE_VIRTUAL_DISPLAY=true${NC}"
    echo ""
    echo -e "${BLUE}文档:${NC}"
    echo "  - README.md"
    echo "  - docs/UNDETECTED_CHROME_USAGE.md"
    echo ""
}

# 主函数
main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  PropertyGuru Crawler 安装脚本${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    check_root
    check_system

    log_info "开始安装..."
    echo ""

    # 安装步骤
    install_system_deps
    echo ""

    install_chrome
    echo ""

    check_python
    echo ""

    install_uv
    echo ""

    install_python_deps
    echo ""

    install_extra_deps
    echo ""

    setup_environment
    echo ""

    test_installation
    echo ""

    show_info
}

# 运行主函数
main "$@"
