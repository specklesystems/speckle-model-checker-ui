package auth

import (
	"fmt"
	"os"
	"path/filepath"

	"encoding/json"
	"io/ioutil"

	"cloud.google.com/go/firestore"
	"cloud.google.com/go/storage"
	firebase "firebase.google.com/go/v4"
	"firebase.google.com/go/v4/auth"
	"github.com/speckle/model-checker/internal/logging"
	"google.golang.org/api/option"
)

var (
	app             *firebase.App
	authClient      *auth.Client
	firestoreClient *firestore.Client
	storageClient   *storage.Client // cache the storage client
	googleAccessID  string
	privateKey      []byte
)

// InitializeFirebase initializes the Firebase Admin SDK
func InitializeFirebase() error {
	// Service account key - try current directory first, then parent directory
	credPath := "./firebase-service-account-key.json"
	if _, err := os.Stat(credPath); os.IsNotExist(err) {
		credPath = filepath.Join("..", "firebase-service-account-key.json")
		if _, err := os.Stat(credPath); os.IsNotExist(err) {
			logging.LogColor(logging.ColorRed, "Firebase service account key not found in current or parent directory")
			return fmt.Errorf("firebase service account key not found in current or parent directory")
		}
	}
	opt := option.WithCredentialsFile(credPath)

	// Firebase App (for Auth & Firestore)
	cfg := &firebase.Config{}
	var err error
	app, err = firebase.NewApp(ctx, cfg, opt)
	if err != nil {
		logging.LogColor(logging.ColorRed, "Failed to initialize Firebase app: %v", err)
		return err
	}

	// Auth client
	authClient, err = app.Auth(ctx)
	if err != nil {
		logging.LogColor(logging.ColorRed, "Failed to initialize Firebase Auth client: %v", err)
		return err
	}

	// Firestore client
	firestoreClient, err = app.Firestore(ctx)
	if err != nil {
		logging.LogColor(logging.ColorRed, "Failed to initialize Firestore client: %v", err)
		return err
	}

	// Storage client (cache it)
	storageClient, err = storage.NewClient(ctx, option.WithCredentialsFile(credPath))
	if err != nil {
		logging.LogColor(logging.ColorRed, "Failed to initialize Storage client: %v", err)
		return err
	}

	logging.LogColor(logging.ColorYellow, "Firebase initialization completed successfully")
	return nil
}

// GetFirestoreClient returns the Firestore client
func GetFirestoreClient() *firestore.Client {
	return firestoreClient
}

// GetAuthClient returns the Auth client
func GetAuthClient() *auth.Client {
	return authClient
}

// GetFirebaseStorageClient returns the cached Google Cloud Storage client
func GetFirebaseStorageClient() *storage.Client {
	return storageClient
}

// Close closes all Firebase clients
func Close() {
	if firestoreClient != nil {
		firestoreClient.Close()
	}
}

// GetGoogleAccessID returns the client_email from the service account JSON, caching after first read
func GetGoogleAccessID() (string, error) {
	if googleAccessID != "" {
		return googleAccessID, nil
	}
	credPath := "./firebase-service-account-key.json"
	if _, err := os.Stat(credPath); os.IsNotExist(err) {
		credPath = filepath.Join("..", "firebase-service-account-key.json")
	}
	data, err := ioutil.ReadFile(credPath)
	if err != nil {
		return "", err
	}
	var creds struct {
		ClientEmail string `json:"client_email"`
	}
	if err := json.Unmarshal(data, &creds); err != nil {
		return "", err
	}
	googleAccessID = creds.ClientEmail
	return googleAccessID, nil
}

// GetPrivateKey returns the private_key from the service account JSON, caching after first read
func GetPrivateKey() ([]byte, error) {
	if privateKey != nil {
		return privateKey, nil
	}
	credPath := "./firebase-service-account-key.json"
	if _, err := os.Stat(credPath); os.IsNotExist(err) {
		credPath = filepath.Join("..", "firebase-service-account-key.json")
	}
	data, err := ioutil.ReadFile(credPath)
	if err != nil {
		return nil, err
	}
	var creds struct {
		PrivateKey string `json:"private_key"`
	}
	if err := json.Unmarshal(data, &creds); err != nil {
		return nil, err
	}
	privateKey = []byte(creds.PrivateKey)
	return privateKey, nil
}
