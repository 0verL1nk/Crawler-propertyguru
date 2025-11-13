package service

import (
	"math"
	"sort"
	"time"

	"core/internal/model"
)

// Match reason constants
const (
	ReasonBedroomsMatch   = "Bedrooms match"
	ReasonBathroomsMatch  = "Bathrooms match"
	ReasonUnitTypeMatch   = "Unit type match"
	ReasonNearMRT         = "Near MRT"
	ReasonLocationMatch   = "Location match"
	ReasonPriceMatch      = "Price within budget"
	ReasonContentRelevant = "Content relevant"
	ReasonNewlyListed     = "Newly listed"
	ReasonHighGreenScore  = "High green score"
	ReasonGeneralMatch    = "General match"
)

// Ranker handles ranking and scoring of search results
type Ranker struct {
	weightText    float64
	weightPrice   float64
	weightRecency float64
}

// NewRanker creates a new ranker with specified weights
func NewRanker(weightText, weightPrice, weightRecency float64) *Ranker {
	return &Ranker{
		weightText:    weightText,
		weightPrice:   weightPrice,
		weightRecency: weightRecency,
	}
}

// RankResults scores and ranks search results
func (r *Ranker) RankResults(
	listings []model.Listing,
	textRanks map[int64]float64,
	filters *model.SearchFilters,
) []model.ListingSearchResult {
	results := make([]model.ListingSearchResult, 0, len(listings))

	for _, listing := range listings {
		result := model.ListingSearchResult{
			Listing:        listing,
			Score:          0,
			MatchedReasons: []string{},
		}

		// Calculate text relevance score (normalized to 0-1)
		textScore := r.normalizeTextScore(textRanks[listing.ListingID])

		// Calculate price match score (normalized to 0-1)
		priceScore := r.calculatePriceScore(listing.Price, filters)

		// Calculate recency score (normalized to 0-1)
		recencyScore := r.calculateRecencyScore(listing.ListedDate)

		// Combined weighted score
		result.Score = (r.weightText * textScore) +
			(r.weightPrice * priceScore) +
			(r.weightRecency * recencyScore)

		// Generate matched reasons
		result.MatchedReasons = r.generateMatchedReasons(listing, filters, textScore, priceScore)

		results = append(results, result)
	}

	// Sort by score descending
	sort.Slice(results, func(i, j int) bool {
		return results[i].Score > results[j].Score
	})

	return results
}

// normalizeTextScore normalizes PostgreSQL ts_rank score to 0-1 range
func (r *Ranker) normalizeTextScore(rank float64) float64 {
	// ts_rank typically returns values between 0 and 1, but can go higher
	// We'll cap it at 1.0
	if rank > 1.0 {
		return 1.0
	}
	return rank
}

// calculatePriceScore calculates how well the price matches user's budget
func (r *Ranker) calculatePriceScore(price *float64, filters *model.SearchFilters) float64 {
	if price == nil {
		return 0.5 // Neutral score if no price
	}

	if filters == nil || (filters.PriceMin == nil && filters.PriceMax == nil) {
		return 1.0 // Full score if no price filter
	}

	actualPrice := *price

	// If within range, calculate proximity to midpoint
	if filters.PriceMin != nil && filters.PriceMax != nil {
		minPrice := *filters.PriceMin
		maxPrice := *filters.PriceMax

		if actualPrice < minPrice || actualPrice > maxPrice {
			// Outside range, penalize
			return 0.0
		}

		// Within range, score based on distance from midpoint
		midpoint := (minPrice + maxPrice) / 2
		priceRange := maxPrice - minPrice

		if priceRange == 0 {
			return 1.0
		}

		distance := math.Abs(actualPrice - midpoint)
		score := 1.0 - (distance / (priceRange / 2))

		if score < 0 {
			score = 0
		}
		return score
	}

	// Only min or max specified
	if filters.PriceMin != nil {
		if actualPrice < *filters.PriceMin {
			return 0.0
		}
		return 1.0
	}

	if filters.PriceMax != nil {
		if actualPrice > *filters.PriceMax {
			return 0.0
		}
		// Closer to max is better
		score := actualPrice / *filters.PriceMax
		if score > 1.0 {
			score = 1.0
		}
		return score
	}

	return 1.0
}

// calculateRecencyScore calculates recency score based on listing date
func (r *Ranker) calculateRecencyScore(listedDate *time.Time) float64 {
	if listedDate == nil {
		return 0.5 // Neutral score if no date
	}

	now := time.Now()
	daysSinceListed := now.Sub(*listedDate).Hours() / 24

	// Exponential decay: newer listings get higher scores
	// Score = e^(-0.01 * days)
	// After 30 days: ~0.74, after 60 days: ~0.55, after 90 days: ~0.41
	score := math.Exp(-0.01 * daysSinceListed)

	if score > 1.0 {
		score = 1.0
	}
	if score < 0 {
		score = 0
	}

	return score
}

// generateMatchedReasons generates human-readable reasons for why this listing matched
func (r *Ranker) generateMatchedReasons(
	listing model.Listing,
	filters *model.SearchFilters,
	textScore float64,
	priceScore float64,
) []string {
	reasons := []string{}

	// Check filter matches
	if filters != nil {
		if filters.Bedrooms != nil && listing.Bedrooms != nil && *listing.Bedrooms == *filters.Bedrooms {
			reasons = append(reasons, ReasonBedroomsMatch)
		}

		if filters.Bathrooms != nil && listing.Bathrooms != nil && *listing.Bathrooms == *filters.Bathrooms {
			reasons = append(reasons, ReasonBathroomsMatch)
		}

		if filters.UnitType != nil && listing.UnitType != nil {
			reasons = append(reasons, ReasonUnitTypeMatch)
		}

		if filters.MRTDistanceMax != nil && listing.MRTDistanceM != nil && *listing.MRTDistanceM <= *filters.MRTDistanceMax {
			reasons = append(reasons, ReasonNearMRT)
		}

		if filters.Location != nil && listing.Location != nil {
			reasons = append(reasons, ReasonLocationMatch)
		}

		if priceScore > 0.8 {
			reasons = append(reasons, ReasonPriceMatch)
		}
	}

	// Check text relevance
	if textScore > 0.1 {
		reasons = append(reasons, ReasonContentRelevant)
	}

	// Check recency
	if listing.ListedDate != nil {
		daysSince := time.Since(*listing.ListedDate).Hours() / 24
		if daysSince < 7 {
			reasons = append(reasons, ReasonNewlyListed)
		}
	}

	// Check special features
	if listing.GreenScoreValue != nil && *listing.GreenScoreValue >= 4.0 {
		reasons = append(reasons, ReasonHighGreenScore)
	}

	if len(reasons) == 0 {
		reasons = append(reasons, ReasonGeneralMatch)
	}

	return reasons
}
