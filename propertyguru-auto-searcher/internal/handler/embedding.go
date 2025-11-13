package handler

import (
	"net/http"

	"core/internal/model"
	"core/internal/service"

	"github.com/gin-gonic/gin"
)

// EmbeddingHandler handles embedding-related HTTP requests
type EmbeddingHandler struct {
	searchService *service.SearchService
}

// NewEmbeddingHandler creates a new embedding handler
func NewEmbeddingHandler(searchService *service.SearchService) *EmbeddingHandler {
	return &EmbeddingHandler{
		searchService: searchService,
	}
}

// BatchUpdate handles POST /api/v1/embeddings/batch
func (h *EmbeddingHandler) BatchUpdate(c *gin.Context) {
	var req model.EmbeddingBatchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request: " + err.Error()})
		return
	}

	if len(req.Embeddings) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "No embeddings provided"})
		return
	}

	// Validate embedding dimensions
	for i, item := range req.Embeddings {
		if len(item.Embedding) != 1536 {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid embedding dimension at index " + string(rune(i)) + ", expected 1536",
			})
			return
		}
	}

	// Update embeddings
	success, errors := h.searchService.UpdateEmbeddings(c.Request.Context(), req.Embeddings)

	response := model.EmbeddingBatchResponse{
		Success: success,
		Failed:  len(req.Embeddings) - success,
		Errors:  errors,
	}

	if len(errors) > 0 {
		c.JSON(http.StatusPartialContent, response)
	} else {
		c.JSON(http.StatusOK, response)
	}
}
