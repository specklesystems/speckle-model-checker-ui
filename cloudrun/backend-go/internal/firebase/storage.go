package firebase

import (
	"context"
	"os"
	"sync"

	"cloud.google.com/go/storage"
	"github.com/speckle/model-checker/internal/logging"
	"google.golang.org/api/option"
)

var (
	storageClient     *storage.Client
	storageClientOnce sync.Once
)

// GetStorageClient returns a singleton instance of the Firebase Storage client
func GetStorageClient() *storage.Client {
	storageClientOnce.Do(func() {
		var err error
		ctx := context.Background()
		credsPath := os.Getenv("FIREBASE_CREDENTIALS_PATH")
		if credsPath == "" {
			logging.LogColor(logging.ColorRed, "FIREBASE_CREDENTIALS_PATH not set, cannot create Firebase Storage client")
			return
		}

		// Use the absolute path directly
		absPath := "/workspace/cloudrun/firebase-service-account-key.json"
		logging.LogColor(logging.ColorYellow, "Initializing Firebase Storage client with credentials from: %s", absPath)
		storageClient, err = storage.NewClient(ctx, option.WithCredentialsFile(absPath))
		if err != nil {
			logging.LogColor(logging.ColorRed, "Failed to create Firebase Storage client: %v", err)
			return
		}
		logging.LogColor(logging.ColorYellow, "Firebase Storage client initialized successfully")
	})
	return storageClient
}

// GetBucket returns a bucket instance for the given bucket name
func GetBucket(bucketName string) *storage.BucketHandle {
	client := GetStorageClient()
	if client == nil {
		logging.LogColor(logging.ColorRed, "Cannot get bucket %s: Firebase Storage client is not initialized", bucketName)
		return nil
	}
	logging.LogColor(logging.ColorYellow, "Getting Firebase Storage bucket: %s", bucketName)
	return client.Bucket(bucketName)
}
