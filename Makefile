.PHONY: help install install-dev lint format type-check test clean pre-commit-install pre-commit-uninstall pre-commit-run

help: ## 显示帮助信息
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install: ## 安装项目依赖
	uv sync

install-dev: ## 安装开发依赖
	uv sync --group dev

lint: ## 运行所有lint检查
	@echo "运行 ruff..."
	ruff check --fix .
	@echo "运行 flake8..."
	flake8 .
	@echo "✓ Lint检查完成"

format: ## 格式化代码
	@echo "运行 black..."
	black .
	@echo "运行 isort..."
	isort .
	@echo "运行 ruff format..."
	ruff format .
	@echo "✓ 代码格式化完成"

type-check: ## 运行类型检查
	@echo "运行 mypy..."
	mypy --python-version 3.10 crawler utils
	@echo "✓ 类型检查完成"

check: lint type-check ## 运行所有检查（lint + type-check）

test: ## 运行测试
	pytest

test-cov: ## 运行测试并生成覆盖率报告
	pytest --cov=crawler --cov=utils --cov-report=html --cov-report=term

clean: ## 清理临时文件
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	find . -type d -name ".ruff_cache" -exec rm -r {} +
	rm -rf htmlcov
	rm -rf .coverage
	@echo "✓ 清理完成"

pre-commit-install: ## 安装pre-commit hooks
	pre-commit install

pre-commit-uninstall: ## 卸载pre-commit hooks
	pre-commit uninstall

pre-commit-run: ## 手动运行pre-commit检查所有文件
	pre-commit run --all-files

all: format check test ## 运行格式化、检查和测试
