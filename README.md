# EVE Online Management Platform

A comprehensive Docker-based management platform for EVE Online, featuring real-time killmail tracking, interactive universe maps, route planning, corporation management, market analysis, and fleet operations.

## Features

### Core Functionality
- **Multi-Character Management**: Link and manage multiple EVE Online characters
- **Real-Time Killmail Tracking**: Live killmail feed via WebSocket with zKillboard integration
- **Interactive Universe Map**: System exploration with activity overlays
- **Route Planning**: A* pathfinding with security status weighting and custom avoid lists
- **Corporation Management**: Member tracking, assets, and structure management
- **Market Analysis**: Order tracking and price history for major trade hubs
- **Fleet Operations**: Fleet management with doctrine compliance checking

### Technical Features
- **OAuth 2.0 + PKCE**: Secure EVE SSO authentication
- **Real-Time Updates**: WebSocket integration for live data
- **Background Jobs**: Celery workers for ESI data synchronization
- **Rate Limiting**: Built-in ESI API rate limit handling
- **Token Management**: Encrypted token storage with automatic refresh

## Architecture

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL 15 with PostGIS extension
- **Cache & Queue**: Redis 7
- **Background Jobs**: Celery with Celery Beat
- **Real-Time**: FastAPI WebSockets

### Frontend
- **Framework**: React 18 with TypeScript
- **State Management**: TanStack Query (React Query) + Zustand
- **Styling**: TailwindCSS with custom EVE theme
- **Real-Time**: Native WebSocket API

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Reverse Proxy**: Traefik
- **Development**: Hot-reload enabled for both frontend and backend

## Quick Start

### Prerequisites
- Docker and Docker Compose
- EVE Online SSO Application (Client ID and Secret)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd eve-online-app-1
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Configure environment variables**
   Edit `.env` and set:
   - `ESI_CLIENT_ID`: Your EVE SSO application client ID
   - `ESI_CLIENT_SECRET`: Your EVE SSO application client secret
   - `ESI_CALLBACK_URL`: Your callback URL (e.g., `http://localhost:3000/auth/callback`)
   - `SECRET_KEY`: A secure random key for session encryption
   - `ENCRYPTION_KEY`: A Fernet encryption key for token storage

4. **Start the application**
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs
   - Flower (Celery Monitor): http://localhost:5555

## Development

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Run API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker
celery -A app.tasks worker --loglevel=info --concurrency=4

# Run Celery Beat scheduler
celery -A app.tasks beat --loglevel=info
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Type check
npm run type-check

# Lint
npm run lint
```

## Project Structure

```
eve-online-app-1/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes and endpoints
│   │   ├── core/         # Config, security, dependencies
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # Business logic layer
│   │   ├── tasks/        # Celery tasks
│   │   └── websockets/   # WebSocket handlers
│   ├── alembic/          # Database migrations
│   ├── tests/            # Backend tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API client services
│   │   ├── hooks/        # Custom React hooks
│   │   ├── utils/        # Utility functions
│   │   └── store/        # State management
│   ├── public/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── docker-compose.dev.yml
└── README.md
```

## API Endpoints

### Authentication
- `GET /api/v1/auth/login` - Initiate EVE SSO login
- `GET /api/v1/auth/callback` - OAuth callback handler
- `GET /api/v1/auth/me` - Get current user info
- `POST /api/v1/auth/refresh` - Refresh access token

### Characters
- `GET /api/v1/characters` - List characters
- `GET /api/v1/characters/{id}` - Get character details

### Killmails
- `GET /api/v1/killmails` - List killmails with filters
- `GET /api/v1/killmails/{id}` - Get killmail details
- `WS /api/v1/killmails/feed` - Real-time killmail feed

### Map & Routes
- `GET /api/v1/map/systems` - Get universe systems
- `GET /api/v1/map/activity` - Get system activity
- `POST /api/v1/routes/calculate` - Calculate route

### Corporations
- `GET /api/v1/corporations/{id}` - Get corporation info
- `GET /api/v1/corporations/{id}/members` - Get members
- `GET /api/v1/corporations/{id}/assets` - Get assets
- `POST /api/v1/corporations/{id}/sync` - Trigger sync

### Market
- `GET /api/v1/market/orders` - Get market orders
- `GET /api/v1/market/prices/{type_id}` - Get prices
- `GET /api/v1/market/prices/{type_id}/history` - Get price history

### Fleets
- `GET /api/v1/fleets` - List fleets
- `GET /api/v1/fleets/{id}` - Get fleet details
- `GET /api/v1/fleets/{id}/members` - Get fleet members
- `POST /api/v1/fleets/{id}/doctrine-check` - Check doctrine compliance

## Environment Variables

See `.env.example` for all required environment variables.

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Secret key for session encryption
- `ENCRYPTION_KEY`: Fernet key for token encryption
- `ESI_CLIENT_ID`: EVE SSO client ID
- `ESI_CLIENT_SECRET`: EVE SSO client secret
- `ESI_CALLBACK_URL`: OAuth callback URL
- `ALLOWED_ORIGINS`: CORS allowed origins

## Background Jobs

The application uses Celery for background task processing:

- **Token Refresh**: Runs every 15 minutes to refresh expiring tokens
- **Killmail Sync**: Runs every 5 minutes to sync killmails from ESI
- **Corporation Sync**: Runs hourly to sync corporation data
- **Market Sync**: Runs every 10 minutes for trade hub markets

## Security Considerations

1. **Token Storage**: All refresh tokens encrypted at rest using Fernet
2. **Access Control**: Strict per-user data isolation in all queries
3. **Secrets Management**: Use environment variables, never hardcode
4. **HTTPS Only**: All external communication over TLS (production)
5. **Input Validation**: Pydantic models for all API inputs
6. **Rate Limiting**: Implemented on API endpoints

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linters
4. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions, please open an issue on the repository.

## Acknowledgments

- EVE Online and ESI API by CCP Games
- zKillboard for killmail data
- The EVE Online community

