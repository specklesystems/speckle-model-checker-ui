# Firebase Implementation (Legacy)

The original implementation of the Speckle Model Checker using Firebase services and HTMX.

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │
│  Web UI         │◄────┤  Cloud          │
│  (HTMX +        │     │  Functions      │
│   Firebase)     │     │                 │
└─────────────────┘     └─────────────────┘
```

## 🎯 Technology Stack

- **Backend**: Cloud Functions (Node.js)
- **Frontend**: HTMX + Firebase Hosting
- **Deployment**: Firebase
- **Key Features**:
  - Stateless backend
  - HTMX with Firebase integration
  - Serverless architecture
  - Firebase Authentication

## 🚀 Development Setup

### Prerequisites

- Node.js (v18 or later)
- Firebase CLI
- Google Cloud SDK

### Setup Steps

1. **Install Firebase CLI**

   ```bash
   npm install -g firebase-tools
   ```

2. **Install dependencies**

   ```bash
   # Install function dependencies
   cd functions
   npm install
   ```

3. **Configure Firebase**

   ```bash
   # Login to Firebase
   firebase login

   # Initialize Firebase project
   firebase init
   ```

4. **Start development servers**
   ```bash
   # Start Firebase emulator
   firebase emulators:start
   ```

## 📦 Project Structure

```
firebase/
├── public/                # Static frontend files
│   └── index.html        # HTMX frontend
│
└── functions/            # Cloud Functions backend
    ├── index.js          # Main function
    ├── auth.js           # Authentication logic
    └── package.json      # Dependencies
```

## 🚀 Deployment

1. **Deploy to Firebase**

   ```bash
   firebase deploy
   ```

2. **Deploy functions only**

   ```bash
   firebase deploy --only functions
   ```

3. **Deploy hosting only**
   ```bash
   firebase deploy --only hosting
   ```

## 🔐 Authentication

The application uses Speckle OAuth for authentication. To set up:

1. Register your application on your Speckle server
2. Configure the required scopes:
   ```
   streams:read
   users:read
   users:email
   profile:read
   ```
3. Set up the redirect URL for your environment

## 🧪 Testing

```bash
# Run function tests
cd functions
npm test
```

## 📚 Documentation

- [API Documentation](docs/api.md)
- [HTMX Implementation](docs/htmx.md)
- [Firebase Setup Guide](FIREBASE.md)

## ⚠️ Legacy Status
