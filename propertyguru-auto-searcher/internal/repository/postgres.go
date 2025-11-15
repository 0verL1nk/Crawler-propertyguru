package repository

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
	"time"

	"core/internal/model"
	"core/internal/utils"

	"github.com/jmoiron/sqlx"
	_ "github.com/lib/pq"
	"github.com/pgvector/pgvector-go"
)

// PostgresRepository handles database operations
type PostgresRepository struct {
	db *sqlx.DB
}

// NewPostgresRepository creates a new PostgreSQL repository
func NewPostgresRepository(dsn string, maxConn, maxIdleConn int) (*PostgresRepository, error) {
	// Disable prepared statement caching to avoid "unnamed prepared statement does not exist" errors
	if !strings.Contains(dsn, "?") {
		dsn += "?prefer_simple_protocol=true"
	} else {
		dsn += "&prefer_simple_protocol=true"
	}

	db, err := sqlx.Connect("postgres", dsn)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}

	db.SetMaxOpenConns(maxConn)
	db.SetMaxIdleConns(maxIdleConn)
	db.SetConnMaxLifetime(5 * time.Minute) // Shorter lifetime to avoid stale connections
	db.SetConnMaxIdleTime(2 * time.Minute) // Close idle connections sooner

	// Test connection
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	return &PostgresRepository{db: db}, nil
}

// Close closes the database connection
func (r *PostgresRepository) Close() error {
	return r.db.Close()
}

// SearchWithFilters performs a filtered search with full-text search
func (r *PostgresRepository) SearchWithFilters(
	ctx context.Context,
	filters *model.SearchFilters,
	semanticKeywords []string,
	limit, offset int,
) ([]model.Listing, int, error) {
	// Build WHERE clause
	whereClauses := []string{"1=1"}
	args := []interface{}{}
	argIndex := 1

	// Always filter for completed listings
	whereClauses = append(whereClauses, "is_completed = true")

	if filters != nil {
		if filters.PriceMin != nil {
			whereClauses = append(whereClauses, fmt.Sprintf("price >= $%d", argIndex))
			args = append(args, *filters.PriceMin)
			argIndex++
		}
		if filters.PriceMax != nil {
			whereClauses = append(whereClauses, fmt.Sprintf("price <= $%d", argIndex))
			args = append(args, *filters.PriceMax)
			argIndex++
		}
		if filters.Bedrooms != nil {
			whereClauses = append(whereClauses, fmt.Sprintf("bedrooms = $%d", argIndex))
			args = append(args, *filters.Bedrooms)
			argIndex++
		}
		if filters.Bathrooms != nil {
			whereClauses = append(whereClauses, fmt.Sprintf("bathrooms = $%d", argIndex))
			args = append(args, *filters.Bathrooms)
			argIndex++
		}
		if filters.AreaSqftMin != nil {
			whereClauses = append(whereClauses, fmt.Sprintf("area_sqft >= $%d", argIndex))
			args = append(args, *filters.AreaSqftMin)
			argIndex++
		}
		if filters.AreaSqftMax != nil {
			whereClauses = append(whereClauses, fmt.Sprintf("area_sqft <= $%d", argIndex))
			args = append(args, *filters.AreaSqftMax)
			argIndex++
		}
		if filters.UnitType != nil {
			whereClauses = append(whereClauses, fmt.Sprintf("unit_type ILIKE $%d", argIndex))
			args = append(args, "%"+*filters.UnitType+"%")
			argIndex++
		}
		if filters.MRTDistanceMax != nil {
			whereClauses = append(whereClauses, fmt.Sprintf("mrt_distance_m <= $%d", argIndex))
			args = append(args, *filters.MRTDistanceMax)
			argIndex++
		}
		if filters.Location != nil {
			whereClauses = append(whereClauses, fmt.Sprintf("location ILIKE $%d", argIndex))
			args = append(args, "%"+*filters.Location+"%")
			argIndex++
		}
		// JSONB amenities filtering - fuzzy matching with common aliases
		if len(filters.Amenities) > 0 {
			amenityConds, amenityParams, newIndex := utils.BuildFuzzyAmenityQuery(filters.Amenities, argIndex)
			whereClauses = append(whereClauses, amenityConds...)
			args = append(args, amenityParams...)
			argIndex = newIndex
		}
		// JSONB facilities filtering - fuzzy matching with common aliases
		if len(filters.Facilities) > 0 {
			facilityConds, facilityParams, newIndex := utils.BuildFuzzyFacilityQuery(filters.Facilities, argIndex)
			whereClauses = append(whereClauses, facilityConds...)
			args = append(args, facilityParams...)
			argIndex = newIndex
		}
	}

	whereClause := strings.Join(whereClauses, " AND ")

	// Count total matching records
	countQuery := fmt.Sprintf("SELECT COUNT(*) FROM listing_info WHERE %s", whereClause)
	var total int
	err := r.db.GetContext(ctx, &total, countQuery, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to count results: %w", err)
	}

	// Build SELECT query with full-text search ranking
	selectQuery := fmt.Sprintf(`
		SELECT 
			id, listing_id, title, price, price_per_sqft, bedrooms, bathrooms,
			area_sqft, unit_type, tenure, build_year, mrt_station, mrt_distance_m,
			location, latitude, longitude, listed_date, listed_age,
			green_score_value, green_score_max, url, property_details,
			description, description_title, amenities, facilities, is_completed,
			created_at, updated_at,
			ts_rank(search_vector, plainto_tsquery('english', $%d)) as text_rank
		FROM listing_info
		WHERE %s
		ORDER BY text_rank DESC, listed_date DESC NULLS LAST
		LIMIT $%d OFFSET $%d
	`, argIndex, whereClause, argIndex+1, argIndex+2)

	// Add semantic keywords for full-text search
	searchText := strings.Join(semanticKeywords, " ")
	args = append(args, searchText, limit, offset)

	var listings []model.Listing
	err = r.db.SelectContext(ctx, &listings, selectQuery, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to fetch listings: %w", err)
	}

	return listings, total, nil
}

// GetListingByID retrieves a single listing by its ID
func (r *PostgresRepository) GetListingByID(ctx context.Context, listingID int64) (*model.Listing, error) {
	var listing model.Listing
	query := `
		SELECT 
			id, listing_id, title, price, price_per_sqft, bedrooms, bathrooms,
			area_sqft, unit_type, tenure, build_year, mrt_station, mrt_distance_m,
			location, latitude, longitude, listed_date, listed_age,
			green_score_value, green_score_max, url, property_details,
			description, description_title, amenities, facilities, is_completed,
			created_at, updated_at
		FROM listing_info
		WHERE listing_id = $1 AND is_completed = true
	`
	err := r.db.GetContext(ctx, &listing, query, listingID)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get listing: %w", err)
	}
	return &listing, nil
}

// UpdateEmbedding updates the embedding vector for a listing
func (r *PostgresRepository) UpdateEmbedding(ctx context.Context, listingID int64, embedding []float32) error {
	vec := pgvector.NewVector(embedding)
	query := `UPDATE listing_info SET embedding = $1, updated_at = NOW() WHERE listing_id = $2`
	_, err := r.db.ExecContext(ctx, query, vec, listingID)
	if err != nil {
		return fmt.Errorf("failed to update embedding: %w", err)
	}
	return nil
}

// BatchUpdateEmbeddings updates embeddings for multiple listings
func (r *PostgresRepository) BatchUpdateEmbeddings(ctx context.Context, items []model.EmbeddingItem) (int, []string) {
	success := 0
	var errors []string

	tx, err := r.db.BeginTxx(ctx, nil)
	if err != nil {
		errors = append(errors, fmt.Sprintf("failed to start transaction: %v", err))
		return success, errors
	}
	defer tx.Rollback()

	stmt, err := tx.PreparexContext(ctx, `UPDATE listing_info SET embedding = $1, updated_at = NOW() WHERE listing_id = $2`)
	if err != nil {
		errors = append(errors, fmt.Sprintf("failed to prepare statement: %v", err))
		return success, errors
	}
	defer stmt.Close()

	for _, item := range items {
		vec := pgvector.NewVector(item.Embedding)
		_, err := stmt.ExecContext(ctx, vec, item.ListingID)
		if err != nil {
			errors = append(errors, fmt.Sprintf("listing_id %d: %v", item.ListingID, err))
			continue
		}
		success++
	}

	if err := tx.Commit(); err != nil {
		errors = append(errors, fmt.Sprintf("failed to commit transaction: %v", err))
		return 0, errors
	}

	return success, errors
}

// LogSearch logs a search query
func (r *PostgresRepository) LogSearch(ctx context.Context, query string, slots *model.IntentSlots, keywords []string, resultCount int, listingIDs []int64, responseTimeMs int) error {
	logQuery := `
		INSERT INTO search_logs (query, intent_slots, semantic_keywords, result_count, returned_listing_ids, response_time_ms)
		VALUES ($1, $2, $3, $4, $5, $6)
	`
	_, err := r.db.ExecContext(ctx, logQuery, query, slots, keywords, resultCount, listingIDs, responseTimeMs)
	if err != nil {
		return fmt.Errorf("failed to log search: %w", err)
	}
	return nil
}

// LogFeedback logs user feedback/action
func (r *PostgresRepository) LogFeedback(ctx context.Context, searchID string, listingID int64, action string) error {
	query := `
		UPDATE search_logs 
		SET clicked_listing_id = $2, action = $3
		WHERE search_id = $1
	`
	_, err := r.db.ExecContext(ctx, query, searchID, listingID, action)
	if err != nil {
		return fmt.Errorf("failed to log feedback: %w", err)
	}
	return nil
}

// VectorSearch performs semantic similarity search (Phase 2, MVP 暂不实现)
func (r *PostgresRepository) VectorSearch(ctx context.Context, queryEmbedding []float32, limit int, filters *model.SearchFilters) ([]model.Listing, error) {
	// TODO: Implement in Phase 2
	return nil, fmt.Errorf("vector search not implemented in MVP")
}
