"""
test_models.py — Tests for SQLAlchemy ORM models.
Verifies relationships, constraints, and defaults behave as expected.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import (
    Matchup,
    Pokemon,
    PokemonStatus,
    PokemonType,
    PokemonTypeEnum,
    Round,
    Session,
    SessionFilter,
    SessionPokemon,
    SessionStatus,
)


# ---------------------------------------------------------------------------
# Pokemon model
# ---------------------------------------------------------------------------
class TestPokemonModel:
    async def test_create_pokemon(self, db):
        p = Pokemon(
            id=1, name="bulbasaur", display_name="Bulbasaur",
            generation=1, evolution_stage=1,
            is_legendary=False, is_mythical=False,
        )
        db.add(p)
        await db.commit()

        result = await db.get(Pokemon, 1)
        assert result.name == "bulbasaur"
        assert result.display_name == "Bulbasaur"
        assert result.is_legendary is False

    async def test_pokemon_defaults(self, db):
        p = Pokemon(id=2, name="ivysaur", display_name="Ivysaur", generation=1, evolution_stage=2)
        db.add(p)
        await db.commit()

        result = await db.get(Pokemon, 2)
        assert result.is_legendary is False
        assert result.is_mythical is False
        assert result.created_at is not None

    async def test_pokemon_unique_name(self, db):
        db.add(Pokemon(id=1, name="bulbasaur", display_name="Bulbasaur", generation=1, evolution_stage=1))
        db.add(Pokemon(id=2, name="bulbasaur", display_name="Bulbasaur", generation=1, evolution_stage=1))
        with pytest.raises(IntegrityError):
            await db.commit()

    async def test_pokemon_type_relationship(self, seeded_db):
        result = await seeded_db.execute(
            select(Pokemon).where(Pokemon.name == "bulbasaur")
        )
        bulbasaur = result.scalar_one()
        await seeded_db.refresh(bulbasaur, ["types"])
        type_names = [t.type for t in bulbasaur.types]
        assert PokemonTypeEnum.grass in type_names
        assert PokemonTypeEnum.poison in type_names

    async def test_legendary_flag(self, seeded_db):
        result = await seeded_db.execute(
            select(Pokemon).where(Pokemon.is_legendary == True)
        )
        legendaries = result.scalars().all()
        names = [p.name for p in legendaries]
        assert "articuno" in names
        assert "zapdos" in names
        assert "moltres" in names
        assert "bulbasaur" not in names

    async def test_mythical_flag(self, seeded_db):
        result = await seeded_db.execute(
            select(Pokemon).where(Pokemon.is_mythical == True)
        )
        mythicals = result.scalars().all()
        assert len(mythicals) == 1
        assert mythicals[0].name == "mew"


# ---------------------------------------------------------------------------
# PokemonType model
# ---------------------------------------------------------------------------
class TestPokemonTypeModel:
    async def test_type_slot_constraint(self, db):
        db.add(Pokemon(id=1, name="test", display_name="Test", generation=1, evolution_stage=1))
        await db.flush()
        db.add(PokemonType(pokemon_id=1, type=PokemonTypeEnum.fire, slot=3))
        with pytest.raises(IntegrityError):
            await db.commit()

    async def test_dual_types(self, seeded_db):
        result = await seeded_db.execute(
            select(PokemonType).where(PokemonType.pokemon_id == 6)  # charizard
        )
        types = result.scalars().all()
        assert len(types) == 2
        slots = {t.slot for t in types}
        assert slots == {1, 2}


# ---------------------------------------------------------------------------
# Session model
# ---------------------------------------------------------------------------
class TestSessionModel:
    async def test_create_session(self, db):
        s = Session(target_remaining=5)
        db.add(s)
        await db.commit()

        result = await db.get(Session, s.id)
        assert result.status == SessionStatus.active
        assert result.target_remaining == 5
        assert result.completed_at is None

    async def test_session_status_transitions(self, db):
        s = Session(target_remaining=3)
        db.add(s)
        await db.commit()

        s.status = SessionStatus.completed
        await db.commit()

        result = await db.get(Session, s.id)
        assert result.status == SessionStatus.completed

    async def test_session_filter_relationship(self, db):
        s = Session(target_remaining=3)
        db.add(s)
        await db.flush()

        db.add(SessionFilter(session_id=s.id, filter_key="generation", filter_value="1"))
        db.add(SessionFilter(session_id=s.id, filter_key="type", filter_value="fire"))
        await db.commit()

        result = await db.get(Session, s.id)
        await db.refresh(result, ["filters"])
        assert len(result.filters) == 2


# ---------------------------------------------------------------------------
# Round model
# ---------------------------------------------------------------------------
class TestRoundModel:
    async def test_create_round(self, db):
        s = Session(target_remaining=3)
        db.add(s)
        await db.flush()

        r = Round(session_id=s.id, round_number=1)
        db.add(r)
        await db.commit()

        result = await db.get(Round, r.id)
        assert result.round_number == 1
        assert result.completed_at is None

    async def test_unique_round_per_session(self, db):
        s = Session(target_remaining=3)
        db.add(s)
        await db.flush()

        db.add(Round(session_id=s.id, round_number=1))
        db.add(Round(session_id=s.id, round_number=1))
        with pytest.raises(IntegrityError):
            await db.commit()


# ---------------------------------------------------------------------------
# Matchup model
# ---------------------------------------------------------------------------
class TestMatchupModel:
    async def test_create_matchup(self, seeded_db):
        s = Session(target_remaining=3)
        seeded_db.add(s)
        await seeded_db.flush()

        r = Round(session_id=s.id, round_number=1)
        seeded_db.add(r)
        await seeded_db.flush()

        m = Matchup(
            round_id=r.id, session_id=s.id,
            pokemon_a_id=1, pokemon_b_id=4,
        )
        seeded_db.add(m)
        await seeded_db.commit()

        result = await seeded_db.get(Matchup, m.id)
        assert result.winner_id is None
        assert result.decided_at is None

    async def test_matchup_same_pokemon_constraint(self, seeded_db):
        s = Session(target_remaining=3)
        seeded_db.add(s)
        await seeded_db.flush()

        r = Round(session_id=s.id, round_number=1)
        seeded_db.add(r)
        await seeded_db.flush()

        seeded_db.add(Matchup(
            round_id=r.id, session_id=s.id,
            pokemon_a_id=1, pokemon_b_id=1,
        ))
        with pytest.raises(IntegrityError):
            await seeded_db.commit()
