package service

import (
	"context"
	"time"

	"core/internal/model"
	"core/internal/repository"
)

// SearchService handles search business logic
type SearchService struct {
	repo   *repository.PostgresRepository
	intent *IntentParser
	ranker *Ranker
}

// NewSearchService creates a new search service
func NewSearchService(
	repo *repository.PostgresRepository,
	intentParser *IntentParser,
	ranker *Ranker,
) *SearchService {
	return &SearchService{
		repo:   repo,
		intent: intentParser,
		ranker: ranker,
	}
}

// SearchEventCallback is called for streaming search events
type SearchEventCallback func(event string, data any) error

// Search performs a complete search with intent parsing, filtering, and ranking
func (s *SearchService) Search(ctx context.Context, req *model.SearchRequest) (*model.SearchResponse, error) {
	startTime := time.Now()

	// Parse intent from natural language query
	intentResult := s.intent.Parse(req.Query)

	// Merge explicit filters with extracted slots
	filters := s.mergeFilters(req.Filters, intentResult.Slots)

	// Set default options
	options := req.Options
	if options == nil {
		options = &model.SearchOptions{
			TopK:     20,
			Offset:   0,
			Semantic: true,
		}
	}

	// Search database with filters and full-text search
	listings, total, err := s.repo.SearchWithFilters(
		ctx,
		filters,
		intentResult.SemanticKeywords,
		options.TopK,
		options.Offset,
	)
	if err != nil {
		return nil, err
	}

	// Build text rank map (from PostgreSQL ts_rank)
	// Note: In production, we'd extract this from the query result
	textRanks := make(map[int64]float64)
	for i, listing := range listings {
		// Higher rank for earlier results (simulated from ORDER BY text_rank DESC)
		textRanks[listing.ListingID] = 1.0 - (float64(i) / float64(len(listings)))
	}

	// Rank and score results
	results := s.ranker.RankResults(listings, textRanks, filters)

	// Calculate response time
	took := time.Since(startTime).Milliseconds()

	// Log search (non-blocking)
	go func() {
		listingIDs := make([]int64, len(results))
		for i, r := range results {
			listingIDs[i] = r.ListingID
		}
		_ = s.repo.LogSearch(context.Background(), req.Query, intentResult.Slots, intentResult.SemanticKeywords, total, listingIDs, int(took))
	}()

	return &model.SearchResponse{
		Results: results,
		Total:   total,
		Intent:  intentResult,
		Took:    took,
	}, nil
}

// SearchStream performs a search with streaming intent parsing
func (s *SearchService) SearchStream(ctx context.Context, req *model.SearchRequest, callback SearchEventCallback) (*model.SearchResponse, error) {
	startTime := time.Now()

	// Send parsing event
	if err := callback("parsing", map[string]any{
		"status": "Parsing your query...",
	}); err != nil {
		return nil, err
	}

	// Parse intent from natural language query with streaming
	intentResult, err := s.intent.ParseStream(ctx, req.Query, func(thinking, content string) error {
		// Send thinking progress
		if thinking != "" {
			return callback("thinking", map[string]any{
				"content": thinking,
			})
		}
		// Send content progress
		if content != "" {
			return callback("content", map[string]any{
				"content": content,
			})
		}
		return nil
	})

	if err != nil {
		return nil, err
	}

	// Send intent parsed event
	if err := callback("intent", intentResult); err != nil {
		return nil, err
	}

	// Merge explicit filters with extracted slots
	filters := s.mergeFilters(req.Filters, intentResult.Slots)

	// Set default options
	options := req.Options
	if options == nil {
		options = &model.SearchOptions{
			TopK:     20,
			Offset:   0,
			Semantic: true,
		}
	}

	// Send searching event
	if err := callback("searching", map[string]any{
		"status": "Searching database...",
	}); err != nil {
		return nil, err
	}

	// Search database with filters and full-text search
	listings, total, err := s.repo.SearchWithFilters(
		ctx,
		filters,
		intentResult.SemanticKeywords,
		options.TopK,
		options.Offset,
	)
	if err != nil {
		return nil, err
	}

	// Build text rank map
	textRanks := make(map[int64]float64)
	for i, listing := range listings {
		textRanks[listing.ListingID] = 1.0 - (float64(i) / float64(len(listings)))
	}

	// Rank and score results
	results := s.ranker.RankResults(listings, textRanks, filters)

	// Calculate response time
	took := time.Since(startTime).Milliseconds()

	// Log search (non-blocking)
	go func() {
		listingIDs := make([]int64, len(results))
		for i, r := range results {
			listingIDs[i] = r.ListingID
		}
		_ = s.repo.LogSearch(context.Background(), req.Query, intentResult.Slots, intentResult.SemanticKeywords, total, listingIDs, int(took))
	}()

	return &model.SearchResponse{
		Results: results,
		Total:   total,
		Intent:  intentResult,
		Took:    took,
	}, nil
}

// GetListing retrieves a single listing by ID
func (s *SearchService) GetListing(ctx context.Context, listingID int64) (*model.Listing, error) {
	return s.repo.GetListingByID(ctx, listingID)
}

// UpdateEmbeddings updates embeddings for multiple listings
func (s *SearchService) UpdateEmbeddings(ctx context.Context, items []model.EmbeddingItem) (int, []string) {
	return s.repo.BatchUpdateEmbeddings(ctx, items)
}

// LogFeedback logs user feedback/action
func (s *SearchService) LogFeedback(ctx context.Context, searchID string, listingID int64, action string) error {
	return s.repo.LogFeedback(ctx, searchID, listingID, action)
}

// mergeFilters merges explicit filters with extracted intent slots
func (s *SearchService) mergeFilters(explicit *model.SearchFilters, slots *model.IntentSlots) *model.SearchFilters {
	// Start with explicit filters
	merged := &model.SearchFilters{}
	if explicit != nil {
		*merged = *explicit
	}

	// Fill in missing fields from intent slots
	if slots != nil {
		if merged.PriceMin == nil && slots.PriceMin != nil {
			merged.PriceMin = slots.PriceMin
		}
		if merged.PriceMax == nil && slots.PriceMax != nil {
			merged.PriceMax = slots.PriceMax
		}
		if merged.Bedrooms == nil && slots.Bedrooms != nil {
			merged.Bedrooms = slots.Bedrooms
		}
		if merged.Bathrooms == nil && slots.Bathrooms != nil {
			merged.Bathrooms = slots.Bathrooms
		}
		if merged.UnitType == nil && slots.UnitType != nil {
			merged.UnitType = slots.UnitType
		}
		if merged.MRTDistanceMax == nil && slots.MRTDistanceMax != nil {
			merged.MRTDistanceMax = slots.MRTDistanceMax
		}
		if merged.Location == nil && slots.Location != nil {
			merged.Location = slots.Location
		}
	}

	// Always ensure completed listings only
	trueVal := true
	merged.IsCompleted = &trueVal

	return merged
}
