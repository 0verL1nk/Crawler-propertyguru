package model

// IntentResult represents the parsed intent from a natural language query
type IntentResult struct {
	Slots            *IntentSlots `json:"slots"`
	SemanticKeywords []string     `json:"semantic_keywords,omitempty"`
	Confidence       float64      `json:"confidence"`
}

// IntentSlots represents structured conditions extracted from query
type IntentSlots struct {
	PriceMin       *float64  `json:"price_min,omitempty"`
	PriceMax       *float64  `json:"price_max,omitempty"`
	Bedrooms       *int      `json:"bedrooms,omitempty"`
	Bathrooms      *int      `json:"bathrooms,omitempty"`
	AreaSqftMin    *float64  `json:"area_sqft_min,omitempty"`   // 最小面积（平方英尺）
	AreaSqftMax    *float64  `json:"area_sqft_max,omitempty"`   // 最大面积（平方英尺）
	UnitType       *string   `json:"unit_type,omitempty"`
	MRTDistanceMax *int      `json:"mrt_distance_max,omitempty"`
	Location       *string   `json:"location,omitempty"`
	BuildYearMin   *int      `json:"build_year_min,omitempty"`
	Amenities      []string  `json:"amenities,omitempty"`       // 用户需求的设施
	Facilities     []string  `json:"facilities,omitempty"`      // 用户需求的公共设施
}
