package model

// SearchRequest represents a search query request
type SearchRequest struct {
	Query   string         `json:"query" binding:"required"`
	Filters *SearchFilters `json:"filters,omitempty"`
	Options *SearchOptions `json:"options,omitempty"`
}

// SearchFilters represents structured search filters
type SearchFilters struct {
	PriceMin       *float64 `json:"price_min,omitempty"`
	PriceMax       *float64 `json:"price_max,omitempty"`
	Bedrooms       *int     `json:"bedrooms,omitempty"`
	Bathrooms      *int     `json:"bathrooms,omitempty"`
	AreaSqftMin    *float64 `json:"area_sqft_min,omitempty"` // 最小面积
	AreaSqftMax    *float64 `json:"area_sqft_max,omitempty"` // 最大面积
	UnitType       *string  `json:"unit_type,omitempty"`
	MRTDistanceMax *int     `json:"mrt_distance_max,omitempty"`
	Location       *string  `json:"location,omitempty"`
	IsCompleted    *bool    `json:"is_completed,omitempty"`
	Amenities      []string `json:"amenities,omitempty"`  // 必须包含的设施
	Facilities     []string `json:"facilities,omitempty"` // 必须包含的公共设施
}

// SearchOptions represents search options
type SearchOptions struct {
	TopK     int  `json:"top_k"`
	Offset   int  `json:"offset"`
	Semantic bool `json:"semantic"`
}

// SearchResponse represents a search result response
type SearchResponse struct {
	Results    []ListingSearchResult `json:"results"`
	Total      int                   `json:"total"`
	Page       int                   `json:"page"`
	PageSize   int                   `json:"page_size"`
	TotalPages int                   `json:"total_pages"`
	HasMore    bool                  `json:"has_more"`
	Intent     *IntentResult         `json:"intent,omitempty"`
	Took       int64                 `json:"took_ms"` // Response time in milliseconds
}

// SearchResultRequest represents a request for paginated search results
type SearchResultRequest struct {
	Filters *SearchFilters `json:"filters,omitempty"`
	Options *SearchOptions `json:"options,omitempty"`
}

// SearchResultResponse represents a paginated search result response
type SearchResultResponse struct {
	Results    []ListingSearchResult `json:"results"`
	Page       int                   `json:"page"`
	PageSize   int                   `json:"page_size"`
	TotalPages int                   `json:"total_pages"`
	HasMore    bool                  `json:"has_more"`
	Took       int64                 `json:"took_ms"` // Response time in milliseconds
}

// EmbeddingBatchRequest represents a batch embedding update request
type EmbeddingBatchRequest struct {
	Embeddings []EmbeddingItem `json:"embeddings" binding:"required"`
}

// EmbeddingItem represents a single embedding with listing info
type EmbeddingItem struct {
	ListingID int64     `json:"listing_id" binding:"required"`
	Embedding []float32 `json:"embedding" binding:"required"`
	Text      string    `json:"text,omitempty"` // The text used to generate embedding
}

// EmbeddingBatchResponse represents the response for batch embedding update
type EmbeddingBatchResponse struct {
	Success int      `json:"success"`
	Failed  int      `json:"failed"`
	Errors  []string `json:"errors,omitempty"`
}

// FeedbackRequest represents user feedback/action
type FeedbackRequest struct {
	SearchID  string `json:"search_id" binding:"required"`
	ListingID int64  `json:"listing_id" binding:"required"`
	Action    string `json:"action" binding:"required"` // click, contact, view_details
}

// FeedbackResponse represents feedback response
type FeedbackResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message,omitempty"`
}
