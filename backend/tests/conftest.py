"""
conftest.py — Shared pytest fixtures for the PokéRanker test suite.

Uses an in-memory SQLite database for fast, isolated tests.
Each test gets a fresh DB with the schema applied and a small
set of seed Pokémon to work with.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models import Base, Pokemon, PokemonType, PokemonTypeEnum

# ---------------------------------------------------------------------------
# Test database — SQLite in-memory for speed and isolation
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create a fresh in-memory DB engine for each test."""
    _engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db(engine):
    """Provide a test DB session."""
    TestSessionLocal = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(engine):
    """
    Provide an async HTTP test client with the test DB injected.
    Overrides the get_db dependency so routes use the test database.
    """
    TestSessionLocal = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed fixtures — minimal Pokémon data for tests
# ---------------------------------------------------------------------------
def make_pokemon(
    id, name, generation=1, evolution_stage=1,
    is_legendary=False, is_mythical=False,
    types=None, sprite_url=None,
):
    """Helper to construct a Pokemon ORM object."""
    p = Pokemon(
        id=id,
        name=name,
        display_name=name.title(),
        generation=generation,
        evolution_stage=evolution_stage,
        is_legendary=is_legendary,
        is_mythical=is_mythical,
        sprite_url=sprite_url or f"https://example.com/{name}.png",
        sprite_shiny_url=None,
    )
    p.types = [
        PokemonType(pokemon_id=id, type=t, slot=i + 1)
        for i, t in enumerate(types or ["normal"])
    ]
    return p


@pytest_asyncio.fixture
async def seeded_db(db):
    """
    A DB session pre-populated with a small set of known Pokémon.
    Enough to cover tournament logic edge cases.
    """
    pokemon = [
        make_pokemon(1,  "bulbasaur",  generation=1, evolution_stage=1, types=["grass", "poison"]),
        make_pokemon(2,  "ivysaur",    generation=1, evolution_stage=2, types=["grass", "poison"]),
        make_pokemon(3,  "venusaur",   generation=1, evolution_stage=3, types=["grass", "poison"]),
        make_pokemon(4,  "charmander", generation=1, evolution_stage=1, types=["fire"]),
        make_pokemon(5,  "charmeleon", generation=1, evolution_stage=2, types=["fire"]),
        make_pokemon(6,  "charizard",  generation=1, evolution_stage=3, types=["fire", "flying"]),
        make_pokemon(7,  "squirtle",   generation=1, evolution_stage=1, types=["water"]),
        make_pokemon(8,  "wartortle",  generation=1, evolution_stage=2, types=["water"]),
        make_pokemon(9,  "blastoise",  generation=1, evolution_stage=3, types=["water"]),
        make_pokemon(144, "articuno", generation=1, evolution_stage=1, is_legendary=True, types=["ice", "flying"]),
        make_pokemon(145, "zapdos",   generation=1, evolution_stage=1, is_legendary=True, types=["electric", "flying"]),
        make_pokemon(146, "moltres",  generation=1, evolution_stage=1, is_legendary=True, types=["fire", "flying"]),
        make_pokemon(151, "mew",      generation=1, evolution_stage=1, is_mythical=True,  types=["psychic"]),
    ]
    for p in pokemon:
        db.add(p)
    await db.commit()
    yield db
