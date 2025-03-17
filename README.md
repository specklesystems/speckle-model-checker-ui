# Speckle Checker UI - Proof of Concept

This document outlines a proof of concept implementation for replacing the Google Sheet interface for Speckle Checker rules with a dedicated web-based UI.

## Architecture Overview

The solution uses a lightweight tech stack focused on simplicity and ease of implementation:

- **Frontend**: HTML + HTMX + Tailwind CSS
- **Backend**: Firebase Cloud Functions (serverless)
- **Database**: Firebase Firestore
- **Authentication**: Speckle Authentication with Firebase Auth
- **Hosting**: Firebase Hosting

This approach eliminates the need for Google Sheets while maintaining a simple, user-friendly interface for managing validation rules.

## Key Features

1. **Authentication**: User management with Speckle Single Sign-On
2. **Rule Management**: Create, edit, and delete rule sets
3. **Rule Editor**: Intuitive interface for defining rule conditions
4. **Sharing**: Generate public URLs for use in Speckle Automations
5. **Export**: Download rules as TSV files compatible with the current Checker function

## Implementation Details

### Authentication Flow

Users authenticate through Speckle's OAuth system:

1. User clicks "Sign In with Speckle"
2. Firebase function generates a secure challenge and redirects to Speckle auth
3. After successful authentication, Speckle redirects back with an access code
4. Server-side function exchanges the code for tokens and creates/updates a Firebase user
5. User signs in to Firebase with a custom token and can access protected features

### Frontend

The frontend is built with HTMX, which provides dynamic content updates without a complex JavaScript framework. This keeps the codebase small and maintainable while still offering a responsive UI experience.

Key components:
- Rule set listing page
- Rule editor interface
- Sharing dialog
- Export functionality

### Backend

Firebase Cloud Functions handle server-side operations:
- Authentication with Speckle
- Firebase token generation
- API endpoints returning HTML fragments for HTMX
- Rule processing
- TSV generation
- Sharing mechanisms

### Database Schema

The Firestore database uses the following structure:

```
ruleSets/
├─ [ruleSetId]/
│  ├─ name: string
│  ├─ userId: string
│  ├─ createdAt: timestamp
│  ├─ updatedAt: timestamp
│  ├─ isShared: boolean
│  ├─ sharedAt: timestamp (optional)
│  ├─ rules: array
│  │  ├─ ruleNumber: number
│  │  ├─ message: string
│  │  ├─ severity: string
│  │  ├─ conditions: array
│  │  │  ├─ logic: string (WHERE/AND/CHECK)
│  │  │  ├─ propertyName: string
│  │  │  ├─ predicate: string
│  │  │  ├─ value: string

userTokens/
├─ [firebaseUserId]/
│  ├─ speckleToken: string
│  ├─ speckleRefreshToken: string
│  ├─ updatedAt: timestamp
```

## Security Improvements

1. **Speckle OAuth Integration**: Users authenticate with their existing Speckle accounts
2. **Server-Side Security**: All sensitive API keys and secrets remain on the server
3. **Protected Routes**: API endpoints verify Firebase Auth tokens before processing requests
4. **Custom Claims**: Firebase users have Speckle IDs attached as custom claims for verification
5. **Token Management**: Secure token exchange and storage protocols

## Deployment

The solution can be deployed with minimal setup:

1. Create a Firebase project
2. Register a Speckle app to obtain APP_ID and APP_SECRET
3. Configure Firebase environment variables with Speckle credentials
4. Enable Authentication, Firestore, Functions, and Hosting
5. Deploy the HTML templates, Cloud Functions, and configuration

The deployment script automates most of these steps.

## Benefits Over Google Sheets

1. **No External Dependencies**: Full control over the entire workflow
2. **Better User Experience**: Purpose-built interface for rule management
3. **Improved Security**: Built-in authentication and permission controls
4. **Streamlined Updates**: Changes are immediately saved to the database
5. **Real-time Validation**: Input validation can be performed as rules are created
6. **Version Control**: Potential to add version history for rule sets
7. **Advanced Features**: Framework for adding rule templates, testing, and more
8. **Speckle Integration**: Seamless authentication with existing Speckle accounts

## Next Steps

To fully implement this proof of concept:

1. Complete the Firebase configuration with your project and Speckle app details
2. Set up secure environment variables for the Speckle APP_ID and APP_SECRET
3. Implement the remaining API endpoints in Cloud Functions
4. Add proper error handling and input validation
5. Add unit tests for critical functionality
6. Consider additional features like rule templates or testing against sample objects

This implementation provides a solid foundation for replacing Google Sheets while maintaining compatibility with the existing Speckle Checker function and adding seamless Speckle authentication.