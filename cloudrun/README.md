# Speckle Model Checker

A tool for checking and validating Speckle models using HTMX.

## 📦 Projects

This repository contains two implementations of the Speckle Model Checker:

1. **[Cloud Run Implementation](cloudrun/README.md)** (Current)

   - Python-based backend with FastAPI
   - HTMX frontend
   - Deployed on Google Cloud Run
   - Native session support

2. **[Firebase Implementation](firebase/README.md)** (Legacy)
   - Node.js Cloud Functions backend
   - HTMX frontend
   - Deployed on Firebase
   - Stateless architecture

## 🎯 Quick Start

Choose your implementation:

- [Cloud Run Setup](cloudrun/README.md#development-setup)
- [Firebase Setup](firebase/README.md#development-setup)

## 🔐 Authentication

Both implementations use Speckle OAuth for authentication. See the respective project READMEs for setup instructions:

- [Cloud Run Auth Setup](cloudrun/README.md#authentication)
- [Firebase Auth Setup](firebase/README.md#authentication)

## 📚 Documentation

- [Cloud Run Documentation](cloudrun/README.md)
- [Firebase Documentation](firebase/README.md)
- [Deployment Guide](DEPLOY.md)

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
