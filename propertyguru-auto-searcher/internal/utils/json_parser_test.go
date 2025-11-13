package utils

import (
	"testing"
)

func TestParseAIJSON(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    map[string]interface{}
		wantErr bool
	}{
		{
			name:  "Pure JSON",
			input: `{"name": "John", "age": 30}`,
			want: map[string]interface{}{
				"name": "John",
				"age":  float64(30),
			},
			wantErr: false,
		},
		{
			name: "JSON in markdown code block",
			input: "```json\n" +
				`{"name": "Jane", "age": 25}` + "\n```",
			want: map[string]interface{}{
				"name": "Jane",
				"age":  float64(25),
			},
			wantErr: false,
		},
		{
			name:  "JSON with surrounding text",
			input: `Here is the result: {"status": "success", "count": 5} and that's it.`,
			want: map[string]interface{}{
				"status": "success",
				"count":  float64(5),
			},
			wantErr: false,
		},
		{
			name:  "JSON with trailing comma",
			input: `{"name": "Bob", "age": 40,}`,
			want: map[string]interface{}{
				"name": "Bob",
				"age":  float64(40),
			},
			wantErr: false,
		},
		{
			name:  "JSON with unquoted keys",
			input: `{name: "Alice", age: 35}`,
			want: map[string]interface{}{
				"name": "Alice",
				"age":  float64(35),
			},
			wantErr: false,
		},
		{
			name:    "Empty string",
			input:   "",
			want:    nil,
			wantErr: true,
		},
		{
			name:    "Invalid JSON",
			input:   "not json at all",
			want:    nil,
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var got map[string]interface{}
			err := ParseAIJSON(tt.input, &got)

			if (err != nil) != tt.wantErr {
				t.Errorf("ParseAIJSON() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if !tt.wantErr {
				if len(got) != len(tt.want) {
					t.Errorf("ParseAIJSON() got = %v, want %v", got, tt.want)
				}
			}
		})
	}
}

func TestExtractFromMarkdown(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  string
	}{
		{
			name:  "JSON code block with json tag",
			input: "```json\n{\"test\": true}\n```",
			want:  `{"test": true}`,
		},
		{
			name:  "JSON code block without tag",
			input: "```\n{\"test\": true}\n```",
			want:  `{"test": true}`,
		},
		{
			name:  "No code block",
			input: `{"test": true}`,
			want:  "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := extractFromMarkdown(tt.input)
			if got != tt.want {
				t.Errorf("extractFromMarkdown() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestExtractBalancedBraces(t *testing.T) {
	tests := []struct {
		name  string
		input string
		open  rune
		close rune
		want  string
	}{
		{
			name:  "Simple object",
			input: `{"a": 1}`,
			open:  '{',
			close: '}',
			want:  `{"a": 1}`,
		},
		{
			name:  "Nested objects",
			input: `{"a": {"b": 2}}`,
			open:  '{',
			close: '}',
			want:  `{"a": {"b": 2}}`,
		},
		{
			name:  "Object with string containing braces",
			input: `{"text": "Hello {world}"}`,
			open:  '{',
			close: '}',
			want:  `{"text": "Hello {world}"}`,
		},
		{
			name:  "Array",
			input: `[1, 2, 3]`,
			open:  '[',
			close: ']',
			want:  `[1, 2, 3]`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := extractBalancedBraces(tt.input, tt.open, tt.close)
			if got != tt.want {
				t.Errorf("extractBalancedBraces() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestValidateJSON(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  bool
	}{
		{
			name:  "Valid object",
			input: `{"test": true}`,
			want:  true,
		},
		{
			name:  "Valid array",
			input: `[1, 2, 3]`,
			want:  true,
		},
		{
			name:  "Invalid JSON",
			input: `{test: true}`,
			want:  false,
		},
		{
			name:  "Empty string",
			input: "",
			want:  false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := ValidateJSON(tt.input)
			if got != tt.want {
				t.Errorf("ValidateJSON() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestExtractJSONSnippets(t *testing.T) {
	input := `Here are two objects: {"a": 1} and {"b": 2}, plus an array [1,2,3]`
	snippets := ExtractJSONSnippets(input)

	if len(snippets) != 3 {
		t.Errorf("ExtractJSONSnippets() found %d snippets, want 3", len(snippets))
	}

	// Verify each snippet is valid JSON
	for i, snippet := range snippets {
		if !ValidateJSON(snippet) {
			t.Errorf("Snippet %d is not valid JSON: %s", i, snippet)
		}
	}
}
