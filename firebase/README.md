# Model Checker UI

A web-based interface for creating, managing, and sharing rule sets for the Model Checker.

## Overview

This application provides a user-friendly interface for creating and managing validation rules for Speckle objects, replacing the previous Google Sheets based approach. It features:

- Authentication via Speckle accounts
- Create, edit, and delete rule sets
- Intuitive rule editing interface
- Share rule sets via links
- Export rules as TSV files compatible with the current Checker function

## Tech Stack

- **Frontend**: HTML + [HTMX](https://htmx.org/) for interactivity
- **CSS**: Tailwind CSS for styling
- **Backend**: Firebase Cloud Functions (Python)
- **Database**: Firebase Firestore
- **Authentication**: Speckle OAuth + Firebase Auth
- **Hosting**: Firebase Hosting

## Setup Instructions

### Prerequisites

1. [Firebase CLI](https://firebase.google.com/docs/cli) installed
2. A Firebase project
3. A Speckle App registered at https://app.speckle.systems/

### Configuration

1. Clone this repository
2. Update `firebase-config.js` with your Firebase project configuration
3. Set up environment variables for Firebase Functions:

```bash
firebase functions:config:set speckle.app_id="YOUR_SPECKLE_APP_ID" speckle.app_secret="YOUR_SPECKLE_APP_SECRET"
```

4. Update the redirect URL in your Speckle App settings to point to your deployed application's auth callback URL: `https://your-app-name.web.app/auth-callback.html`

### Deployment

```bash
# Install dependencies
cd functions
pip install -r requirements.txt
cd ..

# Deploy to Firebase
firebase deploy
```

## Architecture

### HTMX-Based Approach

This application uses HTMX to provide a responsive and dynamic user interface without heavy JavaScript frameworks. HTMX allows for seamless server-rendered HTML updates through simple attributes, reducing client-side complexity while maintaining rich interactivity.

Key benefits of the HTMX approach:
- Simplified frontend development with minimal JavaScript
- Server-side rendering for better performance and SEO
- Progressive enhancement for better accessibility
- Reduced bundle size and faster initial load times

### Authentication Flow

1. User clicks "Sign In with Speckle"
2. The application requests a challenge from the server
3. User is redirected to Speckle authentication with the challenge
4. Speckle redirects back with an access code
5. The server exchanges the code for Speckle tokens and creates/updates a Firebase user
6. The client signs in to Firebase with the custom token

### File Structure

- `/public` - Static files (HTML, CSS, JS)
  - `index.html` - Main application page
  - `auth-callback.html` - OAuth callback handler
  - `shared/{id}.html` - Shared rule set viewer
  - `firebase-config.js` - Firebase configuration
  - `htmx-styles.css` - Styling for HTMX components

- `/functions` - Firebase Cloud Functions
  - `auth_functions.py` - Authentication functions
  - `api_functions.py` - API functions for rule sets
  - `utils.py` - Shared utility functions

### Database Schema

#### Firestore Collections

- `ruleSets/{ruleSetId}`
  - `name`: string
  - `description`: string
  - `userId`: string
  - `createdAt`: timestamp
  - `updatedAt`: timestamp
  - `isShared`: boolean
  - `sharedAt`: timestamp (if shared)
  - `rules`: array
    - `ruleNumber`: number
    - `message`: string
    - `severity`: string (Error, Warning, Info)
    - `conditions`: array
      - `logic`: string (WHERE, AND, OR, CHECK)
      - `propertyName`: string
      - `predicate`: string
      - `value`: string

- `userTokens/{userId}`
  - `speckleToken`: string
  - `speckleRefreshToken`: string
  - `updatedAt`: timestamp

## API Endpoints

### Authentication

- `GET /api/auth/init` - Initialize authentication with Speckle
- `POST /api/auth/token` - Exchange Speckle code for Firebase token

### Rule Sets

- `GET /api/rule-sets` - List user's rule sets
- `POST /api/rule-sets` - Create a new rule set
- `GET /api/rule-sets/{id}` - Get a rule set
- `PUT /api/rule-sets/{id}` - Update a rule set
- `DELETE /api/rule-sets/{id}` - Delete a rule set
- `GET /api/rule-sets/{id}/edit` - Get edit form for a rule set
- `GET /api/rule-sets/{id}/export` - Export a rule set as TSV
- `GET /api/rule-sets/{id}/share` - Get sharing dialog for a rule set
- `PUT /api/rule-sets/{id}/toggle-sharing` - Toggle public sharing

### Rules

- `GET /api/rule-sets/{id}/rules` - List rules for a rule set
- `POST /api/rule-sets/{id}/rules` - Add a rule to a rule set
- `PUT /api/rule-sets/{id}/rules/{index}` - Update a rule
- `DELETE /api/rule-sets/{id}/rules/{index}` - Delete a rule
- `GET /api/rule-sets/{id}/rules/new` - Get form for new rule
- `GET /api/rule-sets/{id}/rules/{index}/edit` - Get form for editing rule
- `GET /api/rule-sets/{id}/condition-row/{index}` - Get new condition row HTML
- `DELETE /api/rule-sets/{id}/condition-row/{index}` - Delete condition row

### Shared Rule Sets

- `GET /api/shared-rule-sets/{id}` - Get a publicly shared rule set

## Security

- Authentication is handled securely through Speckle OAuth
- Sensitive credentials (APP_ID, APP_SECRET) are stored server-side
- API endpoints are protected by Firebase Auth token verification
- Rule sets are protected by user ID verification
- Firestore security rules restrict access to authorized users only

## Local Development

```bash
# Start Firebase emulators
firebase emulators:start

# This will start:
# - Hosting at http://localhost:5000
# - Functions at http://localhost:5001
# - Firestore at http://localhost:8080
# - Auth at http://localhost:9099
# - Emulator UI at http://localhost:4000
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Submit a pull request

## License

MIT