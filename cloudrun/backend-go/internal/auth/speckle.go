package auth

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"

	"github.com/gin-contrib/sessions"
	"github.com/gin-gonic/gin"
	"github.com/speckle/model-checker/internal/models"
)

const (
	speckleServerURL = "https://app.speckle.systems"
)

// InitAuth initializes Speckle authentication
func InitAuth(c *gin.Context) {
	appID := os.Getenv("SPECKLE_APP_ID")
	appSecret := os.Getenv("SPECKLE_APP_SECRET")

	if appID == "" || appSecret == "" {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Speckle App ID or Secret not configured"})
		return
	}

	// Generate challenge ID
	challengeID := generateChallengeID()
	session := sessions.Default(c)
	session.Set("speckle_challenge_id", challengeID)
	session.Save()

	authURL := fmt.Sprintf("%s/authn/verify/%s/%s", speckleServerURL, appID, challengeID)

	c.JSON(http.StatusOK, gin.H{
		"challengeId": challengeID,
		"authUrl":     authURL,
		"appId":       appID,
	})
}

// ExchangeToken exchanges the access code for a token
func ExchangeToken(c *gin.Context) {
	accessCode := c.Query("access_code")
	session := sessions.Default(c)
	challengeID := session.Get("speckle_challenge_id")
	session.Delete("speckle_challenge_id")
	session.Save()

	if accessCode == "" || challengeID == nil {
		c.HTML(http.StatusBadRequest, "base", gin.H{
			"title":   "Error",
			"content": "error",
			"error":   "Missing access code or challenge ID",
		})
		return
	}

	// Exchange code for token
	tokenURL := fmt.Sprintf("%s/auth/token", speckleServerURL)
	data := url.Values{}
	data.Set("accessCode", accessCode)
	data.Set("appId", os.Getenv("SPECKLE_APP_ID"))
	data.Set("appSecret", os.Getenv("SPECKLE_APP_SECRET"))
	data.Set("challenge", challengeID.(string))

	resp, err := http.PostForm(tokenURL, data)
	if err != nil {
		c.HTML(http.StatusInternalServerError, "base", gin.H{
			"title":   "Error",
			"content": "error",
			"error":   "Failed to exchange token",
		})
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		c.HTML(resp.StatusCode, "base", gin.H{
			"title":   "Error",
			"content": "error",
			"error":   "Failed to exchange token",
		})
		return
	}

	var tokenResp struct {
		Token        string `json:"token"`
		RefreshToken string `json:"refreshToken"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&tokenResp); err != nil {
		c.HTML(http.StatusInternalServerError, "base", gin.H{
			"title":   "Error",
			"content": "error",
			"error":   "Failed to decode token response",
		})
		return
	}

	// Get user profile
	profileURL := fmt.Sprintf("%s/graphql", speckleServerURL)
	query := `query { activeUser { id name email avatar } }`
	reqBody := map[string]interface{}{"query": query}
	reqBodyBytes, _ := json.Marshal(reqBody)

	req, _ := http.NewRequest("POST", profileURL, strings.NewReader(string(reqBodyBytes)))
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", tokenResp.Token))
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err = client.Do(req)
	if err != nil {
		c.HTML(http.StatusInternalServerError, "base", gin.H{
			"title":   "Error",
			"content": "error",
			"error":   "Failed to get user profile",
		})
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		c.HTML(resp.StatusCode, "base", gin.H{
			"title":   "Error",
			"content": "error",
			"error":   "Failed to get user profile",
		})
		return
	}

	var profileResp struct {
		Data struct {
			ActiveUser models.User `json:"activeUser"`
		} `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&profileResp); err != nil {
		c.HTML(http.StatusInternalServerError, "base", gin.H{
			"title":   "Error",
			"content": "error",
			"error":   "Failed to decode profile response",
		})
		return
	}

	// Store user token in Firestore
	user := profileResp.Data.ActiveUser
	userToken := models.UserToken{
		SpeckleToken: tokenResp.Token,
		UserID:       user.ID,
	}

	_, err = firestoreClient.Collection("userTokens").Doc(user.ID).Set(context.Background(), userToken)
	if err != nil {
		c.HTML(http.StatusInternalServerError, "base", gin.H{
			"title":   "Error",
			"content": "error",
			"error":   "Failed to store user token",
		})
		return
	}

	// Set user in session
	log.Printf("Attempting to save user data to session: ID=%s, Name=%s, Email=%s", user.ID, user.Name, user.Email)
	session.Set("user_id", user.ID)
	session.Set("user_name", user.Name)
	session.Set("user_email", user.Email)
	if err := session.Save(); err != nil {
		log.Printf("Failed to save session: %v", err)
		log.Printf("Session data that failed to save: ID=%s, Name=%s, Email=%s", user.ID, user.Name, user.Email)
		c.HTML(http.StatusInternalServerError, "base", gin.H{
			"title":   "Error",
			"content": "error",
			"error":   "Failed to save session",
		})
		return
	}

	// Debug: Log session state
	log.Printf("Session after login - User ID: %s, Name: %s", user.ID, user.Name)

	// Redirect to projects page after successful login
	c.Redirect(http.StatusFound, "/projects")
}

// generateChallengeID generates a random challenge ID
func generateChallengeID() string {
	b := make([]byte, 32)
	rand.Read(b)
	return base64.URLEncoding.EncodeToString(b)
}
