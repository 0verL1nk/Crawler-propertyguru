package config

import (
	"fmt"
	"log"
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

// Config holds all configuration for the application
type Config struct {
	PostgreSQL PostgreSQLConfig
	Server     ServerConfig
	Search     SearchConfig
	Ranking    RankingConfig
	Logging    LoggingConfig
	OpenAI     OpenAIConfig
}

// PostgreSQLConfig holds PostgreSQL database configuration
type PostgreSQLConfig struct {
	DSN                string // 完整的数据库连接字符串（优先使用）
	Host               string
	Port               int
	User               string
	Password           string
	Database           string
	SSLMode            string
	MaxConnections     int
	MaxIdleConnections int
}

// ServerConfig holds server configuration
type ServerConfig struct {
	Port           int
	Host           string
	GinMode        string
	AllowedOrigins string
	AllowedMethods string
	AllowedHeaders string
}

// SearchConfig holds search-related configuration
type SearchConfig struct {
	DefaultLimit  int
	MaxLimit      int
	DefaultOffset int
}

// RankingConfig holds ranking weights configuration
type RankingConfig struct {
	WeightText    float64
	WeightPrice   float64
	WeightRecency float64
}

// LoggingConfig holds logging configuration
type LoggingConfig struct {
	Level  string
	Format string
}

// OpenAIConfig holds OpenAI API configuration
type OpenAIConfig struct {
	APIKey              string
	APIBase             string
	ChatModel           string // Model for chat/intent parsing
	ChatTemperature     float64
	ChatTopP            float64
	ChatMaxTokens       int
	ChatExtraBody       string // JSON string for extra_body (e.g., {"chat_template_kwargs":{"thinking":true}})
	EmbeddingModel      string // Model for embeddings
	EmbeddingDimensions int
	EmbeddingExtraBody  string // JSON string for extra_body (e.g., {"truncate":"NONE"})
	BatchSize           int
	Timeout             int
	Enabled             bool
}

// Load reads configuration from environment variables
func Load() (*Config, error) {
	// Try to load .env file (optional)
	_ = godotenv.Load()

	cfg := &Config{
		PostgreSQL: PostgreSQLConfig{
			// 优先使用完整的 DSN (DATABASE_URL, POSTGRESQL_URI, PG_DSN)
			DSN:                getEnv("DATABASE_URL", getEnv("POSTGRESQL_URI", getEnv("PG_DSN", ""))),
			Host:               getEnv("PG_HOST", "localhost"),
			Port:               getEnvAsInt("PG_PORT", 5432),
			User:               getEnv("PG_USER", "postgres"),
			Password:           getEnv("PG_PASSWORD", ""),
			Database:           getEnv("PG_DATABASE", "property_search"),
			SSLMode:            getEnv("PG_SSLMODE", "disable"),
			MaxConnections:     getEnvAsInt("PG_MAX_CONNECTIONS", 25),
			MaxIdleConnections: getEnvAsInt("PG_MAX_IDLE_CONNECTIONS", 5),
		},
		Server: ServerConfig{
			Port:           getEnvAsInt("SERVER_PORT", 8080),
			Host:           getEnv("SERVER_HOST", "0.0.0.0"),
			GinMode:        getEnv("GIN_MODE", "release"),
			AllowedOrigins: getEnv("CORS_ALLOWED_ORIGINS", "*"),
			AllowedMethods: getEnv("CORS_ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS"),
			AllowedHeaders: getEnv("CORS_ALLOWED_HEADERS", "Content-Type,Authorization"),
		},
		Search: SearchConfig{
			DefaultLimit:  getEnvAsInt("SEARCH_DEFAULT_LIMIT", 20),
			MaxLimit:      getEnvAsInt("SEARCH_MAX_LIMIT", 100),
			DefaultOffset: getEnvAsInt("SEARCH_DEFAULT_OFFSET", 0),
		},
		Ranking: RankingConfig{
			WeightText:    getEnvAsFloat("RANK_WEIGHT_TEXT", 0.5),
			WeightPrice:   getEnvAsFloat("RANK_WEIGHT_PRICE", 0.3),
			WeightRecency: getEnvAsFloat("RANK_WEIGHT_RECENCY", 0.2),
		},
		Logging: LoggingConfig{
			Level:  getEnv("LOG_LEVEL", "info"),
			Format: getEnv("LOG_FORMAT", "json"),
		},
		OpenAI: OpenAIConfig{
			APIKey:              getEnv("OPENAI_API_KEY", ""),
			APIBase:             getEnv("OPENAI_API_BASE", "https://integrate.api.nvidia.com/v1"),
			ChatModel:           getEnv("OPENAI_CHAT_MODEL", "deepseek-ai/deepseek-v3.1-terminus"),
			ChatTemperature:     getEnvAsFloat("OPENAI_CHAT_TEMPERATURE", 0.2),
			ChatTopP:            getEnvAsFloat("OPENAI_CHAT_TOP_P", 0.7),
			ChatMaxTokens:       getEnvAsInt("OPENAI_CHAT_MAX_TOKENS", 8192),
			ChatExtraBody:       getEnv("OPENAI_CHAT_EXTRA_BODY", `{"chat_template_kwargs":{"thinking":true}}`),
			EmbeddingModel:      getEnv("OPENAI_EMBEDDING_MODEL", "baai/bge-m3"),
			EmbeddingDimensions: getEnvAsInt("OPENAI_EMBEDDING_DIMENSIONS", 1024),
			EmbeddingExtraBody:  getEnv("OPENAI_EMBEDDING_EXTRA_BODY", `{"truncate":"NONE"}`),
			BatchSize:           getEnvAsInt("OPENAI_BATCH_SIZE", 100),
			Timeout:             getEnvAsInt("OPENAI_TIMEOUT", 30),
			Enabled:             getEnv("OPENAI_API_KEY", "") != "",
		},
	}

	return cfg, nil
}

// GetPostgreSQLDSN returns PostgreSQL connection string
func (c *Config) GetPostgreSQLDSN() string {
	// 优先使用完整的 DSN
	if c.PostgreSQL.DSN != "" {
		return c.PostgreSQL.DSN
	}

	// 否则从各个字段组装 DSN
	return fmt.Sprintf(
		"host=%s port=%d user=%s password=%s dbname=%s sslmode=%s",
		c.PostgreSQL.Host,
		c.PostgreSQL.Port,
		c.PostgreSQL.User,
		c.PostgreSQL.Password,
		c.PostgreSQL.Database,
		c.PostgreSQL.SSLMode,
	)
}

// Helper functions

func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}

func getEnvAsInt(key string, defaultValue int) int {
	valueStr := os.Getenv(key)
	if valueStr == "" {
		return defaultValue
	}
	value, err := strconv.Atoi(valueStr)
	if err != nil {
		log.Printf("Warning: Invalid integer value for %s, using default %d", key, defaultValue)
		return defaultValue
	}
	return value
}

func getEnvAsFloat(key string, defaultValue float64) float64 {
	valueStr := os.Getenv(key)
	if valueStr == "" {
		return defaultValue
	}
	value, err := strconv.ParseFloat(valueStr, 64)
	if err != nil {
		log.Printf("Warning: Invalid float value for %s, using default %f", key, defaultValue)
		return defaultValue
	}
	return value
}
