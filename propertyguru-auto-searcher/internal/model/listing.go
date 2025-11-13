package model

import (
	"database/sql/driver"
	"encoding/json"
	"time"

	"github.com/pgvector/pgvector-go"
)

// Listing represents a property listing
type Listing struct {
	ID               int64           `json:"id" db:"id"`
	ListingID        int64           `json:"listing_id" db:"listing_id"`
	Title            *string         `json:"title,omitempty" db:"title"`
	Price            *float64        `json:"price,omitempty" db:"price"`
	PricePerSqft     *float64        `json:"price_per_sqft,omitempty" db:"price_per_sqft"`
	Bedrooms         *int            `json:"bedrooms,omitempty" db:"bedrooms"`
	Bathrooms        *int            `json:"bathrooms,omitempty" db:"bathrooms"`
	AreaSqft         *float64        `json:"area_sqft,omitempty" db:"area_sqft"`
	UnitType         *string         `json:"unit_type,omitempty" db:"unit_type"`
	Tenure           *string         `json:"tenure,omitempty" db:"tenure"`
	BuildYear        *int            `json:"build_year,omitempty" db:"build_year"`
	MRTStation       *string         `json:"mrt_station,omitempty" db:"mrt_station"`
	MRTDistanceM     *int            `json:"mrt_distance_m,omitempty" db:"mrt_distance_m"`
	Location         *string         `json:"location,omitempty" db:"location"`
	Latitude         *float64        `json:"latitude,omitempty" db:"latitude"`
	Longitude        *float64        `json:"longitude,omitempty" db:"longitude"`
	ListedDate       *time.Time      `json:"listed_date,omitempty" db:"listed_date"`
	ListedAge        *string         `json:"listed_age,omitempty" db:"listed_age"`
	GreenScoreValue  *float64        `json:"green_score_value,omitempty" db:"green_score_value"`
	GreenScoreMax    *float64        `json:"green_score_max,omitempty" db:"green_score_max"`
	URL              *string         `json:"url,omitempty" db:"url"`
	PropertyDetails  JSONMap         `json:"property_details,omitempty" db:"property_details"`
	Description      *string         `json:"description,omitempty" db:"description"`
	DescriptionTitle *string         `json:"description_title,omitempty" db:"description_title"`
	Amenities        JSONArray       `json:"amenities,omitempty" db:"amenities"`
	Facilities       JSONArray       `json:"facilities,omitempty" db:"facilities"`
	IsCompleted      bool            `json:"is_completed" db:"is_completed"`
	Embedding        pgvector.Vector `json:"-" db:"embedding"`
	TextRank         *float64        `json:"text_rank,omitempty" db:"text_rank"` // Full-text search ranking
	CreatedAt        time.Time       `json:"created_at" db:"created_at"`
	UpdatedAt        time.Time       `json:"updated_at" db:"updated_at"`
}

// ListingSearchResult represents a search result with additional metadata
type ListingSearchResult struct {
	Listing
	Score          float64  `json:"score"`
	MatchedReasons []string `json:"matched_reasons"`
}

// JSONArray represents a JSON array field
type JSONArray []string

// Value implements driver.Valuer interface
func (j JSONArray) Value() (driver.Value, error) {
	if j == nil {
		return nil, nil
	}
	return json.Marshal(j)
}

// Scan implements sql.Scanner interface
func (j *JSONArray) Scan(value interface{}) error {
	if value == nil {
		*j = nil
		return nil
	}
	bytes, ok := value.([]byte)
	if !ok {
		return json.Unmarshal([]byte(value.(string)), j)
	}
	return json.Unmarshal(bytes, j)
}

// JSONMap represents a JSON object field
type JSONMap map[string]interface{}

// Value implements driver.Valuer interface
func (j JSONMap) Value() (driver.Value, error) {
	if j == nil {
		return nil, nil
	}
	return json.Marshal(j)
}

// Scan implements sql.Scanner interface
func (j *JSONMap) Scan(value interface{}) error {
	if value == nil {
		*j = nil
		return nil
	}
	bytes, ok := value.([]byte)
	if !ok {
		return json.Unmarshal([]byte(value.(string)), j)
	}
	return json.Unmarshal(bytes, j)
}
