package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/speckle/model-checker/internal/auth"
)

const (
	projectsPerPage  = 20
	modelsPerProject = 20
	versionsPerModel = 1
)

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
