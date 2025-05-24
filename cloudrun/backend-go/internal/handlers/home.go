package handlers

import (
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/speckle/model-checker/internal/auth"
	"github.com/speckle/model-checker/internal/logging"
)

// Home handles the home page
func Home(c *gin.Context) {
	log.Printf("Home handler called - Path: %s, Method: %s", c.Request.URL.Path, c.Request.Method)

	// Get current user through auth package
	user := auth.GetCurrentUser(c)
	log.Printf("Home handler - User type: %T, value: %+v", user, user)

	firebaseToken := c.Query("ft")
	if firebaseToken != "" {
		log.Printf("Firebase token present, rendering firebase_token.html")
		c.HTML(http.StatusOK, "firebase_token.html", gin.H{
			"firebaseToken": firebaseToken,
		})
		return
	}

	if user == nil {
		log.Printf("No user found, rendering base template with login content")
		c.HTML(http.StatusOK, "base", gin.H{
			"title":   "Welcome",
			"content": "login",
			"user":    nil,
		})
		return
	}

	// Get user's Speckle token from Firestore
	userToken, err := auth.GetUserToken(user.ID)
	if err != nil || userToken == nil {
		log.Printf("Failed to get user token: %v", err)
		c.HTML(http.StatusOK, "base", gin.H{
			"title":   "Welcome",
			"content": "welcome",
			"user":    user,
		})
		return
	}

	// Fetch projects from Speckle
	projects, err := auth.GetProjects(userToken.SpeckleToken)
	if err != nil {
		log.Printf("Failed to fetch projects: %v", err)
		c.HTML(http.StatusOK, "base", gin.H{
			"title":   "Welcome",
			"content": "login",
			"user":    user,
		})
		return
	}

	// For logged-in users with projects, render the base template with projects
	logging.LogColor(logging.ColorRed, "Rendering base template with projects content")
	c.HTML(http.StatusOK, "base", gin.H{
		"title":    "Projects",
		"content":  "projects",
		"user":     user,
		"projects": projects,
	})
}
