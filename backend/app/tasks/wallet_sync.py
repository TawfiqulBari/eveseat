"""
Wallet sync tasks

Syncs character wallet journal and transactions from ESI
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
from app.models.wallet import WalletJournal, WalletTransaction
from app.services.esi_client import esi_client, ESIError, ESIRateLimitError
from app.websockets.publisher import event_publisher
from app.websockets.events import EventType

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
def sync_character_wallet(self, character_id: int):
    """
    Sync wallet journal and transactions for a character from ESI

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
                EveToken.scope.contains("esi-wallet.read_character_wallet.v1"),
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

        journal_synced = 0
        transactions_synced = 0

        # Sync wallet journal
        try:
            journal_data = run_async(
                esi_client.request(
                    "GET",
                    f"/characters/{character_id}/wallet/journal/",
                    access_token=access_token,
                )
            )

            logger.info(f"Fetched {len(journal_data)} journal entries for character {character_id}")

            for entry_data in journal_data:
                entry_id = entry_data.get("id")

                # Check if entry already exists
                existing = db.query(WalletJournal).filter(
                    WalletJournal.entry_id == entry_id
                ).first()

                if not existing:
                    entry = WalletJournal(
                        character_id=character.id,
                        entry_id=entry_id,
                        date=datetime.fromisoformat(
                            entry_data.get("date", "").replace("Z", "+00:00")
                        ),
                        ref_type=entry_data.get("ref_type", "unknown"),
                        amount=entry_data.get("amount", 0),
                        balance=entry_data.get("balance"),
                        description=entry_data.get("description", ""),
                        context_id=entry_data.get("context_id"),
                        context_id_type=entry_data.get("context_id_type"),
                        first_party_id=entry_data.get("first_party_id"),
                        second_party_id=entry_data.get("second_party_id"),
                        tax=entry_data.get("tax"),
                        tax_receiver_id=entry_data.get("tax_receiver_id"),
                        reason=entry_data.get("reason"),
                    )
                    db.add(entry)
                    journal_synced += 1

        except ESIError as e:
            logger.warning(f"Failed to sync wallet journal: {e}")

        # Sync wallet transactions
        try:
            transactions_data = run_async(
                esi_client.request(
                    "GET",
                    f"/characters/{character_id}/wallet/transactions/",
                    access_token=access_token,
                )
            )

            logger.info(f"Fetched {len(transactions_data)} transactions for character {character_id}")

            for trans_data in transactions_data:
                transaction_id = trans_data.get("transaction_id")

                # Check if transaction already exists
                existing = db.query(WalletTransaction).filter(
                    WalletTransaction.transaction_id == transaction_id
                ).first()

                if not existing:
                    transaction = WalletTransaction(
                        character_id=character.id,
                        transaction_id=transaction_id,
                        date=datetime.fromisoformat(
                            trans_data.get("date", "").replace("Z", "+00:00")
                        ),
                        type_id=trans_data.get("type_id"),
                        quantity=trans_data.get("quantity", 0),
                        unit_price=trans_data.get("unit_price", 0),
                        is_buy=trans_data.get("is_buy", False),
                        client_id=trans_data.get("client_id"),
                        location_id=trans_data.get("location_id"),
                        is_personal=trans_data.get("is_personal", True),
                        journal_ref_id=trans_data.get("journal_ref_id"),
                    )
                    db.add(transaction)
                    transactions_synced += 1

                    # Publish WebSocket event for new transaction
                    try:
                        event_publisher.publish_wallet_event(
                            character_id=character_id,
                            wallet_data={
                                "transaction_id": transaction_id,
                                "type_id": trans_data.get("type_id"),
                                "quantity": trans_data.get("quantity"),
                                "unit_price": float(trans_data.get("unit_price", 0)),
                                "is_buy": trans_data.get("is_buy", False),
                            },
                            event_type=EventType.WALLET_TRANSACTION,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to publish WebSocket event: {e}")

        except ESIError as e:
            logger.warning(f"Failed to sync wallet transactions: {e}")

        db.commit()

        logger.info(
            f"Synced {journal_synced} journal entries and {transactions_synced} transactions "
            f"for character {character_id}"
        )
        return {
            "success": True,
            "journal_synced": journal_synced,
            "transactions_synced": transactions_synced,
        }

    except ESIRateLimitError as e:
        logger.warning(f"Rate limit hit for character {character_id}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing wallet for character {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
