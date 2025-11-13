package service

import (
	"encoding/json"
)

// NVIDIAStreamChunkParser parses NVIDIA-specific streaming chunks
type NVIDIAStreamChunkParser struct{}

// ParseChunk converts NVIDIA/DeepSeek-specific chunk to generic StreamChunk
func (p *NVIDIAStreamChunkParser) ParseChunk(data []byte) (*StreamChunk, error) {
	// NVIDIA/DeepSeek uses a specific format with reasoning_content
	var rawChunk struct {
		Choices []struct {
			Delta struct {
				Role             string  `json:"role,omitempty"`
				Content          string  `json:"content,omitempty"`
				ReasoningContent *string `json:"reasoning_content,omitempty"` // DeepSeek thinking
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

		// NVIDIA/DeepSeek specific: extract reasoning_content
		if delta.ReasoningContent != nil {
			chunk.ThinkingContent = *delta.ReasoningContent
		}

		chunk.Done = rawChunk.Choices[0].FinishReason != ""
	}

	return chunk, nil
}

// IsNVIDIAProvider checks if the base URL is NVIDIA API
func IsNVIDIAProvider(baseURL string) bool {
	return baseURL == "https://integrate.api.nvidia.com/v1"
}
