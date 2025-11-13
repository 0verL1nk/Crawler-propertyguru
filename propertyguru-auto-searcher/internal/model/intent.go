package model

// IntentResult represents the parsed intent from a natural language query
type IntentResult struct {
	Slots            *IntentSlots `json:"slots"`
	SemanticKeywords []string     `json:"semantic_keywords,omitempty"`
	Confidence       float64      `json:"confidence"`
}

// IntentSlots represents structured conditions extracted from query
type IntentSlots struct {
	PriceMin       *float64 `json:"price_min,omitempty"`
	PriceMax       *float64 `json:"price_max,omitempty"`
	Bedrooms       *int     `json:"bedrooms,omitempty"`
	Bathrooms      *int     `json:"bathrooms,omitempty"`
	UnitType       *string  `json:"unit_type,omitempty"`
	MRTDistanceMax *int     `json:"mrt_distance_max,omitempty"`
	Location       *string  `json:"location,omitempty"`
	BuildYearMin   *int     `json:"build_year_min,omitempty"`
}
