package handlers

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/speckle/model-checker/internal/auth"
	"github.com/speckle/model-checker/internal/logging"
)

func PreviewStream(c *gin.Context) {
	start := time.Now()
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	// Get model IDs from query parameter
	modelIDsStr := c.Query("modelIds")
	var modelIDs []string
	if err := json.Unmarshal([]byte(modelIDsStr), &modelIDs); err != nil {
		logging.LogColor(logging.ColorRed, "Failed to parse model IDs: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid model IDs"})
		return
	}

	// Get user token
	tokenStart := time.Now()
	userToken, err := auth.GetUserToken(user.ID)
	if err != nil {
		logging.LogColor(logging.ColorRed, "Failed to get user token: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get user token"})
		return
	}
	logging.LogColor(logging.ColorReset, "Getting user token took: %v", time.Since(tokenStart))

	// Set up SSE headers
	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("Transfer-Encoding", "chunked")

	// Create a channel to receive preview updates
	previewChan := make(chan map[string]string, len(modelIDs))

	// Start fetching previews in the background
	go func() {
		previews := previewService.GetModelPreviews(modelIDs, userToken.SpeckleToken)
		previewChan <- previews
	}()

	// Stream previews as they become available
	previews := <-previewChan
	for modelID, dataURI := range previews {
		if dataURI != "" {
			// Send each preview as a separate event
			c.SSEvent("preview", gin.H{
				"modelId":    modelID,
				"previewUrl": dataURI,
			})
		}
	}

	// Send completion event
	c.SSEvent("complete", gin.H{
		"total": len(previews),
		"took":  time.Since(start).String(),
	})
}
