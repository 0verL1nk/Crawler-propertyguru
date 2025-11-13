# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The PropertyGuru Auto Searcher is a sophisticated real estate search engine built with Go, PostgreSQL, and AI integration. It enables natural language property searches with semantic understanding powered by OpenAI-compatible APIs.

Architecture:
- Backend: Go with Gin framework
- Frontend: React with TypeScript/Vite and Ant Design
- Database: PostgreSQL with pgvector extension
- AI Integration: OpenAI-compatible API for natural language processing

## Key Components

### Backend Services
- Search Service: Handles property searches with filtering and ranking
- Intent Parser: Converts natural language queries to structured filters using AI
- Ranker: Scores and sorts results using hybrid ranking (text relevance, price match, recency)
- Database Repository: Manages PostgreSQL interactions

### Frontend
- React-based web interface using Ant Design components
- Real-time streaming search with AI thinking visualization
- Property cards with detailed information and matching reasons

## Development Commands

### Build Commands (using Makefile)
```bash
make help          # Show all available commands
make build         # Build complete application (frontend + backend)
make dev           # Development mode (separate frontend/backend servers)
make test          # Run tests
make clean         # Clean build artifacts
```

### Manual Build Commands
```bash
# Build frontend
cd web && npm install && npm run build

# Build backend (with embedded frontend)
go build -o searcher cmd/server/main.go

# Run development servers
go run cmd/server/main.go        # Backend server
cd web && npm run dev           # Frontend dev server
```

### Testing
```bash
make test                       # Run all tests
go test ./...                   # Run Go tests
```

## Deployment

### Docker Deployment (Recommended)
```bash
docker compose up -d            # Start all services
docker compose logs -f searcher # View logs
```

### Configuration
The application is configured through environment variables. Key variables:
- DATABASE_URL: PostgreSQL connection string
- OPENAI_API_KEY: API key for AI intent parsing
- SERVER_PORT: Port to run the server on (default 8080)

See config.example.env for all available configuration options.

## API Endpoints

Main endpoints:
- POST /api/v1/search: Main search endpoint with natural language processing
- POST /api/v1/search/stream: Streaming search with real-time AI thinking visualization
- GET /api/v1/listings/:id: Retrieve specific property details
- POST /api/v1/embeddings/batch: Update property embeddings (Phase 2)
- POST /api/v1/feedback: Record user interactions

Health and monitoring:
- GET /health: Service health check
- GET /version: Version information

## Project Structure

```
propertyguru-auto-searcher/
├── cmd/server/                 # Application entry point
├── internal/                   # Core application code
│   ├── config/                 # Configuration management
│   ├── handler/                # HTTP handlers
│   ├── service/                # Business logic services
│   ├── model/                  # Data models
│   └── repository/             # Database repository
├── web/                        # Frontend React application
├── sql/                        # Database initialization scripts
├── Dockerfile                  # Docker build configuration
├── docker-compose.yml          # Multi-service deployment
├── Makefile                    # Build automation
└── go.mod                      # Go module dependencies
```

## Key Design Patterns

- Dependency Injection: Services are injected into handlers
- Repository Pattern: Database operations abstracted through repository
- Configuration Management: Centralized environment-based configuration
- Structured Logging: JSON-formatted logs with contextual information
- Graceful Shutdown: Proper cleanup on service termination