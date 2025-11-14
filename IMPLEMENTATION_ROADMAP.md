# EVESeat Implementation Roadmap

## Completed Work (Phase 1 & Partial Phase 2)

### ✅ Phase 1: Critical Infrastructure
1. **Docker Compose Services** - Worker, Scheduler, Flower already configured
2. **WebSocket Server** - Complete real-time event streaming system
   - `app/websockets/connection_manager.py` - Connection management with topic subscriptions
   - `app/websockets/events.py` - Event types and data models
   - `app/websockets/server.py` - FastAPI WebSocket server with authentication
   - `app/websockets/redis_pubsub.py` - Redis pub/sub for multi-server scaling
   - `app/websockets/publisher.py` - Event publishing utilities
   - Integrated with killmail sync tasks

### ✅ Phase 2.1: Mail System (In Progress)
- **Models**: `app/models/mail.py` (Mail, MailLabel, MailingList)
- **API**: `app/api/v1/mail.py` (CRUD operations, send, organize)
- **Tasks**: `app/tasks/mail_sync.py` (sync, send via ESI)
- **Integration**: Character model relationships updated

---

## Remaining Work

### 🔨 Phase 2: Core ESI Features (REMAINING)

#### Phase 2.2: Contacts & Calendar
**Models Needed:**
```
app/models/contact.py
  - Contact (character/corp/alliance contacts)
  - ContactLabel

app/models/calendar.py
  - CalendarEvent
  - CalendarEventResponse
```

**API Endpoints:**
```
app/api/v1/contacts.py
  GET    /contacts/                  # List contacts
  POST   /contacts/                  # Add contact
  PUT    /contacts/{contact_id}/     # Update contact
  DELETE /contacts/{contact_id}/     # Remove contact
  GET    /contacts/labels/           # List labels

app/api/v1/calendar.py
  GET    /calendar/                  # List events
  GET    /calendar/{event_id}/       # Event details
  PUT    /calendar/{event_id}/       # Respond to event
  GET    /calendar/{event_id}/attendees/  # Attendee list
```

**Celery Tasks:**
```
app/tasks/contact_sync.py
  - sync_character_contacts()
  - sync_corporation_contacts()

app/tasks/calendar_sync.py
  - sync_character_calendar()
```

**ESI Client Methods:** (add to `app/services/esi_client.py`)
```python
async def get_character_contacts(character_id, access_token)
async def add_character_contact(character_id, contact_data, access_token)
async def delete_character_contact(character_id, contact_ids, access_token)
async def get_calendar_events(character_id, access_token)
async def respond_to_calendar_event(character_id, event_id, response, access_token)
```

#### Phase 2.3: Contracts System
**Models:**
```
app/models/contract.py
  - Contract (contract header data)
  - ContractItem (items in contract)
  - ContractBid (for auctions)
```

**API:**
```
app/api/v1/contracts.py
  GET    /contracts/                  # List contracts
  GET    /contracts/{contract_id}/    # Contract details
  GET    /contracts/{contract_id}/items/  # Contract items
  POST   /contracts/search/           # Search contracts (corp/region)
  GET    /contracts/bids/{contract_id}/  # Auction bids
```

**Tasks:**
```
app/tasks/contract_sync.py
  - sync_character_contracts()
  - sync_corporation_contracts()
  - sync_public_contracts()  # Regional public contracts
```

#### Phase 2.4: Wallet Details
**Models:**
```
app/models/wallet.py
  - WalletJournal (detailed transaction log)
  - WalletTransaction (market transactions)
```

**API:**
```
app/api/v1/wallet.py
  GET    /wallet/balance/{character_id}/     # Current balance
  GET    /wallet/journal/{character_id}/     # Journal entries
  GET    /wallet/transactions/{character_id}/  # Market transactions
  GET    /wallet/statistics/{character_id}/   # Aggregate stats
```

**Tasks:**
```
app/tasks/wallet_sync.py
  - sync_character_wallet_journal()
  - sync_character_wallet_transactions()
  - sync_corporation_wallets()  # All 7 divisions
```

---

### 🏭 Phase 3: Industry & Economy

#### Phase 3.1: Industry Jobs
**Models:**
```
app/models/industry.py
  - IndustryJob (manufacturing, research, reactions)
  - IndustryFacility (available facilities cache)
```

**API:**
```
app/api/v1/industry.py
  GET    /industry/jobs/              # Active jobs
  GET    /industry/jobs/{job_id}/     # Job details
  GET    /industry/facilities/        # Available facilities
  GET    /industry/systems/           # System cost indices
```

**Tasks:**
```
app/tasks/industry_sync.py
  - sync_character_industry_jobs()
  - sync_corporation_industry_jobs()
  - sync_industry_systems()  # Cost index data
```

#### Phase 3.2: Blueprints
**Models:**
```
app/models/blueprint.py
  - Blueprint (owned blueprints with ME/TE)
```

**API:**
```
app/api/v1/blueprints.py
  GET    /blueprints/                 # List blueprints
  GET    /blueprints/{item_id}/       # Blueprint details
  GET    /blueprints/calculator/      # Manufacturing calculator
```

**Tasks:**
```
app/tasks/blueprint_sync.py
  - sync_character_blueprints()
  - sync_corporation_blueprints()
```

#### Phase 3.3: Planetary Interaction
**Models:**
```
app/models/planetary.py
  - Planet (colony data)
  - PlanetaryPin (extractors, processors, storage)
  - PlanetaryRoute (links between pins)
  - CustomsOffice (corp customs offices)
```

**API:**
```
app/api/v1/planets.py
  GET    /planets/                    # List colonies
  GET    /planets/{planet_id}/        # Colony details
  GET    /planets/{planet_id}/layout/ # Pin layout
  GET    /customs-offices/            # Corp customs offices
```

**Tasks:**
```
app/tasks/planetary_sync.py
  - sync_character_planets()
  - sync_corporation_customs_offices()
```

#### Phase 3.4: Loyalty Points
**Models:**
```
app/models/loyalty.py
  - LoyaltyPoint (LP balances per corporation)
  - LoyaltyOffer (LP store items cache)
```

**API:**
```
app/api/v1/loyalty.py
  GET    /loyalty/points/             # LP balances
  GET    /loyalty/offers/{corp_id}/   # LP store offers
  GET    /loyalty/calculator/         # LP conversion calculator
```

**Tasks:**
```
app/tasks/loyalty_sync.py
  - sync_character_loyalty_points()
  - sync_loyalty_offers()  # Cache LP store data
```

---

### 🎨 Phase 4: Frontend Completion

#### Phase 4.1: Interactive Map (D3.js)
**Files:**
```
frontend/src/pages/Map.tsx (complete rewrite)
frontend/src/components/Map/
  - MapCanvas.tsx         # D3 SVG map rendering
  - SystemNode.tsx        # System visualization
  - RouteOverlay.tsx      # Route planning UI
  - ActivityHeatmap.tsx   # Kill/jump activity
  - SovereigntyLayer.tsx  # Null-sec ownership
```

**Features:**
- 3D star map with jump gate connections
- Real-time killmail overlays
- Route planning with waypoints
- Security status coloring
- System activity indicators
- Zoom/pan controls

#### Phase 4.2: Market Analysis
**Files:**
```
frontend/src/pages/Market.tsx (expand)
frontend/src/components/Market/
  - OrderBook.tsx         # Buy/sell orders table
  - PriceChart.tsx        # Historical price graph (Recharts)
  - ProfitCalculator.tsx  # Margin calculator
  - TradeRoutes.tsx       # Inter-hub arbitrage
  - QuickTrade.tsx        # Fast buy/sell interface
```

#### Phase 4.3: Corporation Dashboard
**Files:**
```
frontend/src/pages/Corporation.tsx (expand)
frontend/src/components/Corporation/
  - MemberList.tsx        # Member roster with roles
  - AssetBrowser.tsx      # Corp asset search/filter
  - StructureManager.tsx  # Citadel/POS management
  - WalletDivisions.tsx   # 7 wallet divisions
  - TaxCollector.tsx      # Tax/bounty tracking
```

#### Phase 4.4: Fleet Tools
**Files:**
```
frontend/src/pages/Fleet.tsx (expand)
frontend/src/components/Fleet/
  - FleetComposition.tsx  # Ship type breakdown
  - DoctrineChecker.tsx   # Doctrine compliance
  - SRPCalculator.tsx     # Ship replacement program
  - BroadcastFeed.tsx     # Fleet broadcasts (if in fleet)
```

---

### 📊 Phase 5: Advanced Features

#### Phase 5.1: Intel Tools
**Models:**
```
app/models/sovereignty.py
  - SovereigntyMap (null-sec system ownership)
  - SovereigntyCampaign (ongoing campaigns)

app/models/war.py
  - War (active wars)
  - WarParticipant

app/models/incursion.py
  - Incursion (active incursions)
```

**API:**
```
app/api/v1/sovereignty.py
app/api/v1/wars.py
app/api/v1/incursions.py
```

**Tasks:**
```
app/tasks/intel_sync.py
  - sync_sovereignty_map()
  - sync_active_wars()
  - sync_incursions()
```

**Frontend:**
```
frontend/src/pages/Intel.tsx
frontend/src/components/Intel/
  - SovMap.tsx
  - WarTracker.tsx
  - IncursionMonitor.tsx
```

#### Phase 5.2: Analytics Dashboard
**Files:**
```
frontend/src/pages/Analytics.tsx
frontend/src/components/Analytics/
  - ISKFlow.tsx           # Income/expenses over time
  - AssetValue.tsx        # Net worth tracking
  - KillStats.tsx         # PvP statistics
  - TradingPerformance.tsx # Market trading metrics
  - SkillProgress.tsx     # Skill training analytics
```

#### Phase 5.3: Multi-Character Aggregation
**Backend:**
```
app/api/v1/aggregate.py
  GET    /aggregate/wallets/         # Combined wallet balance
  GET    /aggregate/assets/          # All character assets
  GET    /aggregate/skills/          # Skill queue overview
  GET    /aggregate/industry/        # All industry jobs
```

**Frontend:**
```
frontend/src/pages/Overview.tsx (new)
  - Multi-character dashboard
  - Quick character switcher
  - Aggregate stats display
```

#### Phase 5.4: Contract Manager
**Frontend:**
```
frontend/src/pages/Contracts.tsx
frontend/src/components/Contracts/
  - ContractBrowser.tsx   # Search with filters
  - ContractDetails.tsx   # Full contract view
  - ContractTracker.tsx   # Track courier progress
  - AlertSystem.tsx       # Expiration alerts
```

---

### 🧪 Phase 6: Testing & Quality

#### Phase 6.1: Backend Tests (80%+ coverage)
**Files:**
```
backend/tests/
  conftest.py             # Pytest fixtures
  test_auth.py
  test_characters.py
  test_killmails.py
  test_mail.py
  test_contacts.py
  test_calendar.py
  test_contracts.py
  test_wallet.py
  test_industry.py
  test_planetary.py
  test_websockets.py
  test_esi_client.py

  mocks/
    esi_responses.py      # Mock ESI API responses
```

**Test Coverage Goals:**
- API endpoints: 90%+
- ESI client: 85%+
- Celery tasks: 80%+
- Models: 95%+

#### Phase 6.2: Frontend Tests
**Files:**
```
frontend/src/__tests__/
  components/
    Map.test.tsx
    Market.test.tsx
    Corporation.test.tsx
    Fleet.test.tsx
  hooks/
    useAuth.test.tsx
    useWebSocket.test.tsx
  integration/
    auth-flow.test.tsx
    killmail-feed.test.tsx
```

**E2E Tests (Playwright):**
```
frontend/e2e/
  auth.spec.ts
  killmails.spec.ts
  mail.spec.ts
  market.spec.ts
```

#### Phase 6.3: Performance Optimization
**Backend:**
- Database query optimization (EXPLAIN ANALYZE)
- Redis caching strategy review
- Celery task concurrency tuning
- ESI rate limit optimization

**Frontend:**
- Code splitting (React.lazy)
- Bundle analysis (webpack-bundle-analyzer)
- Memoization optimization
- Image/asset optimization

---

## Database Migrations Needed

```bash
# Create migration for mail tables
alembic revision --autogenerate -m "Add mail tables"

# Create migration for contacts
alembic revision --autogenerate -m "Add contacts table"

# Create migration for calendar
alembic revision --autogenerate -m "Add calendar tables"

# Create migration for contracts
alembic revision --autogenerate -m "Add contract tables"

# Create migration for wallet
alembic revision --autogenerate -m "Add wallet journal and transactions"

# Create migration for industry
alembic revision --autogenerate -m "Add industry tables"

# Create migration for blueprints
alembic revision --autogenerate -m "Add blueprints table"

# Create migration for planetary
alembic revision --autogenerate -m "Add planetary interaction tables"

# Create migration for loyalty
alembic revision --autogenerate -m "Add loyalty points tables"

# Create migration for sovereignty
alembic revision --autogenerate -m "Add sovereignty tables"

# Create migration for wars
alembic revision --autogenerate -m "Add wars tables"

# Create migration for incursions
alembic revision --autogenerate -m "Add incursions table"
```

---

## Configuration Updates

### ESI Scopes to Add (app/core/config.py)
```python
# Communication
"esi-mail.read_mail.v1",
"esi-mail.send_mail.v1",
"esi-mail.organize_mail.v1",

# Contacts
"esi-characters.read_contacts.v1",
"esi-characters.write_contacts.v1",

# Calendar
"esi-calendar.read_calendar_events.v1",
"esi-calendar.respond_calendar_events.v1",

# Contracts
"esi-contracts.read_character_contracts.v1",
"esi-contracts.read_corporation_contracts.v1",

# Industry
"esi-industry.read_character_jobs.v1",
"esi-industry.read_corporation_jobs.v1",

# Planets
"esi-planets.manage_planets.v1",
"esi-planets.read_customs_offices.v1",

# Fittings
"esi-fittings.read_fittings.v1",
"esi-fittings.write_fittings.v1",

# Bookmarks
"esi-bookmarks.read_character_bookmarks.v1",
"esi-bookmarks.read_corporation_bookmarks.v1",

# Clones
"esi-clones.read_clones.v1",
"esi-clones.read_implants.v1",

# Wallet detail
"esi-wallet.read_character_wallet.v1",
"esi-wallet.read_corporation_wallet.v1",

# Search
"esi-search.search_structures.v1",
```

---

## Celery Beat Schedule Updates

```python
celery_app.conf.beat_schedule = {
    # ... existing schedules ...

    "sync-character-mail": {
        "task": "app.tasks.mail_sync.sync_all_character_mail",
        "schedule": 1800.0,  # Every 30 minutes
    },
    "sync-character-contacts": {
        "task": "app.tasks.contact_sync.sync_all_character_contacts",
        "schedule": 3600.0,  # Every hour
    },
    "sync-character-calendar": {
        "task": "app.tasks.calendar_sync.sync_all_character_calendars",
        "schedule": 900.0,  # Every 15 minutes
    },
    "sync-character-contracts": {
        "task": "app.tasks.contract_sync.sync_all_character_contracts",
        "schedule": 1800.0,  # Every 30 minutes
    },
    "sync-character-wallet": {
        "task": "app.tasks.wallet_sync.sync_all_character_wallets",
        "schedule": 600.0,  # Every 10 minutes
    },
    "sync-industry-jobs": {
        "task": "app.tasks.industry_sync.sync_all_industry_jobs",
        "schedule": 1800.0,  # Every 30 minutes
    },
    "sync-planetary-colonies": {
        "task": "app.tasks.planetary_sync.sync_all_planets",
        "schedule": 3600.0,  # Every hour
    },
    "sync-sovereignty": {
        "task": "app.tasks.intel_sync.sync_sovereignty_map",
        "schedule": 3600.0,  # Every hour
    },
    "sync-wars": {
        "task": "app.tasks.intel_sync.sync_active_wars",
        "schedule": 1800.0,  # Every 30 minutes
    },
    "sync-incursions": {
        "task": "app.tasks.intel_sync.sync_incursions",
        "schedule": 600.0,  # Every 10 minutes
    },
}
```

---

## Estimated Remaining Work

### Lines of Code Estimate:
- **Backend**: ~15,000 lines
  - Models: ~2,500 lines
  - API endpoints: ~5,000 lines
  - Celery tasks: ~4,000 lines
  - ESI client methods: ~2,000 lines
  - Tests: ~1,500 lines

- **Frontend**: ~10,000 lines
  - Pages: ~3,000 lines
  - Components: ~5,000 lines
  - Services/Hooks: ~1,500 lines
  - Tests: ~500 lines

### Time Estimate:
- **Phase 2 remaining**: 3-4 days
- **Phase 3**: 5-6 days
- **Phase 4**: 6-8 days
- **Phase 5**: 5-7 days
- **Phase 6**: 4-5 days

**Total**: ~23-30 days of focused development

---

## Priority Recommendations

If time is limited, prioritize in this order:

1. **Critical** (Must Have):
   - Contacts & Calendar (social features)
   - Contracts (core economy)
   - Wallet details (financial tracking)
   - Complete Map page (navigation)

2. **Important** (Should Have):
   - Industry & Blueprints (manufacturing)
   - PI (passive income tracking)
   - Market page completion
   - Corp dashboard completion

3. **Nice to Have**:
   - Loyalty Points
   - Intel tools (Sov/Wars/Incursions)
   - Analytics dashboard
   - Multi-character aggregation

4. **Polish**:
   - Comprehensive testing
   - Performance optimization
   - Advanced search features

---

## Next Immediate Steps

1. Create database migration for mail tables
2. Add mail API routes to main router
3. Update config with mail scopes
4. Create Contacts models and API
5. Create Calendar models and API
6. Create Contracts models and API
7. Create Wallet models and API
8. Test and debug Phase 2 features
9. Continue with Phase 3...

**Current Status**: Phase 2.1 (Mail) ~80% complete, need migration + router registration
