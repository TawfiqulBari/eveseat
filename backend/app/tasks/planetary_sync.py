"""
Planetary Interaction sync tasks

Syncs character planets from ESI
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
from app.models.planetary import Planet, PlanetPin, PlanetRoute, PlanetExtraction
from app.services.esi_client import esi_client, ESIError, ESIRateLimitError
from app.websockets.events import EventType
from app.websockets.publisher import EventPublisher

logger = logging.getLogger(__name__)
event_publisher = EventPublisher()


def run_async(coro):
    """Helper to run async functions in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_character_planets(self, character_id: int):
    """
    Sync planets for a character from ESI

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
                EveToken.scope.contains("esi-planets.manage_planets.v1"),
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

        # Fetch planets list
        planets_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/planets/",
                access_token=access_token,
            )
        )

        logger.info(f"Fetched {len(planets_data)} planets for character {character_id}")

        synced_count = 0

        for planet_data in planets_data:
            planet_id = planet_data.get("planet_id")

            # Check if planet already exists
            existing = db.query(Planet).filter(
                Planet.planet_id == planet_id
            ).first()

            if not existing:
                # Create new planet
                planet = Planet(
                    character_id=character.id,
                    planet_id=planet_id,
                    solar_system_id=planet_data.get("solar_system_id"),
                    planet_type=planet_data.get("planet_type", "unknown"),
                    owner_id=planet_data.get("owner_id", character_id),
                    upgrade_level=planet_data.get("upgrade_level", 0),
                    num_pins=planet_data.get("num_pins", 0),
                    last_update=datetime.fromisoformat(
                        planet_data.get("last_update", "").replace("Z", "+00:00")
                    ) if planet_data.get("last_update") else None,
                )
                db.add(planet)
                synced_count += 1
                db.flush()  # Get planet.id
            else:
                planet = existing
                planet.upgrade_level = planet_data.get("upgrade_level", 0)
                planet.num_pins = planet_data.get("num_pins", 0)
                planet.last_update = datetime.fromisoformat(
                    planet_data.get("last_update", "").replace("Z", "+00:00")
                ) if planet_data.get("last_update") else None

            # Fetch planet details (pins, routes)
            try:
                planet_detail = run_async(
                    esi_client.request(
                        "GET",
                        f"/characters/{character_id}/planets/{planet_id}/",
                        access_token=access_token,
                    )
                )

                # Delete existing pins and routes
                db.query(PlanetPin).filter(PlanetPin.planet_id == planet.id).delete()
                db.query(PlanetRoute).filter(PlanetRoute.planet_id == planet.id).delete()

                # Add pins
                if "pins" in planet_detail:
                    for pin_data in planet_detail["pins"]:
                        pin = PlanetPin(
                            planet_id=planet.id,
                            pin_id=pin_data.get("pin_id"),
                            type_id=pin_data.get("type_id"),
                            schematic_id=pin_data.get("schematic_id"),
                            latitude=pin_data.get("latitude"),
                            longitude=pin_data.get("longitude"),
                            install_time=(
                                datetime.fromisoformat(pin_data.get("install_time", "").replace("Z", "+00:00"))
                                if pin_data.get("install_time")
                                else None
                            ),
                            expiry_time=(
                                datetime.fromisoformat(pin_data.get("expiry_time", "").replace("Z", "+00:00"))
                                if pin_data.get("expiry_time")
                                else None
                            ),
                            product_type_id=pin_data.get("extractor_details", {}).get("product_type_id"),
                            cycle_time=pin_data.get("extractor_details", {}).get("cycle_time"),
                            quantity_per_cycle=pin_data.get("extractor_details", {}).get("qty_per_cycle"),
                            contents=pin_data.get("contents"),
                        )
                        db.add(pin)

                        # Track active extractions
                        if pin.expiry_time and pin.product_type_id:
                            # Check if extraction exists
                            ext_exists = db.query(PlanetExtraction).filter(
                                and_(
                                    PlanetExtraction.planet_id == planet_id,
                                    PlanetExtraction.pin_id == pin.pin_id,
                                )
                            ).first()

                            if not ext_exists:
                                extraction = PlanetExtraction(
                                    character_id=character.id,
                                    planet_id=planet_id,
                                    pin_id=pin.pin_id,
                                    product_type_id=pin.product_type_id,
                                    start_time=pin.install_time or datetime.now(timezone.utc),
                                    expiry_time=pin.expiry_time,
                                    cycle_time=pin.cycle_time,
                                    quantity_per_cycle=pin.quantity_per_cycle,
                                    status="active",
                                )
                                db.add(extraction)

                # Add routes
                if "routes" in planet_detail:
                    for route_data in planet_detail["routes"]:
                        route = PlanetRoute(
                            planet_id=planet.id,
                            route_id=route_data.get("route_id"),
                            source_pin_id=route_data.get("source_pin_id"),
                            destination_pin_id=route_data.get("destination_pin_id"),
                            content_type_id=route_data.get("content_type_id"),
                            quantity=route_data.get("quantity", 0),
                        )
                        db.add(route)

            except ESIError as e:
                logger.warning(f"Failed to fetch details for planet {planet_id}: {e}")

        db.commit()

        # Publish WebSocket event
        event_publisher.publish(
            "planetary",
            EventType.PLANETARY_UPDATE,
            {
                "character_id": character_id,
                "total_planets": len(planets_data),
                "synced": synced_count,
            },
        )

        logger.info(f"Synced {synced_count} new planets for character {character_id}")
        return {"success": True, "synced": synced_count}

    except ESIRateLimitError as e:
        logger.warning(f"Rate limit hit for character {character_id}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing planets for character {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
