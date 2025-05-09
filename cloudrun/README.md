# Cloud Run Implementation

A Python-based implementation of the Speckle Model Checker using FastAPI and HTMX, deployed on Cloud Run.

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │
│  Web UI         │◄────┤  Backend API    │
│  (HTMX + SSR)   │     │  (Cloud Run)    │
│                 │     │                 │
└─────────────────┘     └─────────────────┘
```

## 🎯 Technology Stack

- **Backend**: Python with FastAPI
- **Frontend**: HTMX + Server-side rendering
- **Server**: Uvicorn
- **Deployment**: Cloud Run
- **Key Features**:
  - Server-side rendered UI with HTMX
  - Native session support
  - No build step required
  - Minimal JavaScript
  - Fast response times

## 🚀 Development Setup

### Prerequisites

- Python 3.9+
- Docker (for deployment)
- Google Cloud SDK

### Setup Steps

1. **Set up Python environment**

   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start development server**
   ```bash
   uvicorn main:app --reload
   ```

## 📦 Project Structure

```
cloudrun/
├── backend/                # FastAPI backend
│   ├── main.py            # FastAPI application
│   ├── auth.py            # Authentication logic
│   └── services/          # Business logic
│
├── frontend/              # HTMX frontend
│   └── templates/         # Server-side templates
│
├── Dockerfile            # Container definition
└── env.yaml             # Deployment configuration
```

## 🚀 Deployment

1. **Build the container**

   ```bash
   docker build -t gcr.io/speckle-model-checker/speckle-model-checker:latest .
   ```

2. **Push to Container Registry**

   ```bash
   docker push gcr.io/speckle-model-checker/speckle-model-checker:latest
   ```

3. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy speckle-model-checker \
     --image gcr.io/speckle-model-checker/speckle-model-checker:latest \
     --platform managed \
     --env-vars-file=env.yaml
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
# Run tests
pytest
```

## 📚 Documentation

- [API Documentation](docs/api.md)
- [HTMX Implementation](docs/htmx.md)
- [Deployment Guide](DEPLOY.md)
