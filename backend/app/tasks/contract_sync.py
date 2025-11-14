"""
Contract sync tasks

Syncs character and corporation contracts from ESI
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import asyncio

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.character import Character
from app.models.eve_token import EveToken
from app.models.contract import Contract, ContractItem
from app.services.esi_client import esi_client, ESIError, ESIRateLimitError

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async functions in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_character_contracts(self, character_id: int):
    """
    Sync contracts for a character from ESI

    Args:
        character_id: EVE character ID
    """
    db: Session = SessionLocal()

    try:
        # Find valid token
        now = datetime.now(timezone.utc)
        token = db.query(EveToken).filter(
            and_(
                EveToken.character_id == character_id,
                EveToken.expires_at > now,
                EveToken.scope.contains("esi-contracts.read_character_contracts.v1"),
            )
        ).first()

        if not token:
            logger.warning(f"No valid token found for character {character_id}")
            return {"success": False, "error": "No valid token found"}

        from app.core.encryption import encryption
        access_token = encryption.decrypt(token.access_token_encrypted)

        # Get character
        character = db.query(Character).filter(
            Character.character_id == character_id
        ).first()

        if not character:
            logger.warning(f"Character {character_id} not found")
            return {"success": False, "error": "Character not found"}

        # Fetch contracts
        contracts_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/contracts/",
                access_token=access_token,
            )
        )

        logger.info(f"Fetched {len(contracts_data)} contracts for character {character_id}")

        synced_count = 0

        for contract_data in contracts_data:
            contract_id = contract_data.get("contract_id")

            # Check if contract already exists
            existing = db.query(Contract).filter(
                Contract.contract_id == contract_id
            ).first()

            if existing:
                # Update existing contract
                existing.status = contract_data.get("status", "unknown")
                existing.acceptor_id = contract_data.get("acceptor_id")
                existing.date_accepted = (
                    datetime.fromisoformat(contract_data.get("date_accepted", "").replace("Z", "+00:00"))
                    if contract_data.get("date_accepted")
                    else None
                )
                existing.date_completed = (
                    datetime.fromisoformat(contract_data.get("date_completed", "").replace("Z", "+00:00"))
                    if contract_data.get("date_completed")
                    else None
                )
            else:
                # Create new contract
                contract = Contract(
                    character_id=character.id,
                    contract_id=contract_id,
                    issuer_id=contract_data.get("issuer_id"),
                    issuer_corporation_id=contract_data.get("issuer_corporation_id"),
                    assignee_id=contract_data.get("assignee_id"),
                    acceptor_id=contract_data.get("acceptor_id"),
                    type=contract_data.get("type", "unknown"),
                    availability=contract_data.get("availability", "unknown"),
                    status=contract_data.get("status", "unknown"),
                    title=contract_data.get("title"),
                    for_corporation=contract_data.get("for_corporation", False),
                    price=contract_data.get("price"),
                    reward=contract_data.get("reward"),
                    collateral=contract_data.get("collateral"),
                    buyout=contract_data.get("buyout"),
                    volume=contract_data.get("volume"),
                    date_issued=datetime.fromisoformat(
                        contract_data.get("date_issued", "").replace("Z", "+00:00")
                    ),
                    date_expired=datetime.fromisoformat(
                        contract_data.get("date_expired", "").replace("Z", "+00:00")
                    ),
                    date_accepted=(
                        datetime.fromisoformat(contract_data.get("date_accepted", "").replace("Z", "+00:00"))
                        if contract_data.get("date_accepted")
                        else None
                    ),
                    date_completed=(
                        datetime.fromisoformat(contract_data.get("date_completed", "").replace("Z", "+00:00"))
                        if contract_data.get("date_completed")
                        else None
                    ),
                    days_to_complete=contract_data.get("days_to_complete"),
                    start_location_id=contract_data.get("start_location_id"),
                    end_location_id=contract_data.get("end_location_id"),
                )
                db.add(contract)
                synced_count += 1

                # Fetch contract items
                try:
                    items_data = run_async(
                        esi_client.request(
                            "GET",
                            f"/characters/{character_id}/contracts/{contract_id}/items/",
                            access_token=access_token,
                        )
                    )

                    for item_data in items_data:
                        item = ContractItem(
                            contract_id=contract_id,
                            record_id=item_data.get("record_id"),
                            type_id=item_data.get("type_id"),
                            quantity=item_data.get("quantity", 0),
                            is_included=item_data.get("is_included", True),
                            is_singleton=item_data.get("is_singleton", False),
                            raw_quantity=item_data.get("raw_quantity"),
                        )
                        db.add(item)

                except ESIError as e:
                    logger.warning(f"Failed to fetch items for contract {contract_id}: {e}")

        db.commit()

        logger.info(f"Synced {synced_count} new contracts for character {character_id}")
        return {"success": True, "synced": synced_count}

    except ESIRateLimitError as e:
        logger.warning(f"Rate limit hit for character {character_id}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing contracts for character {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
