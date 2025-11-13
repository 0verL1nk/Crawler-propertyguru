# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a sophisticated property listing crawler for PropertyGuru.com.sg, built with Python and Selenium/Playwright. It supports multiple browsers, proxy configurations, database storage (MySQL/PostgreSQL), media processing with watermark removal, and geographic encoding.

## Key Features

- Multi-browser support: Undetected Chrome (recommended), Remote Browser (Bright Data), Local Browser, Puppeteer/Playwright
- Proxy management with residential/IP rotation support
- Database abstraction layer supporting MySQL and PostgreSQL with ORM models
- Media processing pipeline with optional watermark removal
- Geographic encoding capabilities
- Progress tracking with resume capability
- Update mode for incremental crawling
- Comprehensive data parsing for property listings

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
- PROXY_URL: For residential proxy integration
- DB_TYPE: mysql or postgresql
- WATERMARK_REMOVER_*: For image processing

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
2. **crawler.browser.browser.py** - Multi-browser abstraction layer
3. **crawler.database** - Database abstraction with factory pattern
4. **crawler.parsers.parsers.py** - Page parsing logic for listings and details
5. **crawler.models.listing.py** - Data models for listings, properties, and media
6. **crawler.storage** - Media storage and processing pipeline
7. **crawler.utils** - Utility modules including progress tracking and proxy management

### Database Layer
- Uses SQLAlchemy ORM with support for MySQL and PostgreSQL
- Implements buffered writes for performance
- Schema defined in `crawler.database.orm_models.py`
- Factory pattern in `crawler.database.factory.py` for DB initialization

### Browser Abstraction
Supports four browser modes:
- **UndetectedBrowser**: Enhanced anti-detection capabilities
- **RemoteBrowser**: Bright Data scraping browser
- **LocalBrowser**: Standard local Chrome for testing
- **PuppeteerRemoteBrowser**: Playwright-based remote browser

### Data Flow
1. Initialize components (browser, database, storage)
2. Navigate to listing pages
3. Parse basic listing information
4. For each listing, navigate to detail page
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