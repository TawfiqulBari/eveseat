"""
Database models
"""
from app.models.user import User
from app.models.eve_token import EveToken
from app.models.character import Character
from app.models.killmail import Killmail
from app.models.universe import System, SystemJump, SystemActivity, UniverseType
from app.models.corporation import Corporation, CorporationMember, CorporationAsset, CorporationStructure
from app.models.market import MarketOrder, PriceHistory
from app.models.fleet import Fleet, FleetMember, Doctrine

# Character data models
from app.models.mail import Mail, MailLabel, MailingList
from app.models.wallet import WalletJournal, WalletTransaction
from app.models.contact import Contact, ContactLabel
from app.models.calendar import CalendarEvent, CalendarEventAttendee
from app.models.contract import Contract, ContractItem, ContractBid
from app.models.clone import Clone, ActiveImplant, JumpCloneHistory
from app.models.skill import Skill, SkillQueue, SkillPlan
from app.models.blueprint import Blueprint, BlueprintResearch
from app.models.planetary import Planet, PlanetPin, PlanetRoute, PlanetExtraction
from app.models.loyalty import LoyaltyPoint, LoyaltyOffer, LoyaltyTransaction
from app.models.industry import IndustryJob, IndustryFacility, IndustryActivity
from app.models.bookmark import Bookmark, BookmarkFolder
from app.models.fitting import Fitting, FittingAnalysis
from app.models.analytics import (
    ProfitLoss,
    MarketTrend,
    IndustryProfitability,
    PortfolioSnapshot,
    TradingOpportunity,
    ISKFlow
)
from app.models.alliance import Alliance, AllianceCorporation, AllianceContact
from app.models.war import War, WarAlly, WarKillmail
from app.models.sovereignty import SystemSovereignty, SovereigntyStructure, SovereigntyCampaign
from app.models.moon import MoonExtraction, Moon, MiningLedger
from app.models.incursion import Incursion, IncursionParticipation, IncursionStatistics
from app.models.structure import Structure, StructureVulnerability, StructureService
from app.models.faction_warfare import (
    FactionWarfareSystem,
    FactionWarfareStatistics,
    CharacterFactionWarfare,
    FactionWarfareLeaderboard,
    FactionWarfareSystemHistory
)

__all__ = [
    # Core models
    "User",
    "EveToken",
    "Character",
    "Killmail",
    # Universe models
    "System",
    "SystemJump",
    "SystemActivity",
    "UniverseType",
    # Corporation models
    "Corporation",
    "CorporationMember",
    "CorporationAsset",
    "CorporationStructure",
    # Market models
    "MarketOrder",
    "PriceHistory",
    # Fleet models
    "Fleet",
    "FleetMember",
    "Doctrine",
    # Character data models
    "Mail",
    "MailLabel",
    "MailingList",
    "WalletJournal",
    "WalletTransaction",
    "Contact",
    "ContactLabel",
    "CalendarEvent",
    "CalendarEventAttendee",
    "Contract",
    "ContractItem",
    "ContractBid",
    "Clone",
    "ActiveImplant",
    "JumpCloneHistory",
    "Skill",
    "SkillQueue",
    "SkillPlan",
    "Blueprint",
    "BlueprintResearch",
    "Planet",
    "PlanetPin",
    "PlanetRoute",
    "PlanetExtraction",
    "LoyaltyPoint",
    "LoyaltyOffer",
    "LoyaltyTransaction",
    "IndustryJob",
    "IndustryFacility",
    "IndustryActivity",
    "Bookmark",
    "BookmarkFolder",
    "Fitting",
    "FittingAnalysis",
    # Analytics models
    "ProfitLoss",
    "MarketTrend",
    "IndustryProfitability",
    "PortfolioSnapshot",
    "TradingOpportunity",
    "ISKFlow",
    # Advanced models
    "Alliance",
    "AllianceCorporation",
    "AllianceContact",
    "War",
    "WarAlly",
    "WarKillmail",
    "SystemSovereignty",
    "SovereigntyStructure",
    "SovereigntyCampaign",
    "MoonExtraction",
    "Moon",
    "MiningLedger",
    "Incursion",
    "IncursionParticipation",
    "IncursionStatistics",
    "Structure",
    "StructureVulnerability",
    "StructureService",
    "FactionWarfareSystem",
    "FactionWarfareStatistics",
    "CharacterFactionWarfare",
    "FactionWarfareLeaderboard",
    "FactionWarfareSystemHistory",
]

