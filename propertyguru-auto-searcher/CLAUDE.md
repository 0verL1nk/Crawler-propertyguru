# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🏗️ High-Level Architecture

This is a full-stack property search engine with AI-powered natural language processing:

1. **Frontend** (React + TypeScript + Vite):
   - Located in `web/` directory
   - Uses Ant Design X for UI components
   - Communicates with backend via REST API and Server-Sent Events (SSE) for streaming responses

2. **Backend** (Go + Gin):
   - Main entry point: `cmd/server/main.go`
   - Structured as:
     - `internal/handler/` - HTTP handlers
     - `internal/service/` - Business logic services
     - `internal/repository/` - Database operations
     - `internal/model/` - Data structures
     - `internal/config/` - Configuration management

3. **Database**:
   - PostgreSQL with pgvector extension
   - Shared with propertyguru-crawler project
   - Tables: `listing_info`, `listing_media`, `search_logs`, `user_feedback`

4. **AI Integration**:
   - OpenAI-compatible API for intent parsing
   - Supports multiple providers (OpenAI, NVIDIA, etc.)
   - Semantic search capabilities with embeddings (Phase 2)

## 🚀 Common Development Commands

### Build Commands (Makefile)
```bash
make help              # Show all available commands
make build             # Build complete application (frontend + backend)
make build-frontend    # Build frontend only
make build-backend     # Build backend only (embeds frontend)
make dev               # Development mode (separate frontend/backend)
make clean             # Clean build artifacts
make test              # Run tests
```

### Docker Operations
```bash
docker compose up -d   # Start all services (PostgreSQL + searcher)
docker compose logs -f searcher  # View searcher logs
docker compose down    # Stop all services
```

### Local Development
```bash
# Backend
go run cmd/server/main.go

# Frontend (in web/ directory)
npm run dev
```

### Testing
```bash
# Run Go tests
go test ./...

# Test API endpoint
curl http://localhost:8080/health
```

## 📁 Project Structure Overview

```
propertyguru-auto-searcher/
├── cmd/server/           # Application entry point
├── internal/             # Core Go code
│   ├── config/           # Configuration loading
│   ├── handler/          # HTTP handlers
│   ├── service/          # Business logic
│   ├── repository/       # Database operations
│   └── model/            # Data structures
├── web/                  # Frontend React app
│   ├── src/              # TypeScript source
│   │   └── components/   # React components
│   └── dist/             # Built frontend assets
├── sql/                  # Database initialization scripts
├── build/                # Compiled binaries
└── docker-compose.yml    # Docker configuration
```

## 🔧 Key Configuration Files

1. **Environment Variables** (`.env` or environment):
   - `DATABASE_URL` - PostgreSQL connection string
   - `OPENAI_API_KEY` - Required for AI features
   - `SERVER_PORT` - Service port (default 8080)

2. **Configuration Loading**:
   - `internal/config/config.go` loads from environment variables
   - Supports .env file via godotenv

## 🌐 API Endpoints

### Search
- `POST /api/v1/search` - Standard search (returns search parameters and metadata)
- `POST /api/v1/search/results` - Paginated search results
- `POST /api/v1/search/stream` - Streaming search with SSE

### Other
- `GET /api/v1/listings/:id` - Get specific listing
- `POST /api/v1/embeddings/batch` - Update embeddings (Phase 2)
- `POST /api/v1/feedback` - Submit user feedback
- `GET /health` - Health check
- `GET /version` - Version information

## 🐳 Docker Deployment

The application can be deployed using Docker Compose which starts both PostgreSQL and the searcher service:

1. `docker compose up -d` - Start all services
2. Access web UI at http://localhost:8080
3. Access API at http://localhost:8080/api/v1

## ⚡ Performance Considerations

1. **Database Indexes**:
   - Price, bedrooms, MRT distance indexes for filtering
   - GIN index for full-text search
   - HNSW index for vector similarity search

2. **Connection Pooling**:
   - Configurable PostgreSQL connection pool
   - Proper resource cleanup with defer statements

3. **Caching**:
   - HTTP caching headers for static assets
   - Connection reuse for database and AI services

## 🧪 Testing Strategy

1. **Unit Tests**:
   - Go tests in respective packages
   - JSON parsing utilities tested separately

2. **Integration Tests**:
   - Manual API testing with curl
   - Docker-based testing environment

3. **Frontend Testing**:
   - Manual UI testing
   - Component-based development
- 使用make build构建前后端