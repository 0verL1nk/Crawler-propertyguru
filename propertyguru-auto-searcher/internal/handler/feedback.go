package handler

import (
	"net/http"

	"core/internal/model"
	"core/internal/service"

	"github.com/gin-gonic/gin"
)

// FeedbackHandler handles feedback-related HTTP requests
type FeedbackHandler struct {
	searchService *service.SearchService
}

// NewFeedbackHandler creates a new feedback handler
func NewFeedbackHandler(searchService *service.SearchService) *FeedbackHandler {
	return &FeedbackHandler{
		searchService: searchService,
	}
}

// Submit handles POST /api/v1/feedback
func (h *FeedbackHandler) Submit(c *gin.Context) {
	var req model.FeedbackRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request: " + err.Error()})
		return
	}

	// Validate action
	validActions := map[string]bool{
		"click":        true,
		"contact":      true,
		"view_details": true,
	}

	if !validActions[req.Action] {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid action. Must be one of: click, contact, view_details"})
		return
	}

	// Log feedback
	err := h.searchService.LogFeedback(c.Request.Context(), req.SearchID, req.ListingID, req.Action)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to log feedback: " + err.Error()})
		return
	}

	response := model.FeedbackResponse{
		Success: true,
		Message: "Feedback logged successfully",
	}

	c.JSON(http.StatusOK, response)
}
