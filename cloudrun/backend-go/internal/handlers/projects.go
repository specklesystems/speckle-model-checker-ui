package handlers

import (
	"net/http"

	"context"
	"fmt"
	"io"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/speckle/model-checker/internal/auth"

	"encoding/base64"

	"log"

	"html/template"

	"cloud.google.com/go/storage"
	"github.com/speckle/model-checker/internal/services"
)

const (
	projectsPerPage  = 20
	modelsPerProject = 20
	versionsPerModel = 1
)

// getModelPreviewDataURI fetches or caches and returns the data URI for a model preview
func getModelPreviewDataURI(modelID string, userToken string) template.URL {
	start := time.Now()
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	bucketName := os.Getenv("FIREBASE_STORAGE_BUCKET")
	objectName := fmt.Sprintf("previews/%s.png", modelID)
	client := auth.GetFirebaseStorageClient()
	if client == nil {
		return ""
	}
	bucket := client.Bucket(bucketName)
	obj := bucket.Object(objectName)

	// Try to get from cache first
	cacheStart := time.Now()
	rc, err := obj.NewReader(ctx)
	if err == nil {
		defer rc.Close()
		imgBytes, err := io.ReadAll(rc)
		if err == nil {
			contentType := "image/png"
			base64Data := base64.StdEncoding.EncodeToString(imgBytes)
			log.Printf("Cache hit for model %s, took: %v", modelID, time.Since(cacheStart))
			return template.URL(fmt.Sprintf("data:%s;base64,%s", contentType, base64Data))
		}
	}
	log.Printf("Cache miss for model %s, took: %v", modelID, time.Since(cacheStart))

	// Not in cache, fetch from Speckle
	speckleStart := time.Now()
	model, err := services.GetModelByID(userToken, modelID)
	if err != nil || model == nil || model.PreviewUrl == "" {
		log.Printf("Failed to get model %s from Speckle, took: %v", modelID, time.Since(speckleStart))
		return ""
	}
	log.Printf("Got model %s from Speckle, took: %v", modelID, time.Since(speckleStart))

	// Fetch preview from Speckle
	previewStart := time.Now()
	req, _ := http.NewRequestWithContext(ctx, "GET", model.PreviewUrl, nil)
	req.Header.Set("Authorization", "Bearer "+userToken)
	resp, err := http.DefaultClient.Do(req)
	if err != nil || resp.StatusCode != 200 {
		log.Printf("Failed to fetch preview for model %s, took: %v", modelID, time.Since(previewStart))
		return ""
	}
	defer resp.Body.Close()

	imgBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Printf("Failed to read preview for model %s, took: %v", modelID, time.Since(previewStart))
		return ""
	}
	log.Printf("Fetched preview for model %s, took: %v", modelID, time.Since(previewStart))

	// Cache in Firebase Storage in a goroutine
	go func() {
		cacheStart := time.Now()
		wc := obj.NewWriter(ctx)
		wc.ContentType = "image/png"
		if _, err := wc.Write(imgBytes); err == nil {
			wc.Close()
			log.Printf("Cached preview for model %s, took: %v", modelID, time.Since(cacheStart))
		}
	}()

	// Return data URI immediately
	base64Start := time.Now()
	base64Data := base64.StdEncoding.EncodeToString(imgBytes)
	log.Printf("Base64 encoded preview for model %s, took: %v", modelID, time.Since(base64Start))

	log.Printf("Total preview processing for model %s took: %v", modelID, time.Since(start))
	return template.URL(fmt.Sprintf("data:image/png;base64,%s", base64Data))
}

// GetProjects handles fetching projects
func GetProjects(c *gin.Context) {
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

	// Get cursor from query parameter
	projectsCursor := c.Query("projects_cursor")

	// Get projects with pagination
	projects, nextCursor, err := auth.GetProjectsWithPagination(userToken.SpeckleToken, projectsPerPage, modelsPerProject, versionsPerModel, projectsCursor, "")
	if err != nil {
		c.HTML(http.StatusInternalServerError, "base", gin.H{
			"title":   "Error",
			"content": "error",
			"error":   "Failed to fetch projects",
		})
		return
	}

	// Extract model IDs for each project
	for pi := range projects {
		modelIDs := make([]string, len(projects[pi].Models.Items))
		for mi, model := range projects[pi].Models.Items {
			modelIDs[mi] = model.ID
		}
		projects[pi].ModelIDs = modelIDs
	}

	c.HTML(http.StatusOK, "projects.html", gin.H{
		"title":             "Projects",
		"user":              user,
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
		"models":    project.Models.Items,
		"model_ids": modelIDs,
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
	previewURI := getModelPreviewDataURI(modelID, userToken.SpeckleToken)
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

// GetModelImages handles fetching preview images for models
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
		dataURI := getModelPreviewDataURI(modelID, userToken.SpeckleToken)
		if dataURI != "" {
			images[modelID] = string(dataURI)
		}
	}

	c.JSON(http.StatusOK, images)
}
