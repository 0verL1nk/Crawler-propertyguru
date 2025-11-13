package service

import (
	"testing"
)

// NOTE: These tests are for the old regex-based parser which has been replaced by AI.
// The tests have been updated to work with the new AI-based parser (without OpenAI client).
// For full integration testing with AI, set up a test with actual OpenAI API key.

func TestIntentParser_WithoutAI(t *testing.T) {
	// Create parser without AI client (will return empty results)
	parser := NewIntentParser(nil)

	tests := []struct {
		name  string
		query string
	}{
		{
			name:  "English query",
			query: "3 bedroom HDB near MRT, below $1M",
		},
		{
			name:  "Complex query",
			query: "Condo in Punggol with good view",
		},
		{
			name:  "Empty query",
			query: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := parser.Parse(tt.query)

			// Without AI client, should return empty slots
			if result.Slots == nil {
				t.Fatal("Expected slots to be non-nil")
			}

			// Confidence should be 0 when AI is disabled
			if tt.query != "" && result.Confidence != 0.0 {
				t.Errorf("Expected confidence to be 0.0 without AI, got %.2f", result.Confidence)
			}

			// Should at least include the query as a keyword (if not empty)
			if tt.query != "" && len(result.SemanticKeywords) == 0 {
				t.Error("Expected at least the query as a semantic keyword")
			}
		})
	}
}

// TestIntentParser_BasicStructure verifies the basic structure is correct
func TestIntentParser_BasicStructure(t *testing.T) {
	parser := NewIntentParser(nil)

	result := parser.Parse("test query")

	if result == nil {
		t.Fatal("Expected result to be non-nil")
	}

	if result.Slots == nil {
		t.Error("Expected Slots to be non-nil")
	}

	if result.SemanticKeywords == nil {
		t.Error("Expected SemanticKeywords to be non-nil")
	}

	// Check confidence is within valid range
	if result.Confidence < 0 || result.Confidence > 1 {
		t.Errorf("Confidence should be between 0 and 1, got %.2f", result.Confidence)
	}
}

// Helper functions
func float64Ptr(v float64) *float64 {
	return &v
}

func intPtr(v int) *int {
	return &v
}
