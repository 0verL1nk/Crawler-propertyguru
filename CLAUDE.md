<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🏗️ High-Level Architecture

This repository contains two integrated projects for a complete property search solution:

### 1. PropertyGuru Crawler (`propertyguru-crawler/`)
A sophisticated Python-based web crawler that extracts property listings from PropertyGuru.com.sg.

**Key Features:**
- **Multi-Browser Support**: Undetected Chrome (recommended), Remote Browser, Local Browser
- **HTTP-First Architecture**: Optimized HTTP crawling with browser fallback for maximum performance
- **Dynamic Proxy Management**: Residential proxy support with automatic IP rotation
- **Database Integration**: PostgreSQL with ORM abstraction
- **Media Processing**: Integrated watermark removal and S3-compatible storage
- **Progress Tracking**: Resume capability with detailed statistics
- **Update Mode**: Incremental crawling for ongoing data collection

**Core Components:**
- `main.py` - Entry point with multiple operation modes
- `crawler.core.crawler.PropertyGuruCrawler` - Main orchestrator
- `crawler.browser.*` - Multi-browser abstraction
- `crawler.database.*` - Database operations
- `crawler.http.*` - HTTP crawling pipeline
- `crawler.storage.*` - Media storage and processing

### 2. PropertyGuru Auto Searcher (`propertyguru-auto-searcher/`)
A Go-based intelligent property search engine with AI-powered natural language processing.

**Key Features:**
- **AI-Powered Intent Parsing**: Uses OpenAI/GPT for natural language understanding
- **Hybrid Search**: Combines SQL filtering with PostgreSQL full-text search
- **Vector Similarity Search**: pgvector integration for semantic retrieval
- **Structured Validation**: Strict data structure validation for AI results
- **Hybrid Ranking**: Text relevance, price matching, and recency scoring
- **Streaming Responses**: Server-Sent Events for real-time search feedback
- **Modern Web UI**: React-based frontend with responsive design

**Core Components:**
- `cmd/server/main.go` - Application entry point
- `internal/handler/` - HTTP request handlers
- `internal/service/` - Business logic (search, intent parsing, ranking)
- `internal/repository/` - Database operations
- `internal/model/` - Data structures
- `web/` - React frontend application

## 🔄 Integration Architecture

Both components share the same PostgreSQL database with a unified schema:

```
┌─────────────────┐    writes    ┌──────────────────┐
│  Crawler        ├─────────────►│  listing_info    │
│                 │              │  listing_media   │
└─────────────────┘    reads     └─────────▲────────┘
                                          │
┌─────────────────┐    reads             │ writes
│  Search Engine  ├──────────────────────┼───────┐
│                 │              ┌───────▼───────┤
└─────────────────┘              │ search_logs   │
                                 │ user_feedback │
                                 └───────────────┘
```

**Data Flow:**
1. Crawler extracts property data → Stores in `listing_info` and `listing_media`
2. Search Engine reads from `listing_info` for queries
3. Search Engine writes to `search_logs` and `user_feedback` for analytics

## 🚀 Common Development Commands

### Crawler Project
```bash
# One-click installation (recommended)
./setup.sh

# Or manual setup
uv sync
uv pip install pyvirtualdisplay

# Run crawler in different modes
uv run python main.py --test-single          # Test single listing
uv run python main.py --test-page            # Test first page
uv run python main.py --update-mode          # Update mode (ongoing crawl)
uv run python main.py 1 100                  # Crawl pages 1-100
uv run python main.py --reset-progress       # Reset crawl progress

# Development tools
make format     # Format code
make check      # Run linting and type checking
make test       # Run tests
```

### Search Engine Project
```bash
# Quick setup
./scripts/setup.sh

# Build complete application (frontend + backend)
make build

# Development mode (separate frontend/backend)
make dev

# Run tests
make test

# Docker deployment
docker compose up -d
```

## 🐳 Docker Deployment

For easy deployment, use Docker Compose which starts both PostgreSQL and the searcher service:

```bash
# From propertyguru-auto-searcher directory
docker compose up -d

# Access services
# Web UI: http://localhost:8080
# API: http://localhost:8080/api/v1
```

## 🗄️ Database Schema

Unified PostgreSQL schema with four main tables:

1. **listing_info** - Property listings with all details (crawler writes, searcher reads)
2. **listing_media** - Property media files metadata (crawler writes)
3. **search_logs** - Search query logs (searcher writes)
4. **user_feedback** - User interaction tracking (searcher writes)

Key features:
- pgvector extension for AI embeddings
- Full-text search with GIN indexes
- Geographic coordinates indexing
- Automatic timestamp triggers
- Comprehensive indexing for performance

Initialize with: `psql -f sql/init_postgresql_unified.sql`

## 🔧 Environment Configuration

### Crawler (.env file)
Key variables:
```bash
# Browser configuration
BROWSER_TYPE=undetected
BROWSER_USE_VIRTUAL_DISPLAY=true
BROWSER_DISABLE_IMAGES=true

# Proxy configuration
PROXY_URL=http://your-proxy-url

# Database
POSTGRESQL_URI=postgresql://user:pass@host:port/db

# Image processing (optional)
WATERMARK_REMOVER_PRODUCT_SERIAL=your_serial
```

### Search Engine (.env file)
Key variables:
```bash
# Database (shared with crawler)
DATABASE_URL=postgresql://user:pass@host:port/db

# OpenAI API (required for AI features)
OPENAI_API_KEY=sk-your-api-key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_CHAT_MODEL=gpt-3.5-turbo

# Server configuration
SERVER_PORT=8080
```

## 🌐 API Endpoints

### Search Engine API
- `POST /api/v1/search` - Standard search with AI intent parsing
- `POST /api/v1/search/stream` - Streaming search with real-time results
- `GET /api/v1/listings/:id` - Get specific listing details
- `POST /api/v1/embeddings/batch` - Update vector embeddings
- `POST /api/v1/feedback` - Submit user feedback
- `GET /health` - Health check endpoint
- `GET /version` - Version information

### Example Search Request
```json
{
  "query": "3 bedroom condo near MRT under 1.5M",
  "filters": {
    "price_max": 1500000,
    "bedrooms": 3,
    "unit_type": "Condo",
    "mrt_distance_max": 1000
  },
  "options": {
    "top_k": 20,
    "semantic": true
  }
}
```

## 📈 Performance Considerations

1. **Database Optimization**:
   - Proper indexing on price, bedrooms, MRT distance
   - GIN index for full-text search
   - HNSW index for vector similarity search

2. **Crawler Efficiency**:
   - HTTP-first approach reduces browser overhead
   - Virtual display mode for headless operation
   - Image/resource disabling for faster crawling

3. **Search Engine Scalability**:
   - Connection pooling for database operations
   - Streaming responses for better UX
   - Hybrid ranking algorithm for relevance

## 🧪 Testing Strategy

1. **Crawler Testing**:
   - Unit tests for individual components
   - Integration tests for browser operations
   - HTTP pipeline testing

2. **Search Engine Testing**:
   - Go unit tests for services
   - API endpoint testing
   - Frontend component testing

Run tests with `make test` in each project directory.