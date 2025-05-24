# Speckle Model Checker (Go Version)

This is a Go implementation of the Speckle Model Checker, migrated from the original Python FastAPI version. The application provides a web interface for checking 3D models against custom rulesets.

## Features

- Speckle authentication and project management
- Ruleset creation and management
- Rule creation and management
- Model checking against rulesets
- Firebase integration for user management and storage

## Prerequisites

- Go 1.21 or later
- Firebase project with credentials
- Speckle account and API credentials

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
SPECKLE_APP_ID=your_speckle_app_id
SPECKLE_APP_SECRET=your_speckle_app_secret
SPECKLE_SERVER_URL=https://app.speckle.systems
SESSION_SECRET_KEY=your_session_secret
```

## Building and Running

### Local Development

1. Install dependencies:

```bash
go mod download
```

2. Run the application:

```bash
go run cmd/main.go
```

### Docker

1. Build the Docker image:

```bash
docker build -t speckle-model-checker .
```

2. Run the container:

```bash
docker run -p 8080:8080 \
  -e SPECKLE_APP_ID=your_speckle_app_id \
  -e SPECKLE_APP_SECRET=your_speckle_app_secret \
  -e SESSION_SECRET_KEY=your_session_secret \
  speckle-model-checker
```

## Project Structure

```
.
├── cmd/
│   └── main.go           # Application entry point
├── internal/
│   ├── auth/            # Authentication and authorization
│   ├── handlers/        # HTTP request handlers
│   ├── models/          # Data models
│   └── services/        # Business logic and external services
├── frontend/
│   ├── templates/       # HTML templates
│   └── static/          # Static assets
├── go.mod              # Go module file
├── go.sum              # Go module checksum
└── Dockerfile          # Docker configuration
```

## API Endpoints

### Authentication

- `GET /auth/init` - Initialize Speckle authentication
- `GET /auth/callback` - Handle OAuth callback
- `GET /logout` - Logout user

### Projects

- `GET /projects` - List projects
- `GET /projects/search` - Search projects
- `GET /projects/:project_id` - Get project details

### Rulesets

- `GET /rulesets` - List rulesets
- `GET /rulesets/new` - New ruleset form
- `GET /rulesets/:ruleset_id/edit` - Edit ruleset
- `POST /rulesets` - Create ruleset
- `POST /rulesets/:ruleset_id` - Update ruleset
- `DELETE /api/rulesets/:ruleset_id` - Delete ruleset

### Rules

- `GET /rulesets/:ruleset_id/rules/new` - New rule form
- `POST /rulesets/:ruleset_id/rules` - Add rule
- `GET /rulesets/:ruleset_id/rules/:rule_id/edit` - Edit rule
- `POST /rulesets/:ruleset_id/rules/:rule_id` - Update rule
- `DELETE /api/rulesets/:ruleset_id/rules/:rule_id` - Delete rule

## Migration Notes

This Go implementation maintains feature parity with the original Python FastAPI version while providing the following improvements:

1. Better performance through Go's efficient runtime
2. Stronger type safety with Go's static typing
3. Improved error handling with Go's error handling patterns
4. Better concurrency support with Go's goroutines
5. Smaller container size with multi-stage Docker builds

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
