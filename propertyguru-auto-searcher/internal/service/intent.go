package service

import (
	"context"
	"fmt"
	"log"
	"strings"

	"core/internal/model"
)

// IntentParser parses natural language queries into structured filters using AI
type IntentParser struct {
	aiClient *OpenAIClient
}

// NewIntentParser creates a new intent parser
func NewIntentParser(aiClient *OpenAIClient) *IntentParser {
	return &IntentParser{
		aiClient: aiClient,
	}
}

// Parse extracts structured information from a natural language query using AI
func (p *IntentParser) Parse(query string) *model.IntentResult {
	query = strings.TrimSpace(query)
	if query == "" {
		return &model.IntentResult{
			Slots:            &model.IntentSlots{},
			SemanticKeywords: []string{},
			Confidence:       0.0,
		}
	}

	// Check if AI is enabled
	if p.aiClient == nil || !p.aiClient.config.Enabled {
		log.Printf("OpenAI is not enabled, returning empty result. Please set OPENAI_API_KEY environment variable.")
		return &model.IntentResult{
			Slots:            &model.IntentSlots{},
			SemanticKeywords: []string{query}, // At least include the original query
			Confidence:       0.0,
		}
	}

	// Use AI to parse the query
	result, err := p.parseWithAI(query)
	if err != nil {
		log.Printf("AI parsing failed: %v, returning empty result", err)
		return &model.IntentResult{
			Slots:            &model.IntentSlots{},
			SemanticKeywords: []string{query},
			Confidence:       0.0,
		}
	}

	return result
}

// parseWithAI uses OpenAI to parse the query with strict validation
func (p *IntentParser) parseWithAI(query string) (*model.IntentResult, error) {
	ctx := context.Background()
	aiResult, err := p.aiClient.ParseIntentWithAI(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("OpenAI parsing error: %w", err)
	}

	result := &model.IntentResult{
		Slots:            &model.IntentSlots{},
		SemanticKeywords: []string{},
		Confidence:       0.95, // High confidence for validated AI results
	}

	// Map validated AI response to IntentSlots
	result.Slots.PriceMin = aiResult.PriceMin
	result.Slots.PriceMax = aiResult.PriceMax
	result.Slots.Bedrooms = aiResult.Bedrooms
	result.Slots.Bathrooms = aiResult.Bathrooms
	result.Slots.AreaSqftMin = aiResult.AreaSqftMin
	result.Slots.AreaSqftMax = aiResult.AreaSqftMax
	result.Slots.UnitType = aiResult.UnitType
	result.Slots.Location = aiResult.Location
	result.Slots.MRTDistanceMax = aiResult.MRTDistanceMax
	result.Slots.BuildYearMin = aiResult.BuildYearMin
	result.Slots.Amenities = aiResult.Amenities
	result.Slots.Facilities = aiResult.Facilities

	// Add AI-extracted keywords
	if len(aiResult.Keywords) > 0 {
		result.SemanticKeywords = append(result.SemanticKeywords, aiResult.Keywords...)
	}

	// Always include the original query for full-text search
	result.SemanticKeywords = append(result.SemanticKeywords, query)

	return result, nil
}

// ParseStream extracts structured information with streaming progress updates
func (p *IntentParser) ParseStream(ctx context.Context, query string, callback func(thinking, content string) error) (*model.IntentResult, error) {
	query = strings.TrimSpace(query)
	if query == "" {
		return &model.IntentResult{
			Slots:            &model.IntentSlots{},
			SemanticKeywords: []string{},
			Confidence:       0.0,
		}, nil
	}

	// Check if AI is enabled
	if p.aiClient == nil {
		log.Printf("⚠️  AI client is nil, returning empty result")
		return &model.IntentResult{
			Slots:            &model.IntentSlots{},
			SemanticKeywords: []string{query},
			Confidence:       0.0,
		}, nil
	}

	if !p.aiClient.IsEnabled() {
		log.Printf("⚠️  OpenAI API is not enabled. Please check:")
		log.Printf("   - OPENAI_API_KEY environment variable is set")
		log.Printf("   - OPENAI_API_BASE is configured (current: %s)", p.aiClient.config.APIBase)
		return &model.IntentResult{
			Slots:            &model.IntentSlots{},
			SemanticKeywords: []string{query},
			Confidence:       0.0,
		}, nil
	}

	// Use AI to parse the query with streaming
	result, err := p.parseWithAIStream(ctx, query, callback)
	if err != nil {
		log.Printf("AI streaming parsing failed: %v", err)
		return &model.IntentResult{
			Slots:            &model.IntentSlots{},
			SemanticKeywords: []string{query},
			Confidence:       0.0,
		}, nil
	}

	return result, nil
}

// parseWithAIStream uses OpenAI streaming to parse the query
func (p *IntentParser) parseWithAIStream(ctx context.Context, query string, callback func(thinking, content string) error) (*model.IntentResult, error) {
	log.Printf("[DEBUG] 🚀 Starting AI stream parsing for query: %s", query)

	aiResult, err := p.aiClient.ParseIntentWithAIStream(ctx, query, callback)
	if err != nil {
		log.Printf("[DEBUG] ❌ AI stream parsing failed: %v", err)
		return nil, fmt.Errorf("OpenAI streaming parsing error: %w", err)
	}

	log.Printf("[DEBUG] ✅ AI stream parsing completed successfully")
	log.Printf("[DEBUG] 📊 AI Result - Bedrooms: %v, UnitType: %v, PriceMax: %v, Confidence: %.2f",
		aiResult.Bedrooms, aiResult.UnitType, aiResult.PriceMax, aiResult.Confidence)

	result := &model.IntentResult{
		Slots:            &model.IntentSlots{},
		SemanticKeywords: []string{},
		Confidence:       0.95,
	}

	// Map validated AI response to IntentSlots
	result.Slots.PriceMin = aiResult.PriceMin
	result.Slots.PriceMax = aiResult.PriceMax
	result.Slots.Bedrooms = aiResult.Bedrooms
	result.Slots.Bathrooms = aiResult.Bathrooms
	result.Slots.AreaSqftMin = aiResult.AreaSqftMin
	result.Slots.AreaSqftMax = aiResult.AreaSqftMax
	result.Slots.UnitType = aiResult.UnitType
	result.Slots.Location = aiResult.Location
	result.Slots.MRTDistanceMax = aiResult.MRTDistanceMax
	result.Slots.BuildYearMin = aiResult.BuildYearMin
	result.Slots.Amenities = aiResult.Amenities
	result.Slots.Facilities = aiResult.Facilities

	// Add AI-extracted keywords
	if len(aiResult.Keywords) > 0 {
		result.SemanticKeywords = append(result.SemanticKeywords, aiResult.Keywords...)
	}

	// Always include the original query
	result.SemanticKeywords = append(result.SemanticKeywords, query)

	log.Printf("[DEBUG] 🎯 Final intent result - Slots: %+v, Keywords: %v", result.Slots, result.SemanticKeywords)

	return result, nil
}
