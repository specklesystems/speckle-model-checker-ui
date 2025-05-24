package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/speckle/model-checker/internal/auth"
	"github.com/speckle/model-checker/internal/models"
)

// ListRulesets handles listing all rulesets
func ListRulesets(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.Redirect(http.StatusFound, "/auth/init")
		return
	}

	rulesets, err := auth.GetAllRulesets()
	if err != nil {
		c.HTML(http.StatusInternalServerError, "error.html", gin.H{
			"title": "Error",
			"error": "Failed to fetch rulesets",
		})
		return
	}

	c.HTML(http.StatusOK, "rulesets.html", gin.H{
		"title":    "Rulesets",
		"user":     user,
		"rulesets": rulesets,
	})
}

// NewRuleset handles the new ruleset form
func NewRuleset(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.Redirect(http.StatusFound, "/auth/init")
		return
	}

	c.HTML(http.StatusOK, "ruleset_form.html", gin.H{
		"title": "New Ruleset",
		"user":  user,
	})
}

// EditRuleset handles editing a ruleset
func EditRuleset(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.Redirect(http.StatusFound, "/auth/init")
		return
	}

	rulesetID := c.Param("ruleset_id")
	ruleset, err := auth.GetRuleset(rulesetID)
	if err != nil {
		c.HTML(http.StatusInternalServerError, "error.html", gin.H{
			"title": "Error",
			"error": "Failed to fetch ruleset",
		})
		return
	}

	c.HTML(http.StatusOK, "ruleset_form.html", gin.H{
		"title":   "Edit Ruleset",
		"user":    user,
		"ruleset": ruleset,
	})
}

// CreateRuleset handles creating a new ruleset
func CreateRuleset(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.Redirect(http.StatusFound, "/auth/init")
		return
	}

	var ruleset models.Ruleset
	if err := c.ShouldBind(&ruleset); err != nil {
		c.HTML(http.StatusBadRequest, "error.html", gin.H{
			"title": "Error",
			"error": "Invalid ruleset data",
		})
		return
	}

	if err := auth.CreateRuleset(&ruleset); err != nil {
		c.HTML(http.StatusInternalServerError, "error.html", gin.H{
			"title": "Error",
			"error": "Failed to create ruleset",
		})
		return
	}

	c.Redirect(http.StatusFound, "/rulesets")
}

// UpdateRuleset handles updating a ruleset
func UpdateRuleset(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.Redirect(http.StatusFound, "/auth/init")
		return
	}

	var ruleset models.Ruleset
	if err := c.ShouldBind(&ruleset); err != nil {
		c.HTML(http.StatusBadRequest, "error.html", gin.H{
			"title": "Error",
			"error": "Invalid ruleset data",
		})
		return
	}

	ruleset.ID = c.Param("ruleset_id")
	if err := auth.UpdateRuleset(&ruleset); err != nil {
		c.HTML(http.StatusInternalServerError, "error.html", gin.H{
			"title": "Error",
			"error": "Failed to update ruleset",
		})
		return
	}

	c.Redirect(http.StatusFound, "/rulesets")
}

// DeleteRuleset handles deleting a ruleset
func DeleteRuleset(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	rulesetID := c.Param("ruleset_id")
	if err := auth.DeleteRuleset(rulesetID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to delete ruleset",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Ruleset deleted successfully"})
}
