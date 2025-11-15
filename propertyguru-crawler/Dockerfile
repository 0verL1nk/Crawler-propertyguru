# PropertyGuru Crawler Dockerfile
# 使用 Ubuntu 20.04 作为基础镜像
FROM ubuntu:20.04

# 避免交互式安装
ARG DEBIAN_FRONTEND=noninteractive

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    unzip \
    software-properties-common \
    build-essential \
    xvfb \
    x11-xkb-utils \
    xfonts-100dpi \
    xfonts-75dpi \
    xfonts-scalable \
    xfonts-base \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    && rm -rf /var/lib/apt/lists/*

# 安装 Chrome 浏览器
RUN wget -q -O /tmp/google-chrome-stable_current_amd64.deb \
    https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y /tmp/google-chrome-stable_current_amd64.deb \
    && rm /tmp/google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# 创建 Python 虚拟环境
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装 uv 包管理器
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# 复制项目文件
COPY . .

# 安装 Python 依赖
RUN uv sync

# 安装额外依赖
RUN uv pip install pyvirtualdisplay

# 创建必要的目录
RUN mkdir -p logs data screenshots downloads

# 创建默认的 .env 文件（如果不存在）
RUN if [ ! -f .env ]; then cp env.example .env; fi

# 暴露端口（如果需要）
EXPOSE 8000

# 设置默认命令
CMD ["python", "main.py", "--help"]