//go:build !embed
// +build !embed

package main

import (
	"log"

	"github.com/gin-gonic/gin"
)

// setupStaticFiles configures static file serving for development (no embedding)
func setupStaticFiles(router *gin.Engine) {
	log.Println("🔧 Using local filesystem for frontend assets (development mode)")
	log.Println("   Frontend should be served separately with: cd web && npm run dev")

	// Serve old static files for backward compatibility
	router.Static("/static", "./web/static")
	router.StaticFile("/", "./web/index.html")
	router.StaticFile("/favicon.ico", "./web/static/favicon.ico")

	// For new React frontend, redirect to dev server
	router.NoRoute(func(c *gin.Context) {
		if len(c.Request.URL.Path) > 4 && c.Request.URL.Path[:4] == "/api" {
			c.JSON(404, gin.H{"error": "API endpoint not found"})
			return
		}
		c.JSON(200, gin.H{
			"message": "Frontend is running separately",
			"dev_url": "http://localhost:3000",
			"hint":    "Run 'cd web && npm run dev' to start the frontend",
		})
	})
}
