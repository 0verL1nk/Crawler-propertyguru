package service

import (
	"context"
)

// AIClient is the interface for AI service providers
type AIClient interface {
	// ParseIntentWithAI parses user query into structured intent (non-streaming)
	ParseIntentWithAI(ctx context.Context, query string) (*AIIntentResponse, error)

	// ParseIntentWithAIStream parses user query with streaming support
	// The callback receives (thinkingContent, regularContent) for each chunk
	ParseIntentWithAIStream(ctx context.Context, query string, callback func(thinking, content string) error) (*AIIntentResponse, error)

	// CreateEmbeddings generates embeddings for texts
	CreateEmbeddings(ctx context.Context, texts []string) ([][]float32, error)

	// IsEnabled returns whether the AI client is configured and ready
	IsEnabled() bool
}

// StreamChunk represents a generic streaming response chunk
type StreamChunk struct {
	// Regular content (always present in streaming)
	Content string

	// Thinking/reasoning content (provider-specific, e.g., DeepSeek)
	ThinkingContent string

	// Role (assistant, user, system)
	Role string

	// Whether this is the final chunk
	Done bool

	// Provider-specific metadata
	Metadata map[string]interface{}
}

// AIIntentResponse represents the parsed intent from AI
type AIIntentResponse struct {
	PriceMin        *float64 `json:"price_min,omitempty"`
	PriceMax        *float64 `json:"price_max,omitempty"`
	Bedrooms        *int     `json:"bedrooms,omitempty"`
	Bathrooms       *int     `json:"bathrooms,omitempty"`
	AreaSqftMin     *float64 `json:"area_sqft_min,omitempty"`    // 最小面积（平方英尺）
	AreaSqftMax     *float64 `json:"area_sqft_max,omitempty"`    // 最大面积（平方英尺）
	UnitType        *string  `json:"unit_type,omitempty"`
	Location        *string  `json:"location,omitempty"`
	MRTDistanceMax  *int     `json:"mrt_distance_max,omitempty"`
	BuildYearMin    *int     `json:"build_year_min,omitempty"`
	Amenities       []string `json:"amenities,omitempty"`        // 房源设施需求
	Facilities      []string `json:"facilities,omitempty"`       // 公共设施需求
	Keywords        []string `json:"keywords,omitempty"`
	Confidence      float64  `json:"confidence,omitempty"`
	ThinkingProcess string   `json:"thinking_process,omitempty"` // Full thinking process
}

// Ensure OpenAIClient implements AIClient
var _ AIClient = (*OpenAIClient)(nil)
