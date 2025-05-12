# Deploying to Cloud Run

This guide provides detailed instructions for deploying the Model Checker application to Google Cloud Run.

## Prerequisites

1. **Google Cloud SDK**

   - Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
   - Initialize with `gcloud init`
   - Set your project: `gcloud config set project speckle-model-checker`

2. **Docker**

   - Install [Docker](https://docs.docker.com/get-docker/)
   - Ensure Docker daemon is running

3. **Required Permissions**

   - Editor or Owner role on the GCP project
   - Access to Container Registry
   - Access to Cloud Run

4. **Environment Setup**
   - Ensure you have the following environment variables configured:
     - `GOOGLE_APPLICATION_CREDENTIALS`: Path to your service account key file
     - `SPECKLE_SERVER_URL`: Your Speckle server URL
     - `SPECKLE_CLIENT_ID`: OAuth client ID
     - `SPECKLE_CLIENT_SECRET`: OAuth client secret
     - `SPECKLE_REDIRECT_URL`: OAuth redirect URL

## Speckle OAuth App Registration

1. **Required Scopes**
   When registering your application on the Speckle server, ensure you request these scopes:

   ```
   streams:read
   users:read
   users:email
   profile:read
   ```

2. **Registration Steps**

   - Go to your Speckle server's OAuth applications page
   - Create a new application
   - Set the redirect URL to match your deployment:

     - Production: `https://your-domain.com/auth/callback`

     - Local: `http://localhost:3000/auth/callback`

   - Request the scopes listed above
   - Save the client ID and client secret for your environment configuration

## Environment Configuration

### Local Development (.env)

1. Create a `.env` file in the project root for local development:

```bash
# Copy the template
cp .env.example .env

# Edit the file with your local development values
```

2. Example `.env` structure:

```env
# Speckle OAuth Configuration
SPECKLE_SERVER_URL=http://localhost:3000
SPECKLE_CLIENT_ID=local-dev-client-id
SPECKLE_CLIENT_SECRET=local-dev-client-secret
SPECKLE_REDIRECT_URL=http://localhost:3000/auth/callback

# Application Configuration
PORT=8080

# Security (use different values for local development)
SESSION_SECRET=local-dev-session-secret
```

### Deployment Environments (env.yaml)

1. Create environment-specific `env.yaml` files:

```bash
# Production
touch env.yaml

```

2. Example `env.yaml` structure - essentially the same as the `.env` file but for deployment

```yaml
# Speckle OAuth Configuration
SPECKLE_SERVER_URL: 'https://app.speckle.systems'
SPECKLE_CLIENT_ID: 'prod-client-id'
SPECKLE_CLIENT_SECRET: 'prod-client-secret'
SPECKLE_REDIRECT_URL: 'https://your-domain.com/auth/callback'

# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS: '/path/to/service-account-key.json'
GOOGLE_CLOUD_PROJECT: 'speckle-model-checker'
# Application Configuration
# PORT: '8080' # this is set by the cloud run service
```

In this way we are always deploying to production and developing locally (locally or in dev container)

### Keeping Environments in Sync

1. **Environment Variable Template**:

   - Maintain a `env.yaml` file with all possible variables
   - Include comments explaining each variable
   - Mark required vs optional variables
   - Document expected formats and values

2. **Deployment Process**:

```bash
# Deploy to production
gcloud run deploy speckle-model-checker \
  --image gcr.io/speckle-model-checker/speckle-model-checker:latest \
  --platform managed \
  --env-vars-file=cloudrun/env.prod.yaml \
  --region=us-central1
```

3. **Environment-Specific Considerations**:

   - Configure different redirect URLs
   - Set appropriate log levels (debug for staging, info for prod)
   - Use different Firebase projects
   - Configure different session secrets
   - Use as similar a lcal dev/testing scaffold as possible - The deployment Dockerfile is distinct from the local dev container Dockerfile and can perform some file system choreography to ensure the same codebase is used for local development and deployment.

4. **Version Control**:

   - DO commit: `.env.example`, `env.yaml.example`
   - DO NOT commit: `.env`, `env.prod.yaml`, `env.staging.yaml`
   - Add to `.gitignore` and `.dockerignore`:

     ```
     .env
     env.*.yaml
     !env.yaml.example
     ```

   - And just to .gitignore:
     ```
     firebase-service-account.json # or whatever
     ```

## Build and Push Image

1. Navigate to the project root directory:

```bash
cd model-checker/backend
```

2. Build the Docker image:

```bash
docker build -t gcr.io/speckle-model-checker/speckle-model-checker:latest cloudrun/
```

3. Push the image to Google Container Registry:

```bash
docker push gcr.io/speckle-model-checker/speckle-model-checker:latest
```

## Deploy to Cloud Run

1. Deploy the service:

```bash
gcloud run deploy speckle-model-checker \
  --image gcr.io/speckle-model-checker/speckle-model-checker:latest \
  --platform managed \
  --env-vars-file=cloudrun/env.yaml \
  --region=us-central1 \
  --allow-unauthenticated
```

2. Verify the deployment:

```bash
gcloud run services describe speckle-model-checker
```

## Post-Deployment Steps

1. **Verify Service Health**

   - Check the service logs: `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=speckle-model-checker"`
   - Monitor the service in Google Cloud Console

2. **Update DNS (if applicable)**

   - Configure your domain to point to the Cloud Run service URL
   - Update SSL certificates if using custom domains

3. **Update OAuth Configuration**
   - Update your Speckle OAuth application settings with the new deployment URL
   - Verify the redirect URL matches your deployment

## Troubleshooting

1. **Common Issues**

   - Image build failures: Check Dockerfile syntax and dependencies
   - Deployment failures: Verify environment variables and permissions
   - Runtime errors: Check Cloud Run logs

2. **Useful Commands**

   ```bash
   # View service logs
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=speckle-model-checker"

   # Update environment variables
   gcloud run services update speckle-model-checker --update-env-vars KEY=VALUE

   # Scale the service
   gcloud run services update speckle-model-checker --min-instances=1 --max-instances=10
   ```

## Maintenance

1. **Regular Updates**

   - Keep dependencies updated
   - Monitor resource usage
   - Review and rotate secrets regularly

2. **Backup**
   - Regularly backup environment configurations
   - Document any custom configurations

## Security Considerations

1. **Secrets Management**

   - Use Secret Manager for sensitive data
   - Rotate credentials regularly
   - Follow principle of least privilege

2. **Access Control**
   - Review IAM permissions regularly
   - Use service accounts with minimal required permissions
   - Enable audit logging

For additional support or questions, please refer to the project documentation or contact the development team.

## Development Setup

### Development Container (Recommended for Development)

1. **Why Development Containers?**

   - Consistent development environment across team
   - All dependencies pre-configured
   - No need to install tools locally
   - Easy onboarding for new team members
   - Isolated development environment

2. **Setup Steps**

   ```bash
   # Prerequisites
   - Docker Desktop
   - VS Code with Remote Containers extension

   # Open in container
   - Open project in VS Code
   - Click "Reopen in Container" when prompted
   # or
   - Command Palette (Ctrl/Cmd + Shift + P)
   - Select "Remote-Containers: Reopen in Container"
   ```

3. **Development Workflow**

   ```bash
   # The container will automatically:
   - Install all dependencies
   - Set up the development environment
   - Configure debugging tools
   - Start the development server

   # You can then:
   - Run tests
   - Debug your code
   - Make changes with hot-reload
   ```

### Local Development (Alternative)

If you prefer local development:

1. **Prerequisites**

   ```bash
   # Install Node.js and npm
   # Install Python 3.x
   # Install required system dependencies
   ```

2. **Setup Steps**

   ```bash
   # Clone the repository
   git clone <repository-url>
   cd model-checker/backend

   # Install dependencies
   npm install
   pip install -r requirements.txt

   # Copy environment template
   cp .env.example .env

   # Start the development server
   npm run dev
   ```

## Deployment

> **Important**: While development containers are great for development, deployment should be done outside containers to avoid Docker-in-Docker complexity and improve performance.

### Deployment Prerequisites

1. **Local Environment**

   - Docker installed (for building the deployment image)
   - Google Cloud SDK
   - Access to Google Cloud project

2. **Why Deploy Outside Containers?**
   - Better performance
   - Simpler deployment process
   - No Docker-in-Docker overhead
   - More reliable networking
   - Easier debugging of deployment issues
