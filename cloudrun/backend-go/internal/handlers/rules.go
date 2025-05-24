package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/speckle/model-checker/internal/auth"
	"github.com/speckle/model-checker/internal/models"
)

// NewRuleForm handles the new rule form
func NewRuleForm(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.Redirect(http.StatusFound, "/")
		return
	}

	rulesetID := c.Param("ruleset_id")
	c.HTML(http.StatusOK, "rule_form.html", gin.H{
		"title":     "New Rule",
		"user":      user,
		"rulesetID": rulesetID,
	})
}

// AddRule handles adding a new rule
func AddRule(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.Redirect(http.StatusFound, "/")
		return
	}

	var rule models.Rule
	if err := c.ShouldBind(&rule); err != nil {
		c.HTML(http.StatusBadRequest, "error.html", gin.H{
			"title": "Error",
			"error": "Invalid rule data",
		})
		return
	}

	rulesetID := c.Param("ruleset_id")
	if err := auth.AddRule(rulesetID, &rule); err != nil {
		c.HTML(http.StatusInternalServerError, "error.html", gin.H{
			"title": "Error",
			"error": "Failed to add rule",
		})
		return
	}

	c.Redirect(http.StatusFound, "/rulesets/"+rulesetID+"/edit")
}

// EditRule handles editing a rule
func EditRule(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.Redirect(http.StatusFound, "/")
		return
	}

	rulesetID := c.Param("ruleset_id")
	ruleID := c.Param("rule_id")
	rule, err := auth.GetRule(rulesetID, ruleID)
	if err != nil {
		c.HTML(http.StatusInternalServerError, "error.html", gin.H{
			"title": "Error",
			"error": "Failed to fetch rule",
		})
		return
	}

	c.HTML(http.StatusOK, "rule_form.html", gin.H{
		"title":     "Edit Rule",
		"user":      user,
		"rulesetID": rulesetID,
		"rule":      rule,
	})
}

// UpdateRule handles updating a rule
func UpdateRule(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.Redirect(http.StatusFound, "/")
		return
	}

	var rule models.Rule
	if err := c.ShouldBind(&rule); err != nil {
		c.HTML(http.StatusBadRequest, "error.html", gin.H{
			"title": "Error",
			"error": "Invalid rule data",
		})
		return
	}

	rulesetID := c.Param("ruleset_id")
	rule.ID = c.Param("rule_id")
	if err := auth.UpdateRule(rulesetID, &rule); err != nil {
		c.HTML(http.StatusInternalServerError, "error.html", gin.H{
			"title": "Error",
			"error": "Failed to update rule",
		})
		return
	}

	c.Redirect(http.StatusFound, "/rulesets/"+rulesetID+"/edit")
}

// DeleteRule handles deleting a rule
func DeleteRule(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	rulesetID := c.Param("ruleset_id")
	ruleID := c.Param("rule_id")
	if err := auth.DeleteRule(rulesetID, ruleID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to delete rule",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Rule deleted successfully"})
}

// ReorderRule handles reordering a rule
func ReorderRule(c *gin.Context) {
	user := auth.GetCurrentUser(c)
	if user == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
		return
	}

	rulesetID := c.Param("ruleset_id")
	ruleID := c.Param("rule_id")
	direction := c.Query("direction")

	if err := auth.ReorderRule(rulesetID, ruleID, direction); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to reorder rule",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Rule reordered successfully"})
}
