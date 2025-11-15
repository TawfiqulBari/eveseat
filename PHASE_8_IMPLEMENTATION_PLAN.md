# Phase 8 Implementation Plan - Detailed Todo List

**Based on**: PHASE_8_RESEARCH.md
**Priority Order**: High → Medium → Low
**Total Estimated Effort**: 210-290 hours

---

## Implementation Strategy

### Phase 8A (HIGH Priority) - 60-85 hours
**Goal**: Maximum ROI, full ESI support, critical features
1. Corporation Mining Ledger Analytics (25-35 hours)
2. Skill Plan Optimizer (45-60 hours)

### Phase 8B (MEDIUM Priority) - 55-75 hours
**Goal**: Feature breadth, good ESI support
3. Asset Safety Tracking (15-20 hours)
4. Wormhole Tracking (40-50 hours)
5. Player-Owned Customs Offices (12-18 hours)

### Phase 8C (LOW Priority) - 95-130 hours
**Goal**: Specialized features, limited ESI support
6. Corporation Hangar Management (25-30 hours)
7. Abyssal Deadspace Statistics (30-40 hours)
8. Market Trading Bot Integration (60-80 hours)

---

# PHASE 8A: HIGH PRIORITY FEATURES

## Feature 1: Corporation Mining Ledger Analytics
**Estimated**: 25-35 hours | **Priority**: HIGH | **ESI Support**: Full

### Backend Tasks (12-16 hours)

#### Database Models (3-4 hours)
- [ ] Create `backend/app/models/mining_analytics.py`
  - [ ] `MiningLedgerEntry` model (character, ore, quantity, date, value)
  - [ ] `MiningMemberStatistics` model (per-member aggregations)
  - [ ] `MiningObserverStatistics` model (per-structure stats)
  - [ ] `MiningTaxCalculation` model (tax owed/paid tracking)
  - [ ] Add relationships to `Character` and `Corporation` models

#### API Endpoints (4-5 hours)
- [ ] Create `backend/app/api/v1/mining_analytics.py`
  - [ ] `GET /mining-analytics/ledger` - List ledger entries (with filters)
  - [ ] `GET /mining-analytics/ledger/{observer_id}` - Observer-specific ledger
  - [ ] `GET /mining-analytics/members` - Member statistics with rankings
  - [ ] `GET /mining-analytics/members/{character_id}` - Individual member stats
  - [ ] `GET /mining-analytics/observers` - Observer statistics
  - [ ] `GET /mining-analytics/observers/{observer_id}` - Single observer stats
  - [ ] `GET /mining-analytics/tax/calculate` - Calculate taxes for period
  - [ ] `GET /mining-analytics/tax/outstanding` - List unpaid taxes
  - [ ] `POST /mining-analytics/tax/record-payment` - Record tax payment
  - [ ] `POST /mining-analytics/sync` - Trigger ledger sync
  - [ ] Add Pydantic schemas for all request/response models

#### Celery Sync Tasks (5-7 hours)
- [ ] Create `backend/app/tasks/mining_analytics_sync.py`
  - [ ] `sync_mining_ledger(corporation_id)` - Fetch from ESI observers
  - [ ] `calculate_mining_statistics(corporation_id, period)` - Daily aggregation
  - [ ] `calculate_monthly_taxes(corporation_id, month)` - Monthly tax calc
  - [ ] `update_ore_prices()` - Daily market price updates
  - [ ] Add to Celery Beat schedule (every 6 hours for ledger)
  - [ ] Implement retry logic with exponential backoff
  - [ ] WebSocket events for sync progress

### Frontend Tasks (8-12 hours)

#### TypeScript Service (1-2 hours)
- [ ] Create `frontend/src/services/mining_analytics.ts`
  - [ ] API client methods for all endpoints
  - [ ] TypeScript interfaces matching backend schemas
  - [ ] Error handling and response typing

#### React Pages (7-10 hours)
- [ ] Create `frontend/src/pages/MiningAnalytics.tsx`
  - [ ] Corporation overview dashboard
  - [ ] Total value mined (charts over time)
  - [ ] Top miners leaderboard
  - [ ] Observer breakdown (pie charts by structure)
  - [ ] Filters: date range, observer, ore type

- [ ] Create `frontend/src/pages/MiningLedger.tsx`
  - [ ] Detailed ledger table with pagination
  - [ ] Per-member drill-down
  - [ ] Ore type breakdown
  - [ ] Export to CSV functionality

- [ ] Create `frontend/src/pages/MiningTaxes.tsx`
  - [ ] Tax calculation interface
  - [ ] Outstanding taxes by member
  - [ ] Payment tracking
  - [ ] Monthly reports
  - [ ] Tax rate configuration

### Configuration & Integration (5-7 hours)
- [ ] Update `backend/app/main.py` - Register mining_analytics router
- [ ] Update `backend/app/tasks/__init__.py` - Register tasks
- [ ] Update `frontend/src/App.tsx` - Add routes
- [ ] Update `frontend/src/components/Layout.tsx` - Add navigation
- [ ] Update `backend/app/websockets/events.py` - Add WebSocket events
- [ ] Create database migration for new tables
- [ ] Add required ESI scopes to documentation
- [ ] Write unit tests for critical calculations
- [ ] Update API documentation

---

## Feature 2: Skill Plan Optimizer
**Estimated**: 45-60 hours | **Priority**: HIGH | **ESI Support**: Full

### Backend Tasks (20-28 hours)

#### Database Models (5-7 hours)
- [ ] Create `backend/app/models/skill_planner.py`
  - [ ] `SkillPlan` model (name, description, target ship/activity, status)
  - [ ] `SkillPlanEntry` model (skill, current/target level, prerequisites)
  - [ ] `SkillPlanTemplate` model (pre-made plans library)
  - [ ] `SkillOptimizationResult` model (optimized order, remap suggestions)
  - [ ] Add relationships to `Character` model

#### ESI Integration & Algorithms (8-10 hours)
- [ ] Create `backend/app/services/skill_optimizer.py`
  - [ ] Skill dependency graph builder (from EVE SDE)
  - [ ] Prerequisite resolver (topological sort algorithm)
  - [ ] Training time calculator (attributes + implants)
  - [ ] Remap optimizer (maximize SP/day for plan)
  - [ ] A* pathfinding for optimal skill order
  - [ ] Import EVE SDE skill data (types, prerequisites, multipliers)

#### API Endpoints (7-11 hours)
- [ ] Create `backend/app/api/v1/skill_planner.py`
  - [ ] `GET /skill-planner/plans` - List all plans for character
  - [ ] `GET /skill-planner/plans/{plan_id}` - Get single plan details
  - [ ] `POST /skill-planner/plans` - Create new plan
  - [ ] `PUT /skill-planner/plans/{plan_id}` - Update plan
  - [ ] `DELETE /skill-planner/plans/{plan_id}` - Delete plan
  - [ ] `POST /skill-planner/plans/{plan_id}/skills` - Add skill to plan
  - [ ] `DELETE /skill-planner/plans/{plan_id}/skills/{skill_id}` - Remove skill
  - [ ] `POST /skill-planner/plans/{plan_id}/optimize` - Run optimization
  - [ ] `GET /skill-planner/plans/{plan_id}/prerequisites` - Resolve dependencies
  - [ ] `GET /skill-planner/templates` - List plan templates
  - [ ] `POST /skill-planner/plans/from-template/{template_id}` - Create from template
  - [ ] `GET /skill-planner/skills/search` - Search skills by name/category
  - [ ] `POST /skill-planner/remap/suggest` - Suggest optimal attribute remap

### Frontend Tasks (18-24 hours)

#### TypeScript Service (2-3 hours)
- [ ] Create `frontend/src/services/skill_planner.ts`
  - [ ] API client for all endpoints
  - [ ] Complex TypeScript interfaces (skill tree, dependencies)
  - [ ] Helper functions for skill calculations

#### React Components (16-21 hours)
- [ ] Create `frontend/src/pages/SkillPlanner.tsx`
  - [ ] Plan list/selector sidebar
  - [ ] Drag-and-drop skill order editor
  - [ ] Skill search with autocomplete
  - [ ] Prerequisite tree visualization (D3.js or React Flow)
  - [ ] Training time summary
  - [ ] Progress tracking (completed vs pending)

- [ ] Create `frontend/src/components/SkillPlanBuilder.tsx`
  - [ ] Skill browser with category filters
  - [ ] Add to plan button
  - [ ] Prerequisite indicator
  - [ ] Training time per skill display

- [ ] Create `frontend/src/components/SkillOptimizer.tsx`
  - [ ] Optimization options (minimize time, by attribute, etc.)
  - [ ] Remap simulator
  - [ ] Before/after comparison
  - [ ] Apply optimization button

- [ ] Create `frontend/src/pages/SkillTemplates.tsx`
  - [ ] Template library (by ship type, activity)
  - [ ] Template preview
  - [ ] Create plan from template
  - [ ] Community templates (future)

### Configuration & Integration (7-8 hours)
- [ ] Load EVE SDE skill data into database (one-time import)
- [ ] Update `backend/app/main.py` - Register skill_planner router
- [ ] Update `backend/app/tasks/__init__.py` - Register tasks (if any)
- [ ] Update `frontend/src/App.tsx` - Add routes
- [ ] Update `frontend/src/components/Layout.tsx` - Add navigation
- [ ] Create database migration
- [ ] Seed database with skill templates (common ship fits)
- [ ] Write comprehensive tests (graph algorithms are complex)
- [ ] Performance testing (large skill plans)
- [ ] Export to EVEMon format (bonus feature)

---

# PHASE 8B: MEDIUM PRIORITY FEATURES

## Feature 3: Asset Safety Tracking
**Estimated**: 15-20 hours | **Priority**: MEDIUM | **ESI Support**: Good

### Backend Tasks (7-9 hours)

#### Database Models (2-3 hours)
- [ ] Create `backend/app/models/asset_safety.py`
  - [ ] `AssetSafetyContainer` model (location, origin, expiration, value)
  - [ ] `AssetSafetyItem` model (items in safety)
  - [ ] `AssetSafetyAlert` model (expiration alerts)
  - [ ] Add relationships to `Character` model

#### API Endpoints (2-3 hours)
- [ ] Create `backend/app/api/v1/asset_safety.py`
  - [ ] `GET /asset-safety/containers` - List all safety containers
  - [ ] `GET /asset-safety/containers/{container_id}` - Container details
  - [ ] `GET /asset-safety/alerts` - Get active alerts
  - [ ] `POST /asset-safety/sync` - Trigger sync
  - [ ] `POST /asset-safety/alerts/{alert_id}/dismiss` - Dismiss alert

#### Celery Tasks (3-3 hours)
- [ ] Create `backend/app/tasks/asset_safety_sync.py`
  - [ ] `sync_asset_safety(character_id)` - Scan character assets for safety
  - [ ] `check_asset_safety_expiration()` - Daily check for expiring containers
  - [ ] `send_asset_safety_alerts()` - Send notifications (7d, 3d, 1d)
  - [ ] Add to Celery Beat schedule (every 12 hours)

### Frontend Tasks (6-8 hours)

#### Service & Pages (6-8 hours)
- [ ] Create `frontend/src/services/asset_safety.ts`
- [ ] Create `frontend/src/pages/AssetSafety.tsx`
  - [ ] Active containers list with expiration timers
  - [ ] Item breakdown per container
  - [ ] Location map
  - [ ] Alert notifications (urgent, warning, info)
  - [ ] Historical retrieved containers
  - [ ] Value tracking

### Configuration (2-3 hours)
- [ ] Configuration updates (main.py, tasks, routes, navigation)
- [ ] Database migration
- [ ] WebSocket events for new alerts
- [ ] Tests

---

## Feature 4: Wormhole Tracking
**Estimated**: 40-50 hours | **Priority**: MEDIUM | **ESI Support**: Limited (Manual Entry)

### Backend Tasks (18-22 hours)

#### Database Models (4-5 hours)
- [ ] Create `backend/app/models/wormhole.py`
  - [ ] `WormholeSystem` model (system info, class, effects, statics)
  - [ ] `WormholeConnection` model (from/to systems, type, mass, time)
  - [ ] `WormholeSignature` model (signatures in systems)
  - [ ] Graph algorithms for chain mapping

#### API Endpoints (6-8 hours)
- [ ] Create `backend/app/api/v1/wormholes.py`
  - [ ] `GET /wormholes/systems` - List known WH systems
  - [ ] `GET /wormholes/systems/{system_id}` - System details
  - [ ] `GET /wormholes/connections` - List active connections
  - [ ] `POST /wormholes/connections` - Add new connection (manual)
  - [ ] `PUT /wormholes/connections/{conn_id}` - Update (mass/time status)
  - [ ] `DELETE /wormholes/connections/{conn_id}` - Mark collapsed
  - [ ] `GET /wormholes/chain` - Get chain map from starting system
  - [ ] `POST /wormholes/signatures` - Add signature (paste from game)
  - [ ] `GET /wormholes/signatures/{system_id}` - List signatures
  - [ ] Signature parser for EVE game clipboard format

#### Celery Tasks (4-5 hours)
- [ ] Create `backend/app/tasks/wormhole_sync.py`
  - [ ] `expire_old_wormholes()` - Mark expired (every 5 min)
  - [ ] `cleanup_inactive_signatures()` - Daily cleanup
  - [ ] `detect_location_changes()` - Track if character enters WH

#### Chain Mapping Algorithm (4-4 hours)
- [ ] Create `backend/app/services/wormhole_mapper.py`
  - [ ] Graph-based chain builder
  - [ ] Multi-hop pathfinding
  - [ ] Distance/mass calculations

### Frontend Tasks (18-24 hours)

#### Service & Pages (18-24 hours)
- [ ] Create `frontend/src/services/wormholes.ts`
- [ ] Create `frontend/src/pages/WormholeMapper.tsx`
  - [ ] **Interactive chain visualization** (D3.js or React Flow - most complex)
  - [ ] System info cards (effects, statics, occupied status)
  - [ ] Connection editor (add/edit/delete)
  - [ ] Mass/time status indicators
  - [ ] Signature manager (paste detection)
  - [ ] Export/import chain data
  - [ ] Multi-user collaboration (WebSocket updates)

### Configuration (4-4 hours)
- [ ] Configuration updates
- [ ] Import WH system data (from ESI universe data)
- [ ] Database migration
- [ ] Integration with third-party mappers (optional: Tripwire, Pathfinder API)

---

## Feature 5: Player-Owned Customs Offices (POCOs)
**Estimated**: 12-18 hours | **Priority**: MEDIUM | **ESI Support**: Good (no revenue data)

### Backend Tasks (6-9 hours)

#### Database Models (2-3 hours)
- [ ] Create `backend/app/models/poco.py`
  - [ ] `CustomsOffice` model (location, tax rates, reinforcement)
  - [ ] `POCORevenueEstimate` model (manual revenue tracking)
  - [ ] `POCOAlert` model (reinforcement alerts)

#### API Endpoints (2-3 hours)
- [ ] Create `backend/app/api/v1/pocos.py`
  - [ ] `GET /pocos` - List corp POCOs
  - [ ] `GET /pocos/{office_id}` - POCO details
  - [ ] `PUT /pocos/{office_id}/tax-rates` - Update tax rates
  - [ ] `POST /pocos/revenue` - Manual revenue entry
  - [ ] `POST /pocos/sync` - Trigger sync

#### Celery Tasks (2-3 hours)
- [ ] Create `backend/app/tasks/poco_sync.py`
  - [ ] `sync_corporation_pocos(corp_id)` - Sync from ESI
  - [ ] `check_poco_reinforcement()` - Alert on reinforcement (every 30 min)

### Frontend Tasks (5-7 hours)
- [ ] Create `frontend/src/services/pocos.ts`
- [ ] Create `frontend/src/pages/POCOs.tsx`
  - [ ] POCO list grouped by system
  - [ ] Tax rate editor (bulk update)
  - [ ] Reinforcement timer
  - [ ] Revenue tracking (manual entry)
  - [ ] Map view showing POCO distribution

### Configuration (1-2 hours)
- [ ] Standard configuration updates
- [ ] Database migration

---

# PHASE 8C: LOW PRIORITY FEATURES

## Feature 6: Corporation Hangar Management
**Estimated**: 25-30 hours | **Priority**: LOW | **ESI Support**: Limited (no audit logs)

### Backend Tasks (12-15 hours)
- [ ] Create `backend/app/models/hangar.py`
  - [ ] `CorporationHangar`, `HangarItem`, `HangarAuditLog`, `HangarSnapshot`
- [ ] Create `backend/app/api/v1/hangars.py` (10+ endpoints)
- [ ] Create `backend/app/tasks/hangar_sync.py`
  - [ ] Snapshot comparison algorithm (diff detection)
  - [ ] Value tracking with market prices

### Frontend Tasks (10-12 hours)
- [ ] Create `frontend/src/services/hangars.ts`
- [ ] Create `frontend/src/pages/Hangars.tsx`
  - [ ] Hangar browser (division selector)
  - [ ] Item search across locations
  - [ ] Change log viewer
  - [ ] Capacity warnings
  - [ ] Export capabilities

### Configuration (3-3 hours)
- [ ] Standard updates and migration

---

## Feature 7: Abyssal Deadspace Statistics
**Estimated**: 30-40 hours | **Priority**: LOW | **ESI Support**: None (manual tracking)

### Backend Tasks (14-18 hours)
- [ ] Create `backend/app/models/abyssal.py`
  - [ ] `AbyssalRun`, `AbyssalStatistics`
- [ ] Create `backend/app/api/v1/abyssal.py`
  - [ ] Manual run entry
  - [ ] Combat log parser (optional, complex)
  - [ ] Statistics aggregation
- [ ] Create `backend/app/tasks/abyssal_sync.py`
  - [ ] `calculate_abyssal_statistics()`
  - [ ] Combat log parsing (if implemented)

### Frontend Tasks (12-16 hours)
- [ ] Create `frontend/src/services/abyssal.ts`
- [ ] Create `frontend/src/pages/Abyssal.tsx`
  - [ ] Run entry form
  - [ ] Run history with profit/loss
  - [ ] Statistics dashboard (success rate, tier breakdown)
  - [ ] Combat log upload (optional)

### Configuration (4-6 hours)
- [ ] Standard updates
- [ ] Combat log parser library integration (if doing auto-detection)

---

## Feature 8: Market Trading Bot Integration
**Estimated**: 60-80 hours | **Priority**: LOW | **ESI Support**: Good (Read-only, no auto-trading)

### Backend Tasks (28-36 hours)
- [ ] Create `backend/app/models/trading_bot.py`
  - [ ] `TradingStrategy`, `TradingOpportunity`, `TradingPerformance`, `PriceAlert`
- [ ] Create `backend/app/services/market_analyzer.py`
  - [ ] Opportunity detection algorithms
  - [ ] Margin calculations
  - [ ] Competition analysis
  - [ ] Profit calculator (fees, taxes)
- [ ] Create `backend/app/api/v1/trading.py` (15+ endpoints)
- [ ] Create `backend/app/tasks/trading_sync.py`
  - [ ] `scan_market_opportunities()` - Every 5 minutes
  - [ ] `update_trading_performance()` - Hourly
  - [ ] `check_price_alerts()` - Every 10 minutes

### Frontend Tasks (24-32 hours)
- [ ] Create `frontend/src/services/trading.ts`
- [ ] Create `frontend/src/pages/TradingBot.tsx`
  - [ ] Strategy builder
  - [ ] Opportunity feed (real-time)
  - [ ] One-click order copying
  - [ ] Performance charts
  - [ ] Watchlist with alerts

### Legal & Safety (8-12 hours)
- [ ] User confirmation UI (NO auto-trading)
- [ ] EULA compliance review
- [ ] Rate limiting to avoid ESI bans
- [ ] Warnings about market risks
- [ ] Documentation on legal usage

---

# IMPLEMENTATION CHECKLIST (For Each Feature)

## Backend
- [ ] Create database models file
- [ ] Create API router file
- [ ] Create Celery tasks file (if needed)
- [ ] Create service/helper file (if complex logic)
- [ ] Update `backend/app/main.py` - Import and register router
- [ ] Update `backend/app/tasks/__init__.py` - Register tasks
- [ ] Update `backend/app/models/character.py` - Add relationships (if needed)
- [ ] Update `backend/app/websockets/events.py` - Add events
- [ ] Create Alembic migration: `alembic revision --autogenerate -m "Add Feature X"`
- [ ] Write unit tests
- [ ] Update API documentation

## Frontend
- [ ] Create TypeScript service file
- [ ] Create React page component(s)
- [ ] Create specialized components (if needed)
- [ ] Update `frontend/src/App.tsx` - Add routes
- [ ] Update `frontend/src/components/Layout.tsx` - Add navigation
- [ ] Add to appropriate navigation category
- [ ] Update TypeScript types (if shared)
- [ ] Write component tests

## Testing & Documentation
- [ ] Manual testing of all endpoints
- [ ] Test WebSocket events
- [ ] Test Celery tasks manually
- [ ] Performance testing (large datasets)
- [ ] Update CLAUDE.md with feature description
- [ ] Update SESSION_STATUS.md with completion

## Deployment
- [ ] Commit changes with descriptive message
- [ ] Push to GitHub
- [ ] Verify CI/CD pipeline passes
- [ ] Deploy to production
- [ ] Verify in production environment
- [ ] Monitor logs for errors

---

# RECOMMENDED IMPLEMENTATION ORDER

## Week 1-2: Phase 8A-1 (Mining Analytics)
**Goal**: Critical corp feature with full ESI support

1. Day 1-2: Database models + migrations
2. Day 3-4: API endpoints + ESI integration
3. Day 5-6: Celery sync tasks
4. Day 7-8: Frontend service + Mining Analytics page
5. Day 9-10: Mining Ledger + Taxes pages
6. Day 11-12: Testing, refinement, deployment

## Week 3-5: Phase 8A-2 (Skill Planner)
**Goal**: High-value feature, complex algorithms

1. Week 3: Backend (models, algorithms, API)
2. Week 4: Frontend (planner UI, optimization)
3. Week 5: Templates, testing, polish

## Week 6-7: Phase 8B Features
**Goal**: Broader feature set

1. Asset Safety (2-3 days)
2. POCOs (2-3 days)
3. Wormhole Tracking (5-7 days)

## Week 8-12: Phase 8C Features (Optional)
**Goal**: Specialized features as needed

Implement based on user demand and available resources.

---

# SUCCESS METRICS

For each feature, track:
- [ ] Backend API response time < 200ms (95th percentile)
- [ ] Frontend page load < 2s
- [ ] Zero critical bugs in production
- [ ] ESI rate limit compliance (< 50 errors/min)
- [ ] User adoption rate (% of users using feature)
- [ ] Background task success rate > 95%

---

# NOTES

- **Start with Phase 8A** - highest ROI
- **Test incrementally** - don't wait until end
- **Commit frequently** - small, atomic commits
- **Monitor ESI usage** - avoid rate limits
- **Get user feedback early** - especially for UX-heavy features (skill planner, WH mapper)
- **Performance matters** - mining ledger can have massive datasets
- **Security first** - especially for trading bot (no auto-trading!)

---

**Total Features**: 8
**Total Estimated Hours**: 210-290 hours
**Phases**: 3 (8A, 8B, 8C)
**Recommended Start**: Corporation Mining Ledger Analytics

---

End of Implementation Plan
