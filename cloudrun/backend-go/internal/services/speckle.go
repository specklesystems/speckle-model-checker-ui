package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/speckle/model-checker/internal/logging"
	"github.com/speckle/model-checker/internal/models"
)

const (
	speckleServerURL = "https://app.speckle.systems"
	cacheTTL         = 5 * time.Minute
)

// cachedProjects holds the cached projects data with expiration
type cachedProjects struct {
	projects []models.Project
	cursor   string
	expires  time.Time
}

// SpeckleService handles interactions with the Speckle API
type SpeckleService struct {
	client *http.Client
	mu     sync.RWMutex
	cache  map[string]cachedProjects // key is token:cursor
}

// NewSpeckleService creates a new SpeckleService instance
func NewSpeckleService() *SpeckleService {
	return &SpeckleService{
		client: &http.Client{},
		cache:  make(map[string]cachedProjects),
	}
}

// GetProjects fetches projects from Speckle
func (s *SpeckleService) GetProjects(token string, limit int, cursor string) ([]models.Project, string, error) {
	start := time.Now()

	// Compute cache key using both token and cursor
	cacheKey := fmt.Sprintf("%s:%s", token, cursor)
	// Check cache first
	s.mu.RLock()
	if cached, ok := s.cache[cacheKey]; ok && time.Now().Before(cached.expires) {
		s.mu.RUnlock()
		logging.LogColor(logging.ColorGreen, "Cache hit for projects, took: %v", time.Since(start))
		return cached.projects, cached.cursor, nil
	}
	s.mu.RUnlock()

	query := `
		query($projectsLimit: Int!, $modelsLimit: Int!, $versionsLimit: Int!, $modelsCursor: String, $projectsCursor: String) {
			activeUser {
				projects(limit: $projectsLimit, cursor: $projectsCursor) {
					totalCount
					cursor
					items {
						id
						name
						description
						workspace {
							id
							name
						}
						models(limit: $modelsLimit, cursor: $modelsCursor) {
							totalCount
							cursor
							items {
								id
								name
								description
								previewUrl
								versions(limit: $versionsLimit) {
									items {
										sourceApplication
									}
								}
							}
						}
					}
				}
			}
		}
	`

	variables := map[string]interface{}{
		"projectsLimit":  limit,
		"modelsLimit":    20,
		"versionsLimit":  1,
		"modelsCursor":   nil,
		"projectsCursor": cursor,
	}

	var response struct {
		Data struct {
			ActiveUser struct {
				Projects struct {
					TotalCount int              `json:"totalCount"`
					Cursor     string           `json:"cursor"`
					Items      []models.Project `json:"items"`
				} `json:"projects"`
			} `json:"activeUser"`
		} `json:"data"`
	}

	executeStart := time.Now()
	if err := s.executeGraphQL(token, query, variables, &response); err != nil {
		logging.LogColor(logging.ColorRed, "executeGraphQL failed: %v", err)
		return nil, "", err
	}
	logging.LogColor(logging.ColorBlue, "executeGraphQL took: %v", time.Since(executeStart))

	// Cache the results
	s.mu.Lock()
	s.cache[cacheKey] = cachedProjects{
		projects: response.Data.ActiveUser.Projects.Items,
		cursor:   response.Data.ActiveUser.Projects.Cursor,
		expires:  time.Now().Add(cacheTTL),
	}
	s.mu.Unlock()

	log.Printf("Total GetProjects took: %v", time.Since(start))
	return response.Data.ActiveUser.Projects.Items, response.Data.ActiveUser.Projects.Cursor, nil
}

// InvalidateCache invalidates the cache for a given token
func (s *SpeckleService) InvalidateCache(token string) {
	s.mu.Lock()
	delete(s.cache, token)
	s.mu.Unlock()
}

// SearchProjects searches for projects in Speckle
func (s *SpeckleService) SearchProjects(token, searchQuery string, modelsLimit, versionsLimit int) ([]models.Project, error) {
	query := `
		query($filter: UserProjectsFilter, $modelsLimit: Int!, $versionsLimit: Int!) {
			activeUser {
				projects(filter: $filter) {
					items {
						id
						name
						description
						models(limit: $modelsLimit) {
							totalCount
							items {
								id
								name
								description
								previewUrl
								versions(limit: $versionsLimit) {
									items {
										sourceApplication
									}
								}
							}
						}
					}
				}
			}
		}
	`

	variables := map[string]interface{}{
		"filter": map[string]string{
			"search": searchQuery,
		},
		"modelsLimit":   modelsLimit,
		"versionsLimit": versionsLimit,
	}

	var response struct {
		Data struct {
			ActiveUser struct {
				Projects struct {
					Items []models.Project `json:"items"`
				} `json:"projects"`
			} `json:"activeUser"`
		} `json:"data"`
	}

	if err := s.executeGraphQL(token, query, variables, &response); err != nil {
		return nil, err
	}

	return response.Data.ActiveUser.Projects.Items, nil
}

// GetProjectDetails fetches details for a specific project
func (s *SpeckleService) GetProjectDetails(token, projectID string) (*models.Project, error) {
	query := `
		query($projectId: String!, $modelsLimit: Int!, $versionsLimit: Int!) {
			project(id: $projectId) {
				id
				name
				description
				models(limit: $modelsLimit) {
					totalCount
					items {
						id
						name
						description
						previewUrl
						versions(limit: $versionsLimit) {
							items {
								sourceApplication
							}
						}
					}
				}
			}
		}
	`

	variables := map[string]interface{}{
		"projectId":     projectID,
		"modelsLimit":   20,
		"versionsLimit": 1,
	}

	var response struct {
		Data struct {
			Project models.Project `json:"project"`
		} `json:"data"`
	}

	if err := s.executeGraphQL(token, query, variables, &response); err != nil {
		return nil, err
	}

	return &response.Data.Project, nil
}

// executeGraphQL executes a GraphQL query against the Speckle API
func (s *SpeckleService) executeGraphQL(token, query string, variables map[string]interface{}, response interface{}) error {
	start := time.Now()
	reqBody := map[string]interface{}{
		"query":     query,
		"variables": variables,
	}

	marshalStart := time.Now()
	reqBodyBytes, err := json.Marshal(reqBody)
	if err != nil {
		logging.LogColor(logging.ColorRed, "json.Marshal failed: %v", err)
		return err
	}
	log.Printf("json.Marshal took: %v", time.Since(marshalStart))

	req, err := http.NewRequest("POST", fmt.Sprintf("%s/graphql", speckleServerURL), bytes.NewBuffer(reqBodyBytes))
	if err != nil {
		logging.LogColor(logging.ColorRed, "Failed to create request: %v", err)
		return err
	}

	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", token))
	req.Header.Set("Content-Type", "application/json")

	httpStart := time.Now()
	resp, err := s.client.Do(req)
	if err != nil {
		logging.LogColor(logging.ColorRed, "http.Do failed: %v", err)
		return err
	}
	defer resp.Body.Close()
	log.Printf("http.Do took: %v", time.Since(httpStart))

	if resp.StatusCode != http.StatusOK {
		logging.LogColor(logging.ColorRed, "GraphQL request failed with status: %d", resp.StatusCode)
		return fmt.Errorf("GraphQL request failed with status: %d", resp.StatusCode)
	}

	decodeStart := time.Now()
	if err := json.NewDecoder(resp.Body).Decode(response); err != nil {
		logging.LogColor(logging.ColorRed, "json.Decode failed: %v", err)
		return err
	}
	log.Printf("json.Decode took: %v", time.Since(decodeStart))

	log.Printf("Total executeGraphQL took: %v", time.Since(start))
	return nil
}

// GetModelByID fetches a model by its ID by searching all projects and their models
func GetModelByID(token, modelID string) (*models.Model, error) {
	s := NewSpeckleService()
	projects, _, err := s.GetProjects(token, 100, "")
	if err != nil {
		return nil, err
	}
	for _, project := range projects {
		for _, model := range project.Models.Items {
			if model.ID == modelID {
				return &model, nil
			}
		}
	}
	return nil, fmt.Errorf("model not found")
}
