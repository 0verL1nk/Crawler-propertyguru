package handler

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"

	"core/internal/model"
	"core/internal/service"

	"github.com/gin-gonic/gin"
)

// SearchHandler handles search-related HTTP requests
type SearchHandler struct {
	searchService *service.SearchService
	defaultLimit  int
	maxLimit      int
}

// NewSearchHandler creates a new search handler
func NewSearchHandler(searchService *service.SearchService, defaultLimit, maxLimit int) *SearchHandler {
	return &SearchHandler{
		searchService: searchService,
		defaultLimit:  defaultLimit,
		maxLimit:      maxLimit,
	}
}

// Search handles POST /api/v1/search
func (h *SearchHandler) Search(c *gin.Context) {
	var req model.SearchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request: " + err.Error()})
		return
	}

	// Set default options if not provided
	if req.Options == nil {
		req.Options = &model.SearchOptions{
			TopK:     h.defaultLimit,
			Offset:   0,
			Semantic: true,
		}
	} else {
		// Validate and cap limits
		if req.Options.TopK <= 0 {
			req.Options.TopK = h.defaultLimit
		}
		if req.Options.TopK > h.maxLimit {
			req.Options.TopK = h.maxLimit
		}
		if req.Options.Offset < 0 {
			req.Options.Offset = 0
		}
	}

	// Perform search
	response, err := h.searchService.Search(c.Request.Context(), &req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Search failed: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, response)
}

// SearchStream handles POST /api/v1/search/stream - SSE streaming search
func (h *SearchHandler) SearchStream(c *gin.Context) {
	var req model.SearchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request: " + err.Error()})
		return
	}

	// Set default options if not provided
	if req.Options == nil {
		req.Options = &model.SearchOptions{
			TopK:     h.defaultLimit,
			Offset:   0,
			Semantic: true,
		}
	} else {
		// Validate and cap limits
		if req.Options.TopK <= 0 {
			req.Options.TopK = h.defaultLimit
		}
		if req.Options.TopK > h.maxLimit {
			req.Options.TopK = h.maxLimit
		}
		if req.Options.Offset < 0 {
			req.Options.Offset = 0
		}
	}

	// Set SSE headers
	c.Header("Content-Type", "text/event-stream; charset=utf-8")
	c.Header("Cache-Control", "no-cache, no-store, must-revalidate")
	c.Header("Pragma", "no-cache")
	c.Header("Expires", "0")
	c.Header("Connection", "keep-alive")
	c.Header("X-Accel-Buffering", "no")
	c.Header("Transfer-Encoding", "chunked")

	// Create flusher for SSE
	flusher, ok := c.Writer.(http.Flusher)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Streaming not supported"})
		return
	}

	// Send initial event
	sendSSE(c, "start", map[string]any{"query": req.Query})
	flusher.Flush()

	// Perform search with streaming
	response, err := h.searchService.SearchStream(c.Request.Context(), &req, func(event string, data any) error {
		sendSSE(c, event, data)
		flusher.Flush()
		return nil
	})

	if err != nil {
		sendSSE(c, "error", map[string]any{"error": err.Error()})
		flusher.Flush()
		return
	}

	// Send final results
	sendSSE(c, "results", response)
	flusher.Flush()

	// Send done event
	sendSSE(c, "done", nil)
	flusher.Flush()
}

// sendSSE sends a Server-Sent Event
func sendSSE(c *gin.Context, event string, data any) {
	if data != nil {
		jsonData, err := json.Marshal(data)
		if err != nil {
			fmt.Fprintf(c.Writer, "event: error\ndata: {\"error\": \"JSON marshal failed\"}\n\n")
			return
		}
		fmt.Fprintf(c.Writer, "event: %s\ndata: %s\n\n", event, string(jsonData))
	} else {
		fmt.Fprintf(c.Writer, "event: %s\ndata: {}\n\n", event)
	}
}

// GetListing handles GET /api/v1/listings/:id
func (h *SearchHandler) GetListing(c *gin.Context) {
	listingIDStr := c.Param("id")
	listingID, err := strconv.ParseInt(listingIDStr, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid listing ID"})
		return
	}

	listing, err := h.searchService.GetListing(c.Request.Context(), listingID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get listing: " + err.Error()})
		return
	}

	if listing == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Listing not found"})
		return
	}

	c.JSON(http.StatusOK, listing)
}
