package models

import (
	"html/template"
	"time"
)

// User represents a Speckle user
type User struct {
	ID     string `json:"id"`
	Name   string `json:"name"`
	Email  string `json:"email"`
	Avatar string `json:"avatar"`
}

// UserToken represents a user's Speckle token stored in Firestore
type UserToken struct {
	SpeckleToken string    `firestore:"speckleToken"`
	UserID       string    `firestore:"userId"`
	CreatedAt    time.Time `firestore:"createdAt"`
	UpdatedAt    time.Time `firestore:"updatedAt"`
}

// Project represents a Speckle project
type Project struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description"`
	Models      struct {
		TotalCount int     `json:"totalCount"`
		Cursor     string  `json:"cursor"`
		Items      []Model `json:"items"`
	} `json:"models"`
	ModelIDs []string `json:"-"` // Model IDs for lazy loading
}

// Model represents a Speckle model
type Model struct {
	ID             string       `json:"id"`
	Name           string       `json:"name"`
	Description    string       `json:"description"`
	PreviewUrl     string       `json:"previewUrl"`
	PreviewDataURI template.URL // base64 data URI for template rendering
	Versions       struct {
		Items []Version `json:"items"`
	} `json:"versions"`
	TotalCount int    `json:"totalCount"`
	Cursor     string `json:"cursor"`
}

// Version represents a Speckle model version
type Version struct {
	SourceApplication string `json:"sourceApplication"`
}

// Ruleset represents a set of rules for model checking
type Ruleset struct {
	ID          string    `firestore:"id"`
	Name        string    `firestore:"name"`
	Description string    `firestore:"description"`
	ProjectID   string    `firestore:"projectId"`
	Rules       []Rule    `firestore:"rules"`
	CreatedAt   time.Time `firestore:"createdAt"`
	UpdatedAt   time.Time `firestore:"updatedAt"`
}

// Rule represents a single rule in a ruleset
type Rule struct {
	ID          string      `firestore:"id"`
	Name        string      `firestore:"name"`
	Description string      `firestore:"description"`
	Conditions  []Condition `firestore:"conditions"`
	Message     string      `firestore:"message"`
	CreatedAt   time.Time   `firestore:"createdAt"`
	UpdatedAt   time.Time   `firestore:"updatedAt"`
}

// Condition represents a condition in a rule
type Condition struct {
	PropertyName string      `firestore:"propertyName"`
	Predicate    string      `firestore:"predicate"`
	Value        interface{} `firestore:"value"`
}
