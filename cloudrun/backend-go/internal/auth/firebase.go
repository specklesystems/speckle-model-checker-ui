package auth

import (
	"fmt"
	"os"
	"path/filepath"

	"cloud.google.com/go/firestore"
	firebase "firebase.google.com/go/v4"
	"firebase.google.com/go/v4/auth"
	"google.golang.org/api/option"
)

var (
	app             *firebase.App
	authClient      *auth.Client
	firestoreClient *firestore.Client
)

// InitializeFirebase initializes the Firebase Admin SDK
func InitializeFirebase() error {
	// Service account key - try current directory first, then parent directory
	credPath := "./firebase-service-account-key.json"
	if _, err := os.Stat(credPath); os.IsNotExist(err) {
		credPath = filepath.Join("..", "firebase-service-account-key.json")
		if _, err := os.Stat(credPath); os.IsNotExist(err) {
			return fmt.Errorf("firebase service account key not found in current or parent directory")
		}
	}
	opt := option.WithCredentialsFile(credPath)

	// Firebase App (for Auth & Firestore)
	cfg := &firebase.Config{}
	var err error
	app, err = firebase.NewApp(ctx, cfg, opt)
	if err != nil {
		return err
	}

	// Auth client
	authClient, err = app.Auth(ctx)
	if err != nil {
		return err
	}

	// Firestore client
	firestoreClient, err = app.Firestore(ctx)
	if err != nil {
		return err
	}

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

// Close closes all Firebase clients
func Close() {
	if firestoreClient != nil {
		firestoreClient.Close()
	}
}
