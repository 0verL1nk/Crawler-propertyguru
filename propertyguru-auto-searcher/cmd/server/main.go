package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"core/internal/config"
	"core/internal/handler"
	"core/internal/repository"
	"core/internal/service"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

var (
	Version   = "dev"
	BuildTime = "unknown"
	GitCommit = "unknown"
)

// performAIHealthCheck performs a basic health check on the AI service
func performAIHealthCheck(client *service.OpenAIClient, model string) error {
	if client == nil || !client.IsEnabled() {
		return fmt.Errorf("AI client is not enabled")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// Test basic chat completion
	request := service.ChatCompletionRequest{
		Model: model,
		Messages: []service.ChatMessage{
			{Role: "user", Content: "Hello, this is a health check. Please respond with 'OK'."},
		},
		Temperature: 0.1,
		MaxTokens:   10,
	}

	response, err := client.ChatCompletion(ctx, request)
	if err != nil {
		return fmt.Errorf("chat completion test failed: %w", err)
	}

	if len(response.Choices) == 0 || response.Choices[0].Message.Content == "" {
		return fmt.Errorf("received empty response from AI service")
	}

	log.Printf("   🤖 AI service response: %s", response.Choices[0].Message.Content)
	return nil
}

func main() {
	// Print version info
	log.Printf("PropertyGuru Auto Searcher")
	log.Printf("Version: %s", Version)
	log.Printf("Build Time: %s", BuildTime)
	log.Printf("Git Commit: %s", GitCommit)
	log.Println("")

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Set Gin mode
	gin.SetMode(cfg.Server.GinMode)

	// Initialize database connection
	repo, err := repository.NewPostgresRepository(
		cfg.GetPostgreSQLDSN(),
		cfg.PostgreSQL.MaxConnections,
		cfg.PostgreSQL.MaxIdleConnections,
	)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer repo.Close()

	log.Println("✅ Connected to PostgreSQL database")

	// Initialize OpenAI client
	var openaiClient *service.OpenAIClient
	if cfg.OpenAI.Enabled {
		openaiClient = service.NewOpenAIClient(&cfg.OpenAI)
		log.Printf("✅ OpenAI client initialized")
		log.Printf("   - API Base: %s", cfg.OpenAI.APIBase)
		log.Printf("   - Chat model: %s", cfg.OpenAI.ChatModel)
		log.Printf("   - Embedding model: %s", cfg.OpenAI.EmbeddingModel)
		log.Printf("   - Chat Temperature: %.2f", cfg.OpenAI.ChatTemperature)
		log.Printf("   - Chat TopP: %.2f", cfg.OpenAI.ChatTopP)
		log.Printf("   - Chat MaxTokens: %d", cfg.OpenAI.ChatMaxTokens)
		log.Printf("   - Chat ExtraBody: %s", cfg.OpenAI.ChatExtraBody)
		log.Printf("   - Embedding ExtraBody: %s", cfg.OpenAI.EmbeddingExtraBody)

		// Perform health check on AI service
		if err := performAIHealthCheck(openaiClient, cfg.OpenAI.ChatModel); err != nil {
			log.Printf("⚠️  AI health check failed: %v", err)
			log.Println("   AI-powered features may not work properly")
		} else {
			log.Println("✅ AI service health check passed")
		}
	} else {
		log.Println("⚠️  OpenAI is disabled - AI-powered search intent parsing will not work")
		log.Println("   Set OPENAI_API_KEY environment variable to enable AI features")
	}

	// Initialize services
	intentParser := service.NewIntentParser(openaiClient)
	ranker := service.NewRanker(
		cfg.Ranking.WeightText,
		cfg.Ranking.WeightPrice,
		cfg.Ranking.WeightRecency,
	)
	searchService := service.NewSearchService(repo, intentParser, ranker)

	log.Println("✅ Services initialized")

	// Initialize handlers
	searchHandler := handler.NewSearchHandler(searchService, cfg.Search.DefaultLimit, cfg.Search.MaxLimit)
	embeddingHandler := handler.NewEmbeddingHandler(searchService)
	feedbackHandler := handler.NewFeedbackHandler(searchService)

	// Setup Gin router
	router := gin.Default()

	// CORS configuration
	corsConfig := cors.DefaultConfig()
	corsConfig.AllowOrigins = []string{cfg.Server.AllowedOrigins}
	corsConfig.AllowMethods = []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"}
	corsConfig.AllowHeaders = []string{"Content-Type", "Authorization"}
	router.Use(cors.New(corsConfig))

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":     "healthy",
			"service":    "property-search-engine",
			"version":    Version,
			"build_time": BuildTime,
			"git_commit": GitCommit,
		})
	})

	// Version endpoint
	router.GET("/version", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"version":    Version,
			"build_time": BuildTime,
			"git_commit": GitCommit,
		})
	})

	// API routes
	apiV1 := router.Group("/api/v1")
	{
		// Search endpoints
		apiV1.POST("/search", searchHandler.Search)
		apiV1.POST("/search/results", searchHandler.SearchResults) // Paginated search results
		apiV1.POST("/search/stream", searchHandler.SearchStream) // Streaming search
		apiV1.GET("/listings/:id", searchHandler.GetListing)

		// Embedding endpoints
		apiV1.POST("/embeddings/batch", embeddingHandler.BatchUpdate)

		// Feedback endpoint
		apiV1.POST("/feedback", feedbackHandler.Submit)
	}

	// Serve static files (frontend)
	// This function is implemented in embed.go (production) or static_dev.go (development)
	setupStaticFiles(router)

	// Start server
	addr := fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port)
	log.Printf("🚀 Starting server on %s", addr)
	log.Printf("📝 API Documentation: http://localhost:%d/api/v1", cfg.Server.Port)
	log.Printf("🌐 Web UI: http://localhost:%d", cfg.Server.Port)

	// Graceful shutdown
	go func() {
		if err := router.Run(addr); err != nil {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("🛑 Shutting down server...")
	log.Println("✅ Server stopped")
}
