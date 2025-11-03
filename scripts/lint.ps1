# Lint脚本 - 运行所有代码质量检查 (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "🔍 开始代码质量检查..." -ForegroundColor Cyan
Write-Host ""

# 检查ruff
Write-Host "[1/4] 运行 ruff 检查..." -ForegroundColor Yellow
try {
    ruff check .
    Write-Host "✓ Ruff 检查通过" -ForegroundColor Green
} catch {
    Write-Host "✗ Ruff 检查失败" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 检查flake8
Write-Host "[2/4] 运行 flake8 检查..." -ForegroundColor Yellow
try {
    flake8 .
    Write-Host "✓ Flake8 检查通过" -ForegroundColor Green
} catch {
    Write-Host "✗ Flake8 检查失败" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 类型检查
Write-Host "[3/4] 运行 mypy 类型检查..." -ForegroundColor Yellow
try {
    mypy crawler utils --ignore-missing-imports
    Write-Host "✓ Mypy 类型检查通过" -ForegroundColor Green
} catch {
    Write-Host "✗ Mypy 类型检查失败" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 导入排序检查
Write-Host "[4/4] 检查导入排序..." -ForegroundColor Yellow
try {
    isort --check-only --profile black .
    Write-Host "✓ 导入排序检查通过" -ForegroundColor Green
} catch {
    Write-Host "⚠ 导入排序需要调整，运行 'make format' 自动修复" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "✅ 所有检查完成！" -ForegroundColor Green

