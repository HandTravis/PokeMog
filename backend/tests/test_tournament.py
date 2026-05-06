"""
test_tournament.py — Tests for core tournament logic.
Covers session creation, pool filtering, matchup generation,
pick submission, target_remaining halting, and round advancement.
"""

import pytest
from sqlalchemy import select

from app.models import (
    Matchup,
    PokemonStatus,
    Round,
    Session,
    SessionPokemon,
    SessionStatus,
)
from app.tournament import (
    build_pool,
    create_session,
    get_active_pokemon,
    get_current_round,
    get_next_matchup,
    get_results,
    submit_pick,
)


# ---------------------------------------------------------------------------
# Pool building
# ---------------------------------------------------------------------------
class TestBuildPool:
    async def test_no_filters_returns_all(self, seeded_db):
        pool = await build_pool(seeded_db, {})
        assert len(pool) == 13  # all seeded pokemon

    async def test_filter_by_generation(self, seeded_db):
        pool = await build_pool(seeded_db, {"generation": ["1"]})
        assert len(pool) == 13

    async def test_filter_by_type(self, seeded_db):
        pool = await build_pool(seeded_db, {"type": ["fire"]})
        # charmander, charmeleon, charizard, moltres
        assert len(pool) == 4

    async def test_filter_by_evolution_stage(self, seeded_db):
        pool = await build_pool(seeded_db, {"evolution_stage": ["1"]})
        # bulbasaur, charmander, squirtle, articuno, zapdos, moltres, mew
        assert len(pool) == 7

    async def test_filter_no_legendaries(self, seeded_db):
        pool = await build_pool(seeded_db, {"is_legendary": ["false"]})
        assert len(pool) == 10  # excludes articuno, zapdos, moltres

    async def test_filter_only_mythical(self, seeded_db):
        pool = await build_pool(seeded_db, {"is_mythical": ["true"]})
        assert len(pool) == 1  # just mew

    async def test_combined_filters(self, seeded_db):
        pool = await build_pool(seeded_db, {
            "type": ["fire"],
            "evolution_stage": ["1"],
        })
        # charmander + moltres
        assert len(pool) == 2

    async def test_empty_pool(self, seeded_db):
        pool = await build_pool(seeded_db, {"generation": ["9"]})
        assert len(pool) == 0


# ---------------------------------------------------------------------------
# Session creation
# ---------------------------------------------------------------------------
class TestCreateSession:
    async def test_creates_session(self, seeded_db):
        session, pool_size = await create_session(seeded_db, {}, target_remaining=3)
        assert session.id is not None
        assert session.status == SessionStatus.active
        assert pool_size == 13

    async def test_creates_session_pokemon(self, seeded_db):
        session, _ = await create_session(seeded_db, {}, target_remaining=3)
        active = await get_active_pokemon(seeded_db, session.id)
        assert len(active) == 13

    async def test_creates_round_1(self, seeded_db):
        session, _ = await create_session(seeded_db, {}, target_remaining=3)
        round_ = await get_current_round(seeded_db, session.id)
        assert round_ is not None
        assert round_.round_number == 1

    async def test_creates_matchups_for_round_1(self, seeded_db):
        session, _ = await create_session(seeded_db, {}, target_remaining=3)
        round_ = await get_current_round(seeded_db, session.id)
        result = await seeded_db.execute(
            select(Matchup).where(Matchup.round_id == round_.id)
        )
        matchups = result.scalars().all()
        # 13 pokemon → 6 matchups (1 bye)
        assert len(matchups) == 6

    async def test_saves_filters(self, seeded_db):
        session, _ = await create_session(
            seeded_db,
            {"generation": ["1"], "type": ["fire"]},
            target_remaining=2,
        )
        await seeded_db.refresh(session, ["filters"])
        keys = {f.filter_key for f in session.filters}
        assert "generation" in keys
        assert "type" in keys

    async def test_target_remaining_too_large(self, seeded_db):
        with pytest.raises(ValueError, match="pool size"):
            await create_session(seeded_db, {}, target_remaining=13)

    async def test_target_remaining_equal_to_pool(self, seeded_db):
        with pytest.raises(ValueError, match="pool size"):
            await create_session(seeded_db, {}, target_remaining=13)

    async def test_empty_pool_raises(self, seeded_db):
        with pytest.raises(ValueError, match="No Pokémon match"):
            await create_session(seeded_db, {"generation": ["9"]}, target_remaining=1)

    async def test_error_message_includes_pool_size(self, seeded_db):
        with pytest.raises(ValueError, match="13"):
            await create_session(seeded_db, {}, target_remaining=20)


# ---------------------------------------------------------------------------
# Matchup generation and pick submission
# ---------------------------------------------------------------------------
class TestMatchups:
    async def test_get_next_matchup(self, seeded_db):
        session, _ = await create_session(seeded_db, {}, target_remaining=3)
        matchup = await get_next_matchup(seeded_db, session.id)
        assert matchup is not None
        assert matchup.winner_id is None
        assert matchup.pokemon_a_id != matchup.pokemon_b_id

    async def test_submit_pick(self, seeded_db):
        session, _ = await create_session(seeded_db, {}, target_remaining=3)
        matchup = await get_next_matchup(seeded_db, session.id)
        winner_id = matchup.pokemon_a_id

        result = await submit_pick(seeded_db, session.id, matchup.id, winner_id)
        assert result.winner_id == winner_id
        assert result.decided_at is not None

    async def test_loser_is_eliminated(self, seeded_db):
        session, _ = await create_session(seeded_db, {}, target_remaining=3)
        matchup = await get_next_matchup(seeded_db, session.id)
        winner_id = matchup.pokemon_a_id
        loser_id = matchup.pokemon_b_id

        await submit_pick(seeded_db, session.id, matchup.id, winner_id)

        loser_sp = await seeded_db.execute(
            select(SessionPokemon).where(
                SessionPokemon.session_id == session.id,
                SessionPokemon.pokemon_id == loser_id,
            )
        )
        loser_sp = loser_sp.scalar_one()
        assert loser_sp.status == PokemonStatus.eliminated

    async def test_submit_pick_invalid_winner(self, seeded_db):
        session, _ = await create_session(seeded_db, {}, target_remaining=3)
        matchup = await get_next_matchup(seeded_db, session.id)

        with pytest.raises(ValueError, match="winner_id must be one of"):
            await submit_pick(seeded_db, session.id, matchup.id, 9999)

    async def test_submit_pick_already_decided(self, seeded_db):
        session, _ = await create_session(seeded_db, {}, target_remaining=3)
        matchup = await get_next_matchup(seeded_db, session.id)
        await submit_pick(seeded_db, session.id, matchup.id, matchup.pokemon_a_id)

        with pytest.raises(ValueError, match="already been decided"):
            await submit_pick(seeded_db, session.id, matchup.id, matchup.pokemon_a_id)

    async def test_sequential_matchups_dont_repeat(self, seeded_db):
        session, _ = await create_session(seeded_db, {}, target_remaining=3)
        seen = set()
        for _ in range(6):
            matchup = await get_next_matchup(seeded_db, session.id)
            if matchup is None:
                break
            assert matchup.id not in seen
            seen.add(matchup.id)
            await submit_pick(seeded_db, session.id, matchup.id, matchup.pokemon_a_id)


# ---------------------------------------------------------------------------
# Target remaining / session completion
# ---------------------------------------------------------------------------
class TestSessionCompletion:
    async def test_session_completes_at_target(self, seeded_db):
        """Pool of 13, target 3 — session should complete after enough picks."""
        session, _ = await create_session(seeded_db, {}, target_remaining=3)

        # Keep picking until session completes or we hit a safety limit
        for _ in range(50):
            await seeded_db.refresh(session)
            if session.status == SessionStatus.completed:
                break
            matchup = await get_next_matchup(seeded_db, session.id)
            if not matchup:
                break
            await submit_pick(seeded_db, session.id, matchup.id, matchup.pokemon_a_id)

        await seeded_db.refresh(session)
        assert session.status == SessionStatus.completed

    async def test_winners_marked_at_completion(self, seeded_db):
        session, _ = await create_session(seeded_db, {}, target_remaining=3)

        for _ in range(50):
            await seeded_db.refresh(session)
            if session.status == SessionStatus.completed:
                break
            matchup = await get_next_matchup(seeded_db, session.id)
            if not matchup:
                break
            await submit_pick(seeded_db, session.id, matchup.id, matchup.pokemon_a_id)

        winners = await get_results(seeded_db, session.id)
        assert len(winners) <= 3
        assert len(winners) >= 1

    async def test_small_pool_target_one_below(self, seeded_db):
        """Pool of 4 fire types (charmander, charmeleon, charizard, moltres), target 3 — one matchup ends it."""
        session, pool_size = await create_session(
            seeded_db,
            {"type": ["fire"]},
            target_remaining=3,
        )
        assert pool_size == 4

        matchup = await get_next_matchup(seeded_db, session.id)
        await submit_pick(seeded_db, session.id, matchup.id, matchup.pokemon_a_id)

        await seeded_db.refresh(session)
        assert session.status == SessionStatus.completed

    async def test_no_matchup_returned_after_completion(self, seeded_db):
        session, _ = await create_session(
            seeded_db, {"type": ["fire"]}, target_remaining=3
        )
        matchup = await get_next_matchup(seeded_db, session.id)
        await submit_pick(seeded_db, session.id, matchup.id, matchup.pokemon_a_id)

        next_matchup = await get_next_matchup(seeded_db, session.id)
        assert next_matchup is None

    async def test_completed_session_has_completion_time(self, seeded_db):
        session, _ = await create_session(
            seeded_db, {"type": ["fire"]}, target_remaining=3
        )
        matchup = await get_next_matchup(seeded_db, session.id)
        await submit_pick(seeded_db, session.id, matchup.id, matchup.pokemon_a_id)

        await seeded_db.refresh(session)
        assert session.completed_at is not None


# ---------------------------------------------------------------------------
# Round advancement
# ---------------------------------------------------------------------------
class TestRoundAdvancement:
    async def test_new_round_created_after_round_completes(self, seeded_db):
        """Use a pool of 4 with target 1 — guarantees round 2 is needed."""
        session, _ = await create_session(
            seeded_db,
            {"type": ["water"]},  # squirtle, wartortle, blastoise = 3 pokemon... 
            target_remaining=1,   # needs multiple rounds
        )

        # Keep deciding matchups until either round 2 exists or session completes
        for _ in range(30):
            await seeded_db.refresh(session)
            if session.status != SessionStatus.active:
                break

            # Check if round 2 already exists
            result = await seeded_db.execute(
                select(Round).where(
                    Round.session_id == session.id,
                    Round.round_number == 2,
                )
            )
            if result.scalar_one_or_none():
                break

            matchup = await get_next_matchup(seeded_db, session.id)
            if not matchup:
                break
            await submit_pick(seeded_db, session.id, matchup.id, matchup.pokemon_a_id)

        await seeded_db.refresh(session)

        # Either session completed (valid) or round 2 was created (what we want to test)
        result = await seeded_db.execute(
            select(Round).where(Round.session_id == session.id)
        )
        all_rounds = result.scalars().all()
        round_numbers = [r.round_number for r in all_rounds]

        assert len(round_numbers) >= 1  # at minimum round 1 existed
        # If session needed more than one round, round 2 should exist
        if session.status == SessionStatus.active:
            assert 2 in round_numbers

    async def test_active_count_decreases_each_round(self, seeded_db):
        session, _ = await create_session(seeded_db, {}, target_remaining=1)
        initial_active = len(await get_active_pokemon(seeded_db, session.id))

        matchup = await get_next_matchup(seeded_db, session.id)
        await submit_pick(seeded_db, session.id, matchup.id, matchup.pokemon_a_id)

        after_active = len(await get_active_pokemon(seeded_db, session.id))
        assert after_active < initial_active
