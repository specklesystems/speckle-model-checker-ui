# Speckle Checker UI - Proof of Concept

This document outlines a proof of concept implementation for replacing the Google Sheet interface for Speckle Checker rules with a dedicated web-based UI.

## Architecture Overview

The solution uses a lightweight tech stack focused on simplicity and ease of implementation:

- **Frontend**: HTML + HTMX + Tailwind CSS
- **Backend**: Firebase Cloud Functions (serverless)
- **Database**: Firebase Firestore
- **Authentication**: Firebase Authentication
- **Hosting**: Firebase Hosting

This approach eliminates the need for Google Sheets while maintaining a simple, user-friendly interface for managing validation rules.

## Key Features

1. **Authentication**: User management with Google Sign-In
2. **Rule Management**: Create, edit, and delete rule sets
3. **Rule Editor**: Intuitive interface for defining rule conditions
4. **Sharing**: Generate public URLs for use in Speckle Automations
5. **Export**: Download rules as TSV files compatible with the current Checker function

## Implementation Details

### Frontend

The frontend is built with HTMX, which provides dynamic content updates without a complex JavaScript framework. This keeps the codebase small and maintainable while still offering a responsive UI experience.

Key components:
- Rule set listing page
- Rule editor interface
- Sharing dialog
- Export functionality

### Backend

Firebase Cloud Functions handle server-side operations:
- Authentication validation
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
```

## Deployment

The solution can be deployed with minimal setup:

1. Create a Firebase project
2. Enable Authentication, Firestore, Functions, and Hosting
3. Deploy the HTML templates, Cloud Functions, and configuration
4. Configure authentication providers

The deployment script automates most of these steps.

## Benefits Over Google Sheets

1. **No External Dependencies**: Full control over the entire workflow
2. **Better User Experience**: Purpose-built interface for rule management
3. **Improved Security**: Built-in authentication and permission controls
4. **Streamlined Updates**: Changes are immediately saved to the database
5. **Real-time Validation**: Input validation can be performed as rules are created
6. **Version Control**: Potential to add version history for rule sets
7. **Advanced Features**: Framework for adding rule templates, testing, and more

## Next Steps

To fully implement this proof of concept:

1. Complete the Firebase configuration with your project details
2. Implement the remaining API endpoints in Cloud Functions
3. Add proper error handling and input validation
4. Add unit tests for critical functionality
5. Consider additional features like rule templates or testing against sample objects

This implementation provides a solid foundation for replacing Google Sheets while maintaining compatibility with the existing Speckle Checker function.