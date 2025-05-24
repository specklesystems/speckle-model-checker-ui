package handlers

import (
	"net/http"

	"github.com/gin-contrib/sessions"
	"github.com/gin-gonic/gin"
	"github.com/speckle/model-checker/internal/auth"
)

// AuthInit handles the initialization of Speckle authentication
func AuthInit(c *gin.Context) {
	auth.InitAuth(c)
}

// AuthCallback handles the OAuth callback from Speckle
func AuthCallback(c *gin.Context) {
	auth.ExchangeToken(c)
}

// Logout handles user logout
func Logout(c *gin.Context) {
	session := sessions.Default(c)
	session.Clear()
	session.Save()

	c.Redirect(http.StatusFound, "/")
}
