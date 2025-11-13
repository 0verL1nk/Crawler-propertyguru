package service

import (
	"encoding/json"
	"strings"
)

// OpenAIStreamChunkParser parses standard OpenAI-format streaming chunks
type OpenAIStreamChunkParser struct{}

// ParseChunk converts standard OpenAI chunk to generic StreamChunk
func (p *OpenAIStreamChunkParser) ParseChunk(data []byte) (*StreamChunk, error) {
	// Standard OpenAI format (no reasoning_content)
	var rawChunk struct {
		Choices []struct {
			Delta struct {
				Role    string `json:"role,omitempty"`
				Content string `json:"content,omitempty"`
			} `json:"delta"`
			FinishReason string `json:"finish_reason,omitempty"`
		} `json:"choices"`
	}

	if err := json.Unmarshal(data, &rawChunk); err != nil {
		return nil, err
	}

	chunk := &StreamChunk{
		Metadata: make(map[string]interface{}),
	}

	if len(rawChunk.Choices) > 0 {
		delta := rawChunk.Choices[0].Delta
		chunk.Role = delta.Role
		chunk.Content = delta.Content
		chunk.Done = rawChunk.Choices[0].FinishReason != ""
	}

	return chunk, nil
}

// IsOpenAIProvider checks if the base URL is official OpenAI API
func IsOpenAIProvider(baseURL string) bool {
	return strings.Contains(baseURL, "api.openai.com")
}
