# Speckle Model Checker

Speckle Model Checker is a web application that allows Speckle users to create and manage rule sets for validating their 3D models. This tool integrates with Speckle and allows for creating, sharing, and exporting rule sets.

## Features

- **Authentication**: Secure login with your Speckle account
- **Project Integration**: View and select your Speckle projects
- **Rule Management**: Create, edit, delete, and organize validation rules
- **Rule Sharing**: Share rule sets with other Speckle users
- **Export Functionality**: Export rule sets to TSV format for use in other systems

## Tech Stack

- **Frontend**: HTML, CSS (Tailwind CSS), JavaScript
- **Backend**: Python Flask application
- **Database**: Google Firestore
- **Authentication**: Firebase Authentication with Speckle OAuth
- **Hosting**: Google Cloud Run

## Project Structure

```
/
├── public/               # Static files served to the client
│   ├── js/               # JavaScript files
│   ├── img/              # Image assets
│   ├── index.html        # Main HTML file
│   ├── fbconfig.js       # Firebase configuration
│   ├── speckle-theme.css # Speckle styling
│   └── htmx-styles.css   # HTMX-specific styles
├── src/                  # Server-side Python code
│   ├── auth.py           # Authentication functions
│   ├── database.py       # Database operations
│   ├── mapping.py        # Data mapping functions
│   ├── routes.py         # API routes
│   ├── rule_routes.py    # Rule-specific routes
│   ├── speckle.py        # Speckle API client
│   └── utils.py          # Utility functions
├── templates/            # HTML templates
├── Dockerfile            # Production Docker configuration
├── Dockerfile.dev        # Development Docker configuration
├── main.py               # Main application entry point
├── requirements.txt      # Python dependencies
├── scripts/              # Helper scripts
└── README.md             # Project documentation
```

## Setup and Local Development

### Prerequisites

- Python 3.9+ installed
- Google Cloud SDK installed (for Firebase)
- Speckle account with API access
- Firebase project with Firestore database

### Configuration

1. Create a `.env` file in the root directory with the following variables:

```
FLASK_APP=main.py
FLASK_ENV=development
FLASK_DEBUG=1
PORT=8080
SPECKLE_APP_ID=your_speckle_app_id
SPECKLE_APP_SECRET=your_speckle_app_secret
SPECKLE_CHALLENGE_ID=your_speckle_challenge_id
SPECKLE_SERVER_URL=https://app.speckle.systems
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/firebase/key.json
```

2. Create a Firebase project and download the service account key.
3. Register a Speckle app to get the app ID and secret.

### Running Locally

#### Using Docker (Recommended)

```bash
# Development mode with hot reloading
./scripts/run_dev_docker.sh

# Production-like mode
./scripts/run_docker_local.sh
```

#### Without Docker

```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
./scripts/run_local.sh
```

The application will be available at http://localhost:8080

## Deployment

### Google Cloud Run

1. Build the Docker image:
```bash
gcloud builds submit --tag gcr.io/your-project-id/speckle-model-checker
```

2. Deploy to Cloud Run:
```bash
gcloud run deploy speckle-model-checker \
  --image gcr.io/your-project-id/speckle-model-checker \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="SPECKLE_APP_ID=your_app_id,SPECKLE_APP_SECRET=your_app_secret"
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.