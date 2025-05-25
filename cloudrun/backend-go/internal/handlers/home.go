package handlers

import (
	"log"
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
		c.HTML(http.StatusOK, "firebase_token.html", gin.H{
			"firebaseToken": firebaseToken,
		})
		return
	}

	if user == nil {
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
		log.Printf("GetUserToken took: %v", time.Since(tokenStart))
		c.HTML(http.StatusOK, "base", gin.H{
			"title":   "Welcome",
			"content": "welcome",
			"user":    user,
		})
		return
	}
	log.Printf("GetUserToken took: %v", time.Since(tokenStart))

	projectsStart := time.Now()
	projects, nextCursor, err := auth.GetProjectsWithPagination(userToken.SpeckleToken, projectsPerPage, modelsPerProject, versionsPerModel, "", "")
	if err != nil {
		log.Printf("GetProjects took: %v", time.Since(projectsStart))
		c.HTML(http.StatusOK, "base", gin.H{
			"title":   "Welcome",
			"content": "login",
			"user":    user,
		})
		return
	}
	log.Printf("GetProjects took: %v", time.Since(projectsStart))

	// Don't load previews on initial page load
	// They will be loaded lazily via HTMX when needed

	logging.LogColor(logging.ColorPurple, "Next Cursor: %v", nextCursor)

	c.HTML(http.StatusOK, "base", gin.H{
		"title":                "Projects",
		"content":              "projects",
		"user":                 user,
		"projects":             projects,
		"has_more_projects":    nextCursor != "",
		"next_cursor":          nextCursor,
		"next_projects_cursor": nextCursor,
	})
	log.Printf("Total Home handler took: %v", time.Since(start))
}
