# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a sophisticated property listing crawler for PropertyGuru.com.sg, built with Python and supporting multiple browser technologies, proxy configurations, database storage options, and media processing capabilities. It features a hybrid HTTP-first approach with browser fallback for optimal performance and reliability.

## Key Features

- **Multi-Browser Support**: Undetected Chrome (recommended), Remote Browser (Bright Data), Local Browser, Puppeteer/Playwright
- **HTTP-First Architecture**: Optimized HTTP crawling with browser fallback for maximum performance
- **Multiple Database Support**: MySQL and PostgreSQL with ORM abstraction
- **Proxy Management**: Dynamic residential proxy support with automatic IP rotation
- **Media Processing Pipeline**: Integrated watermark removal and S3-compatible storage
- **Progress Tracking**: Resume capability with detailed statistics
- **Update Mode**: Incremental crawling for ongoing data collection
- **Geographic Encoding**: Location-based coordinate mapping
- **Flexible Configuration**: YAML config with environment variable overrides

## Development Commands

### Setup & Installation
```bash
# One-click installation (recommended)
./setup.sh

# Or manual setup with uv
uv sync
uv pip install pyvirtualdisplay

# Activate virtual environment
source .venv/bin/activate
```

### Environment Configuration
Copy and configure the environment file:
```bash
cp env.example .env
```

Key configuration options:
- BROWSER_TYPE: undetected (recommended), remote, local, puppeteer
- DB_TYPE: mysql or postgresql
- USE_HTTP_CRAWLER: true (recommended for performance)
- HTTP_PROVIDER: direct, zenrows, scraperapi, oxylabs

### Running the Crawler
```bash
# Test single listing
uv run python main.py --test-single

# Test single page
uv run python main.py --test-page

# Normal crawl mode
uv run python main.py 1 10          # Crawl pages 1-10
uv run python main.py 1             # Crawl from page 1 to end

# Update mode (recommended for ongoing crawling)
uv run python main.py --update-mode --interval 10  # Every 10 minutes
uv run python main.py --update-mode --interval 0   # Run once

# Reset progress
uv run python main.py --reset-progress
```

### Development Tools
```bash
# Code formatting
make format

# Linting and type checking
make check
make lint
make type-check

# Testing
make test
make test-cov

# Pre-commit hooks
make pre-commit-install
make pre-commit-run
```

## Architecture Overview

### Core Components

1. **crawler.core.crawler.py** - Main crawler orchestrator (`PropertyGuruCrawler`)
2. **crawler.browser.factory.py** - Multi-browser abstraction factory
3. **crawler.database.factory.py** - Database abstraction factory
4. **crawler.pages.factory.py** - HTTP page crawling factory
5. **crawler.http.client.py** - HTTP client with provider abstraction
6. **crawler.storage.manager.py** - Media storage and processing pipeline
7. **crawler.utils.progress_manager.py** - Progress tracking with resume capability

### Database Layer
- Uses SQLAlchemy ORM with support for MySQL and PostgreSQL
- Implements buffered writes for performance
- Schema defined in `crawler/database/orm_models.py`
- Factory pattern in `crawler/database/factory.py` for DB initialization

### Browser Abstraction
Supports multiple browser modes:
- **UndetectedBrowser**: Enhanced anti-detection capabilities (recommended)
- **RemoteBrowser**: Bright Data scraping browser (Playwright implementation)
- **PyppeteerBrowserNew**: Default remote browser (Pyppeteer/CDP)
- **LocalBrowser**: Standard local Chrome for testing
- **PuppeteerRemoteBrowser**: Legacy Puppeteer-based remote browser

### HTTP Provider Abstraction
Supports multiple HTTP providers for bypassing anti-bot protection:
- **DirectHttpProvider**: Direct HTTP requests (no proxy)
- **ZenRowsHttpProvider**: ZenRows proxy service
- **ScraperApiHttpProvider**: ScraperAPI proxy service
- **OxylabsHttpProvider**: Oxylabs proxy service

### Data Flow
1. Initialize components (browser, database, storage)
2. Navigate to listing pages (HTTP-first approach)
3. Parse basic listing information from `__NEXT_DATA__` JSON
4. For each listing, navigate to detail page (HTTP-first with browser fallback)
5. Extract comprehensive property details
6. Process and store media assets
7. Save all data to database with completion tracking

### Progress Tracking
- Uses `crawl_progress.json` to track completed listings/pages
- Automatically resumes from last position
- Supports manual reset with `--reset-progress`

## Testing
Tests are located in the `tests/` directory. Run with:
```bash
make test
```

Key test categories:
- Browser functionality
- Proxy handling
- Watermark removal
- Database operations
- HTTP provider integration

## Important Notes

1. **HTTP-First Approach**: The crawler prioritizes HTTP requests for performance, falling back to browser-based crawling only when necessary. Enable with `USE_HTTP_CRAWLER=true` and `USE_HTTP_DETAIL_CRAWLER=true`.

2. **Proxy Configuration**: For production use, configure residential proxies (Bright Data) for reliable large-scale crawling. Set `PROXY_URL` in environment variables.

3. **Database Selection**: PostgreSQL is recommended for production deployments. Configure with `DB_TYPE=postgresql` and appropriate connection settings.

4. **Anti-Detection**: For evading bot detection, use `BROWSER_TYPE=undetected` with virtual display mode (`BROWSER_USE_VIRTUAL_DISPLAY=true`).

5. **Media Processing**: Configure watermark removal service credentials in environment variables for image processing capabilities.

6. **Performance Optimization**: Disable image loading (`BROWSER_DISABLE_IMAGES=true`) and use appropriate concurrency settings in config.yaml.

7. **Code Quality**: Follow established patterns with pre-commit hooks, type checking, and comprehensive testing before committing changes.