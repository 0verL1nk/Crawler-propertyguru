package utils

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
)

// ParseAIJSON extracts and parses JSON from AI output that may contain:
// - Pure JSON
// - JSON wrapped in markdown code blocks (```json ... ```)
// - JSON with surrounding text
// - Partial or malformed JSON
func ParseAIJSON(input string, target interface{}) error {
	if input == "" {
		return fmt.Errorf("empty input")
	}

	// Try direct parsing first (most common case)
	if err := json.Unmarshal([]byte(input), target); err == nil {
		return nil
	}

	// Try to extract JSON from markdown code blocks
	if extracted := extractFromMarkdown(input); extracted != "" {
		if err := json.Unmarshal([]byte(extracted), target); err == nil {
			return nil
		}
	}

	// Try to find JSON object/array in text
	if extracted := extractJSONFromText(input); extracted != "" {
		if err := json.Unmarshal([]byte(extracted), target); err == nil {
			return nil
		}
	}

	// Try to clean and fix common JSON issues
	if cleaned := cleanAndFixJSON(input); cleaned != "" {
		if err := json.Unmarshal([]byte(cleaned), target); err == nil {
			return nil
		}
	}

	return fmt.Errorf("failed to parse JSON from input: %s", truncateString(input, 100))
}

// extractFromMarkdown extracts JSON from markdown code blocks
// Supports: ```json {...} ```, ```{...}```, or ```\n{...}\n```
func extractFromMarkdown(input string) string {
	// Pattern 1: ```json ... ```
	re1 := regexp.MustCompile("(?s)```json\\s*(.+?)\\s*```")
	if matches := re1.FindStringSubmatch(input); len(matches) > 1 {
		return strings.TrimSpace(matches[1])
	}

	// Pattern 2: ``` ... ```
	re2 := regexp.MustCompile("(?s)```\\s*(.+?)\\s*```")
	if matches := re2.FindStringSubmatch(input); len(matches) > 1 {
		content := strings.TrimSpace(matches[1])
		// Check if it looks like JSON
		if strings.HasPrefix(content, "{") || strings.HasPrefix(content, "[") {
			return content
		}
	}

	return ""
}

// extractJSONFromText finds JSON object or array in surrounding text
func extractJSONFromText(input string) string {
	// Try to find JSON object
	if start := strings.Index(input, "{"); start >= 0 {
		if extracted := extractBalancedBraces(input[start:], '{', '}'); extracted != "" {
			return extracted
		}
	}

	// Try to find JSON array
	if start := strings.Index(input, "["); start >= 0 {
		if extracted := extractBalancedBraces(input[start:], '[', ']'); extracted != "" {
			return extracted
		}
	}

	return ""
}

// extractBalancedBraces extracts content with balanced braces
func extractBalancedBraces(input string, open, close rune) string {
	if len(input) == 0 {
		return ""
	}

	depth := 0
	inString := false
	escape := false
	start := 0

	for i, ch := range input {
		if escape {
			escape = false
			continue
		}

		if ch == '\\' {
			escape = true
			continue
		}

		if ch == '"' {
			inString = !inString
			continue
		}

		if inString {
			continue
		}

		if ch == open {
			if depth == 0 {
				start = i
			}
			depth++
		} else if ch == close {
			depth--
			if depth == 0 {
				return input[start : i+1]
			}
		}
	}

	return ""
}

// cleanAndFixJSON attempts to fix common JSON formatting issues
func cleanAndFixJSON(input string) string {
	s := strings.TrimSpace(input)

	// Remove BOM if present
	s = strings.TrimPrefix(s, "\ufeff")

	// Remove trailing commas before closing braces/brackets
	re1 := regexp.MustCompile(`,\s*([}\]])`)
	s = re1.ReplaceAllString(s, "$1")

	// Fix missing quotes around keys (common AI mistake)
	// Match: {word: "value"} -> {"word": "value"}
	re2 := regexp.MustCompile(`([{,]\s*)(\w+)(\s*:)`)
	s = re2.ReplaceAllString(s, `$1"$2"$3`)

	// Fix single quotes to double quotes (outside of strings)
	s = fixSingleQuotes(s)

	// Remove control characters
	s = removeControlCharacters(s)

	return s
}

// fixSingleQuotes converts single quotes to double quotes for JSON compatibility
func fixSingleQuotes(input string) string {
	var result strings.Builder
	inDoubleQuote := false
	escape := false

	for i, ch := range input {
		if escape {
			result.WriteRune(ch)
			escape = false
			continue
		}

		if ch == '\\' {
			result.WriteRune(ch)
			escape = true
			continue
		}

		if ch == '"' {
			inDoubleQuote = !inDoubleQuote
			result.WriteRune(ch)
			continue
		}

		// Only replace single quotes outside of double-quoted strings
		if ch == '\'' && !inDoubleQuote {
			// Check if it's likely a quote character (not apostrophe in word)
			prevChar := rune(0)
			if i > 0 {
				prevChar = rune(input[i-1])
			}
			// Convert to double quote if it's at start/end or after special chars
			if i == 0 || prevChar == ':' || prevChar == ',' || prevChar == '[' || prevChar == '{' {
				result.WriteRune('"')
				continue
			}
		}

		result.WriteRune(ch)
	}

	return result.String()
}

// removeControlCharacters removes non-printable control characters
func removeControlCharacters(input string) string {
	return regexp.MustCompile(`[\x00-\x08\x0B\x0C\x0E-\x1F]`).ReplaceAllString(input, "")
}

// truncateString truncates a string to maxLen characters
func truncateString(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}

// TryParseJSONArray attempts to parse a JSON array with fallback strategies
func TryParseJSONArray(input string) ([]interface{}, error) {
	var result []interface{}
	if err := ParseAIJSON(input, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// TryParseJSONObject attempts to parse a JSON object with fallback strategies
func TryParseJSONObject(input string) (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := ParseAIJSON(input, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// ExtractJSONSnippets finds all JSON objects or arrays in text
func ExtractJSONSnippets(input string) []string {
	var snippets []string

	// Find all JSON objects
	for i := 0; i < len(input); i++ {
		if input[i] == '{' {
			if extracted := extractBalancedBraces(input[i:], '{', '}'); extracted != "" {
				snippets = append(snippets, extracted)
				i += len(extracted) - 1
			}
		} else if input[i] == '[' {
			if extracted := extractBalancedBraces(input[i:], '[', ']'); extracted != "" {
				snippets = append(snippets, extracted)
				i += len(extracted) - 1
			}
		}
	}

	return snippets
}

// ValidateJSON checks if a string is valid JSON
func ValidateJSON(input string) bool {
	var js interface{}
	return json.Unmarshal([]byte(input), &js) == nil
}

// PrettyPrintJSON formats JSON with indentation
func PrettyPrintJSON(v interface{}) (string, error) {
	bytes, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return "", err
	}
	return string(bytes), nil
}
