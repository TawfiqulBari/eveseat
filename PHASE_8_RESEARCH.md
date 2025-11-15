# Phase 8+ Research & Implementation Plan

**Date**: 2025-11-15
**Author**: Claude Code
**Status**: Research Complete - Ready for Implementation

---

## Executive Summary

This document provides comprehensive research and implementation plans for 8 advanced features to extend the EVE Online Management Platform. Each feature has been analyzed for ESI endpoints, data models, complexity, and implementation approach.

**Priority Ranking** (High → Medium → Low):
1. **HIGH**: Corporation Mining Ledger Analytics, Skill Plan Optimizer
2. **MEDIUM**: Wormhole Tracking, Asset Safety Tracking, POCOs
3. **LOW**: Abyssal Deadspace Statistics, Corporation Hangar Management, Market Trading Bot

---

## Feature 1: Wormhole Tracking

### Overview
Track wormhole connections, signatures, and exploration data for mapping J-space and K-space connections.

### ESI Endpoints Required
- **Character Location**: `/characters/{character_id}/location/` (requires `esi-location.read_location.v1`)
- **Character Ship**: `/characters/{character_id}/ship/` (requires `esi-location.read_ship_type.v1`)
- **Universe System**: `/universe/systems/{system_id}/`
- **Universe Wormholes**: No direct ESI support - must be tracked manually or via third-party integrations

### Data Models

```python
# backend/app/models/wormhole.py

class WormholeSystem(Base):
    """Wormhole system information"""
    __tablename__ = "wormhole_systems"

    id = Column(Integer, primary_key=True)
    solar_system_id = Column(Integer, unique=True, nullable=False, index=True)
    system_name = Column(String(255), nullable=False)
    class_id = Column(Integer, nullable=False)  # 1-6, 13 (shattered), etc.
    static_connections = Column(JSONB)  # List of static wormhole types
    effects = Column(JSONB)  # System effects (pulsar, wolf-rayet, etc.)

class WormholeConnection(Base):
    """Tracked wormhole connections"""
    __tablename__ = "wormhole_connections"

    id = Column(Integer, primary_key=True)
    from_system_id = Column(Integer, ForeignKey("wormhole_systems.id"), index=True)
    to_system_id = Column(Integer, ForeignKey("wormhole_systems.id"), index=True)
    wormhole_type = Column(String(50))  # K162, H296, etc.
    signature = Column(String(10))  # ABC-123
    mass_remaining = Column(String(20))  # "stable", "destab", "critical"
    time_remaining = Column(String(20))  # "stable", "eol"
    discovered_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True))
    discovered_by_character_id = Column(Integer, ForeignKey("characters.id"))
    is_active = Column(Boolean, default=True, index=True)

class WormholeSignature(Base):
    """Cosmic signatures in wormhole systems"""
    __tablename__ = "wormhole_signatures"

    id = Column(Integer, primary_key=True)
    system_id = Column(Integer, ForeignKey("wormhole_systems.id"), index=True)
    signature_id = Column(String(10), nullable=False)  # ABC-123
    signature_type = Column(String(50))  # wormhole, data, relic, gas, combat
    signature_name = Column(String(255))
    scan_strength = Column(Float)  # 0.0 to 100.0
    scanned_by_character_id = Column(Integer, ForeignKey("characters.id"))
    scanned_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True))
```

### Implementation Complexity
**Difficulty**: High
**Estimated Effort**: 40-50 hours

**Challenges**:
1. **No Direct ESI Support**: Wormhole connections are not provided by ESI - must rely on manual player input or third-party tools
2. **Real-time Tracking**: Wormholes have limited lifespans (16-24 hours) and need constant monitoring
3. **Chain Mapping**: Complex graph algorithms needed for multi-hop wormhole chain visualization
4. **Mass Calculation**: Tracking mass limits and ship transits through wormholes
5. **Integration**: Tripwire, Pathfinder, or Siggy API integration for existing mapper data

### Implementation Approach

**Backend**:
1. Create manual entry API endpoints for wormhole connections
2. Implement graph-based chain mapping algorithm
3. Add signature scanning upload from game clipboard (paste format)
4. Create expiration tracking with automated cleanup
5. Add integration hooks for third-party wormhole mappers

**Frontend**:
1. Interactive wormhole chain visualization (D3.js or React Flow)
2. Signature management interface with paste detection
3. Connection editor with mass/time status
4. System info cards with static connections and effects
5. Real-time updates via WebSocket

**Celery Tasks**:
- `expire_old_wormholes`: Every 5 minutes, mark expired connections
- `cleanup_inactive_signatures`: Daily cleanup of old signatures

### User Value
**Medium-High** - Essential for wormhole corps and explorers, but limited ESI support means reliance on manual input.

---

## Feature 2: Abyssal Deadspace Statistics

### Overview
Track abyssal deadspace runs, filament types, loot values, and completion statistics.

### ESI Endpoints Required
- **Character Wallet**: `/characters/{character_id}/wallet/journal/` (track loot sales)
- **Character Killmails**: `/characters/{character_id}/killmails/recent/` (track ship losses)
- **Universe Types**: `/universe/types/{type_id}/` (filament and loot info)
- **No Direct Abyssal Data**: ESI does not provide abyssal run statistics

### Data Models

```python
# backend/app/models/abyssal.py

class AbyssalRun(Base):
    """Abyssal deadspace run tracking"""
    __tablename__ = "abyssal_runs"

    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    filament_type_id = Column(Integer, nullable=False)  # Type ID of filament used
    filament_tier = Column(Integer)  # 1-6 (T1-T6)
    weather_type = Column(String(50))  # Electrical, Dark, Firestorm, etc.

    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    ship_type_id = Column(Integer)
    ship_name = Column(String(255))
    fit_value = Column(BigInteger)  # ISK value of ship + fit

    # Outcome
    result = Column(String(20))  # "completed", "failed", "abandoned"
    rooms_cleared = Column(Integer, default=0)
    final_room_reached = Column(Boolean, default=False)

    # Loot
    loot_value = Column(BigInteger, default=0)
    loot_items = Column(JSONB)  # [{type_id, quantity, value}]

    # Stats
    total_damage_taken = Column(BigInteger, default=0)
    total_damage_dealt = Column(BigInteger, default=0)
    npcs_killed = Column(Integer, default=0)

    profit = Column(BigInteger)  # loot_value - filament_cost - (ship_loss if failed)

class AbyssalStatistics(Base):
    """Aggregated abyssal statistics per character"""
    __tablename__ = "abyssal_statistics"

    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey("characters.id"), unique=True)

    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    success_rate = Column(Float)  # Percentage

    total_profit = Column(BigInteger, default=0)
    total_loot_value = Column(BigInteger, default=0)
    average_profit_per_run = Column(BigInteger)
    best_run_profit = Column(BigInteger)

    favorite_tier = Column(Integer)  # Most run tier
    favorite_weather = Column(String(50))  # Most run weather

    synced_at = Column(DateTime(timezone=True))
```

### Implementation Complexity
**Difficulty**: Medium-High
**Estimated Effort**: 30-40 hours

**Challenges**:
1. **No ESI Data**: Abyssal runs are not tracked by ESI - must rely on manual logging or combat log parsing
2. **Combat Log Parsing**: Requires file upload and parsing of EVE combat logs
3. **Loot Attribution**: Difficult to automatically attribute wallet transactions to specific runs
4. **Time Tracking**: Must track when character enters/exits abyssal space via location changes
5. **Fit Value Calculation**: Need to snapshot ship fitting before run starts

### Implementation Approach

**Backend**:
1. Manual run entry API with filament type, duration, outcome
2. Combat log parser for automated run detection (optional)
3. Wallet journal correlation for loot value estimation
4. Statistics aggregation with profit/loss calculations
5. Leaderboards for best runs, fastest clears, highest profits

**Frontend**:
1. Run entry form with filament selector and outcome tracking
2. Run history table with profit/loss calculations
3. Statistics dashboard with tier/weather breakdowns
4. Profit charts over time
5. Combat log upload interface (optional)

**Celery Tasks**:
- `calculate_abyssal_statistics`: Hourly aggregation of run data
- `parse_combat_log`: Background parsing of uploaded combat logs

### User Value
**Low-Medium** - Valuable for dedicated abyssal runners, but limited ESI support means manual tracking burden.

---

## Feature 3: Corporation Mining Ledger Analytics

### Overview
Advanced analytics on corporation mining ledger data with per-member statistics, ore type breakdowns, and profitability tracking.

### ESI Endpoints Required
- **Corp Mining Ledger**: `/corporation/{corporation_id}/mining/observers/{observer_id}/` (requires `esi-industry.read_corporation_mining.v1`)
- **Corp Mining Observers**: `/corporation/{corporation_id}/mining/observers/` (structure list)
- **Universe Types**: `/universe/types/{type_id}/` (ore information)
- **Market Prices**: `/markets/{region_id}/history/` (ore pricing)

### Data Models

```python
# backend/app/models/mining_analytics.py

class MiningLedgerEntry(Base):
    """Individual mining ledger entries"""
    __tablename__ = "mining_ledger_entries"

    id = Column(Integer, primary_key=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), index=True)
    observer_id = Column(BigInteger, index=True)  # Structure ID
    character_id = Column(Integer, ForeignKey("characters.id"), index=True)

    ore_type_id = Column(Integer, nullable=False, index=True)
    ore_name = Column(String(255))
    quantity = Column(BigInteger, nullable=False)

    recorded_date = Column(Date, nullable=False, index=True)
    last_updated = Column(DateTime(timezone=True))

    # Calculated fields
    estimated_value = Column(BigInteger)  # Based on market price at recorded_date
    ore_category = Column(String(50))  # "Moon Ore", "Standard Ore", "Ice", "Mercoxit"

class MiningMemberStatistics(Base):
    """Per-member mining statistics"""
    __tablename__ = "mining_member_statistics"

    id = Column(Integer, primary_key=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), index=True)

    # Time period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Volume stats
    total_m3_mined = Column(BigInteger, default=0)
    total_value_mined = Column(BigInteger, default=0)
    total_ore_units = Column(BigInteger, default=0)

    # Activity
    days_active = Column(Integer, default=0)
    average_daily_value = Column(BigInteger)

    # Top ores
    top_ore_type_id = Column(Integer)
    top_ore_quantity = Column(BigInteger)

    # Rankings
    rank_by_value = Column(Integer)  # Corporation-wide ranking
    rank_by_volume = Column(Integer)

class MiningObserverStatistics(Base):
    """Per-structure/observer statistics"""
    __tablename__ = "mining_observer_statistics"

    id = Column(Integer, primary_key=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), index=True)
    observer_id = Column(BigInteger, index=True)
    observer_name = Column(String(255))
    system_id = Column(Integer)

    # Time period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Activity
    total_value_mined = Column(BigInteger, default=0)
    unique_miners = Column(Integer, default=0)
    most_productive_day = Column(Date)
    most_productive_day_value = Column(BigInteger)

    # Ore breakdown
    ore_breakdown = Column(JSONB)  # {ore_type_id: {quantity, value}}

class MiningTaxCalculation(Base):
    """Tax/contribution calculations for mining"""
    __tablename__ = "mining_tax_calculations"

    id = Column(Integer, primary_key=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), index=True)

    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False)

    total_value_mined = Column(BigInteger, nullable=False)
    tax_rate = Column(Float, default=0.0)  # 0.0 to 1.0 (e.g., 0.05 = 5%)
    tax_owed = Column(BigInteger)
    tax_paid = Column(BigInteger, default=0)
    tax_outstanding = Column(BigInteger)

    payment_status = Column(String(20), default="pending")  # pending, partial, paid
```

### Implementation Complexity
**Difficulty**: Medium
**Estimated Effort**: 25-35 hours

**Challenges**:
1. **Data Volume**: Mining ledger can be massive for active corps
2. **Price Correlation**: Need historical market prices for accurate value calculations
3. **Tax Tracking**: Complex logic for different tax structures (flat rate, tiered, exemptions)
4. **Multi-Observer**: Large corps may have dozens of structures to track
5. **Performance**: Aggregation queries must be optimized for large datasets

### Implementation Approach

**Backend**:
1. Sync mining ledger from all corp observers
2. Calculate ore values using historical market prices
3. Aggregate statistics by member, observer, time period
4. Implement tax calculation engine with configurable rates
5. Generate monthly reports and leaderboards

**Frontend**:
1. Corporation mining dashboard with total value charts
2. Member leaderboards with filtering by time period
3. Observer/structure breakdown with ore type pie charts
4. Tax tracking interface with payment status
5. Export capabilities for Excel/CSV reports
6. Drill-down from corp → member → observer → daily breakdown

**Celery Tasks**:
- `sync_mining_ledger`: Every 6 hours, fetch ledger from all observers
- `calculate_mining_statistics`: Daily aggregation of statistics
- `calculate_monthly_taxes`: Monthly tax calculations
- `update_ore_prices`: Daily update of ore market prices

### User Value
**HIGH** - Essential for mining corps to track contributions, calculate taxes, and analyze productivity. Strong ESI support makes this fully automated.

---

## Feature 4: Asset Safety Tracking

### Overview
Track items in asset safety after structure destruction and monitor retrieval status.

### ESI Endpoints Required
- **Character Assets**: `/characters/{character_id}/assets/` (requires `esi-assets.read_assets.v1`)
- **Asset Locations**: `/characters/{character_id}/assets/locations/` (asset location IDs)
- **Asset Names**: `/characters/{character_id}/assets/names/` (container names)
- **Killmails**: `/characters/{character_id}/killmails/recent/` (structure destruction)

### Data Models

```python
# backend/app/models/asset_safety.py

class AssetSafetyContainer(Base):
    """Asset safety containers"""
    __tablename__ = "asset_safety_containers"

    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey("characters.id"), index=True)

    container_item_id = Column(BigInteger, unique=True, nullable=False)  # ESI item_id
    container_name = Column(String(255))

    # Location info
    location_id = Column(BigInteger, index=True)  # NPC station where safety is
    location_name = Column(String(255))
    system_id = Column(Integer)
    region_id = Column(Integer)

    # Origin info
    original_structure_id = Column(BigInteger)
    original_structure_name = Column(String(255))
    original_system_id = Column(Integer)

    # Timing
    safety_triggered_at = Column(DateTime(timezone=True))  # Structure died
    expires_at = Column(DateTime(timezone=True))  # When items auto-deliver
    retrieved_at = Column(DateTime(timezone=True))

    # Contents
    total_items = Column(Integer, default=0)
    estimated_value = Column(BigInteger, default=0)

    status = Column(String(20), default="active")  # active, retrieved, expired

class AssetSafetyItem(Base):
    """Items in asset safety"""
    __tablename__ = "asset_safety_items"

    id = Column(Integer, primary_key=True)
    container_id = Column(Integer, ForeignKey("asset_safety_containers.id"), index=True)

    item_id = Column(BigInteger, unique=True, nullable=False)
    type_id = Column(Integer, nullable=False)
    type_name = Column(String(255))
    quantity = Column(Integer, nullable=False)

    is_blueprint_copy = Column(Boolean, default=False)
    is_singleton = Column(Boolean, default=False)

    estimated_value = Column(BigInteger)

class AssetSafetyAlert(Base):
    """Alerts for expiring asset safety"""
    __tablename__ = "asset_safety_alerts"

    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey("characters.id"), index=True)
    container_id = Column(Integer, ForeignKey("asset_safety_containers.id"))

    alert_type = Column(String(50))  # "new_safety", "expiring_soon", "expired"
    message = Column(Text)

    created_at = Column(DateTime(timezone=True), nullable=False)
    is_read = Column(Boolean, default=False)
```

### Implementation Complexity
**Difficulty**: Low-Medium
**Estimated Effort**: 15-20 hours

**Challenges**:
1. **Detection**: Asset safety items must be detected from normal asset scan
2. **Attribution**: Linking safety containers to original structure (no direct ESI link)
3. **Expiration Tracking**: Calculate 20-day expiration from trigger date
4. **Notifications**: Alert users before expiration
5. **Historical Data**: ESI doesn't provide historical structure kill events

### Implementation Approach

**Backend**:
1. Scan character assets for asset safety containers (location_flag = "AssetSafety")
2. Track container creation and expiration dates
3. Calculate item values from market prices
4. Create alerts for expiring containers (7 days, 3 days, 1 day)
5. Mark containers as retrieved when they disappear from assets

**Frontend**:
1. Asset safety dashboard showing all active containers
2. Expiration countdown timers with urgency indicators
3. Item breakdown by container with value estimates
4. Location map showing where items are
5. Alert notifications for expiring containers
6. Historical log of retrieved containers

**Celery Tasks**:
- `sync_asset_safety`: Every 12 hours, scan for asset safety containers
- `check_asset_safety_expiration`: Daily check for expiring containers
- `send_asset_safety_alerts`: Send alerts for expiring containers

### User Value
**MEDIUM** - Useful for all players, especially those in null-sec with structure risks. Prevents item loss from forgotten asset safety.

---

## Feature 5: Player-Owned Customs Offices (POCOs)

### Overview
Track POCO ownership, tax rates, and revenue generation for corporation-owned customs offices.

### ESI Endpoints Required
- **Corp Customs Offices**: `/corporations/{corporation_id}/customs_offices/` (requires `esi-planets.read_customs_offices.v1`)
- **Planet Info**: `/universe/planets/{planet_id}/`
- **System Info**: `/universe/systems/{system_id}/`
- **No Tax Revenue Data**: ESI does not provide POCO tax collection information

### Data Models

```python
# backend/app/models/poco.py

class CustomsOffice(Base):
    """Corporation-owned customs offices"""
    __tablename__ = "customs_offices"

    id = Column(Integer, primary_key=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), index=True)

    office_id = Column(BigInteger, unique=True, nullable=False)

    # Location
    system_id = Column(Integer, nullable=False, index=True)
    system_name = Column(String(255))
    planet_id = Column(Integer, nullable=False)
    planet_name = Column(String(255))
    planet_type = Column(String(50))  # Barren, Temperate, etc.

    # Tax rates (0.0 to 1.0)
    tax_rate_alliance = Column(Float, default=0.0)
    tax_rate_corp = Column(Float, default=0.0)
    tax_rate_standing_good = Column(Float, default=0.0)
    tax_rate_standing_neutral = Column(Float, default=0.05)
    tax_rate_standing_bad = Column(Float, default=0.1)

    # Status
    reinforcement_exit_time = Column(DateTime(timezone=True))
    is_reinforced = Column(Boolean, default=False, index=True)

    synced_at = Column(DateTime(timezone=True))

class POCORevenueEstimate(Base):
    """Estimated POCO tax revenue (manual tracking)"""
    __tablename__ = "poco_revenue_estimates"

    id = Column(Integer, primary_key=True)
    office_id = Column(Integer, ForeignKey("customs_offices.id"), index=True)

    date = Column(Date, nullable=False, index=True)

    # Manual entry fields
    estimated_transfers = Column(Integer, default=0)  # Number of transfers
    estimated_volume_m3 = Column(BigInteger, default=0)
    estimated_tax_collected = Column(BigInteger, default=0)

    notes = Column(Text)

class POCOAlert(Base):
    """Alerts for POCO reinforcement"""
    __tablename__ = "poco_alerts"

    id = Column(Integer, primary_key=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), index=True)
    office_id = Column(Integer, ForeignKey("customs_offices.id"))

    alert_type = Column(String(50))  # "reinforced", "exit_soon"
    system_id = Column(Integer)
    planet_name = Column(String(255))

    reinforcement_exit = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False)
    is_read = Column(Boolean, default=False)
```

### Implementation Complexity
**Difficulty**: Low
**Estimated Effort**: 12-18 hours

**Challenges**:
1. **No Revenue Data**: ESI doesn't provide tax collection data - must estimate or manually track
2. **Limited Metrics**: Can only track structure status, not actual usage
3. **Manual Entry**: Revenue tracking requires manual wallet journal correlation
4. **Multi-System**: Large corps may have hundreds of POCOs

### Implementation Approach

**Backend**:
1. Sync POCO list and tax rates from ESI
2. Track reinforcement status and alert on changes
3. Manual revenue entry interface for tracking
4. Calculate total potential tax revenue based on rates
5. System-level aggregation for multi-POCO systems

**Frontend**:
1. POCO management dashboard with system grouping
2. Tax rate editor for bulk updates
3. Reinforcement status with timer countdowns
4. Revenue tracking interface (manual entry)
5. Map view showing POCO distribution
6. Analytics on most profitable systems

**Celery Tasks**:
- `sync_corporation_pocos`: Every 12 hours, sync POCO list and status
- `check_poco_reinforcement`: Every 30 minutes, check for new reinforcements

### User Value
**MEDIUM** - Important for null/low-sec corps with POCO networks, but limited by lack of ESI revenue data.

---

## Feature 6: Corporation Hangar Management

### Overview
Advanced management of corporation hangars with audit logs, access control tracking, and item movement monitoring.

### ESI Endpoints Required
- **Corp Assets**: `/corporations/{corporation_id}/assets/` (requires `esi-assets.read_corporation_assets.v1`)
- **Asset Locations**: `/corporations/{corporation_id}/assets/locations/`
- **Asset Names**: `/corporations/{corporation_id}/assets/names/`
- **Corp Divisions**: `/corporations/{corporation_id}/divisions/` (hangar/wallet division names)
- **No Access Logs**: ESI does not provide audit logs for hangar access

### Data Models

```python
# backend/app/models/hangar.py

class CorporationHangar(Base):
    """Corporation hangar divisions"""
    __tablename__ = "corporation_hangars"

    id = Column(Integer, primary_key=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), index=True)

    division_id = Column(Integer, nullable=False)  # 1-7
    division_name = Column(String(255))

    # Location
    location_id = Column(BigInteger, index=True)  # Station or structure
    location_name = Column(String(255))
    system_id = Column(Integer)

    # Contents summary
    total_items = Column(Integer, default=0)
    unique_types = Column(Integer, default=0)
    estimated_value = Column(BigInteger, default=0)
    total_volume_m3 = Column(Float, default=0.0)

    last_synced = Column(DateTime(timezone=True))

class HangarItem(Base):
    """Items in corporation hangars"""
    __tablename__ = "hangar_items"

    id = Column(Integer, primary_key=True)
    hangar_id = Column(Integer, ForeignKey("corporation_hangars.id"), index=True)

    item_id = Column(BigInteger, unique=True, nullable=False, index=True)
    type_id = Column(Integer, nullable=False, index=True)
    type_name = Column(String(255))

    quantity = Column(Integer, nullable=False)
    location_flag = Column(String(50))  # CorpSAG1, CorpSAG2, etc.

    is_blueprint_copy = Column(Boolean, default=False)
    is_singleton = Column(Boolean, default=False)

    estimated_unit_value = Column(BigInteger)
    estimated_total_value = Column(BigInteger)

    last_seen = Column(DateTime(timezone=True), nullable=False)

class HangarAuditLog(Base):
    """Manual audit log for hangar changes"""
    __tablename__ = "hangar_audit_logs"

    id = Column(Integer, primary_key=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), index=True)
    hangar_id = Column(Integer, ForeignKey("corporation_hangars.id"))

    # Change detection
    change_type = Column(String(50))  # "item_added", "item_removed", "quantity_change"
    item_type_id = Column(Integer)
    item_type_name = Column(String(255))

    quantity_before = Column(Integer)
    quantity_after = Column(Integer)
    quantity_delta = Column(Integer)  # Positive = added, negative = removed

    # Estimated responsible party (unreliable)
    suspected_character_id = Column(Integer, ForeignKey("characters.id"))

    detected_at = Column(DateTime(timezone=True), nullable=False, index=True)

class HangarSnapshot(Base):
    """Daily snapshots of hangar contents"""
    __tablename__ = "hangar_snapshots"

    id = Column(Integer, primary_key=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), index=True)

    snapshot_date = Column(Date, nullable=False, index=True)

    total_value = Column(BigInteger)
    total_items = Column(Integer)
    hangar_breakdown = Column(JSONB)  # {division_id: {items, value, volume}}

    top_items_by_value = Column(JSONB)  # [{type_id, quantity, value}]
```

### Implementation Complexity
**Difficulty**: Medium
**Estimated Effort**: 25-30 hours

**Challenges**:
1. **No Audit Logs**: ESI doesn't provide who accessed or moved items
2. **Change Detection**: Must diff snapshots to detect changes
3. **Attribution**: Cannot reliably determine which member made changes
4. **Data Volume**: Large corp hangars have thousands of items
5. **Multi-Location**: Items spread across many structures and stations

### Implementation Approach

**Backend**:
1. Regular snapshots of all corp hangar divisions
2. Diff algorithm to detect item additions/removals
3. Value tracking using market prices
4. Volume and capacity monitoring
5. Search and filter capabilities across all locations

**Frontend**:
1. Hangar browser with division selector
2. Item search across all locations
3. Value tracking charts over time
4. Change log viewer (detected changes only)
5. Capacity warnings for full divisions
6. Export capabilities for inventory reports

**Celery Tasks**:
- `sync_corporation_hangars`: Every 6 hours, snapshot all hangars
- `detect_hangar_changes`: After each sync, diff with previous snapshot
- `calculate_hangar_values`: Daily value recalculation with updated prices

### User Value
**MEDIUM-LOW** - Useful for corp logistics, but lack of audit logs limits usefulness for security.

---

## Feature 7: Skill Plan Optimizer

### Overview
Intelligent skill planning with training time optimization, prerequisite resolution, and multi-character queue management.

### ESI Endpoints Required
- **Character Skills**: `/characters/{character_id}/skills/` (requires `esi-skills.read_skills.v1`)
- **Skill Queue**: `/characters/{character_id}/skillqueue/` (requires `esi-skills.read_skillqueue.v1`)
- **Character Attributes**: `/characters/{character_id}/attributes/` (requires `esi-skills.read_skills.v1`)
- **Universe Types**: `/universe/types/{type_id}/` (skill information)

### Data Models

```python
# backend/app/models/skill_planner.py

class SkillPlan(Base):
    """Skill training plans"""
    __tablename__ = "skill_plans"

    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey("characters.id"), index=True)

    plan_name = Column(String(255), nullable=False)
    description = Column(Text)

    # Training goals
    target_ship_type_ids = Column(ARRAY(Integer))  # Ships to fly
    target_activity = Column(String(50))  # "pvp", "mining", "industry", "exploration"

    # Stats
    total_skills = Column(Integer, default=0)
    total_skillpoints = Column(BigInteger, default=0)
    estimated_training_time_days = Column(Float)

    # Status
    status = Column(String(20), default="draft")  # draft, active, completed
    priority = Column(Integer, default=0)  # Higher = more important

    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True))

class SkillPlanEntry(Base):
    """Individual skills in a plan"""
    __tablename__ = "skill_plan_entries"

    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("skill_plans.id"), index=True)

    skill_type_id = Column(Integer, nullable=False)
    skill_name = Column(String(255), nullable=False)

    current_level = Column(Integer, default=0)  # 0-5
    target_level = Column(Integer, nullable=False)  # 1-5

    # Training requirements
    primary_attribute = Column(String(50))  # Intelligence, Memory, etc.
    secondary_attribute = Column(String(50))
    rank = Column(Integer)  # Skill rank/multiplier

    skillpoints_required = Column(BigInteger)
    training_time_seconds = Column(BigInteger)

    # Dependencies
    prerequisite_skills = Column(JSONB)  # [{skill_id, level}]
    blocks_skills = Column(ARRAY(Integer))  # Skills that depend on this

    # Ordering
    position = Column(Integer, nullable=False)  # Order in plan
    is_completed = Column(Boolean, default=False)

class SkillPlanTemplate(Base):
    """Pre-made skill plan templates"""
    __tablename__ = "skill_plan_templates"

    id = Column(Integer, primary_key=True)

    template_name = Column(String(255), nullable=False, unique=True)
    category = Column(String(50))  # "Ships", "Industry", "Combat", etc.
    description = Column(Text)

    # Target
    target_ship_type_id = Column(Integer)  # If for a specific ship
    target_ship_name = Column(String(255))

    # Skills list
    skills = Column(JSONB)  # [{skill_id, level, description}]

    # Metadata
    difficulty = Column(String(20))  # "beginner", "intermediate", "advanced"
    estimated_days = Column(Float)
    total_skillpoints = Column(BigInteger)

    is_public = Column(Boolean, default=True)
    created_by_character_id = Column(Integer, ForeignKey("characters.id"))

class SkillOptimizationResult(Base):
    """Optimization results for skill plans"""
    __tablename__ = "skill_optimization_results"

    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("skill_plans.id"), index=True)

    optimization_type = Column(String(50))  # "time", "prerequisites", "attributes"

    # Results
    optimized_order = Column(JSONB)  # [{skill_id, level, position}]
    time_saved_days = Column(Float)
    recommended_remap = Column(JSONB)  # {intelligence, memory, perception, willpower, charisma}

    calculated_at = Column(DateTime(timezone=True), nullable=False)
```

### Implementation Complexity
**Difficulty**: High
**Estimated Effort**: 45-60 hours

**Challenges**:
1. **Dependency Resolution**: Complex prerequisite chains need graph algorithms
2. **Time Optimization**: Calculate optimal training order based on attributes
3. **Remap Calculation**: Suggest optimal attribute remaps for plans
4. **Multi-Character**: Compare training across multiple characters
5. **Implant Integration**: Factor in implants and boosters
6. **Dynamic Updates**: Queue changes affect plan ordering

### Implementation Approach

**Backend**:
1. Skill dependency graph builder from EVE SDE
2. Training time calculator with attribute bonuses
3. Prerequisite resolver (topological sort)
4. Optimization algorithms:
   - Minimize total training time
   - Maximize SP/day efficiency
   - Optimal remap suggestions
5. Template library for common skill plans
6. Export to EVEMon format

**Frontend**:
1. Drag-and-drop skill plan builder
2. Skill search with filtering by category
3. Visual prerequisite tree display
4. Training time calculator with remap simulation
5. Multi-character comparison view
6. Plan templates library with categories
7. Export/import functionality
8. Queue integration (add to game queue)

**Celery Tasks**:
- `optimize_skill_plan`: Calculate optimal training order
- `calculate_plan_prerequisites`: Resolve all dependencies
- `update_plan_progress`: Track completed skills from queue updates

### User Value
**HIGH** - Essential for all players planning character progression. Strong ESI support and high automation potential.

---

## Feature 8: Market Trading Bot Integration

### Overview
Automated market trading assistant with price alerts, margin tracking, and trade opportunity detection.

### ESI Endpoints Required
- **Market Orders**: `/markets/{region_id}/orders/` (public data)
- **Character Orders**: `/characters/{character_id}/orders/` (requires `esi-markets.read_character_orders.v1`)
- **Historical Prices**: `/markets/{region_id}/history/`
- **Wallet Journal**: `/characters/{character_id}/wallet/journal/`
- **Wallet Transactions**: `/characters/{character_id}/wallet/transactions/`

### Data Models

```python
# backend/app/models/trading_bot.py

class TradingStrategy(Base):
    """Trading bot strategies"""
    __tablename__ = "trading_strategies"

    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey("characters.id"), index=True)

    strategy_name = Column(String(255), nullable=False)
    strategy_type = Column(String(50))  # "station_trading", "arbitrage", "margin_trading"

    # Parameters
    max_buy_price = Column(BigInteger)
    min_sell_price = Column(BigInteger)
    target_margin_percent = Column(Float)  # Minimum profit margin
    max_investment_per_item = Column(BigInteger)

    # Item filters
    item_type_ids = Column(ARRAY(Integer))  # Specific items to trade
    item_categories = Column(ARRAY(Integer))  # Item categories
    min_daily_volume = Column(Integer)  # Minimum market activity

    # Locations
    trade_hub_ids = Column(ARRAY(BigInteger))  # Stations/structures

    # Status
    is_active = Column(Boolean, default=False)
    auto_update_orders = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), nullable=False)

class TradingOpportunity(Base):
    """Detected trading opportunities"""
    __tablename__ = "trading_opportunities"

    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey("trading_strategies.id"), index=True)

    item_type_id = Column(Integer, nullable=False, index=True)
    item_name = Column(String(255))

    # Opportunity details
    opportunity_type = Column(String(50))  # "buy_undercut", "sell_relist", "arbitrage"

    current_buy_price = Column(BigInteger)
    recommended_buy_price = Column(BigInteger)
    current_sell_price = Column(BigInteger)
    recommended_sell_price = Column(BigInteger)

    estimated_margin = Column(BigInteger)
    estimated_margin_percent = Column(Float)
    estimated_daily_volume = Column(Integer)

    # Competition
    buy_order_count = Column(Integer)
    sell_order_count = Column(Integer)

    # Timing
    detected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True))

    # Action tracking
    action_taken = Column(String(50))  # "order_placed", "ignored", "snoozed"
    order_id = Column(BigInteger)  # If order was placed

class TradingPerformance(Base):
    """Trading performance metrics"""
    __tablename__ = "trading_performance"

    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey("characters.id"), index=True)
    strategy_id = Column(Integer, ForeignKey("trading_strategies.id"))

    # Time period
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False)

    # Volume
    total_buy_volume = Column(BigInteger, default=0)
    total_sell_volume = Column(BigInteger, default=0)
    items_traded = Column(Integer, default=0)

    # Profit
    gross_profit = Column(BigInteger, default=0)
    fees_paid = Column(BigInteger, default=0)
    taxes_paid = Column(BigInteger, default=0)
    net_profit = Column(BigInteger, default=0)

    # Efficiency
    average_margin_percent = Column(Float)
    roi_percent = Column(Float)  # Return on investment
    isk_per_hour = Column(BigInteger)

    # Best trades
    best_trade_profit = Column(BigInteger)
    best_trade_item_id = Column(Integer)

class PriceAlert(Base):
    """Price alerts for items"""
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey("characters.id"), index=True)

    item_type_id = Column(Integer, nullable=False, index=True)
    item_name = Column(String(255))

    region_id = Column(Integer, nullable=False)

    # Alert conditions
    alert_type = Column(String(50))  # "price_above", "price_below", "margin_above"
    threshold_value = Column(BigInteger)

    # Current state
    current_value = Column(BigInteger)
    is_triggered = Column(Boolean, default=False, index=True)
    triggered_at = Column(DateTime(timezone=True))

    # Notifications
    notification_sent = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
```

### Implementation Complexity
**Difficulty**: Very High
**Estimated Effort**: 60-80 hours

**Challenges**:
1. **Real-time Pricing**: Need frequent market updates for accurate data
2. **Order Management**: Cannot auto-place orders via ESI (read-only API)
3. **Competition Detection**: Analyze order books for undercutting
4. **Multi-Hub Trading**: Track prices across multiple stations
5. **Profit Calculation**: Complex with taxes, broker fees, relist costs
6. **Rate Limiting**: Heavy market API usage risks ESI bans
7. **Legal Concerns**: Automated trading may violate EULA (user must confirm all actions)

### Implementation Approach

**Backend**:
1. Market scanner for configured items across trade hubs
2. Opportunity detection algorithms:
   - Buy/sell spread analysis
   - Undercut detection
   - Cross-region arbitrage
   - Volume trend analysis
3. Profit calculator with fees and taxes
4. Performance tracking with ROI calculations
5. **IMPORTANT**: User confirmation required for all actions (ESI is read-only, can't auto-place orders)

**Frontend**:
1. Trading dashboard with active strategies
2. Opportunity feed with recommended actions
3. One-click order copying (to EVE game client)
4. Performance charts with profit/loss over time
5. Item watchlist with price alerts
6. Strategy builder with filters and parameters
7. Historical trade log with transaction details

**Celery Tasks**:
- `scan_market_opportunities`: Every 5 minutes, scan markets for configured strategies
- `update_trading_performance`: Hourly calculation of profits from wallet
- `check_price_alerts`: Every 10 minutes, check alert conditions

### User Value
**MEDIUM-LOW** - Useful for traders, but ESI limitations mean cannot fully automate. Legal/EULA concerns require careful implementation.

---

## Implementation Priority & Roadmap

### Phase 8A (High Priority - 60-85 hours)
1. **Corporation Mining Ledger Analytics** (25-35 hours)
   - Full ESI support
   - High corp value
   - Clear use case

2. **Skill Plan Optimizer** (45-60 hours)
   - High player value
   - Full ESI support
   - Complex but rewarding

**Deliverables**: Mining analytics dashboard, skill planner with optimization

---

### Phase 8B (Medium Priority - 55-75 hours)
3. **Asset Safety Tracking** (15-20 hours)
   - Good ESI support
   - Clear value proposition
   - Relatively simple

4. **Wormhole Tracking** (40-50 hours)
   - Limited ESI support
   - High value for WH corps
   - Complex chain mapping

5. **POCOs** (12-18 hours)
   - Limited ESI support
   - Narrow use case
   - Simple implementation

**Deliverables**: Asset safety dashboard, wormhole mapper, POCO manager

---

### Phase 8C (Low Priority - 95-130 hours)
6. **Corporation Hangar Management** (25-30 hours)
   - Limited audit capabilities
   - Medium value

7. **Abyssal Deadspace Statistics** (30-40 hours)
   - No ESI support
   - Manual tracking burden

8. **Market Trading Bot** (60-80 hours)
   - ESI limitations
   - EULA concerns
   - Cannot automate

**Deliverables**: Hangar browser, abyssal tracker, trading assistant

---

## Technical Architecture Considerations

### Database Impact
- **New Tables**: ~35 tables across all features
- **Indexes**: Heavy indexing on character_id, date ranges, type_ids
- **JSONB Usage**: Extensive for flexible data structures
- **Partitioning**: Consider partitioning for mining_ledger_entries, hangar_items

### API Performance
- **Caching**: Redis caching for market data, skill info
- **Rate Limiting**: Careful ESI usage tracking across features
- **Pagination**: Required for large datasets (mining ledger, hangar items)
- **Background Jobs**: Heavy use of Celery for data syncing

### Frontend Complexity
- **Visualizations**: D3.js for skill trees, wormhole maps
- **Real-time**: WebSocket integration for live updates
- **Data Tables**: Advanced sorting, filtering, pagination
- **Mobile Support**: Responsive design for all features

### Third-Party Integration
- **Wormhole Mappers**: Tripwire, Pathfinder API integration
- **EVEMon**: Export format support for skill plans
- **Market Tools**: EVE Tycoon, EVE Marketer API consideration

---

## Risk Assessment

### High Risk
- **Market Trading Bot**: EULA violation risk if automated
- **Wormhole Tracking**: Limited ESI = heavy manual input

### Medium Risk
- **Skill Plan Optimizer**: Complex algorithms may have edge cases
- **Mining Analytics**: Large data volume performance concerns

### Low Risk
- **Asset Safety**: Well-defined ESI endpoints
- **POCOs**: Simple data model and sync

---

## Conclusion

This research document provides a comprehensive foundation for implementing 8 advanced features. The recommended approach is to implement in phases based on priority:

1. **Start with Phase 8A** (Mining + Skills) for maximum user value
2. **Add Phase 8B** (Asset Safety, Wormholes, POCOs) for feature breadth
3. **Consider Phase 8C** based on user demand and resources

Each feature is designed to integrate seamlessly with existing Phase 1-7 architecture, following established patterns for models, API endpoints, Celery tasks, and frontend components.

**Total Estimated Effort**: 210-290 hours for all 8 features
**Recommended First Implementation**: Corporation Mining Ledger Analytics (25-35 hours)

---

**End of Research Document**
