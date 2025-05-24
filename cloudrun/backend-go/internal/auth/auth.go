package auth

import (
	"context"
	"fmt"
	"log"
	"time"

	"cloud.google.com/go/firestore"
	"github.com/gin-contrib/sessions"
	"github.com/gin-gonic/gin"
	"github.com/speckle/model-checker/internal/models"
	"github.com/speckle/model-checker/internal/services"
)

var (
	speckleService = services.NewSpeckleService()
	db             *firestore.Client
	ctx            = context.Background()
)

// Initialize initializes the auth package
func Initialize(client *firestore.Client) {
	db = client
}

// InitializeFromFirebase initializes the auth package using the Firebase client
func InitializeFromFirebase() error {
	if firestoreClient == nil {
		return fmt.Errorf("firestore client not initialized")
	}
	db = firestoreClient
	return nil
}

// GetUserToken retrieves the user's Speckle token from Firestore
func GetUserToken(userID string) (*models.UserToken, error) {
	doc, err := db.Collection("userTokens").Doc(userID).Get(ctx)
	if err != nil {
		return nil, err
	}

	var token models.UserToken
	if err := doc.DataTo(&token); err != nil {
		return nil, err
	}
	return &token, nil
}

// GetProjects retrieves projects from Speckle
func GetProjects(token string) ([]models.Project, error) {
	return speckleService.GetProjects(token, 5, "")
}

// GetProjectsWithPagination retrieves projects with pagination
func GetProjectsWithPagination(token string, projectsLimit, modelsLimit, versionsLimit int, projectsCursor, modelsCursor string) ([]models.Project, error) {
	return speckleService.GetProjects(token, projectsLimit, projectsCursor)
}

// SearchProjects searches for projects in Speckle
func SearchProjects(token, searchQuery string, modelsLimit, versionsLimit int) ([]models.Project, error) {
	return speckleService.SearchProjects(token, searchQuery, modelsLimit, versionsLimit)
}

// GetProjectDetails retrieves details for a specific project
func GetProjectDetails(token, projectID string) (*models.Project, error) {
	return speckleService.GetProjectDetails(token, projectID)
}

// GetProjectRulesets retrieves rulesets for a project
func GetProjectRulesets(projectID string) ([]models.Ruleset, error) {
	iter := db.Collection("rulesets").Where("projectId", "==", projectID).Documents(ctx)
	var rulesets []models.Ruleset
	for {
		doc, err := iter.Next()
		if err != nil {
			break
		}
		var ruleset models.Ruleset
		if err := doc.DataTo(&ruleset); err != nil {
			continue
		}
		ruleset.ID = doc.Ref.ID
		rulesets = append(rulesets, ruleset)
	}
	return rulesets, nil
}

// AddRule adds a new rule to a ruleset
func AddRule(rulesetID string, rule *models.Rule) error {
	rule.CreatedAt = time.Now()
	rule.UpdatedAt = time.Now()
	_, _, err := db.Collection("rulesets").Doc(rulesetID).Collection("rules").Add(ctx, rule)
	return err
}

// GetCurrentUser retrieves the current user from the context or session
func GetCurrentUser(c *gin.Context) *models.User {
	// First check if user is in context
	if user, exists := c.Get("user"); exists {
		log.Printf("GetCurrentUser - Found user in context: type=%T, value=%+v", user, user)
		if u, ok := user.(*models.User); ok {
			return u
		}
	}

	// If not in context, try to get from session
	session := sessions.Default(c)
	userID := session.Get("user_id")
	userName := session.Get("user_name")
	userEmail := session.Get("user_email")

	log.Printf("GetCurrentUser - Session values: userID=%v, userName=%v, userEmail=%v", userID, userName, userEmail)

	if userID == nil || userName == nil || userEmail == nil {
		log.Printf("GetCurrentUser - Missing session data")
		return nil
	}

	user := &models.User{
		ID:    userID.(string),
		Name:  userName.(string),
		Email: userEmail.(string),
	}
	log.Printf("GetCurrentUser - Created user from session: %+v", user)

	// Set user in context for future use
	c.Set("user", user)
	return user
}

// GetAllRulesets retrieves all rulesets
func GetAllRulesets() ([]models.Ruleset, error) {
	iter := db.Collection("rulesets").Documents(ctx)
	var rulesets []models.Ruleset
	for {
		doc, err := iter.Next()
		if err != nil {
			break
		}
		var ruleset models.Ruleset
		if err := doc.DataTo(&ruleset); err != nil {
			continue
		}
		ruleset.ID = doc.Ref.ID
		rulesets = append(rulesets, ruleset)
	}
	return rulesets, nil
}

// GetRuleset retrieves a specific ruleset
func GetRuleset(rulesetID string) (*models.Ruleset, error) {
	doc, err := db.Collection("rulesets").Doc(rulesetID).Get(ctx)
	if err != nil {
		return nil, err
	}

	var ruleset models.Ruleset
	if err := doc.DataTo(&ruleset); err != nil {
		return nil, err
	}
	ruleset.ID = doc.Ref.ID
	return &ruleset, nil
}

// CreateRuleset creates a new ruleset
func CreateRuleset(ruleset *models.Ruleset) error {
	ruleset.CreatedAt = time.Now()
	ruleset.UpdatedAt = time.Now()
	_, _, err := db.Collection("rulesets").Add(ctx, ruleset)
	return err
}

// UpdateRuleset updates an existing ruleset
func UpdateRuleset(ruleset *models.Ruleset) error {
	ruleset.UpdatedAt = time.Now()
	_, err := db.Collection("rulesets").Doc(ruleset.ID).Set(ctx, ruleset)
	return err
}

// DeleteRuleset deletes a ruleset
func DeleteRuleset(rulesetID string) error {
	_, err := db.Collection("rulesets").Doc(rulesetID).Delete(ctx)
	return err
}

// GetRule retrieves a specific rule from a ruleset
func GetRule(rulesetID, ruleID string) (*models.Rule, error) {
	doc, err := db.Collection("rulesets").Doc(rulesetID).Collection("rules").Doc(ruleID).Get(ctx)
	if err != nil {
		return nil, err
	}

	var rule models.Rule
	if err := doc.DataTo(&rule); err != nil {
		return nil, err
	}
	rule.ID = doc.Ref.ID
	return &rule, nil
}

// UpdateRule updates an existing rule
func UpdateRule(rulesetID string, rule *models.Rule) error {
	rule.UpdatedAt = time.Now()
	_, err := db.Collection("rulesets").Doc(rulesetID).Collection("rules").Doc(rule.ID).Set(ctx, rule)
	return err
}

// DeleteRule deletes a rule
func DeleteRule(rulesetID, ruleID string) error {
	_, err := db.Collection("rulesets").Doc(rulesetID).Collection("rules").Doc(ruleID).Delete(ctx)
	return err
}

// ReorderRule reorders a rule within a ruleset
func ReorderRule(rulesetID, ruleID, direction string) error {
	// Get all rules in the ruleset
	iter := db.Collection("rulesets").Doc(rulesetID).Collection("rules").Documents(ctx)
	var rules []models.Rule
	for {
		doc, err := iter.Next()
		if err != nil {
			break
		}
		var rule models.Rule
		if err := doc.DataTo(&rule); err != nil {
			continue
		}
		rule.ID = doc.Ref.ID
		rules = append(rules, rule)
	}

	// Find the rule to reorder
	var currentIndex int
	for i, rule := range rules {
		if rule.ID == ruleID {
			currentIndex = i
			break
		}
	}

	// Calculate new index
	var newIndex int
	if direction == "up" && currentIndex > 0 {
		newIndex = currentIndex - 1
	} else if direction == "down" && currentIndex < len(rules)-1 {
		newIndex = currentIndex + 1
	} else {
		return nil // No reordering needed
	}

	// Swap rules
	rules[currentIndex], rules[newIndex] = rules[newIndex], rules[currentIndex]

	// Update rules in Firestore
	batch := db.Batch()
	for _, rule := range rules {
		ref := db.Collection("rulesets").Doc(rulesetID).Collection("rules").Doc(rule.ID)
		batch.Set(ref, rule)
	}
	_, err := batch.Commit(ctx)
	return err
}
