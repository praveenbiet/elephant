# E-Learning Platform

A modular monolith e-learning platform built with FastAPI, React, and PostgreSQL.

## Project Overview

This e-learning platform is designed as a modular monolith, providing the following features:

- User authentication and authorization
- Course creation and management
- Video content delivery
- Assessment and quiz functionality
- Learning paths and progress tracking
- Search and recommendations
- Discussion forums
- Subscription and billing management
- Notifications
- Analytics dashboard

## Architecture

The system uses a modular monolith architecture with clear boundaries between modules:

- **Backend**: FastAPI-based Python monolith with modular organization
- **Frontend**: Multiple React applications (web app, admin portal)
- **Database**: PostgreSQL for persistent storage
- **Cache**: Redis for caching and session management
- **Message Broker**: Kafka for event-driven communication
- **Storage**: S3-compatible object storage for media files
- **Search**: Elasticsearch for full-text search capabilities

## Project Structure

```
/
├── apps/                  # Frontend applications
│   ├── web-app/           # Main web application for learners
│   └── admin-portal/      # Admin portal for content management
├── monolith/              # Backend monolith
│   ├── src/
│   │   ├── api/           # API endpoints
│   │   ├── common/        # Shared utilities
│   │   └── modules/       # Business domain modules
│   ├── requirements.txt   # Python dependencies
│   └── Dockerfile         # Container definition
├── shared/                # Shared libraries
│   ├── backend-python/    # Shared Python code
│   └── frontend-libs/     # Shared frontend components
├── docs/                  # Documentation
├── infrastructure/        # Infrastructure as code
├── scripts/               # Helper scripts
└── docker-compose.yml     # Local development setup
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 16+ and npm/yarn
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Kafka 2.8+

### Development Setup

1. Clone the repository:

```bash
git clone https://github.com/your-org/elearning-platform.git
cd elearning-platform
```

2. Create a `.env` file based on the example:

```bash
cp .env.example .env
# Edit .env with your local settings
```

3. Start the development environment:

```bash
docker-compose up -d
```

4. Run migrations:

```bash
./scripts/db_migrate.sh
```

5. Start the backend:

```bash
cd monolith
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m src.main
```

6. Start the frontend:

```bash
cd apps/web-app
npm install
npm run dev
```

## API Documentation

API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
