package main

import (
	"encoding/json"
	"html/template"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/gin-contrib/sessions"
	"github.com/gin-contrib/sessions/cookie"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"github.com/speckle/model-checker/internal/auth"
	"github.com/speckle/model-checker/internal/handlers"
	"github.com/speckle/model-checker/internal/logging"
	"github.com/speckle/model-checker/internal/models"
)

func loadTemplates() *template.Template {
	// Create a new template with a name
	templates := template.New("")

	// Add custom template functions
	templates.Funcs(template.FuncMap{
		"lower": strings.ToLower,
		"json": func(v interface{}) (string, error) {
			b, err := json.Marshal(v)
			if err != nil {
				return "", err
			}
			return string(b), nil
		},
	})

	// Load all templates at once
	logging.LogColor(logging.ColorBlue, "Loading all templates")
	templates = template.Must(templates.ParseGlob("go-templates/*.html"))
	templates = template.Must(templates.ParseGlob("go-templates/partials/*.html"))

	// Debug: List all loaded templates
	logging.LogColor(logging.ColorGreen, "Loaded templates:")
	for _, tmpl := range templates.Templates() {
		logging.LogColor(logging.ColorCyan, "  - %s", tmpl.Name())
	}

	return templates
}

func main() {
	// Load environment variables from parent directory
	if err := godotenv.Load(filepath.Join("..", ".env")); err != nil {
		logging.LogColor(logging.ColorYellow, "Warning: .env file not found: %v", err)
	}

	// Debug: Check if session secret key is loaded
	sessionKey := os.Getenv("SESSION_SECRET_KEY")
	if sessionKey == "" {
		logging.LogColor(logging.ColorRed, "SESSION_SECRET_KEY environment variable is not set")
		log.Fatal("SESSION_SECRET_KEY environment variable is not set")
	}
	logging.LogColor(logging.ColorGreen, "Session secret key length: %d", len(sessionKey))

	// Initialize Firebase
	if err := auth.InitializeFirebase(); err != nil {
		logging.LogColor(logging.ColorRed, "Failed to initialize Firebase: %v", err)
		log.Fatalf("Failed to initialize Firebase: %v", err)
	}

	// Initialize auth package with Firestore client
	if err := auth.InitializeFromFirebase(); err != nil {
		logging.LogColor(logging.ColorRed, "Failed to initialize auth package: %v", err)
		log.Fatalf("Failed to initialize auth package: %v", err)
	}

	// Create Gin router
	r := gin.Default()

	// Load templates
	templates := loadTemplates()
	r.SetHTMLTemplate(templates)

	// Add request logging middleware
	r.Use(func(c *gin.Context) {
		logging.LogColor(logging.ColorBlue, "Request: %s %s", c.Request.Method, c.Request.URL.Path)
		c.Next()
		logging.LogColor(logging.ColorGreen, "Response: %s %s - Status: %d", c.Request.Method, c.Request.URL.Path, c.Writer.Status())
	})

	// Set up session middleware
	store := cookie.NewStore([]byte(sessionKey))
	store.Options(sessions.Options{
		Path:     "/",
		MaxAge:   86400 * 7, // 7 days
		HttpOnly: true,
		Secure:   os.Getenv("GO_ENV") == "production",
		SameSite: http.SameSiteLaxMode,
	})

	// Initialize session middleware first
	r.Use(sessions.Sessions("speckle_session", store))

	// Then add session debug logging
	r.Use(func(c *gin.Context) {
		session := sessions.Default(c)
		userID := session.Get("user_id")
		if userID != nil {
			logging.LogColor(logging.ColorCyan, "Session before request - User ID: %v", userID)
		}
		c.Next()
		userID = session.Get("user_id")
		if userID != nil {
			logging.LogColor(logging.ColorCyan, "Session after request - User ID: %v", userID)
		}
	})

	// Add middleware to load user from session
	r.Use(func(c *gin.Context) {
		session := sessions.Default(c)
		userID := session.Get("user_id")
		if userID != nil {
			userName := session.Get("user_name")
			userEmail := session.Get("user_email")
			if userName != nil && userEmail != nil {
				user := &models.User{
					ID:    userID.(string),
					Name:  userName.(string),
					Email: userEmail.(string),
				}
				logging.LogColor(logging.ColorGreen, "Session middleware - Setting user in context: %+v", user)
				c.Set("user", user)
			} else {
				logging.LogColor(logging.ColorYellow, "Session middleware - Incomplete user data in session")
			}
		} else {
			logging.LogColor(logging.ColorYellow, "Session middleware - No user found in session")
		}
		c.Next()
	})

	// Set up template functions
	r.SetFuncMap(template.FuncMap{
		"user": func(c *gin.Context) *models.User {
			if user, exists := c.Get("user"); exists {
				if u, ok := user.(*models.User); ok {
					return u
				}
			}
			return nil
		},
	})

	// Add template debug logging
	r.Use(func(c *gin.Context) {
		c.Next()
		if c.Writer.Status() == http.StatusOK && c.Writer.Header().Get("Content-Type") == "text/html; charset=utf-8" {
			logging.LogColor(logging.ColorBlue, "Rendering template for path: %s", c.Request.URL.Path)
			if tmpl := r.HTMLRender; tmpl != nil {
				logging.LogColor(logging.ColorCyan, "Template renderer type: %T", tmpl)
			}
		}
	})

	// Static files
	logging.LogColor(logging.ColorBlue, "Setting up static files from frontend/static")
	r.Static("/static", "./go-templates/static")

	// Auth routes
	r.GET("/auth/init", handlers.AuthInit)
	r.GET("/auth/callback", handlers.AuthCallback)
	r.GET("/logout", handlers.Logout)

	// Main routes
	r.GET("/", handlers.Home)
	r.GET("/debug", func(c *gin.Context) {
		logging.LogColor(logging.ColorBlue, "Debug route called")
		c.HTML(http.StatusOK, "base", gin.H{
			"title":       "Debug",
			"user":        nil,
			"currentYear": time.Now().Year(),
		})
	})
	r.GET("/projects", handlers.GetProjects)
	r.GET("/projects/search", handlers.SearchProjects)
	r.GET("/projects/:project_id", handlers.ProjectDetails)
	r.GET("/projects/:project_id/models", handlers.GetProjectModels)

	// Ruleset routes
	r.GET("/rulesets", handlers.ListRulesets)
	r.GET("/rulesets/new", handlers.NewRuleset)
	r.GET("/rulesets/:ruleset_id/edit", handlers.EditRuleset)
	r.POST("/rulesets", handlers.CreateRuleset)
	r.POST("/rulesets/:ruleset_id", handlers.UpdateRuleset)

	// Rule routes
	r.GET("/rulesets/:ruleset_id/rules/new", handlers.NewRuleForm)
	r.POST("/rulesets/:ruleset_id/rules", handlers.AddRule)
	r.GET("/rulesets/:ruleset_id/rules/:rule_id/edit", handlers.EditRule)
	r.POST("/rulesets/:ruleset_id/rules/:rule_id", handlers.UpdateRule)

	// API routes
	api := r.Group("/api")
	{
		// Project routes
		api.GET("/projects", handlers.GetProjects)

		// Model routes
		api.GET("/model-preview/:model_id", handlers.GetModelPreview)
		api.POST("/models/images", handlers.GetModelImages)
		api.GET("/models/preview-stream", handlers.GetModelPreviewStream)

		// Ruleset routes
		api.DELETE("/rulesets/:ruleset_id", handlers.DeleteRuleset)

		// Rule routes
		api.DELETE("/rulesets/:ruleset_id/rules/:rule_id", handlers.DeleteRule)
	}

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}
	logging.LogColor(logging.ColorGreen, "Starting server on port %s", port)
	if err := r.Run(":" + port); err != nil {
		logging.LogColor(logging.ColorRed, "Failed to start server: %v", err)
		log.Fatalf("Failed to start server: %v", err)
	}
}
