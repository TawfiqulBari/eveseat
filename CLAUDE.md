# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ PROJECT STATUS: ABANDONED

**Date**: 2025-11-15
**Status**: Development halted due to persistent technical issues

### Critical Issues
1. **Mixed Content Errors**: HTTPS page loading HTTP resources despite multiple refactoring attempts
2. **Container Networking**: Frequent IP address changes breaking reverse proxy routing
3. **Browser Caching**: Inability to properly deploy frontend updates
4. **Infrastructure Complexity**: Nginx reverse proxy configuration requires manual IP updates on every container restart

### Lessons Learned
- Hardcoded container IPs in reverse proxy configs are not maintainable
- Need service discovery or DNS-based routing for container communication
- Frontend deployment strategy needs cache-busting headers
- Docker networking should use service names, not IP addresses

---

## Project Overview

This is an EVE Online management platform designed as a Docker-based, multi-tenant application. It integrates with EVE Online's ESI (EVE Swagger Interface) API to provide comprehensive character and corporation management:

### Core Features
- Multi-character management across a single user account
- Live killmail tracking and analytics with real-time WebSocket updates
- Interactive universe map with route planning
- Corporation and alliance management
- Market data analysis and order tracking
- Fleet management and doctrine compliance

### Character Management (Phase 2 - COMPLETE)
- **Mail System**: Full EVE mail support with labels, mailing lists, and compose/read functionality
- **Contacts**: Contact management with standings, labels, and watch lists
- **Calendar**: Event tracking with RSVP functionality and upcoming events
- **Contracts**: Contract tracking for all types (item exchange, auction, courier, loan) with detailed items
- **Wallet**: Transaction history, journal entries, and financial analytics with 30-day statistics

### Industry & Economy (Phase 3 - COMPLETE)
- **Industry Jobs**: Manufacturing, research, copying, and invention job tracking with facility management
- **Blueprints**: Blueprint library with ME/TE research levels for both BPOs and BPCs
- **Planetary Interaction**: Colony management with pin tracking and extraction monitoring
- **Loyalty Points**: LP balance tracking across all corporations with top corporation rankings

### Advanced Features (Phase 4 - COMPLETE)
- **Ship Fittings**: Ship fitting management with module tracking and detailed item breakdown
- **Skills**: Character skills tracking, skill queue monitoring, and skillpoint statistics
- **Jump Clones**: Jump clone management with implant tracking and clone history
- **Bookmarks**: ⚠️ UNAVAILABLE - ESI bookmark endpoints permanently disabled by CCP Games as of 2025

### Corporation Features (Phase 5 - COMPLETE)
- **Structures**: Corporation structure management with fuel tracking and reinforcement schedules
- **Moon Mining**: Moon extraction tracking and mining ledger for corp mining operations
- **Sovereignty**: System sovereignty tracking, structure monitoring, and active campaign alerts

### Advanced Analytics (Phase 6 - COMPLETE)
- **Analytics Dashboard**: Comprehensive financial overview with net worth, profit/loss, and industry performance
- **Profit & Loss Tracking**: Daily income and expense tracking with category breakdown
- **Market Trends**: Price trend analysis with volatility indicators and volume statistics
- **Industry Calculator**: Job profitability calculations with cost breakdown and margin analysis
- **ISK Flow**: Income and expense flow categorization and visualization
- **Trading Opportunities**: Automated detection of profitable trading opportunities
- **Portfolio Snapshots**: Net worth tracking over time with change metrics

### Real-time Features
- WebSocket server for live data updates across all features
- Redis pub/sub for scalable multi-server deployment
- Background sync tasks with Celery for automated data updates
- Intelligent rate limiting and ESI cache management

The application follows a microservices architecture with separate containers for frontend, API, workers, and supporting services.

## Tech Stack

### Backend
- **Framework**: Python/FastAPI
- **Database**: PostgreSQL with PostGIS extension
- **Cache & Queue**: Redis
- **Background Jobs**: Celery with Celery Beat scheduler
- **Real-time**: WebSockets (FastAPI WebSockets)

### Frontend
- **Framework**: React 18+ with TypeScript
- **State Management**: Zustand or Redux Toolkit
- **API State**: TanStack Query (React Query)
- **Styling**: TailwindCSS
- **Visualization**: Recharts or D3.js
- **Real-time**: Socket.io-client

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Reverse Proxy**: Traefik or Nginx
- **Orchestration**: Docker Swarm or Kubernetes (production)

## Docker Architecture

The application is composed of these microservices:

- **traefik**: Reverse proxy and load balancer with SSL termination
- **frontend**: React app served by Nginx
- **api**: FastAPI application (port 8000)
- **websocket**: Dedicated WebSocket server (port 8001)
- **worker**: Celery worker for background tasks
- **scheduler**: Celery Beat for periodic tasks
- **flower**: Celery monitoring UI
- **postgres**: PostgreSQL 15 with persistent volume
- **redis**: Redis 7 for caching and message broker

## Key Development Commands

### Docker Operations
```bash
# Start all services in development
docker-compose -f docker-compose.dev.yml up

# Start all services in production
docker-compose up -d

# View logs
docker-compose logs -f [service-name]

# Rebuild a specific service
docker-compose build [service-name]

# Stop all services
docker-compose down
```

### Backend (Python/FastAPI)
```bash
# Create and activate virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# Run API server locally (dev)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker
celery -A app.tasks worker --loglevel=info --concurrency=4

# Run Celery Beat scheduler
celery -A app.tasks beat --loglevel=info

# Run Celery Flower (monitoring)
celery -A app.tasks flower

# Run tests
pytest

# Run tests with coverage
pytest --cov=app tests/
```

### Frontend (React/TypeScript)
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm start

# Build for production
npm run build

# Run tests
npm test

# Run linter
npm run lint

# Type check
npm run type-check
```

## EVE Online ESI Integration

### Authentication Flow
- Uses OAuth 2.0 + PKCE with EVE Online SSO
- Base URLs:
  - ESI API: `https://esi.evetech.net/latest`
  - SSO Auth: `https://login.eveonline.com/v2/oauth/authorize`
  - SSO Token: `https://login.eveonline.com/v2/oauth/token`
  - JWKS: `https://login.eveonline.com/oauth/jwks`

### ESI Best Practices
1. **Rate Limiting**: ESI has error limit of 100 errors/60s leading to automatic ban
2. **Caching**: Always use ETags and respect cache headers
3. **Token Refresh**: Access tokens expire in 20 minutes; implement proactive refresh
4. **User-Agent**: Include descriptive user agent with contact info
5. **Compatibility Date**: Use X-Compatibility-Date header for API versioning

### Key ESI Scopes Required
```python
SCOPES = [
    "esi-characters.read_corporation_roles.v1",
    "esi-corporations.read_corporation_membership.v1",
    "esi-killmails.read_killmails.v1",
    "esi-location.read_location.v1",
    "esi-assets.read_corporation_assets.v1",
    "esi-wallet.read_corporation_wallets.v1",
    "esi-structures.read_structures.v1",
    "esi-universe.read_structures.v1",
    "esi-markets.read_corporation_orders.v1",
    "esi-fleets.read_fleet.v1",
]
```

## Database Architecture

### Core Tables
- **users**: Application user accounts
- **eve_tokens**: OAuth tokens (access & refresh, encrypted at rest)
- **characters**: Linked EVE characters with metadata
- **corporations**: Corporation information
- **corporation_members**: Many-to-many relationship with roles
- **killmails**: Killmail data with JSONB for full payload
- **systems**: Universe system data with coordinates
- **system_jumps**: Graph of stargate connections
- **system_activity**: Time-series activity data
- **fleets**: Fleet management
- **doctrines**: Ship doctrine definitions

### Indexes
All tables with time-series data use descending indexes on timestamp columns. System and killmail queries are optimized with compound indexes on frequently queried fields.

## Background Job Patterns

### Token Refresh (runs every 15 minutes)
```python
@celery.task
def refresh_expired_tokens():
    expiring_tokens = get_tokens_expiring_soon(minutes=5)
    for token in expiring_tokens:
        new_token = refresh_esi_token(token.refresh_token)
        token.update(new_token)
```

### Corporation Sync (scheduled or on-demand)
```python
@celery.task(bind=True, max_retries=3)
def sync_corporation_data(self, corporation_id: int):
    # Fetch corp info, members, assets, structures
    # Handle ESIRateLimitError with exponential backoff
```

### Killmail Processing (continuous)
- Poll ESI every 5 minutes for recent killmails
- Subscribe to zKillboard RedisQ for real-time kills
- Process and store with pre-computed analytics

## External APIs

### zKillboard Integration
- **RedisQ**: `https://zkillboard.com/api/no-items/no-attackers/queueID/{QUEUE_ID}/`
- **Killmail Details**: `https://zkillboard.com/api/killID/{killmail_id}/`
- **Price History**: Available via zKill API
- Subscribe to real-time feed for instant kill notifications

## Security Considerations

1. **Token Storage**: All refresh tokens encrypted at rest using Fernet
2. **Access Control**: Strict per-user data isolation in all queries
3. **Secrets Management**: Use environment variables, never hardcode
4. **HTTPS Only**: All external communication over TLS
5. **Input Validation**: Pydantic models for all API inputs
6. **Rate Limiting**: Implement on API endpoints to prevent abuse

## Map & Route Planning

### Route Calculation
Custom A* pathfinding algorithm with:
- Security status weighting (prefer high-sec or avoid low-sec)
- Custom avoid lists (systems/regions to exclude)
- Ansiblex jump gate support
- Wormhole connections integration

### Map Overlays
- Recent kill activity (heatmap)
- Sovereignty ownership (color-coded by alliance)
- Jump bridges and stargates
- Planned routes with waypoints
- System activity (jumps, NPC kills)

## File Structure

```
eve-app/
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
│   │   └── utils/        # Utility functions
│   ├── public/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
└── README.md
```

## Environment Variables

Required environment variables (see .env.example):

```env
DATABASE_URL=postgresql://user:pass@postgres:5432/eve_db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key-here
ESI_CLIENT_ID=your-client-id
ESI_CLIENT_SECRET=your-client-secret
ESI_CALLBACK_URL=https://your-domain.com/callback
ENCRYPTION_KEY=your-encryption-key
```

## Testing Strategy

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test API endpoints with test database
- **ESI Mocking**: Mock ESI responses to avoid rate limits in tests
- **Frontend Tests**: Jest + React Testing Library
- **E2E Tests**: Consider Playwright for critical user flows

## Code Style & Patterns

### Backend (Python)
- Follow PEP 8 style guide
- Use type hints for all functions
- Pydantic models for data validation
- Async/await for I/O operations
- Service layer pattern for business logic

### Frontend (TypeScript)
- Functional components with hooks
- Custom hooks for reusable logic
- TanStack Query for server state
- Zustand/Redux for client state
- Strict TypeScript mode enabled

## Multi-Character Support

Users can link multiple EVE characters to a single account:
- Each character has separate OAuth tokens
- Data can be viewed per-character or aggregated
- Character switching in UI updates context
- All ESI calls use the appropriate character's token

## Deployment

### Development
```bash
docker-compose -f docker-compose.dev.yml up
```
Access:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Flower: http://localhost:5555

### Production
- Use Kubernetes for orchestration (EKS, GKE, or Hetzner)
- Managed database (AWS RDS, Cloud SQL)
- Redis cluster for high availability
- Automated backups and monitoring
- CI/CD pipeline for automated deployment

## Useful Resources

- ESI Swagger: https://esi.evetech.net/
- ESI Docs: https://docs.esi.evetech.net/
- zKillboard API: https://github.com/zKillboard/zKillboard/wiki
- EVE Developers: https://developers.eveonline.com/
- EVE University Wiki: https://wiki.eveuniversity.org/EVE_Stable_Infrastructure

## Development Workflow

1. Create feature branch from main
2. Implement feature with tests
3. Run linters and tests locally
4. Create pull request
5. CI runs tests and builds
6. Code review and merge
7. CD deploys to staging/production
