package handlers

import (
	"net/http"

	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/speckle/model-checker/internal/auth"
	"github.com/speckle/model-checker/internal/logging"

	"encoding/json"

	"log"

	"sync"

	"cloud.google.com/go/storage"
	"github.com/speckle/model-checker/internal/services"
)

const (
	projectsPerPage  = 5
	modelsPerProject = 20
	versionsPerModel = 1
)

var previewService = services.NewPreviewService()

// GetModelPreviewDataURI fetches or caches and returns the data URI for a model preview
func GetModelPreviewDataURI(modelID string, userToken string) string {
	return previewService.GetModelPreviewDataURI(modelID, userToken)
}

// GetProjects handles fetching projects
func GetProjects(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		if strings.HasPrefix(c.Request.URL.Path, "/api/") {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		} else {
			c.Redirect(http.StatusFound, "/")
		}
		return
	}

	userToken, err := auth.GetUserToken(user.ID)
	if err != nil || userToken == nil {
		if strings.HasPrefix(c.Request.URL.Path, "/api/") {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		} else {
			c.Redirect(http.StatusFound, "/")
		}
		return
	}

	// Get cursor from query parameter
	projectsCursor := c.Query("projects_cursor")
	logging.LogColor(logging.ColorYellow, "Projects Cursor: %v", projectsCursor)

	// Get projects with pagination
	projects, nextCursor, err := auth.GetProjectsWithPagination(userToken.SpeckleToken, projectsPerPage, modelsPerProject, versionsPerModel, projectsCursor, "")
	if err != nil {
		if strings.HasPrefix(c.Request.URL.Path, "/api/") {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch projects"})
		} else {
			c.HTML(http.StatusInternalServerError, "base", gin.H{
				"title":   "Error",
				"content": "error",
				"error":   "Failed to fetch projects",
			})
		}
		return
	}

	// Detect HTMX request
	isHTMX := c.GetHeader("HX-Request") == "true"
	if isHTMX {
		// Render only the project list content and OOB button
		c.HTML(http.StatusOK, "project_list_content", gin.H{
			"projects":          projects,
			"has_more_projects": nextCursor != "",
			"next_cursor":       nextCursor,
		})
		c.HTML(http.StatusOK, "load_more_oob", gin.H{
			"has_more_projects":    nextCursor != "",
			"next_projects_cursor": nextCursor,
		})
		return
	}

	// Handle API request
	if strings.HasPrefix(c.Request.URL.Path, "/api/") {
		c.JSON(http.StatusOK, gin.H{
			"projects":   projects,
			"nextCursor": nextCursor,
		})
		return
	}

	// Regular HTML response
	c.HTML(http.StatusOK, "base", gin.H{
		"title":             "Projects",
		"user":              user,
		"content":           "projects",
		"projects":          projects,
		"has_more_projects": nextCursor != "",
		"next_cursor":       nextCursor,
	})
}

// SearchProjects handles searching for projects
func SearchProjects(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.Redirect(http.StatusFound, "/")
		return
	}

	userToken, err := auth.GetUserToken(user.ID)
	if err != nil || userToken == nil {
		c.Redirect(http.StatusFound, "/")
		return
	}

	searchQuery := c.Query("q")
	if searchQuery == "" {
		c.Redirect(http.StatusFound, "/projects")
		return
	}

	projects, err := auth.SearchProjects(userToken.SpeckleToken, searchQuery, modelsPerProject, versionsPerModel)
	if err != nil {
		c.HTML(http.StatusInternalServerError, "error.html", gin.H{
			"title": "Error",
			"error": "Failed to search projects",
		})
		return
	}

	// Return just the project list content for HTMX requests
	c.HTML(http.StatusOK, "project_list_content", gin.H{
		"projects":             projects,
		"has_more_projects":    false,
		"next_projects_cursor": "",
	})
}

// ProjectDetails handles fetching project details
func ProjectDetails(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.Redirect(http.StatusFound, "/")
		return
	}

	userToken, err := auth.GetUserToken(user.ID)
	if err != nil || userToken == nil {
		c.Redirect(http.StatusFound, "/")
		return
	}

	projectID := c.Param("project_id")
	project, err := auth.GetProjectDetails(userToken.SpeckleToken, projectID)
	if err != nil {
		c.HTML(http.StatusInternalServerError, "error.html", gin.H{
			"title": "Error",
			"error": "Failed to fetch project details",
		})
		return
	}

	rulesets, err := auth.GetProjectRulesets(projectID)
	if err != nil {
		c.HTML(http.StatusInternalServerError, "error.html", gin.H{
			"title": "Error",
			"error": "Failed to fetch project rulesets",
		})
		return
	}

	c.HTML(http.StatusOK, "project_rulesets.html", gin.H{
		"title":    project.Name,
		"user":     user,
		"project":  project,
		"rulesets": rulesets,
	})
}

// Handler handles project-related requests
type Handler struct {
	speckleService *services.SpeckleService
}

// NewHandler creates a new Handler instance
func NewHandler() *Handler {
	return &Handler{
		speckleService: services.NewSpeckleService(),
	}
}

// GetProjectModels handles fetching models for a project
func GetProjectModels(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	userToken, err := auth.GetUserToken(user.ID)
	if err != nil || userToken == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid user token"})
		return
	}

	projectID := c.Param("project_id")
	project, err := auth.GetProjectDetails(userToken.SpeckleToken, projectID)
	if err != nil {
		c.HTML(http.StatusInternalServerError, "error.html", gin.H{
			"title": "Error",
			"error": "Failed to fetch project details",
		})
		return
	}

	// Extract model IDs
	modelIDs := make([]string, len(project.Models.Items))
	for i, model := range project.Models.Items {
		modelIDs[i] = model.ID
	}

	// Return HTML with just the model IDs, no preview data URIs
	c.HTML(http.StatusOK, "partials/models_grid.html", gin.H{
		"models":     project.Models.Items,
		"model_ids":  modelIDs,
		"project_id": projectID,
	})
}

// GetModelPreview handles individual preview image requests
func GetModelPreview(c *gin.Context) {
	start := time.Now()
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	userToken, err := auth.GetUserToken(user.ID)
	if err != nil || userToken == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	modelID := c.Param("model_id")
	if modelID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Missing model_id"})
		return
	}

	// Get the preview data URI
	previewURI := GetModelPreviewDataURI(modelID, userToken.SpeckleToken)
	if previewURI == "" {
		c.JSON(http.StatusNotFound, gin.H{"error": "Preview not found"})
		return
	}

	log.Printf("Loaded preview for model %s in %v", modelID, time.Since(start))
	c.Data(http.StatusOK, "text/plain; charset=utf-8", []byte(previewURI))
}

// generateSignedURL creates a signed URL for the object in Firebase Storage.
func generateSignedURL(bucketName, objectName string, expiry time.Duration) (string, error) {
	googleAccessID, err := auth.GetGoogleAccessID()
	if err != nil {
		return "", err
	}
	privateKey, err := auth.GetPrivateKey()
	if err != nil {
		return "", err
	}
	return storage.SignedURL(bucketName, objectName, &storage.SignedURLOptions{
		GoogleAccessID: googleAccessID,
		PrivateKey:     privateKey,
		Method:         "GET",
		Expires:        time.Now().Add(expiry),
	})
}

// GetModelPreviewStream handles streaming preview images for models using SSE
func GetModelPreviewStream(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	userToken, err := auth.GetUserToken(user.ID)
	if err != nil || userToken == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid user token"})
		return
	}

	// Get model IDs from query parameter
	modelIDsStr := c.Query("modelIds")
	if modelIDsStr == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Missing modelIds parameter"})
		return
	}

	var modelIDs []string
	if err := json.Unmarshal([]byte(modelIDsStr), &modelIDs); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid modelIds format"})
		return
	}

	// Set up SSE headers
	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("Transfer-Encoding", "chunked")

	// Create a channel to receive preview results
	previewChan := make(chan struct {
		modelID    string
		previewURL string
	})

	// Create a WaitGroup to track when all goroutines are done
	var wg sync.WaitGroup
	wg.Add(len(modelIDs))

	// Start goroutines to fetch previews concurrently
	for _, modelID := range modelIDs {
		go func(modelID string) {
			defer wg.Done()
			previewDataURI := GetModelPreviewDataURI(modelID, userToken.SpeckleToken)
			if previewDataURI != "" {
				previewChan <- struct {
					modelID    string
					previewURL string
				}{modelID, previewDataURI}
			}
		}(modelID)
	}

	// Start a goroutine to close the channel when all previews are done
	go func() {
		wg.Wait()
		close(previewChan)
	}()

	// Stream previews as they become available
	previewCount := 0
	totalPreviews := len(modelIDs)

	// Set a timeout for the entire operation
	timeout := time.After(10 * time.Second)

	// Process previews until either all are done or we hit the timeout
	for previewCount < totalPreviews {
		select {
		case preview, ok := <-previewChan:
			if !ok {
				// Channel closed, all previews are done
				goto done
			}
			previewData := gin.H{
				"modelId":    preview.modelID,
				"previewUrl": preview.previewURL,
			}
			previewJSON, _ := json.Marshal(previewData)
			c.SSEvent("preview", string(previewJSON))
			previewCount++
		case <-timeout:
			// Break if we've waited too long
			goto done
		}
	}

done:
	// Send completion event
	c.SSEvent("complete", "")
}

// GetModelImages handles fetching preview images for models (legacy endpoint)
func GetModelImages(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	userToken, err := auth.GetUserToken(user.ID)
	if err != nil || userToken == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid user token"})
		return
	}

	var req struct {
		ModelIDs []string `json:"modelIds"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	// Create a map to store model ID -> data URI
	images := make(map[string]string)

	// Fetch images for each model ID
	for _, modelID := range req.ModelIDs {
		dataURI := GetModelPreviewDataURI(modelID, userToken.SpeckleToken)
		if dataURI != "" {
			images[modelID] = dataURI
		}
	}

	c.JSON(http.StatusOK, images)
}

// GetModelPreviews handles batch loading of model previews
func GetModelPreviews(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	userToken, err := auth.GetUserToken(user.ID)
	if err != nil || userToken == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	var request struct {
		Models []struct {
			ModelID   string `json:"modelId"`
			ProjectID string `json:"projectId"`
		} `json:"models"`
	}

	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	previews := make([]gin.H, 0, len(request.Models))
	for _, model := range request.Models {
		previewURL := GetModelPreviewDataURI(model.ModelID, userToken.SpeckleToken)
		previews = append(previews, gin.H{
			"modelId":    model.ModelID,
			"previewUrl": previewURL,
		})
	}

	c.JSON(http.StatusOK, gin.H{"previews": previews})
}
