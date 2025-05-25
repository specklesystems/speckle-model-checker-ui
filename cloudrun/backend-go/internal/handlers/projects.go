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
	ctx := context.Background()
	bucketName := os.Getenv("FIREBASE_STORAGE_BUCKET")
	objectName := fmt.Sprintf("previews/%s.png", modelID)
	client := auth.GetFirebaseStorageClient()
	if client == nil {
		return ""
	}
	bucket := client.Bucket(bucketName)
	obj := bucket.Object(objectName)

	attrs, err := obj.Attrs(ctx)
	if err != nil {
		// Not found: fetch from Speckle, upload, then cache
		model, err := services.GetModelByID(userToken, modelID)
		if err != nil || model == nil || model.PreviewUrl == "" {
			return ""
		}
		previewUrl := model.PreviewUrl
		req, _ := http.NewRequest("GET", previewUrl, nil)
		req.Header.Set("Authorization", "Bearer "+userToken)
		resp, err := http.DefaultClient.Do(req)
		if err != nil || resp.StatusCode != 200 {
			return ""
		}
		defer resp.Body.Close()
		imgBytes, _ := io.ReadAll(resp.Body)
		contentType := resp.Header.Get("Content-Type")
		if contentType == "" {
			contentType = "image/png"
		}
		wc := obj.NewWriter(ctx)
		wc.ContentType = contentType
		if _, err := wc.Write(imgBytes); err != nil {
			return ""
		}
		if err := wc.Close(); err != nil {
			return ""
		}
		attrs, err = obj.Attrs(ctx)
		if err != nil {
			return ""
		}
	}

	rc, err := obj.NewReader(ctx)
	if err != nil {
		return ""
	}
	defer rc.Close()
	imgBytes, err := io.ReadAll(rc)
	if err != nil {
		return ""
	}
	contentType := attrs.ContentType
	if contentType == "" {
		contentType = "image/png"
	}
	base64Data := base64.StdEncoding.EncodeToString(imgBytes)
	return template.URL(fmt.Sprintf("data:%s;base64,%s", contentType, base64Data))
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

	// Populate PreviewDataURI for each model
	for pi := range projects {
		for mi := range projects[pi].Models.Items {
			projects[pi].Models.Items[mi].PreviewDataURI = getModelPreviewDataURI(projects[pi].Models.Items[mi].ID, userToken.SpeckleToken)
		}
	}

	// Check if this is an HTMX request
	if c.GetHeader("HX-Request") == "true" {
		// Return just the project list content
		c.HTML(http.StatusOK, "project_list_content", gin.H{
			"projects":             projects,
			"has_more_projects":    nextCursor != "",
			"next_projects_cursor": nextCursor,
		})
		return
	}

	// Return the full page
	c.HTML(http.StatusOK, "base", gin.H{
		"title":                "Projects",
		"content":              "projects",
		"user":                 user,
		"projects":             projects,
		"has_more_projects":    nextCursor != "",
		"next_projects_cursor": nextCursor,
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

// GetModelPreview handles fetching and caching model preview images
func GetModelPreview(c *gin.Context) {
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

	ctx := context.Background()
	bucketName := os.Getenv("FIREBASE_STORAGE_BUCKET")
	objectName := fmt.Sprintf("previews/%s.png", modelID)
	client := auth.GetFirebaseStorageClient()
	if client == nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create storage client"})
		return
	}
	bucket := client.Bucket(bucketName)
	obj := bucket.Object(objectName)

	// Check if the object exists
	attrs, err := obj.Attrs(ctx)
	if err != nil {
		// Not found: fetch from Speckle, upload, then cache
		model, err := services.GetModelByID(userToken.SpeckleToken, modelID)
		if err != nil || model == nil || model.PreviewUrl == "" {
			c.JSON(http.StatusNotFound, gin.H{"error": "Model or preview not found"})
			return
		}
		previewUrl := model.PreviewUrl
		req, _ := http.NewRequest("GET", previewUrl, nil)
		req.Header.Set("Authorization", "Bearer "+userToken.SpeckleToken)
		resp, err := http.DefaultClient.Do(req)
		if err != nil || resp.StatusCode != 200 {
			c.JSON(http.StatusBadGateway, gin.H{"error": "Failed to fetch preview from Speckle"})
			return
		}
		defer resp.Body.Close()
		imgBytes, _ := io.ReadAll(resp.Body)
		contentType := resp.Header.Get("Content-Type")
		if contentType == "" {
			contentType = "image/png"
		}
		wc := obj.NewWriter(ctx)
		wc.ContentType = contentType
		if _, err := wc.Write(imgBytes); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to upload to Firebase"})
			return
		}
		if err := wc.Close(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to finalize upload"})
			return
		}
		attrs, err = obj.Attrs(ctx)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get uploaded object attrs"})
			return
		}
	}

	// Read the blob from storage
	rc, err := obj.NewReader(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read image from storage"})
		return
	}
	defer rc.Close()
	imgBytes, err := io.ReadAll(rc)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to read image data"})
		return
	}
	log.Printf("Read image bytes: %d", len(imgBytes))
	contentType := attrs.ContentType
	if contentType == "" {
		contentType = "image/png"
	}
	base64Data := base64.StdEncoding.EncodeToString(imgBytes)
	dataURI := fmt.Sprintf("data:%s;base64,%s", contentType, base64Data)
	log.Printf("Returning data URI of length: %d", len(dataURI))

	c.Data(http.StatusOK, "text/plain; charset=utf-8", []byte(dataURI))
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
