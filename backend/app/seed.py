"""
seed.py — Populate the pokemon, pokemon_types tables from PokéAPI.

Usage:
    python -m app.seed              # via docker compose --profile seed run --rm seeder
    python backend/app/seed.py      # direct (set DATABASE_URL in env)

Environment variables:
    DATABASE_URL      — postgres connection string
    POKEAPI_BASE_URL  — defaults to https://pokeapi.co/api/v2
    GENERATION_LIMIT  — highest generation to seed (default: 9)
"""

import asyncio
import logging
import os
import sys

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ["DATABASE_URL"].replace(
    "postgresql://", "postgresql+asyncpg://"
)
POKEAPI_BASE = os.getenv("POKEAPI_BASE_URL", "https://pokeapi.co/api/v2")
GENERATION_LIMIT = int(os.getenv("GENERATION_LIMIT", "9"))

# PokéAPI generation → national dex range
GENERATION_RANGES = {
    1: (1, 151),
    2: (152, 251),
    3: (252, 386),
    4: (387, 493),
    5: (494, 649),
    6: (650, 721),
    7: (722, 809),
    8: (810, 905),
    9: (906, 1025),
}

# ---------------------------------------------------------------------------
# DB setup
# ---------------------------------------------------------------------------
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_generation(pokemon_id: int) -> int:
    for gen, (lo, hi) in GENERATION_RANGES.items():
        if lo <= pokemon_id <= hi:
            return gen
    return 9  # fallback for edge cases


def get_evolution_stage(chain, target_name: str, stage: int = 1) -> int:
    """Recursively walk an evolution chain to find the stage of target_name."""
    if chain["species"]["name"] == target_name:
        return stage
    for evolution in chain.get("evolves_to", []):
        result = get_evolution_stage(evolution, target_name, stage + 1)
        if result:
            return result
    return 1  # default to basic if not found


async def fetch_json(client: httpx.AsyncClient, url: str) -> dict:
    response = await client.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


async def fetch_evolution_stage(client: httpx.AsyncClient, species_data: dict) -> int:
    try:
        chain_url = species_data["evolution_chain"]["url"]
        chain_data = await fetch_json(client, chain_url)
        return get_evolution_stage(chain_data["chain"], species_data["name"])
    except Exception as e:
        log.warning(f"Could not fetch evolution chain: {e}")
        return 1


# ---------------------------------------------------------------------------
# Core seeding logic
# ---------------------------------------------------------------------------
async def seed_pokemon(client: httpx.AsyncClient, pokemon_id: int):
    """Fetch a single Pokémon from PokéAPI and upsert into the DB."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await _seed_pokemon_inner(session, client, pokemon_id)
 
 
async def _seed_pokemon_inner(session: AsyncSession, client: httpx.AsyncClient, pokemon_id: int):
    # Skip if already seeded
    result = await session.execute(
        text("SELECT id FROM pokemon WHERE id = :id"), {"id": pokemon_id}
    )
    if result.fetchone():
        log.debug(f"Pokémon #{pokemon_id} already exists, skipping.")
        return
 
    # Fetch base data
    try:
        poke_data = await fetch_json(client, f"{POKEAPI_BASE}/pokemon/{pokemon_id}")
        species_data = await fetch_json(client, f"{POKEAPI_BASE}/pokemon-species/{pokemon_id}")
    except httpx.HTTPStatusError as e:
        log.warning(f"Skipping #{pokemon_id}: {e}")
        return
 
    name = poke_data["name"]
    display_name = name.replace("-", " ").title()
    generation = get_generation(pokemon_id)
    is_legendary = species_data.get("is_legendary", False)
    is_mythical = species_data.get("is_mythical", False)
    evolution_stage = await fetch_evolution_stage(client, species_data)
 
    sprites = poke_data.get("sprites", {})
    sprite_url = sprites.get("front_default")
    sprite_shiny_url = sprites.get("front_shiny")
 
    types = [
        {"slot": t["slot"], "type": t["type"]["name"]}
        for t in poke_data.get("types", [])
    ]
 
    # Insert pokemon row
    await session.execute(
        text("""
            INSERT INTO pokemon
                (id, name, display_name, generation, is_legendary, is_mythical,
                 evolution_stage, sprite_url, sprite_shiny_url)
            VALUES
                (:id, :name, :display_name, :generation, :is_legendary, :is_mythical,
                 :evolution_stage, :sprite_url, :sprite_shiny_url)
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id": pokemon_id,
            "name": name,
            "display_name": display_name,
            "generation": generation,
            "is_legendary": is_legendary,
            "is_mythical": is_mythical,
            "evolution_stage": min(evolution_stage, 3),  # cap at 3
            "sprite_url": sprite_url,
            "sprite_shiny_url": sprite_shiny_url,
        },
    )
 
    # Insert types
    for t in types:
        await session.execute(
            text("""
                INSERT INTO pokemon_types (pokemon_id, type, slot)
                VALUES (:pokemon_id, :type, :slot)
                ON CONFLICT DO NOTHING
            """),
            {"pokemon_id": pokemon_id, "type": t["type"], "slot": t["slot"]},
        )
 
    log.info(f"Seeded #{pokemon_id} {display_name} (gen {generation}, stage {evolution_stage})")

async def run_seed():
    max_id = GENERATION_RANGES[GENERATION_LIMIT][1]
    ids_to_seed = list(range(1, max_id + 1))
 
    log.info(f"Seeding generations 1–{GENERATION_LIMIT} ({len(ids_to_seed)} Pokémon)...")
 
    async with httpx.AsyncClient() as client:
        # Each seed_pokemon opens its own session — safe to gather concurrently
        batch_size = 20
        for i in range(0, len(ids_to_seed), batch_size):
            batch = ids_to_seed[i : i + batch_size]
            tasks = [seed_pokemon(client, pid) for pid in batch]
            await asyncio.gather(*tasks)
            log.info(f"Committed batch {i // batch_size + 1} / {-(-len(ids_to_seed) // batch_size)}")
 
    log.info("Seeding complete.")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if "DATABASE_URL" not in os.environ:
        log.error("DATABASE_URL environment variable is not set.")
        sys.exit(1)
    asyncio.run(run_seed())