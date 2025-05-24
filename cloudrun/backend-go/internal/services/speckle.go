package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/speckle/model-checker/internal/models"
)

const (
	speckleServerURL = "https://app.speckle.systems"
)

// SpeckleService handles interactions with the Speckle API
type SpeckleService struct {
	client *http.Client
}

// NewSpeckleService creates a new SpeckleService instance
func NewSpeckleService() *SpeckleService {
	return &SpeckleService{
		client: &http.Client{},
	}
}

// GetProjects fetches projects from Speckle
func (s *SpeckleService) GetProjects(token string, limit int, cursor string) ([]models.Project, error) {
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

	if err := s.executeGraphQL(token, query, variables, &response); err != nil {
		return nil, err
	}

	return response.Data.ActiveUser.Projects.Items, nil
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
	reqBody := map[string]interface{}{
		"query":     query,
		"variables": variables,
	}

	reqBodyBytes, err := json.Marshal(reqBody)
	if err != nil {
		return fmt.Errorf("failed to marshal request body: %v", err)
	}

	req, err := http.NewRequest("POST", fmt.Sprintf("%s/graphql", speckleServerURL), bytes.NewReader(reqBodyBytes))
	if err != nil {
		return fmt.Errorf("failed to create request: %v", err)
	}

	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", token))
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to execute request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	if err := json.NewDecoder(resp.Body).Decode(response); err != nil {
		return fmt.Errorf("failed to decode response: %v", err)
	}

	return nil
}
