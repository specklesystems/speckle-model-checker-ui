package auth

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"strings"

	"github.com/gin-contrib/sessions"
	"github.com/gin-gonic/gin"
	"github.com/speckle/model-checker/internal/logging"
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
		logging.LogColor(logging.ColorRed, "Speckle App ID or Secret not configured")
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Speckle App ID or Secret not configured"})
		return
	}

	// Generate challenge ID
	challengeID := generateChallengeID()
	session := sessions.Default(c)
	session.Set("speckle_challenge_id", challengeID)
	session.Save()

	authURL := fmt.Sprintf("%s/authn/verify/%s/%s", speckleServerURL, appID, challengeID)
	logging.LogColor(logging.ColorBlue, "Initialized Speckle authentication with challenge ID: %s", challengeID)

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
		logging.LogColor(logging.ColorRed, "Missing access code or challenge ID")
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

	logging.LogColor(logging.ColorBlue, "Exchanging access code for token")
	resp, err := http.PostForm(tokenURL, data)
	if err != nil {
		logging.LogColor(logging.ColorRed, "Failed to exchange token: %v", err)
		c.HTML(http.StatusInternalServerError, "base", gin.H{
			"title":   "Error",
			"content": "error",
			"error":   "Failed to exchange token",
		})
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		logging.LogColor(logging.ColorRed, "Token exchange failed with status: %d", resp.StatusCode)
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
		logging.LogColor(logging.ColorRed, "Failed to decode token response: %v", err)
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

	logging.LogColor(logging.ColorBlue, "Fetching user profile from Speckle")
	client := &http.Client{}
	resp, err = client.Do(req)
	if err != nil {
		logging.LogColor(logging.ColorRed, "Failed to get user profile: %v", err)
		c.HTML(http.StatusInternalServerError, "base", gin.H{
			"title":   "Error",
			"content": "error",
			"error":   "Failed to get user profile",
		})
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		logging.LogColor(logging.ColorRed, "Profile fetch failed with status: %d", resp.StatusCode)
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
		logging.LogColor(logging.ColorRed, "Failed to decode profile response: %v", err)
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

	logging.LogColor(logging.ColorYellow, "Storing user token in Firestore for user: %s", user.ID)
	_, err = firestoreClient.Collection("userTokens").Doc(user.ID).Set(context.Background(), userToken)
	if err != nil {
		logging.LogColor(logging.ColorRed, "Failed to store user token: %v", err)
		c.HTML(http.StatusInternalServerError, "base", gin.H{
			"title":   "Error",
			"content": "error",
			"error":   "Failed to store user token",
		})
		return
	}

	// Set user data in session
	session.Set("user_id", user.ID)
	session.Set("user_name", user.Name)
	session.Set("user_email", user.Email)
	if err := session.Save(); err != nil {
		logging.LogColor(logging.ColorRed, "Failed to save session: %v", err)
	}

	logging.LogColor(logging.ColorBlue, "Authentication completed successfully for user: %s", user.ID)
	c.Redirect(http.StatusFound, "/")
}

// generateChallengeID generates a random challenge ID
func generateChallengeID() string {
	b := make([]byte, 32)
	rand.Read(b)
	return base64.URLEncoding.EncodeToString(b)
}
