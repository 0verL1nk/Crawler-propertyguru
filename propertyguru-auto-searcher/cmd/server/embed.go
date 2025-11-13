//go:build embed
// +build embed

package main

import (
	"embed"
	"io"
	"io/fs"
	"log"
	"net/http"
	"path"

	"github.com/gin-gonic/gin"
)

//go:embed web/dist
var webDist embed.FS

// setupStaticFiles configures the static file serving with embedded frontend
func setupStaticFiles(router *gin.Engine) {
	log.Println("📦 Using embedded frontend assets")

	// Get the sub-filesystem for dist directory
	distFS, err := fs.Sub(webDist, "web/dist")
	if err != nil {
		log.Fatalf("Failed to get dist subdirectory: %v", err)
	}

	// Serve static files from embedded FS
	router.NoRoute(func(c *gin.Context) {
		urlPath := c.Request.URL.Path

		// Skip API routes (they are handled by other routes)
		if len(urlPath) >= 4 && urlPath[:4] == "/api" {
			c.JSON(404, gin.H{"error": "API endpoint not found"})
			return
		}

		// Clean the path
		cleanPath := path.Clean(urlPath)
		if cleanPath == "/" {
			cleanPath = "/index.html"
		} else {
			// Remove leading slash for fs.Open
			cleanPath = cleanPath[1:]
		}

		// Try to open the file
		file, err := distFS.Open(cleanPath)
		if err == nil {
			defer file.Close()
			stat, err := file.Stat()
			if err == nil && !stat.IsDir() {
				// File exists, serve it
				content, err := io.ReadAll(file)
				if err == nil {
					// Determine content type
					contentType := "text/html; charset=utf-8"
					ext := path.Ext(cleanPath)
					switch ext {
					case ".js":
						contentType = "application/javascript; charset=utf-8"
					case ".css":
						contentType = "text/css; charset=utf-8"
					case ".json":
						contentType = "application/json; charset=utf-8"
					case ".png":
						contentType = "image/png"
					case ".jpg", ".jpeg":
						contentType = "image/jpeg"
					case ".svg":
						contentType = "image/svg+xml"
					case ".ico":
						contentType = "image/x-icon"
					}
					c.Data(http.StatusOK, contentType, content)
					return
				}
			}
		}

		// File not found, serve index.html for SPA routing
		indexFile, err := distFS.Open("index.html")
		if err != nil {
			c.String(http.StatusNotFound, "404 page not found")
			return
		}
		defer indexFile.Close()

		content, err := io.ReadAll(indexFile)
		if err != nil {
			c.String(http.StatusInternalServerError, "Error reading index.html")
			return
		}

		c.Data(http.StatusOK, "text/html; charset=utf-8", content)
	})
}
