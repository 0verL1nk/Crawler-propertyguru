package utils

import (
"strings"
)

// FuzzyMatchAmenity performs fuzzy matching for amenity names
// Returns true if the search term fuzzy matches the amenity
func FuzzyMatchAmenity(searchTerm, amenity string) bool {
searchLower := strings.ToLower(strings.TrimSpace(searchTerm))
amenityLower := strings.ToLower(strings.TrimSpace(amenity))

// Exact match
if searchLower == amenityLower {
return true
}

// Contains match
if strings.Contains(amenityLower, searchLower) {
return true
}

// Common aliases for amenities
aliases := map[string][]string{
"pool":         {"swimming pool", "pool"},
"gym":          {"gym", "gymnasium", "fitness", "fitness center"},
"aircon":       {"air conditioner", "air conditioning", "aircon", "a/c", "ac"},
"washer":       {"washer", "washing machine", "washer/dryer", "laundry"},
"dryer":        {"dryer", "washer/dryer"},
"wardrobe":     {"wardrobe", "built-in wardrobe", "closet"},
"tennis":       {"tennis", "tennis court"},
"bbq":          {"bbq", "barbecue", "bbq pit", "bbq pits"},
"parking":      {"parking", "car park", "covered parking"},
"security":     {"security", "24-hour security", "24hr security"},
"playground":   {"playground", "children's playground", "kids playground"},
"function":     {"function room", "function hall", "multipurpose hall"},
"balcony":      {"balcony", "terrace"},
"kitchen":      {"kitchen", "open kitchen", "closed kitchen"},
"fridge":       {"fridge", "refrigerator"},
"water heater": {"water heater", "heater"},
}

// Check aliases
for key, values := range aliases {
if strings.Contains(searchLower, key) {
for _, alias := range values {
if strings.Contains(amenityLower, alias) {
return true
}
}
}
}

// Reverse check: if amenity contains any keyword from search
for key, values := range aliases {
for _, alias := range values {
if strings.Contains(amenityLower, alias) && strings.Contains(searchLower, key) {
return true
}
}
}

return false
}

// NormalizeAmenity normalizes amenity names to standard form
func NormalizeAmenity(amenity string) string {
amenityLower := strings.ToLower(strings.TrimSpace(amenity))

// Common normalizations
normalizations := map[string]string{
"pool":             "Swimming pool",
"swimming pool":    "Swimming pool",
"gym":              "Gym",
"gymnasium":        "Gym",
"fitness":          "Gym",
"fitness center":   "Gym",
"aircon":           "Air conditioner",
"air conditioning": "Air conditioner",
"a/c":              "Air conditioner",
"ac":               "Air conditioner",
"washer":           "Washer/dryer",
"washing machine":  "Washer/dryer",
"dryer":            "Washer/dryer",
"wardrobe":         "Built-in wardrobe",
"closet":           "Built-in wardrobe",
"tennis":           "Tennis court",
"tennis court":     "Tennis court",
"bbq":              "BBQ pits",
"barbecue":         "BBQ pits",
"bbq pit":          "BBQ pits",
"parking":          "Covered parking",
"car park":         "Covered parking",
"security":         "24-hour security",
"24hr security":    "24-hour security",
"playground":       "Playground",
"function room":    "Function room",
"function hall":    "Function room",
"balcony":          "Balcony",
"terrace":          "Balcony",
"fridge":           "Fridge",
"refrigerator":     "Fridge",
"water heater":     "Water heater",
"heater":           "Water heater",
}

if normalized, ok := normalizations[amenityLower]; ok {
return normalized
}

// If not in map, return title case
return strings.Title(amenityLower)
}

// BuildFuzzyAmenityQuery builds JSONB query for fuzzy amenity matching
// Returns SQL condition and parameters for PostgreSQL JSONB array matching
func BuildFuzzyAmenityQuery(searchTerms []string, paramIndex int) ([]string, []interface{}, int) {
if len(searchTerms) == 0 {
return nil, nil, paramIndex
}

var conditions []string
var params []interface{}

// Common amenity patterns for ILIKE matching
amenityPatterns := map[string][]string{
"pool":       {"Swimming pool", "Pool"},
"gym":        {"Gym", "Gymnasium", "Fitness"},
"aircon":     {"Air conditioner", "Air conditioning", "Aircon", "A/C"},
"washer":     {"Washer", "Washing machine", "Washer/dryer", "Laundry"},
"dryer":      {"Dryer", "Washer/dryer"},
"wardrobe":   {"Wardrobe", "Built-in wardrobe", "Closet"},
"tennis":     {"Tennis", "Tennis court"},
"bbq":        {"BBQ", "Barbecue", "BBQ pit"},
"parking":    {"Parking", "Car park", "Covered parking"},
"security":   {"Security", "24-hour security"},
"playground": {"Playground", "Children playground"},
"function":   {"Function room", "Function hall"},
"balcony":    {"Balcony", "Terrace"},
"fridge":     {"Fridge", "Refrigerator"},
}

for _, term := range searchTerms {
termLower := strings.ToLower(strings.TrimSpace(term))

// Find matching patterns
var patterns []string
matched := false

for key, values := range amenityPatterns {
if strings.Contains(termLower, key) {
patterns = values
matched = true
break
}
}

if !matched {
// If no pattern found, use the term itself (title case)
patterns = []string{strings.Title(term)}
}

// Build OR condition for all patterns
var orConditions []string
for _, pattern := range patterns {
orConditions = append(orConditions, "elem::text ILIKE $"+string(rune('0'+paramIndex)))
params = append(params, "%"+pattern+"%")
paramIndex++
}

// Combine with OR and wrap in EXISTS
condition := "EXISTS (SELECT 1 FROM jsonb_array_elements(amenities) elem WHERE " + strings.Join(orConditions, " OR ") + ")"
conditions = append(conditions, condition)
}

return conditions, params, paramIndex
}

// BuildFuzzyFacilityQuery builds JSONB query for fuzzy facility matching
func BuildFuzzyFacilityQuery(searchTerms []string, paramIndex int) ([]string, []interface{}, int) {
// For now, use same logic as amenities
// You can customize this if facilities have different patterns
return BuildFuzzyAmenityQuery(searchTerms, paramIndex)
}
