You're absolutely right - let's do this properly with direct research. I'll use targeted searches to gather the information and build you a comprehensive prompt. Let me start gathering the key technical details:Perfect! I've gathered comprehensive information on Eve Online's ESI API, EveSeat's architecture, killmail tracking, route planning, tech stacks, and real-time systems. Now let me compile this into a detailed technical prompt for you.

---

# **COMPREHENSIVE TECHNICAL PROMPT: EVE ONLINE API APPLICATION**

## **Executive Summary**
Build a Docker-based, multi-tenant Eve Online management platform similar to EveSeat but with enhanced features including advanced map integration, live killmail tracking, intelligent route planning, and comprehensive corporation management. The application should start as a personal tool but be architected to scale into a SaaS offering for the Eve Online community.

---

## **1. RECOMMENDED TECH STACK**

### **Backend: Python/FastAPI** ✅ **RECOMMENDED**
**Rationale:**
- **Performance**: FastAPI matches Node.js in speed (4,831 req/sec) while offering superior async capabilities
- **Eve Integration**: Python ecosystem has mature ESI libraries (esipy, evepraisal)
- **Data Processing**: Native data science libraries (pandas, numpy) for kill analytics and route optimization
- **Type Safety**: Pydantic provides automatic validation and serialization
- **Documentation**: Auto-generated OpenAPI/Swagger docs
- **Developer Experience**: Cleaner, more maintainable code than Node.js for complex logic

**Alternative**: Node.js/NestJS (if team has strong JS background and needs real-time focus)

### **Frontend: React + TypeScript**
- **React 18+** with hooks and context API
- **TypeScript** for type safety
- **TanStack Query** (React Query) for API state management
- **Zustand** or **Redux Toolkit** for global state
- **TailwindCSS** for styling
- **Recharts** or **D3.js** for data visualization
- **Socket.io-client** for WebSocket connections

### **Database: PostgreSQL**
- Mature, reliable, excellent JSON support
- Superior for complex queries (killmail analytics, route pathfinding)
- Strong indexing capabilities for large datasets
- PostGIS extension for spatial data (map coordinates)

### **Cache & Queue: Redis**
- Message broker for Celery
- Caching ESI responses (critical for rate limiting)
- Session storage
- Real-time data pub/sub

### **Background Jobs: Celery**
- ESI API polling (refresh tokens, corporation data)
- Killmail fetching and analysis
- Route calculation
- Market data aggregation

### **Real-time: WebSockets (FastAPI WebSockets + Socket.IO)**
- Live killmail feeds
- System activity notifications
- Fleet status updates
- Background job progress

---

## **2. DOCKER ARCHITECTURE**

### **Microservices Structure**
```yaml
services:
  # Reverse Proxy & Load Balancer
  traefik:
    image: traefik:v2.10
    # SSL termination, routing, load balancing
  
  # Frontend
  frontend:
    build: ./frontend
    # React app served by nginx
    
  # API Gateway
  api:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000
    # FastAPI application
    
  # WebSocket Server
  websocket:
    build: ./backend
    command: uvicorn websocket:app --host 0.0.0.0 --port 8001
    # Dedicated WebSocket server
    
  # Background Workers
  worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info --concurrency=4
    # ESI polling, data processing
    
  # Scheduler
  scheduler:
    build: ./backend
    command: celery -A tasks beat --loglevel=info
    # Cron jobs for periodic tasks
    
  # Task Monitor
  flower:
    build: ./backend
    command: celery -A tasks flower
    # Celery monitoring UI
    
  # Database
  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  # Cache & Message Broker
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:

networks:
  eve-network:
    driver: bridge
```

---

## **3. EVE ONLINE ESI API INTEGRATION**

### **Authentication Flow (OAuth 2.0 + PKCE)**
```python
# SSO Configuration
ESI_BASE_URL = "https://esi.evetech.net/latest"
SSO_AUTH_URL = "https://login.eveonline.com/v2/oauth/authorize"
SSO_TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"
SSO_JWKS_URL = "https://login.eveonline.com/oauth/jwks"

# Required Scopes (comprehensive list)
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
    # Add all required scopes
]
```

### **Critical ESI Considerations**
1. **Rate Limiting**: Error limit = 100 errors/60s → Automatic ban
2. **Caching**: Use ETags and cache headers aggressively
3. **Token Refresh**: Access tokens expire in 20 minutes
4. **User-Agent**: Always include descriptive user agent with contact info
5. **Compatibility Date**: Use X-Compatibility-Date header for API versioning

### **Key ESI Endpoints**
```python
# Character & Corporation
GET /characters/{character_id}/
GET /corporations/{corporation_id}/
GET /corporations/{corporation_id}/members/
GET /corporations/{corporation_id}/assets/

# Killmails
GET /characters/{character_id}/killmails/recent/
GET /corporations/{corporation_id}/killmails/recent/
GET /killmails/{killmail_id}/{killmail_hash}/

# Universe & Map
GET /universe/systems/{system_id}/
GET /universe/structures/{structure_id}/
GET /route/{origin}/{destination}/
GET /universe/systems/{system_id}/kills/

# Market
GET /markets/{region_id}/orders/
GET /markets/{region_id}/history/
GET /markets/prices/
```

---

## **4. CORE FEATURES IMPLEMENTATION**

### **4.1 Authentication & Multi-Tenancy**

**Database Schema**:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    eve_character_id BIGINT UNIQUE NOT NULL,
    character_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE TABLE eve_tokens (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    scopes TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE corporations (
    id SERIAL PRIMARY KEY,
    eve_corporation_id BIGINT UNIQUE NOT NULL,
    corporation_name VARCHAR(255),
    ticker VARCHAR(10),
    owner_user_id INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE corporation_members (
    corporation_id INT REFERENCES corporations(id),
    user_id INT REFERENCES users(id),
    role VARCHAR(50),
    added_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (corporation_id, user_id)
);
```

**Token Refresh Strategy**:
```python
# Background task runs every 15 minutes
@celery.task
def refresh_expired_tokens():
    expiring_tokens = get_tokens_expiring_soon(minutes=5)
    for token in expiring_tokens:
        new_token = refresh_esi_token(token.refresh_token)
        token.update(new_token)
```

### **4.2 Killmail Tracking & Analytics**

**Architecture**:
1. **ESI Polling**: Celery task fetches recent killmails every 5 minutes
2. **zKillboard Integration**: Subscribe to zKillboard RedisQ for instant kills
3. **Storage**: Store killmails with indexed fields for fast queries
4. **Analytics**: Pre-compute statistics (efficiency, top killers, etc.)

**Database Schema**:
```sql
CREATE TABLE killmails (
    killmail_id BIGINT PRIMARY KEY,
    killmail_hash VARCHAR(64),
    solar_system_id INT,
    killmail_time TIMESTAMP,
    victim_character_id BIGINT,
    victim_corporation_id BIGINT,
    victim_alliance_id BIGINT,
    victim_ship_type_id INT,
    total_value NUMERIC(20,2),
    attackers_count INT,
    raw_data JSONB, -- Full killmail JSON
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_killmail_time ON killmails(killmail_time DESC);
CREATE INDEX idx_killmail_corp ON killmails(victim_corporation_id);
CREATE INDEX idx_killmail_system ON killmails(solar_system_id);
CREATE INDEX idx_killmail_value ON killmails(total_value DESC);
```

**zKillboard API Integration**:
```python
# RedisQ subscription for real-time kills
ZKILL_REDISQ = "https://zkillboard.com/api/no-items/no-attackers/"

@celery.task
def fetch_zkill_realtime():
    while True:
        response = requests.get(f"{ZKILL_REDISQ}queueID/{QUEUE_ID}/")
        if response.json().get('package'):
            killmail = response.json()['package']
            process_killmail(killmail)
            
# Fetch specific killmail details
def get_zkill_killmail(killmail_id):
    return requests.get(
        f"https://zkillboard.com/api/killID/{killmail_id}/"
    ).json()
```

### **4.3 Map Integration & Intel System**

**Features**:
- Live system kill feed
- Jump range visualization
- Recent activity heatmap
- Dangerous system highlighting
- Custom waypoint management

**Database Schema**:
```sql
CREATE TABLE systems (
    system_id INT PRIMARY KEY,
    system_name VARCHAR(255),
    region_id INT,
    constellation_id INT,
    security_status NUMERIC(3,2),
    coordinates_x NUMERIC,
    coordinates_y NUMERIC,
    coordinates_z NUMERIC,
    metadata JSONB
);

CREATE TABLE system_jumps (
    from_system_id INT,
    to_system_id INT,
    PRIMARY KEY (from_system_id, to_system_id)
);

CREATE TABLE system_activity (
    system_id INT,
    activity_time TIMESTAMP,
    ship_kills INT DEFAULT 0,
    npc_kills INT DEFAULT 0,
    pod_kills INT DEFAULT 0,
    jumps INT DEFAULT 0,
    PRIMARY KEY (system_id, activity_time)
);

CREATE INDEX idx_activity_time ON system_activity(activity_time DESC);
```

**Real-time Updates**:
```python
# WebSocket endpoint for live kill feed
@app.websocket("/ws/killFeed")
async def killmail_feed(websocket: WebSocket):
    await websocket.accept()
    async for kill in kill_stream:
        await websocket.send_json({
            "type": "killmail",
            "data": kill
        })
```

### **4.4 Route Planning & Navigation**

**Features**:
- Safest route calculation (avoid dangerous systems)
- Fastest route (shortest jumps)
- Custom waypoint optimization
- Avoid specific systems/regions
- Integration with Ansiblex jump gates
- Wormhole connections (via Eve-Scout/Tripwire)

**Pathfinding Algorithm** (A* with custom heuristics):
```python
import heapq
from dataclasses import dataclass

@dataclass
class RouteNode:
    system_id: int
    g_cost: float  # Actual cost from start
    h_cost: float  # Heuristic cost to goal
    parent: Optional['RouteNode'] = None
    
    @property
    def f_cost(self):
        return self.g_cost + self.h_cost

def calculate_route(
    start_system: int,
    end_system: int,
    avoid_systems: List[int],
    prefer_safer: bool = True,
    security_penalty: float = 1.0
) -> List[int]:
    """
    A* pathfinding with security preference
    """
    open_set = []
    closed_set = set()
    
    start_node = RouteNode(
        system_id=start_system,
        g_cost=0,
        h_cost=heuristic_distance(start_system, end_system)
    )
    heapq.heappush(open_set, (start_node.f_cost, start_node))
    
    while open_set:
        current = heapq.heappop(open_set)[1]
        
        if current.system_id == end_system:
            return reconstruct_path(current)
        
        closed_set.add(current.system_id)
        
        for neighbor_id in get_connected_systems(current.system_id):
            if neighbor_id in avoid_systems or neighbor_id in closed_set:
                continue
            
            # Calculate cost with security penalty
            security = get_system_security(neighbor_id)
            jump_cost = 1.0
            
            if prefer_safer and security < 0.5:
                jump_cost += (0.5 - security) * security_penalty
            
            g_cost = current.g_cost + jump_cost
            h_cost = heuristic_distance(neighbor_id, end_system)
            
            neighbor = RouteNode(
                system_id=neighbor_id,
                g_cost=g_cost,
                h_cost=h_cost,
                parent=current
            )
            
            heapq.heappush(open_set, (neighbor.f_cost, neighbor))
    
    return []  # No route found
```

**API Endpoint**:
```python
@app.post("/api/route/calculate")
async def calculate_route_api(request: RouteRequest):
    route = calculate_route(
        start_system=request.origin,
        end_system=request.destination,
        avoid_systems=request.avoid_systems,
        prefer_safer=request.prefer_safer,
        security_penalty=request.security_penalty
    )
    
    # Enhance with system details
    route_details = [
        {
            "system_id": sys_id,
            "system_name": get_system_name(sys_id),
            "security_status": get_system_security(sys_id),
            "recent_kills": get_recent_kills(sys_id, hours=24)
        }
        for sys_id in route
    ]
    
    return {
        "route": route_details,
        "total_jumps": len(route) - 1,
        "estimated_time": (len(route) - 1) * 3  # 3 seconds per jump
    }
```

### **4.5 Corporation Management**

**Features**:
- Member tracking & roles
- Asset management
- Wallet & transactions
- Structure management
- Moon mining tracking
- Fleet composition analysis

**Background Sync**:
```python
@celery.task(bind=True, max_retries=3)
def sync_corporation_data(self, corporation_id: int):
    """
    Comprehensive corporation data sync
    """
    try:
        # Fetch and update corporation info
        corp_info = fetch_esi(f"/corporations/{corporation_id}/")
        update_corporation(corporation_id, corp_info)
        
        # Sync members
        members = fetch_esi(
            f"/corporations/{corporation_id}/members/",
            requires_auth=True
        )
        sync_corporation_members(corporation_id, members)
        
        # Sync assets
        assets = fetch_esi(
            f"/corporations/{corporation_id}/assets/",
            requires_auth=True
        )
        sync_corporation_assets(corporation_id, assets)
        
        # Sync structures
        structures = fetch_esi(
            f"/corporations/{corporation_id}/structures/",
            requires_auth=True
        )
        sync_corporation_structures(corporation_id, structures)
        
    except ESIRateLimitError:
        # Retry with exponential backoff
        self.retry(countdown=60 * (2 ** self.request.retries))
```

### **4.6 Market Analysis**

**Features**:
- Price tracking & history
- Trade hub comparisons
- Market orders (buy/sell)
- Profit margin calculator
- Volume analysis

**Data Collection**:
```python
@celery.task
def sync_market_data():
    """
    Sync market data for major trade hubs
    """
    TRADE_HUBS = {
        'Jita': 30000142,
        'Amarr': 30002187,
        'Dodixie': 30002659,
        'Rens': 30002510,
        'Hek': 30002053
    }
    
    for hub_name, region_id in TRADE_HUBS.items():
        orders = fetch_esi(f"/markets/{region_id}/orders/")
        store_market_orders(hub_name, region_id, orders)
        
        # Fetch price history
        # (Limited to specific items due to API constraints)
        for type_id in TRACKED_ITEMS:
            history = fetch_esi(
                f"/markets/{region_id}/history/",
                params={"type_id": type_id}
            )
            store_price_history(type_id, region_id, history)
```

### **4.7 Fleet Management**

**Features**:
- Fleet composition tracking
- Doctrine compliance checking
- Fitting analysis
- Fleet activity logging
- Member attendance

**Database Schema**:
```sql
CREATE TABLE fleets (
    fleet_id BIGINT PRIMARY KEY,
    fleet_commander_id BIGINT,
    corporation_id INT REFERENCES corporations(id),
    created_at TIMESTAMP,
    ended_at TIMESTAMP,
    doctrine VARCHAR(255),
    metadata JSONB
);

CREATE TABLE fleet_members (
    fleet_id BIGINT REFERENCES fleets(fleet_id),
    character_id BIGINT,
    ship_type_id INT,
    joined_at TIMESTAMP,
    left_at TIMESTAMP
);

CREATE TABLE doctrines (
    id SERIAL PRIMARY KEY,
    corporation_id INT REFERENCES corporations(id),
    name VARCHAR(255),
    ship_types INT[],
    required_skills JSONB,
    fittings JSONB
);
```

---

## **5. SECURITY & BEST PRACTICES**

### **Token Security**
```python
from cryptography.fernet import Fernet

# Encrypt refresh tokens at rest
def encrypt_token(token: str) -> str:
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted: str) -> str:
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.decrypt(encrypted.encode()).decode()
```

### **Rate Limiting**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/killmails")
@limiter.limit("100/minute")
async def get_killmails(request: Request):
    pass
```

### **Input Validation**
```python
from pydantic import BaseModel, validator

class RouteRequest(BaseModel):
    origin: int
    destination: int
    avoid_systems: List[int] = []
    prefer_safer: bool = True
    security_penalty: float = 1.0
    
    @validator('security_penalty')
    def validate_penalty(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Security penalty must be between 0 and 100')
        return v
```

---

## **6. DEPLOYMENT STRATEGY**

### **Development Environment**
```bash
# docker-compose.dev.yml
docker-compose -f docker-compose.dev.yml up
```

### **Production Environment**
```yaml
# Use Docker Swarm or Kubernetes
# Horizontal scaling for API and workers
# Redis cluster for high availability
# PostgreSQL with replication
# Automated backups
# Monitoring with Prometheus + Grafana
# Logging with ELK stack
```

### **Environment Variables**
```env
# .env.example
DATABASE_URL=postgresql://user:pass@postgres:5432/eve_db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key-here
ESI_CLIENT_ID=your-client-id
ESI_CLIENT_SECRET=your-client-secret
ESI_CALLBACK_URL=https://your-domain.com/callback
ENCRYPTION_KEY=your-encryption-key
```

---

## **7. MONITORING & MAINTENANCE**

### **Health Checks**
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": await check_database(),
        "redis": await check_redis(),
        "esi": await check_esi_connection()
    }
```

### **Metrics**
- API response times
- ESI error rates
- Celery task success/failure rates
- Database query performance
- WebSocket connection count
- Cache hit rates

### **Logging**
```python
import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
```

---

## **8. ROADMAP**

### **Phase 1: MVP (Months 1-3)**
- ✅ ESI authentication & token management
- ✅ Basic corporation data sync
- ✅ Killmail tracking (ESI + zKillboard)
- ✅ Simple map view with system info
- ✅ Basic route planning

### **Phase 2: Enhanced Features (Months 4-6)**
- Live killmail feed (WebSocket)
- Advanced route planning with custom weights
- Market data integration
- Fleet management
- Mobile-responsive design

### **Phase 3: Multi-Tenancy & SaaS (Months 7-12)**
- User registration & billing
- Corporation/alliance subscriptions
- Advanced analytics & reporting
- API for third-party integrations
- White-label options

---

## **9. GETTING STARTED**

### **Step 1: Project Structure**
```
eve-app/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Config, security
│   │   ├── models/       # Database models
│   │   ├── services/     # Business logic
│   │   ├── tasks/        # Celery tasks
│   │   └── websockets/   # WebSocket handlers
│   ├── alembic/          # Database migrations
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/     # API clients
│   │   ├── hooks/
│   │   └── utils/
│   ├── public/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
└── README.md
```

### **Step 2: Initialize Backend**
```bash
# Create FastAPI project
cd backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy alembic celery redis pydantic requests

# Create database migrations
alembic init alembic
alembic revision --autogenerate -m "Initial"
alembic upgrade head
```

### **Step 3: Initialize Frontend**
```bash
cd frontend
npx create-react-app . --template typescript
npm install @tanstack/react-query axios socket.io-client zustand recharts
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### **Step 4: Configure ESI Application**
1. Go to https://developers.eveonline.com/applications
2. Create new application
3. Select "Authentication & API Access"
4. Add all required scopes
5. Set callback URL
6. Save CLIENT_ID and CLIENT_SECRET

### **Step 5: Start Development**
```bash
# Start all services
docker-compose -f docker-compose.dev.yml up

# Access:
# - Frontend: http://localhost:3000
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Flower: http://localhost:5555
```

---

## **10. ADDITIONAL RESOURCES**

### **Documentation**
- ESI Swagger: https://esi.evetech.net/
- ESI Docs: https://docs.esi.evetech.net/
- zKillboard API: https://github.com/zKillboard/zKillboard/wiki
- EveSeat Docs: https://eveseat.github.io/docs/

### **Libraries**
- **Python**: esipy, aiohttp, celery, fastapi
- **JavaScript**: socket.io, axios, react-query

### **Community**
- r/Eve (Reddit)
- Tweetfleet Slack
- Eve University Forums

---

