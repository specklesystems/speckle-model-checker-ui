package services

import (
	"context"
	"encoding/base64"
	"fmt"
	"io"
	"log"
	"math"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/speckle/model-checker/internal/firebase"
	"github.com/speckle/model-checker/internal/logging"
	"github.com/speckle/model-checker/internal/models"
)

// Model represents a Speckle model
type Model struct {
	ID         string `json:"id"`
	PreviewUrl string `json:"previewUrl"`
}

const (
	previewCacheTTL = 24 * time.Hour   // Cache previews for 24 hours
	speckleTimeout  = 10 * time.Second // Reduced timeout for Speckle API calls
	firebaseTimeout = 5 * time.Second  // Reduced timeout for Firebase operations
	batchSize       = 5                // Reduced batch size to avoid rate limits
	maxRetries      = 3                // Maximum number of retries for failed requests
	initialBackoff  = 1 * time.Second  // Initial backoff duration
)

// cachedPreview holds the cached preview data with expiration
type cachedPreview struct {
	dataURI string
	expires time.Time
}

// PreviewService handles model preview caching and retrieval
type PreviewService struct {
	mu    sync.RWMutex
	cache map[string]cachedPreview // key is modelID
}

// NewPreviewService creates a new PreviewService instance
func NewPreviewService() *PreviewService {
	return &PreviewService{
		cache: make(map[string]cachedPreview),
	}
}

// GetModelPreviewDataURI fetches or caches and returns the data URI for a model preview
func (s *PreviewService) GetModelPreviewDataURI(modelID string, userToken string) string {
	start := time.Now()
	log.Printf("Starting preview fetch for model %s", modelID)

	// Check local cache first
	s.mu.RLock()
	if cached, ok := s.cache[modelID]; ok && time.Now().Before(cached.expires) {
		s.mu.RUnlock()
		logging.LogColor(logging.ColorGreen, "Local cache hit for model %s, took: %v", modelID, time.Since(start))
		return cached.dataURI
	}
	s.mu.RUnlock()
	log.Printf("Local cache miss for model %s", modelID)

	// Try Firebase Storage
	ctx, cancel := context.WithTimeout(context.Background(), firebaseTimeout)
	defer cancel()

	bucketName := os.Getenv("FIREBASE_STORAGE_BUCKET")
	objectName := fmt.Sprintf("previews/%s.png", modelID)
	bucket := firebase.GetBucket(bucketName)

	// Only try Firebase if we have a valid bucket
	if bucket != nil {
		obj := bucket.Object(objectName)
		cacheStart := time.Now()
		logging.LogColor(logging.ColorYellow, "Attempting Firebase Storage fetch for model %s", modelID)
		rc, err := obj.NewReader(ctx)
		if err == nil {
			defer rc.Close()
			imgBytes, err := io.ReadAll(rc)
			if err == nil {
				contentType := "image/png"
				base64Data := base64.StdEncoding.EncodeToString(imgBytes)
				dataURI := fmt.Sprintf("data:%s;base64,%s", contentType, base64Data)

				// Cache in local memory
				s.mu.Lock()
				s.cache[modelID] = cachedPreview{
					dataURI: dataURI,
					expires: time.Now().Add(previewCacheTTL),
				}
				s.mu.Unlock()

				logging.LogColor(logging.ColorYellow, "Firebase cache hit for model %s, took: %v", modelID, time.Since(cacheStart))
				return dataURI
			}
		}
		logging.LogColor(logging.ColorYellow, "Firebase cache miss for model %s, took: %v", modelID, time.Since(cacheStart))
	} else {
		logging.LogColor(logging.ColorYellow, "Firebase Storage unavailable, falling back to Speckle for model %s", modelID)
	}

	// Not in cache or Firebase unavailable, fetch from Speckle with retries
	speckleStart := time.Now()
	logging.LogColor(logging.ColorBlue, "Fetching model %s from Speckle API", modelID)

	var model *models.Model
	var err error
	backoff := initialBackoff

	for retry := 0; retry < maxRetries; retry++ {
		model, err = GetModelByID(userToken, modelID)
		if err == nil && model != nil {
			break
		}

		if retry < maxRetries-1 {
			logging.LogColor(logging.ColorYellow, "Retry %d for model %s, backing off for %v", retry+1, modelID, backoff)
			time.Sleep(backoff)
			backoff = time.Duration(math.Pow(2, float64(retry+1))) * initialBackoff
		}
	}

	if err != nil || model == nil || model.PreviewUrl == "" {
		logging.LogColor(logging.ColorRed, "Failed to get model %s from Speckle after %d retries, took: %v", modelID, maxRetries, time.Since(speckleStart))
		return ""
	}
	logging.LogColor(logging.ColorBlue, "Got model %s from Speckle, took: %v", modelID, time.Since(speckleStart))

	// Fetch preview from Speckle with retries
	previewStart := time.Now()
	logging.LogColor(logging.ColorBlue, "Fetching preview from Speckle for model %s", modelID)

	var imgBytes []byte
	backoff = initialBackoff

	for retry := 0; retry < maxRetries; retry++ {
		req, _ := http.NewRequestWithContext(ctx, "GET", model.PreviewUrl, nil)
		req.Header.Set("Authorization", "Bearer "+userToken)
		resp, err := http.DefaultClient.Do(req)
		if err == nil && resp.StatusCode == 200 {
			imgBytes, err = io.ReadAll(resp.Body)
			resp.Body.Close()
			if err == nil && len(imgBytes) > 0 {
				break
			}
		}

		if retry < maxRetries-1 {
			logging.LogColor(logging.ColorYellow, "Retry %d for preview %s, backing off for %v", retry+1, modelID, backoff)
			time.Sleep(backoff)
			backoff = time.Duration(math.Pow(2, float64(retry+1))) * initialBackoff
		}
	}

	if len(imgBytes) == 0 {
		logging.LogColor(logging.ColorRed, "Failed to fetch preview for model %s after %d retries, took: %v", modelID, maxRetries, time.Since(previewStart))
		return ""
	}

	logging.LogColor(logging.ColorBlue, "Fetched preview for model %s, size: %d bytes, took: %v", modelID, len(imgBytes), time.Since(previewStart))

	// Try to cache in Firebase Storage in a goroutine if available
	if bucket != nil {
		go func() {
			cacheStart := time.Now()
			logging.LogColor(logging.ColorYellow, "Caching preview in Firebase for model %s", modelID)
			// Create a new context specifically for Firebase caching
			cacheCtx, cacheCancel := context.WithTimeout(context.Background(), firebaseTimeout)
			defer cacheCancel()
			wc := bucket.Object(objectName).NewWriter(cacheCtx)
			wc.ContentType = "image/png"
			if _, err := wc.Write(imgBytes); err == nil {
				wc.Close()
				logging.LogColor(logging.ColorYellow, "Cached preview for model %s in Firebase, took: %v", modelID, time.Since(cacheStart))
			} else {
				logging.LogColor(logging.ColorRed, "Failed to cache preview in Firebase for model %s: %v", modelID, err)
			}
		}()
	}

	// Cache in local memory
	base64Data := base64.StdEncoding.EncodeToString(imgBytes)
	dataURI := fmt.Sprintf("data:image/png;base64,%s", base64Data)
	s.mu.Lock()
	s.cache[modelID] = cachedPreview{
		dataURI: dataURI,
		expires: time.Now().Add(previewCacheTTL),
	}
	s.mu.Unlock()

	log.Printf("Total preview processing for model %s took: %v", modelID, time.Since(start))
	return dataURI
}

// GetModelPreviews fetches previews for multiple models concurrently
func (s *PreviewService) GetModelPreviews(modelIDs []string, userToken string) map[string]string {
	start := time.Now()
	logging.LogColor(logging.ColorBlue, "Fetching previews for %d models", len(modelIDs))

	// First, check local cache for all models
	previews := make(map[string]string)
	remainingIDs := make([]string, 0, len(modelIDs))

	s.mu.RLock()
	for _, modelID := range modelIDs {
		if cached, ok := s.cache[modelID]; ok && time.Now().Before(cached.expires) {
			previews[modelID] = cached.dataURI
		} else {
			remainingIDs = append(remainingIDs, modelID)
		}
	}
	s.mu.RUnlock()

	if len(remainingIDs) == 0 {
		logging.LogColor(logging.ColorGreen, "All %d previews found in local cache, took: %v", len(modelIDs), time.Since(start))
		return previews
	}

	// Create a channel to receive results
	type result struct {
		modelID string
		dataURI string
	}
	results := make(chan result, len(remainingIDs))

	// Create a WaitGroup to track completion
	var wg sync.WaitGroup

	// Process models in smaller batches with delay between batches
	for i := 0; i < len(remainingIDs); i += batchSize {
		end := i + batchSize
		if end > len(remainingIDs) {
			end = len(remainingIDs)
		}
		batch := remainingIDs[i:end]
		wg.Add(len(batch))

		// Add delay between batches to avoid rate limits
		if i > 0 {
			time.Sleep(2 * time.Second)
		}

		// Fetch each preview in a goroutine
		for _, modelID := range batch {
			go func(id string) {
				defer wg.Done()
				dataURI := s.GetModelPreviewDataURI(id, userToken)
				results <- result{modelID: id, dataURI: dataURI}
			}(modelID)
		}
	}

	// Start a goroutine to close the results channel when all fetches are done
	go func() {
		wg.Wait()
		close(results)
	}()

	// Collect results
	for r := range results {
		if r.dataURI != "" {
			previews[r.modelID] = r.dataURI
		}
	}

	logging.LogColor(logging.ColorBlue, "Fetched %d/%d previews, took: %v", len(previews), len(modelIDs), time.Since(start))
	return previews
}

// InvalidateCache invalidates the cache for a given model
func (s *PreviewService) InvalidateCache(modelID string) {
	s.mu.Lock()
	delete(s.cache, modelID)
	s.mu.Unlock()
}
