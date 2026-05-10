"""
tournament.py — Core tournament logic for PokéRanker.

Handles:
- Building the filtered Pokémon pool for a session
- Pairing Pokémon into matchups (with odd-one-out handling)
- Advancing winners between rounds
- Detecting round/session completion
"""

import random
from uuid import UUID

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Matchup,
    Pokemon,
    PokemonStatus,
    PokemonType,
    Round,
    Session,
    SessionFilter,
    SessionPokemon,
    SessionStatus,
)


# ---------------------------------------------------------------------------
# Pool building
# ---------------------------------------------------------------------------
async def build_pool(
    db: AsyncSession,
    filters: dict[str, list[str]],
) -> list[int]:
    """
    Return a list of pokemon IDs matching the given filters.

    filters example:
        {
            "generation": ["1", "2"],
            "type": ["fire", "water"],
            "evolution_stage": ["1"],
            "is_legendary": ["false"],
            "is_mythical": ["false"],
        }
    """
    query = select(Pokemon.id)

    if "generation" in filters:
        generations = [int(g) for g in filters["generation"]]
        query = query.where(Pokemon.generation.in_(generations))

    if "evolution_stage" in filters:
        stages = [int(s) for s in filters["evolution_stage"]]
        query = query.where(Pokemon.evolution_stage.in_(stages))

    if "is_legendary" in filters:
        val = filters["is_legendary"][0].lower() == "true"
        query = query.where(Pokemon.is_legendary == val)

    if "is_mythical" in filters:
        val = filters["is_mythical"][0].lower() == "true"
        query = query.where(Pokemon.is_mythical == val)

    if "type" in filters:
        # Pokemon must have at least one matching type
        query = query.where(
            Pokemon.id.in_(
                select(PokemonType.pokemon_id).where(
                    PokemonType.type.in_(filters["type"])
                )
            )
        )

    result = await db.execute(query)
    return [row[0] for row in result.fetchall()]


# ---------------------------------------------------------------------------
# Session creation
# ---------------------------------------------------------------------------
async def create_session(
    db: AsyncSession,
    filters: dict[str, list[str]],
    target_remaining: int,
) -> tuple[Session, int]:
    """
    Create a new session with the given filters and target_remaining.
    Returns (session, pool_size).
    Raises ValueError if target_remaining >= pool_size.
    """
    pool_ids = await build_pool(db, filters)
    pool_size = len(pool_ids)

    if pool_size == 0:
        raise ValueError("No Pokémon match the selected filters. Try broadening your search.")

    if target_remaining >= pool_size:
        raise ValueError(
            f"target_remaining ({target_remaining}) must be less than the total pool size "
            f"({pool_size} Pokémon match your filters). Try increasing your filters or reducing your target."
        )

    # Shuffle pool for randomness
    random.shuffle(pool_ids)

    # Create session
    session = Session(target_remaining=target_remaining)
    db.add(session)
    await db.flush()  # get session.id without committing

    # Save filters
    for key, values in filters.items():
        for value in values:
            db.add(SessionFilter(
                session_id=session.id,
                filter_key=key,
                filter_value=value,
            ))

    # Add Pokémon to session pool
    for pid in pool_ids:
        db.add(SessionPokemon(
            session_id=session.id,
            pokemon_id=pid,
            status=PokemonStatus.active,
        ))

    # Kick off round 1
    round_ = await _create_round(db, session.id, round_number=1)
    await _generate_round_matchups(db, session.id, round_=round_)
    await db.commit()
    await db.refresh(session)
    

    return session, pool_size


# ---------------------------------------------------------------------------
# Round management
# ---------------------------------------------------------------------------
async def _create_round(
    db: AsyncSession,
    session_id: UUID,
    round_number: int,
) -> Round:
    """Create a new round row for the session."""
    round_ = Round(session_id=session_id, round_number=round_number)
    db.add(round_)
    await db.flush()
    return round_


async def get_current_round(
    db: AsyncSession,
    session_id: UUID,
) -> Round | None:
    """Return the most recent incomplete round for a session."""
    result = await db.execute(
        select(Round)
        .where(
            and_(
                Round.session_id == session_id,
                Round.completed_at.is_(None),
            )
        )
        .order_by(Round.round_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_active_pokemon(
    db: AsyncSession,
    session_id: UUID,
) -> list[SessionPokemon]:
    """Return all active (non-eliminated) Pokémon in the session."""
    result = await db.execute(
        select(SessionPokemon).where(
            and_(
                SessionPokemon.session_id == session_id,
                SessionPokemon.status == PokemonStatus.active,
            )
        )
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Matchup generation
# ---------------------------------------------------------------------------
async def _generate_round_matchups(
    db: AsyncSession,
    session_id: UUID,
    round_: Round,
) -> None:
    """Pair all active Pokémon into matchups for the given round."""
    # Guard: don't generate matchups if they already exist for this round
    existing = await db.execute(
        select(Matchup).where(Matchup.round_id == round_.id).limit(1)
    )
    if existing.scalar_one_or_none():
        return

    active = await get_active_pokemon(db, session_id)
    pokemon_ids = [sp.pokemon_id for sp in active]
    random.shuffle(pokemon_ids)

    for i in range(0, len(pokemon_ids) - 1, 2):
        db.add(Matchup(
            round_id=round_.id,
            session_id=session_id,
            pokemon_a_id=pokemon_ids[i],
            pokemon_b_id=pokemon_ids[i + 1],
        ))

    await db.commit()


async def get_next_matchup(
    db: AsyncSession,
    session_id: UUID,
) -> Matchup | None:
    """
    Return the next undecided matchup for the session.
    If no undecided matchup exists, attempt to advance the round.
    Returns None if the session is complete.
    """
    # Check session is still active
    session = await db.get(Session, session_id)
    if not session or session.status != SessionStatus.active:
        return None

    # Find existing undecided matchup
    undecided = await _get_undecided_matchup(db, session_id)
    if undecided:
        return undecided

    # No undecided matchup — check if we need to advance
    current_round = await get_current_round(db, session_id)
    if not current_round:
        return None

    # Check if all matchups in the round are decided
    all_decided = await _round_is_decided(db, current_round.id)
    if not all_decided:
        # Round has undecided matchups but none returned above — shouldn't happen
        return None

    # Check for odd-one-out tiebreaker before closing the round
    tiebreaker = await _check_tiebreaker(db, session, current_round)
    if tiebreaker:
        return tiebreaker

    # Close the round and check for session completion
    complete = await _advance_round(db, session, current_round)
    if complete:
        return None

    # Get the next matchup from the new round
    return await _get_undecided_matchup(db, session_id)


async def _get_undecided_matchup(
    db: AsyncSession,
    session_id: UUID,
) -> Matchup | None:
    """Return the oldest undecided matchup in the current round."""
    result = await db.execute(
        select(Matchup)
        .join(Round, Matchup.round_id == Round.id)
        .where(
            and_(
                Matchup.session_id == session_id,
                Matchup.winner_id.is_(None),
                Round.completed_at.is_(None),
            )
        )
        .order_by(Matchup.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _round_is_decided(
    db: AsyncSession,
    round_id: int,
) -> bool:
    """Return True if all matchups in the round have a winner."""
    result = await db.execute(
        select(func.count())
        .select_from(Matchup)
        .where(
            and_(
                Matchup.round_id == round_id,
                Matchup.winner_id.is_(None),
            )
        )
    )
    return result.scalar() == 0


async def _check_tiebreaker(
    db: AsyncSession,
    session: Session,
    current_round: Round,
) -> Matchup | None:
    """
    If the round produced an odd number of winners and we're above
    target_remaining, create a tiebreaker matchup between the bye
    Pokémon and a random winner from this round.
    """
    # Get all matchups in this round
    result = await db.execute(
        select(Matchup).where(Matchup.round_id == current_round.id)
    )
    matchups = result.scalars().all()

    # No matchups yet means round just started — no tiebreaker needed
    if not matchups:
        return None

    winner_ids = [m.winner_id for m in matchups]
    loser_ids = [
        m.pokemon_b_id if m.winner_id == m.pokemon_a_id else m.pokemon_a_id
        for m in matchups
    ]

    # Find the active Pokémon not yet in any matchup this round (the bye)
    active = await get_active_pokemon(db, session.id)
    active_ids = {sp.pokemon_id for sp in active}
    paired_ids = set(winner_ids) | set(loser_ids)
    bye_ids = active_ids - paired_ids

    if not bye_ids:
        return None  # everyone was paired, no tiebreaker needed

    # We have a bye — create tiebreaker if above target_remaining
    active_count = len(active_ids)
    if active_count <= session.target_remaining:
        return None  # already at or below target, no tiebreaker needed

    bye_id = random.choice(list(bye_ids))
    opponent_id = random.choice(winner_ids)

    tiebreaker = Matchup(
        round_id=current_round.id,
        session_id=session.id,
        pokemon_a_id=bye_id,
        pokemon_b_id=opponent_id,
    )
    db.add(tiebreaker)
    await db.flush()
    return tiebreaker


# ---------------------------------------------------------------------------
# Round advancement
# ---------------------------------------------------------------------------
async def _advance_round(
    db: AsyncSession,
    session: Session,
    current_round: Round,
) -> bool:
    """
    Close the current round, eliminate losers, and either:
    - Complete the session if active Pokémon <= target_remaining
    - Start a new round otherwise

    Returns True if the session is now complete.
    """
    from datetime import datetime, timezone

    # Collect winners and losers from this round
    result = await db.execute(
        select(Matchup).where(Matchup.round_id == current_round.id)
    )
    matchups = result.scalars().all()

    winner_ids = set(m.winner_id for m in matchups)
    loser_ids = set()
    for m in matchups:
        loser = m.pokemon_b_id if m.winner_id == m.pokemon_a_id else m.pokemon_a_id
        loser_ids.add(loser)

    # Eliminate losers
    for sp in await get_active_pokemon(db, session.id):
        if sp.pokemon_id in loser_ids:
            sp.status = PokemonStatus.eliminated
            sp.round_eliminated = current_round.round_number

    # Close the round
    current_round.completed_at = datetime.now(timezone.utc)

    # Check active count after elimination
    remaining = await get_active_pokemon(db, session.id)
    # Re-fetch after status updates
    result = await db.execute(
        select(SessionPokemon).where(
            and_(
                SessionPokemon.session_id == session.id,
                SessionPokemon.status == PokemonStatus.active,
            )
        )
    )
    remaining = result.scalars().all()

    if len(remaining) <= session.target_remaining:
        # Session complete — mark all remaining as winners
        for sp in remaining:
            sp.status = PokemonStatus.winner
        session.status = SessionStatus.completed
        session.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return True

    # Start next round — shuffle remaining for randomness
    remaining_ids = [sp.pokemon_id for sp in remaining]
    random.shuffle(remaining_ids)
    next_round_number = current_round.round_number + 1

    next_round_ = await _create_round(
        db, session.id, round_number=next_round_number
    )
    await _generate_round_matchups(db, session.id, next_round_)
    # Pre-pair the next round's matchups lazily (done in get_next_matchup)
    await db.commit()
    return False


# ---------------------------------------------------------------------------
# Submitting a pick
# ---------------------------------------------------------------------------
async def submit_pick(
    db: AsyncSession,
    session_id: UUID,
    matchup_id: UUID,
    winner_id: int,
) -> Matchup:
    """
    Record the winner of a matchup.
    Raises ValueError on invalid input.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select, and_
    from app.models import SessionPokemon, PokemonStatus

    matchup = await db.get(Matchup, matchup_id)

    if not matchup:
        raise ValueError("Matchup not found.")
    if matchup.session_id != session_id:
        raise ValueError("Matchup does not belong to this session.")
    if matchup.winner_id is not None:
        raise ValueError("Matchup has already been decided.")
    if winner_id not in (matchup.pokemon_a_id, matchup.pokemon_b_id):
        raise ValueError("winner_id must be one of the two Pokémon in this matchup.")

    matchup.winner_id = winner_id
    matchup.decided_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(matchup)


    # Eliminate the loser immediately
    loser_id = matchup.pokemon_b_id if winner_id == matchup.pokemon_a_id else matchup.pokemon_a_id
    loser_sp = await db.execute(
        select(SessionPokemon).where(
            and_(
                SessionPokemon.session_id == session_id,
                SessionPokemon.pokemon_id == loser_id,
            )
        )
    )
    loser_sp = loser_sp.scalar_one_or_none()
    if loser_sp:
        loser_sp.status = PokemonStatus.eliminated

    # Check if we've hit target_remaining after this elimination
    session = await db.get(Session, session_id)
    remaining = await db.execute(
        select(SessionPokemon).where(
            and_(
                SessionPokemon.session_id == session_id,
                SessionPokemon.status == PokemonStatus.active,
            )
        )
    )
    remaining = remaining.scalars().all()

    if len(remaining) <= session.target_remaining:
        # Mark all remaining as winners and close the session
        for sp in remaining:
            sp.status = PokemonStatus.winner
        session.status = SessionStatus.completed
        session.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(matchup)

    return matchup


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
async def get_results(
    db: AsyncSession,
    session_id: UUID,
) -> list[Pokemon]:
    """Return the surviving Pokémon for a completed session."""
    result = await db.execute(
        select(Pokemon)
        .join(SessionPokemon, SessionPokemon.pokemon_id == Pokemon.id)
        .where(
            and_(
                SessionPokemon.session_id == session_id,
                SessionPokemon.status == PokemonStatus.winner,
            )
        )
        .order_by(Pokemon.id)
    )
    return result.scalars().all()