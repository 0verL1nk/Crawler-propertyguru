#!/bin/bash
# 修复 Xvfb 权限问题（WSL2 常见问题）

set -e

echo "修复 Xvfb 权限问题..."

# 1. 修复 /tmp/.X11-unix 目录权限
echo "1. 修复 /tmp/.X11-unix 权限..."
if [ -d /tmp/.X11-unix ]; then
    sudo chmod 1777 /tmp/.X11-unix
    echo "✓ 权限已修复"
else
    sudo mkdir -p /tmp/.X11-unix
    sudo chmod 1777 /tmp/.X11-unix
    echo "✓ 目录已创建并设置权限"
fi

# 2. 清理可能存在的 Xvfb 进程
echo "2. 清理旧的 Xvfb 进程..."
if pgrep Xvfb > /dev/null; then
    sudo pkill Xvfb || true
    sleep 1
    echo "✓ 旧进程已清理"
else
    echo "✓ 没有运行中的 Xvfb 进程"
fi

# 3. 清理锁文件
echo "3. 清理 X11 锁文件..."
sudo rm -f /tmp/.X*-lock 2>/dev/null || true
sudo rm -f /tmp/.X11-unix/X* 2>/dev/null || true
echo "✓ 锁文件已清理"

echo ""
echo "✅ 修复完成！现在可以尝试运行爬虫了。"
echo ""
echo "提示：如果仍有问题，可以尝试直接使用有头模式（不使用虚拟显示）："
echo "  BROWSER_USE_VIRTUAL_DISPLAY=false"
