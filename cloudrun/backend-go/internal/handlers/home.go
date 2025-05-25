package handlers

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/speckle/model-checker/internal/auth"
	"github.com/speckle/model-checker/internal/logging"
)

// Home handles the home page
func Home(c *gin.Context) {
	start := time.Now()
	user := auth.GetCurrentUser(c)

	firebaseToken := c.Query("ft")
	if firebaseToken != "" {
		logging.LogColor(logging.ColorYellow, "Received Firebase token in query parameter")
		c.HTML(http.StatusOK, "firebase_token.html", gin.H{
			"firebaseToken": firebaseToken,
		})
		return
	}

	if user == nil {
		logging.LogColor(logging.ColorBlue, "No user found in session, showing login page")
		c.HTML(http.StatusOK, "base", gin.H{
			"title":   "Welcome",
			"content": "login",
			"user":    nil,
		})
		return
	}

	tokenStart := time.Now()
	userToken, err := auth.GetUserToken(user.ID)
	if err != nil || userToken == nil {
		logging.LogColor(logging.ColorRed, "Failed to get user token for user %s: %v", user.ID, err)
		logging.LogColor(logging.ColorReset, "Getting user token took: %v", time.Since(tokenStart))
		c.HTML(http.StatusOK, "base", gin.H{
			"title":   "Welcome",
			"content": "welcome",
			"user":    user,
		})
		return
	}
	logging.LogColor(logging.ColorReset, "Getting user token took: %v", time.Since(tokenStart))

	projectsStart := time.Now()
	projects, nextCursor, err := auth.GetProjectsWithPagination(userToken.SpeckleToken, projectsPerPage, modelsPerProject, versionsPerModel, "", "")
	if err != nil {
		logging.LogColor(logging.ColorRed, "Failed to get projects for user %s: %v", user.ID, err)
		logging.LogColor(logging.ColorReset, "Getting projects took: %v", time.Since(projectsStart))
		c.HTML(http.StatusOK, "base", gin.H{
			"title":   "Welcome",
			"content": "login",
			"user":    user,
		})
		return
	}
	logging.LogColor(logging.ColorBlue, "Successfully fetched %d projects for user %s", len(projects), user.ID)
	logging.LogColor(logging.ColorReset, "Getting projects took: %v", time.Since(projectsStart))

	// Don't load previews on initial page load
	// They will be loaded lazily via HTMX when needed
	c.HTML(http.StatusOK, "base", gin.H{
		"title":                "Projects",
		"content":              "projects",
		"user":                 user,
		"projects":             projects,
		"has_more_projects":    nextCursor != "",
		"next_cursor":          nextCursor,
		"next_projects_cursor": nextCursor,
	})
	logging.LogColor(logging.ColorReset, "Total time for Home handler: %v", time.Since(start))
}
