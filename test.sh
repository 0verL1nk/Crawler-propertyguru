#!/bin/bash
# PropertyGuru爬虫测试脚本
# 分阶段测试：单个 -> 第一页 -> 十页 -> 全部

set -e

echo "=========================================="
echo "PropertyGuru爬虫测试脚本"
echo "=========================================="
echo ""

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo "❌ 错误: 配置文件 config.yaml 不存在"
    exit 1
fi

# 检查环境变量
if [ -z "$BROWSER_AUTH" ]; then
    echo "⚠️  警告: BROWSER_AUTH 环境变量未设置"
fi

echo "请选择测试模式:"
echo "1) 测试第一页的第一个房源"
echo "2) 测试第一页的所有房源"
echo "3) 测试前10页"
echo "4) 爬取全部页面"
echo "5) 自定义页面范围"
echo ""
read -p "请输入选项 (1-5): " choice

case $choice in
    1)
        echo ""
        echo "=========================================="
        echo "测试模式：爬取第一页的第一个房源"
        echo "=========================================="
        echo ""
        python main.py --test-single
        ;;
    2)
        echo ""
        echo "=========================================="
        echo "测试模式：爬取第一页的所有房源"
        echo "=========================================="
        echo ""
        python main.py --test-page
        ;;
    3)
        echo ""
        echo "=========================================="
        echo "测试模式：爬取前10页"
        echo "=========================================="
        echo ""
        python main.py --test-pages 10
        ;;
    4)
        echo ""
        echo "=========================================="
        echo "开始爬取全部页面"
        echo "=========================================="
        echo ""
        read -p "确认开始爬取全部页面？(y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            python main.py
        else
            echo "已取消"
        fi
        ;;
    5)
        read -p "请输入起始页码: " start_page
        read -p "请输入结束页码（留空表示到最后）: " end_page
        echo ""
        echo "=========================================="
        echo "开始爬取: 第 $start_page 页 - ${end_page:-全部}"
        echo "=========================================="
        echo ""
        if [ -z "$end_page" ]; then
            python main.py $start_page
        else
            python main.py $start_page $end_page
        fi
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
