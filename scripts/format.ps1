# 格式化脚本 - 自动格式化代码 (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "🎨 开始格式化代码..." -ForegroundColor Cyan
Write-Host ""

# 运行black
Write-Host "[1/4] 运行 black..." -ForegroundColor Yellow
black .
Write-Host "✓ Black 完成" -ForegroundColor Green
Write-Host ""

# 运行isort
Write-Host "[2/4] 运行 isort..." -ForegroundColor Yellow
isort --profile black .
Write-Host "✓ Isort 完成" -ForegroundColor Green
Write-Host ""

# 运行ruff format
Write-Host "[3/4] 运行 ruff format..." -ForegroundColor Yellow
ruff format .
Write-Host "✓ Ruff format 完成" -ForegroundColor Green
Write-Host ""

# 运行ruff fix
Write-Host "[4/4] 运行 ruff fix..." -ForegroundColor Yellow
ruff check --fix .
Write-Host "✓ Ruff fix 完成" -ForegroundColor Green
Write-Host ""

Write-Host "✅ 代码格式化完成！" -ForegroundColor Green

