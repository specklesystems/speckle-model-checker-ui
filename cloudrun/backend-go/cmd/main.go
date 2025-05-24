package main

import (
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/gin-contrib/sessions"
	"github.com/gin-contrib/sessions/cookie"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"github.com/speckle/model-checker/internal/auth"
	"github.com/speckle/model-checker/internal/handlers"
	"github.com/speckle/model-checker/internal/models"
)

// ANSI color codes
const (
	colorReset  = "\x1b[0m"
	colorRed    = "\x1b[31;1m"
	colorGreen  = "\x1b[32;1m"
	colorYellow = "\x1b[33;1m"
	colorBlue   = "\x1b[34;1m"
	colorPurple = "\x1b[35;1m"
	colorCyan   = "\x1b[36;1m"
)

// logColor prints a colored log message
func logColor(color, format string, v ...interface{}) {
	msg := fmt.Sprintf(format, v...)
	log.Printf("%s%s%s", color, msg, colorReset)
}

func loadTemplates() *template.Template {
	// Create a new template with a name
	templates := template.New("")

	// Load all templates at once
	logColor(colorBlue, "Loading all templates")
	templates = template.Must(templates.ParseGlob("go-templates/*.html"))
	templates = template.Must(templates.ParseGlob("go-templates/partials/*.html"))

	// Debug: List all loaded templates
	logColor(colorGreen, "Loaded templates:")
	for _, tmpl := range templates.Templates() {
		logColor(colorCyan, "  - %s", tmpl.Name())
	}

	return templates
}

func main() {
	// Load environment variables from parent directory
	if err := godotenv.Load(filepath.Join("..", ".env")); err != nil {
		logColor(colorYellow, "Warning: .env file not found: %v", err)
	}

	// Debug: Check if session secret key is loaded
	sessionKey := os.Getenv("SESSION_SECRET_KEY")
	if sessionKey == "" {
		logColor(colorRed, "SESSION_SECRET_KEY environment variable is not set")
		log.Fatal("SESSION_SECRET_KEY environment variable is not set")
	}
	logColor(colorGreen, "Session secret key length: %d", len(sessionKey))

	// Initialize Firebase
	if err := auth.InitializeFirebase(); err != nil {
		logColor(colorRed, "Failed to initialize Firebase: %v", err)
		log.Fatalf("Failed to initialize Firebase: %v", err)
	}

	// Initialize auth package with Firestore client
	if err := auth.InitializeFromFirebase(); err != nil {
		logColor(colorRed, "Failed to initialize auth package: %v", err)
		log.Fatalf("Failed to initialize auth package: %v", err)
	}

	// Create Gin router
	r := gin.Default()

	// Load templates
	templates := loadTemplates()
	r.SetHTMLTemplate(templates)

	// Add request logging middleware
	r.Use(func(c *gin.Context) {
		logColor(colorBlue, "Request: %s %s", c.Request.Method, c.Request.URL.Path)
		c.Next()
		logColor(colorGreen, "Response: %s %s - Status: %d", c.Request.Method, c.Request.URL.Path, c.Writer.Status())
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
			logColor(colorCyan, "Session before request - User ID: %v", userID)
		}
		c.Next()
		userID = session.Get("user_id")
		if userID != nil {
			logColor(colorCyan, "Session after request - User ID: %v", userID)
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
				logColor(colorGreen, "Session middleware - Setting user in context: %+v", user)
				c.Set("user", user)
			} else {
				logColor(colorYellow, "Session middleware - Incomplete user data in session")
			}
		} else {
			logColor(colorYellow, "Session middleware - No user found in session")
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
			logColor(colorBlue, "Rendering template for path: %s", c.Request.URL.Path)
			if tmpl := r.HTMLRender; tmpl != nil {
				logColor(colorCyan, "Template renderer type: %T", tmpl)
			}
		}
	})

	// Static files
	logColor(colorBlue, "Setting up static files from frontend/static")
	r.Static("/static", "./go-templates/static")

	// Auth routes
	r.GET("/auth/init", handlers.AuthInit)
	r.GET("/auth/callback", handlers.AuthCallback)
	r.GET("/logout", handlers.Logout)

	// Main routes
	r.GET("/", handlers.Home)
	r.GET("/debug", func(c *gin.Context) {
		logColor(colorBlue, "Debug route called")
		c.HTML(http.StatusOK, "base", gin.H{
			"title":       "Debug",
			"user":        nil,
			"currentYear": time.Now().Year(),
		})
	})
	r.GET("/projects", handlers.GetProjects)
	r.GET("/projects/search", handlers.SearchProjects)
	r.GET("/projects/:project_id", handlers.ProjectDetails)

	// Ruleset routes
	r.GET("/rulesets", handlers.ListRulesets)
	r.GET("/rulesets/new", handlers.NewRuleset)
	r.GET("/rulesets/:ruleset_id/edit", handlers.EditRuleset)
	r.POST("/rulesets", handlers.CreateRuleset)
	r.POST("/rulesets/:ruleset_id", handlers.UpdateRuleset)
	r.DELETE("/api/rulesets/:ruleset_id", handlers.DeleteRuleset)

	// Rule routes
	r.GET("/rulesets/:ruleset_id/rules/new", handlers.NewRuleForm)
	r.POST("/rulesets/:ruleset_id/rules", handlers.AddRule)
	r.GET("/rulesets/:ruleset_id/rules/:rule_id/edit", handlers.EditRule)
	r.POST("/rulesets/:ruleset_id/rules/:rule_id", handlers.UpdateRule)
	r.DELETE("/api/rulesets/:ruleset_id/rules/:rule_id", handlers.DeleteRule)

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}
	logColor(colorGreen, "Starting server on port %s", port)
	if err := r.Run(":" + port); err != nil {
		logColor(colorRed, "Failed to start server: %v", err)
		log.Fatalf("Failed to start server: %v", err)
	}
}
