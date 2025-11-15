package service

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"

	"core/internal/config"
	"core/internal/utils"
)

// StreamChunkParser is the interface for provider-specific chunk parsing
type StreamChunkParser interface {
	ParseChunk(data []byte) (*StreamChunk, error)
}

// OpenAIClient handles OpenAI-compatible API interactions
type OpenAIClient struct {
	config      *config.OpenAIConfig
	httpClient  *http.Client
	chunkParser StreamChunkParser // Provider-specific chunk parser
}

// NewOpenAIClient creates a new OpenAI-compatible client with auto-detection of provider
func NewOpenAIClient(cfg *config.OpenAIConfig) *OpenAIClient {
	// Auto-detect provider based on base URL
	var parser StreamChunkParser
	if IsNVIDIAProvider(cfg.APIBase) {
		parser = &NVIDIAStreamChunkParser{}
		log.Printf("🔧 Detected NVIDIA API provider (supports reasoning/thinking)")
	} else if IsOpenAIProvider(cfg.APIBase) {
		parser = &OpenAIStreamChunkParser{}
		log.Printf("🔧 Detected OpenAI API provider")
	} else {
		// Default to OpenAI format for unknown providers
		parser = &OpenAIStreamChunkParser{}
		log.Printf("🔧 Using standard OpenAI format for: %s", cfg.APIBase)
	}

	return &OpenAIClient{
		config:      cfg,
		chunkParser: parser,
		httpClient: &http.Client{
			Timeout: time.Duration(cfg.Timeout) * time.Second,
		},
	}
}

// IsEnabled returns whether the client is configured and ready
func (c *OpenAIClient) IsEnabled() bool {
	return c.config.Enabled
}

// ChatCompletionRequest represents a chat completion request
type ChatCompletionRequest struct {
	Model          string          `json:"model"`
	Messages       []ChatMessage   `json:"messages"`
	Temperature    float64         `json:"temperature,omitempty"`
	TopP           float64         `json:"top_p,omitempty"` // For DeepSeek/NVIDIA API
	MaxTokens      int             `json:"max_tokens,omitempty"`
	ResponseFormat *ResponseFormat `json:"response_format,omitempty"`
	Stream         bool            `json:"stream,omitempty"`     // For streaming responses
	ExtraBody      map[string]any  `json:"extra_body,omitempty"` // For DeepSeek: {"chat_template_kwargs": {"thinking":True}}
}

// ChatMessage represents a single message in the conversation
type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ResponseFormat specifies the format of the response
type ResponseFormat struct {
	Type string `json:"type"` // "json_object" or "text"
}

// ChatCompletionResponse represents the API response
type ChatCompletionResponse struct {
	ID      string `json:"id"`
	Object  string `json:"object"`
	Created int64  `json:"created"`
	Model   string `json:"model"`
	Choices []struct {
		Index        int         `json:"index"`
		Message      ChatMessage `json:"message"`
		FinishReason string      `json:"finish_reason"`
	} `json:"choices"`
	Usage struct {
		PromptTokens     int `json:"prompt_tokens"`
		CompletionTokens int `json:"completion_tokens"`
		TotalTokens      int `json:"total_tokens"`
	} `json:"usage"`
}

// StreamCallback is called for each chunk in streaming mode
// Generic callback that works with all providers
type StreamCallback func(chunk *StreamChunk) error

// EmbeddingRequest represents an embedding request
type EmbeddingRequest struct {
	Model          string         `json:"model"`
	Input          []string       `json:"input"`
	Dimensions     int            `json:"dimensions,omitempty"`
	EncodingFormat string         `json:"encoding_format,omitempty"` // For NVIDIA API: "float"
	ExtraBody      map[string]any `json:"extra_body,omitempty"`      // For NVIDIA API: {"truncate": "NONE"}
}

// EmbeddingResponse represents the embedding API response
type EmbeddingResponse struct {
	Object string `json:"object"`
	Data   []struct {
		Object    string    `json:"object"`
		Embedding []float32 `json:"embedding"`
		Index     int       `json:"index"`
	} `json:"data"`
	Model string `json:"model"`
	Usage struct {
		PromptTokens int `json:"prompt_tokens"`
		TotalTokens  int `json:"total_tokens"`
	} `json:"usage"`
}

// ChatCompletion performs a chat completion request
func (c *OpenAIClient) ChatCompletion(ctx context.Context, req ChatCompletionRequest) (*ChatCompletionResponse, error) {
	if !c.config.Enabled {
		return nil, fmt.Errorf("OpenAI API is not enabled (missing API key)")
	}

	// Use configured model if not specified
	if req.Model == "" {
		req.Model = c.config.ChatModel
	}

	// Apply default parameters from config
	if req.Temperature == 0 && c.config.ChatTemperature > 0 {
		req.Temperature = c.config.ChatTemperature
	}
	if req.TopP == 0 && c.config.ChatTopP > 0 {
		req.TopP = c.config.ChatTopP
	}
	if req.MaxTokens == 0 && c.config.ChatMaxTokens > 0 {
		req.MaxTokens = c.config.ChatMaxTokens
	}

	// Parse and apply extra_body from config if not already set
	if req.ExtraBody == nil && c.config.ChatExtraBody != "" {
		var extraBody map[string]any
		if err := json.Unmarshal([]byte(c.config.ChatExtraBody), &extraBody); err == nil {
			req.ExtraBody = extraBody
			log.Printf("[DEBUG] ✅ ChatExtraBody parsed successfully: %+v", extraBody)
		} else {
			log.Printf("Warning: Failed to parse OPENAI_CHAT_EXTRA_BODY: %v", err)
		}
	}

	reqBody, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	url := fmt.Sprintf("%s/chat/completions", c.config.APIBase)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(reqBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.config.APIKey))

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(body))
	}

	var result ChatCompletionResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &result, nil
}

// ChatCompletionStream performs a streaming chat completion request
func (c *OpenAIClient) ChatCompletionStream(ctx context.Context, req ChatCompletionRequest, callback StreamCallback) error {
	if !c.config.Enabled {
		return fmt.Errorf("OpenAI API is not enabled (missing API key)")
	}

	// Use configured model if not specified
	if req.Model == "" {
		req.Model = c.config.ChatModel
	}

	// Apply default parameters from config
	if req.Temperature == 0 && c.config.ChatTemperature > 0 {
		req.Temperature = c.config.ChatTemperature
	}
	if req.TopP == 0 && c.config.ChatTopP > 0 {
		req.TopP = c.config.ChatTopP
	}
	if req.MaxTokens == 0 && c.config.ChatMaxTokens > 0 {
		req.MaxTokens = c.config.ChatMaxTokens
	}

	// Parse and apply extra_body from config if not already set
	if req.ExtraBody == nil && c.config.ChatExtraBody != "" {
		log.Printf("[DEBUG] 🔧 Applying ChatExtraBody from config: %s", c.config.ChatExtraBody)
		var extraBody map[string]any
		if err := json.Unmarshal([]byte(c.config.ChatExtraBody), &extraBody); err == nil {
			req.ExtraBody = extraBody
			log.Printf("[DEBUG] ✅ ChatExtraBody parsed successfully: %+v", extraBody)
		} else {
			log.Printf("[DEBUG] ❌ Failed to parse OPENAI_CHAT_EXTRA_BODY: %v", err)
		}
	} else {
		log.Printf("[DEBUG] ⚠️  No ChatExtraBody: ExtraBody=%v, ChatExtraBody='%s'", req.ExtraBody, c.config.ChatExtraBody)
	}

	// Enable streaming
	req.Stream = true

	reqBody, err := json.Marshal(req)
	if err != nil {
		return fmt.Errorf("failed to marshal request: %w", err)
	}

	log.Printf("[DEBUG] 📤 Streaming request body: %s", string(reqBody))

	url := fmt.Sprintf("%s/chat/completions", c.config.APIBase)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(reqBody))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.config.APIKey))
	httpReq.Header.Set("Accept", "text/event-stream")

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(body))
	}

	// Process streaming response
	reader := bufio.NewReader(resp.Body)
	for {
		line, err := reader.ReadBytes('\n')
		if err != nil {
			if err == io.EOF {
				break
			}
			return fmt.Errorf("failed to read stream: %w", err)
		}

		// Skip empty lines
		line = bytes.TrimSpace(line)
		if len(line) == 0 {
			continue
		}

		// Parse SSE format: "data: {...}"
		if bytes.HasPrefix(line, []byte("data: ")) {
			data := bytes.TrimPrefix(line, []byte("data: "))

			// Check for [DONE] marker
			if bytes.Equal(data, []byte("[DONE]")) {
				break
			}

			// Parse chunk using provider-specific parser
			chunk, err := c.chunkParser.ParseChunk(data)
			if err != nil {
				log.Printf("Warning: Failed to parse stream chunk: %v", err)
				continue
			}

			// Call callback with generic chunk
			if err := callback(chunk); err != nil {
				return fmt.Errorf("callback error: %w", err)
			}
		}
	}

	return nil
}

// CreateEmbeddings creates embeddings for the given texts
func (c *OpenAIClient) CreateEmbeddings(ctx context.Context, texts []string) ([][]float32, error) {
	if !c.config.Enabled {
		return nil, fmt.Errorf("OpenAI API is not enabled (missing API key)")
	}

	if len(texts) == 0 {
		return [][]float32{}, nil
	}

	// Process in batches
	allEmbeddings := make([][]float32, 0, len(texts))
	batchSize := c.config.BatchSize

	for i := 0; i < len(texts); i += batchSize {
		end := i + batchSize
		if end > len(texts) {
			end = len(texts)
		}
		batch := texts[i:end]

		embeddings, err := c.createEmbeddingBatch(ctx, batch)
		if err != nil {
			return nil, fmt.Errorf("failed to create embeddings for batch %d: %w", i/batchSize, err)
		}

		allEmbeddings = append(allEmbeddings, embeddings...)

		// Rate limiting: small delay between batches
		if end < len(texts) {
			time.Sleep(100 * time.Millisecond)
		}
	}

	return allEmbeddings, nil
}

// createEmbeddingBatch creates embeddings for a single batch
func (c *OpenAIClient) createEmbeddingBatch(ctx context.Context, texts []string) ([][]float32, error) {
	req := EmbeddingRequest{
		Model:          c.config.EmbeddingModel,
		Input:          texts,
		Dimensions:     c.config.EmbeddingDimensions,
		EncodingFormat: "float", // For NVIDIA API compatibility
	}

	// Parse and apply extra_body from config
	if c.config.EmbeddingExtraBody != "" {
		var extraBody map[string]any
		if err := json.Unmarshal([]byte(c.config.EmbeddingExtraBody), &extraBody); err == nil {
			req.ExtraBody = extraBody
		} else {
			log.Printf("Warning: Failed to parse OPENAI_EMBEDDING_EXTRA_BODY: %v", err)
		}
	}

	reqBody, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	url := fmt.Sprintf("%s/embeddings", c.config.APIBase)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(reqBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.config.APIKey))

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(body))
	}

	var result EmbeddingResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	// Extract embeddings in order
	embeddings := make([][]float32, len(texts))
	for _, item := range result.Data {
		if item.Index < len(embeddings) {
			embeddings[item.Index] = item.Embedding
		}
	}

	log.Printf("Created %d embeddings using model %s (tokens: %d)", len(embeddings), result.Model, result.Usage.TotalTokens)

	return embeddings, nil
}

// Note: AIIntentResponse is now defined in ai_client.go for better abstraction

// ParseIntentWithAI uses OpenAI to parse natural language query into structured filters
func (c *OpenAIClient) ParseIntentWithAI(ctx context.Context, query string) (*AIIntentResponse, error) {
	if !c.config.Enabled {
		return nil, fmt.Errorf("OpenAI API is not enabled")
	}

	systemPrompt := `You are a real estate search assistant in Singapore. Parse the user's natural language query into structured filters.

Extract the following information if present:
- price_min: minimum price in SGD (number)
- price_max: maximum price in SGD (number)
- bedrooms: number of bedrooms (integer)
- bathrooms: number of bathrooms (integer)
- area_sqft_min: minimum area in square feet (number)
- area_sqft_max: maximum area in square feet (number)
- unit_type: property type - must be one of: "HDB", "Condo", "Landed", "Executive" (string)
- location: Singapore district or area name (string)
- mrt_distance_max: maximum walking time to MRT station in minutes (integer, default 15 if "near MRT" mentioned)
- build_year_min: minimum build year (integer)
- amenities: array of required amenities/features (e.g., ["Air conditioner", "Balcony", "Washer/dryer"])
- facilities: array of required facilities (e.g., ["Swimming pool", "Gym", "BBQ pits", "Playground"])
- keywords: array of important keywords for semantic search (e.g., "spacious", "view", "renovated", "quiet")

Common amenities: Air conditioner, Balcony, Built-in wardrobe, Curtains, Fridge, Washer/dryer, Water heater, Dining table, Bed frame, Study table
Common facilities: Swimming pool, Gym, Tennis court, BBQ pits, Playground, Function room, 24-hour security, Covered parking

Important rules:
- All property data is in English
- Respond ONLY with valid JSON
- If a field is not mentioned, omit it
- For prices: "1.5M" = 1500000, "800K" = 800000
- For areas: "1000 sqft" = 1000, "1200 square feet" = 1200
- Common terms: "bright" (natural light), "spacious" (large area), "view" (good scenery)
- When user mentions facilities like "pool", "gym", "tennis", add them to facilities array
- When user mentions appliances/features like "aircon", "balcony", add them to amenities array

Examples:
Query: "3 bedroom condo in Punggol under 1.5M"
Response: {"bedrooms": 3, "unit_type": "Condo", "location": "Punggol", "price_max": 1500000, "keywords": ["condo", "punggol"]}

Query: "HDB near MRT with good view and spacious layout"
Response: {"unit_type": "HDB", "mrt_distance_max": 15, "keywords": ["view", "spacious", "near mrt", "hdb"]}

Query: "Condo with swimming pool and gym, 2 bedrooms, at least 1000 sqft"
Response: {"bedrooms": 2, "unit_type": "Condo", "area_sqft_min": 1000, "facilities": ["Swimming pool", "Gym"], "keywords": ["condo", "pool", "gym"]}

Query: "Apartment with balcony and air conditioning, fully furnished, 800-1200 sqft"
Response: {"area_sqft_min": 800, "area_sqft_max": 1200, "amenities": ["Balcony", "Air conditioner"], "keywords": ["furnished", "balcony", "aircon"]}

Query: "Large 4-bedroom landed house, minimum 2500 sqft"
Response: {"bedrooms": 4, "unit_type": "Landed", "area_sqft_min": 2500, "keywords": ["large", "landed", "house"]}

Query: "Landed property in Bukit Timah, 4 bed 3 bath, modern"
Response: {"unit_type": "Landed", "location": "Bukit Timah", "bedrooms": 4, "bathrooms": 3, "keywords": ["modern", "landed", "bukit timah"]}

Query: "New condo near Orchard, budget 2M max"
Response: {"unit_type": "Condo", "location": "Orchard", "price_max": 2000000, "build_year_min": 2015, "keywords": ["new", "condo", "orchard"]}`

	req := ChatCompletionRequest{
		Model: c.config.ChatModel,
		Messages: []ChatMessage{
			{Role: "system", Content: systemPrompt},
			{Role: "user", Content: query},
		},
		Temperature:    0.3,
		ResponseFormat: &ResponseFormat{Type: "json_object"},
	}

	resp, err := c.ChatCompletion(ctx, req)
	if err != nil {
		return nil, err
	}

	if len(resp.Choices) == 0 {
		return nil, fmt.Errorf("no response from OpenAI")
	}

	// Use robust JSON parser to handle various AI output formats
	var result AIIntentResponse
	content := resp.Choices[0].Message.Content
	if err := utils.ParseAIJSON(content, &result); err != nil {
		log.Printf("Failed to parse AI response, content: %s", content)
		return nil, fmt.Errorf("failed to parse AI response: %w", err)
	}

	// Validate the response structure
	if err := c.validateIntentResponse(&result); err != nil {
		return nil, fmt.Errorf("AI response validation failed: %w", err)
	}

	return &result, nil
}

// validateIntentResponse validates the AI response using business rules
func (c *OpenAIClient) validateIntentResponse(resp *AIIntentResponse) error {
	// Validate price range
	if resp.PriceMin != nil && resp.PriceMax != nil {
		if *resp.PriceMin > *resp.PriceMax {
			return fmt.Errorf("price_min (%f) cannot be greater than price_max (%f)", *resp.PriceMin, *resp.PriceMax)
		}
	}

	// Validate unit type enum
	if resp.UnitType != nil {
		validTypes := map[string]bool{"HDB": true, "Condo": true, "Landed": true, "Executive": true}
		if !validTypes[*resp.UnitType] {
			return fmt.Errorf("invalid unit_type: %s, must be one of: HDB, Condo, Landed, Executive", *resp.UnitType)
		}
	}

	// Validate numeric ranges
	if resp.Bedrooms != nil && (*resp.Bedrooms < 0 || *resp.Bedrooms > 10) {
		return fmt.Errorf("bedrooms must be between 0 and 10")
	}
	if resp.Bathrooms != nil && (*resp.Bathrooms < 0 || *resp.Bathrooms > 10) {
		return fmt.Errorf("bathrooms must be between 0 and 10")
	}
	if resp.MRTDistanceMax != nil && (*resp.MRTDistanceMax < 0 || *resp.MRTDistanceMax > 60) {
		return fmt.Errorf("mrt_distance_max must be between 0 and 60 minutes")
	}
	if resp.BuildYearMin != nil && (*resp.BuildYearMin < 1900 || *resp.BuildYearMin > 2100) {
		return fmt.Errorf("build_year_min must be between 1900 and 2100")
	}

	return nil
}

// ParseIntentWithAIStream uses OpenAI streaming to parse natural language query
func (c *OpenAIClient) ParseIntentWithAIStream(ctx context.Context, query string, callback func(thinking, content string) error) (*AIIntentResponse, error) {
	log.Printf("[DEBUG] 🤖 ParseIntentWithAIStream called for query: %s", query)

	if !c.config.Enabled {
		log.Printf("[DEBUG] ❌ OpenAI API is not enabled")
		return nil, fmt.Errorf("OpenAI API is not enabled")
	}

	log.Printf("[DEBUG] ✅ OpenAI API enabled, model: %s, base: %s", c.config.ChatModel, c.config.APIBase)

	systemPrompt := `You are a real estate search assistant in Singapore. Parse the user's natural language query into structured filters.

Extract the following information if present:
- price_min: minimum price in SGD (number)
- price_max: maximum price in SGD (number)
- bedrooms: number of bedrooms (integer)
- bathrooms: number of bathrooms (integer)
- area_sqft_min: minimum area in square feet (number)
- area_sqft_max: maximum area in square feet (number)
- unit_type: property type - must be one of: "HDB", "Condo", "Landed", "Executive" (string)
- location: Singapore district or area name (string)
- mrt_distance_max: maximum walking time to MRT station in minutes (integer, default 15 if "near MRT" mentioned)
- build_year_min: minimum build year (integer)
- amenities: array of required amenities/features (e.g., ["Air conditioner", "Balcony"])
- facilities: array of required facilities (e.g., ["Swimming pool", "Gym"])
- keywords: array of important keywords for semantic search

Important rules:
- All property data is in English
- Respond ONLY with valid JSON
- If a field is not mentioned, omit it
- For prices: "1.5M" = 1500000, "800K" = 800000
- For areas: "1000 sqft" = 1000, "1200 square feet" = 1200

Examples:
Query: "3 bedroom condo under 1.5M"
Response: {"bedrooms": 3, "unit_type": "Condo", "price_max": 1500000, "keywords": ["condo"]}

Query: "2 bed with pool and gym, at least 1000 sqft"
Response: {"bedrooms": 2, "area_sqft_min": 1000, "facilities": ["Swimming pool", "Gym"], "keywords": ["pool", "gym"]}

Now parse the following query into JSON format:`

	req := ChatCompletionRequest{
		Model: c.config.ChatModel,
		Messages: []ChatMessage{
			{Role: "system", Content: systemPrompt},
			{Role: "user", Content: query},
		},
		ResponseFormat: &ResponseFormat{
			Type: "json_object",
		},
	}

	log.Printf("[DEBUG] 📤 Sending request to AI API...")

	// Accumulate the response
	var fullContent strings.Builder
	var fullThinking strings.Builder
	chunkCount := 0

	err := c.ChatCompletionStream(ctx, req, func(chunk *StreamChunk) error {
		chunkCount++

		// Handle thinking content (provider-specific, e.g., DeepSeek)
		if chunk.ThinkingContent != "" {
			fullThinking.WriteString(chunk.ThinkingContent)
			log.Printf("[DEBUG] 💭 Thinking chunk #%d: %d chars", chunkCount, len(chunk.ThinkingContent))
			if err := callback(chunk.ThinkingContent, ""); err != nil {
				return err
			}
		}

		// Handle regular content
		if chunk.Content != "" {
			fullContent.WriteString(chunk.Content)
			log.Printf("[DEBUG] 📝 Content chunk #%d: %s", chunkCount, chunk.Content)
			if err := callback("", chunk.Content); err != nil {
				return err
			}
		}

		return nil
	})

	if err != nil {
		log.Printf("[DEBUG] ❌ Streaming error: %v", err)
		return nil, fmt.Errorf("streaming error: %w", err)
	}

	log.Printf("[DEBUG] 🎉 Streaming completed. Total chunks: %d", chunkCount)
	log.Printf("[DEBUG] 📊 Full thinking length: %d chars", fullThinking.Len())
	log.Printf("[DEBUG] 📊 Full content length: %d chars", fullContent.Len())

	// Parse the accumulated JSON response using robust parser
	content := fullContent.String()
	log.Printf("[DEBUG] 🔍 Attempting to parse JSON: %s", content)

	var result AIIntentResponse
	if err := utils.ParseAIJSON(content, &result); err != nil {
		log.Printf("[DEBUG] ❌ JSON parse failed: %v", err)
		return nil, fmt.Errorf("failed to parse AI response: %w (content: %s)", err, content)
	}

	log.Printf("[DEBUG] ✅ Streaming AI intent parsed successfully: %+v", result)
	return &result, nil
}
