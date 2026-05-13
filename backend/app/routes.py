"""
routes.py — FastAPI route definitions for PokéRanker.

Mount in main.py:
    from app.routes import router
    app.include_router(router, prefix="/api")
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from app.database import get_db
from app.models import (
    Matchup,
    Pokemon,
    PokemonType,
    Session,
    SessionPokemon,
    SessionStatus,
)
from app.tournament import (
    create_session,
    get_active_pokemon,
    get_current_round,
    get_next_matchup,
    get_results,
    submit_pick,
)

from app.auth import get_current_user, get_optional_user
from app.models import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class PokemonOut(BaseModel):
    id: int
    name: str
    display_name: str
    generation: int
    is_legendary: bool
    is_mythical: bool
    evolution_stage: int
    sprite_url: str | None
    sprite_shiny_url: str | None
    types: list[str]

    model_config = ConfigDict(from_attributes=True)


class MatchupOut(BaseModel):
    id: UUID
    round_number: int
    pokemon_a: PokemonOut
    pokemon_b: PokemonOut
    winner_id: int | None

    model_config = ConfigDict(from_attributes=True)


class SessionOut(BaseModel):
    id: UUID
    status: str
    target_remaining: int
    current_round: int | None
    active_count: int
    pool_size: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CreateSessionRequest(BaseModel):
    target_remaining: int = Field(..., gt=0, description="How many Pokémon survivors you want")
    filters: dict[str, list[str]] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True, json_schema_extra = {
            "example": {
                "target_remaining": 3,
                "filters": {
                    "generation": ["1"],
                    "type": ["fire", "water"],
                    "evolution_stage": ["1", "2"],
                    "is_legendary": ["false"],
                }
            }
        })


class CreateSessionResponse(BaseModel):
    session_id: UUID
    pool_size: int
    message: str


class SubmitPickRequest(BaseModel):
    winner_id: int


class ResultsResponse(BaseModel):
    session_id: UUID
    status: str
    winners: list[PokemonOut]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _pokemon_to_out(db: AsyncSession, pokemon: Pokemon) -> PokemonOut:
    """Serialize a Pokemon ORM object including its types."""
    result = await db.execute(
        select(PokemonType).where(PokemonType.pokemon_id == pokemon.id)
    )
    types = [pt.type.value for pt in result.scalars().all()]
    return PokemonOut(
        id=pokemon.id,
        name=pokemon.name,
        display_name=pokemon.display_name,
        generation=pokemon.generation,
        is_legendary=pokemon.is_legendary,
        is_mythical=pokemon.is_mythical,
        evolution_stage=pokemon.evolution_stage,
        sprite_url=pokemon.sprite_url,
        sprite_shiny_url=pokemon.sprite_shiny_url,
        types=types,
    )


async def _matchup_to_out(db: AsyncSession, matchup: Matchup) -> MatchupOut:
    """Serialize a Matchup ORM object with full Pokémon details."""
    from app.models import Round
    round_ = await db.get(Round, matchup.round_id)
    pokemon_a = await db.get(Pokemon, matchup.pokemon_a_id)
    pokemon_b = await db.get(Pokemon, matchup.pokemon_b_id)
    return MatchupOut(
        id=matchup.id,
        round_number=round_.round_number,
        pokemon_a=await _pokemon_to_out(db, pokemon_a),
        pokemon_b=await _pokemon_to_out(db, pokemon_b),
        winner_id=matchup.winner_id,
    )


# ---------------------------------------------------------------------------
# Pokemon routes
# ---------------------------------------------------------------------------
@router.get("/pokemon", response_model=list[PokemonOut])
async def list_pokemon(
    generation: int | None = None,
    evolution_stage: int | None = None,
    is_legendary: bool | None = None,
    is_mythical: bool | None = None,
    type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List Pokémon with optional filters. Useful for populating the filter UI."""
    query = select(Pokemon)

    if generation is not None:
        query = query.where(Pokemon.generation == generation)
    if evolution_stage is not None:
        query = query.where(Pokemon.evolution_stage == evolution_stage)
    if is_legendary is not None:
        query = query.where(Pokemon.is_legendary == is_legendary)
    if is_mythical is not None:
        query = query.where(Pokemon.is_mythical == is_mythical)
    if type is not None:
        query = query.where(
            Pokemon.id.in_(
                select(PokemonType.pokemon_id).where(PokemonType.type == type)
            )
        )

    result = await db.execute(query.order_by(Pokemon.id))
    pokemon_list = result.scalars().all()
    return [await _pokemon_to_out(db, p) for p in pokemon_list]


@router.get("/pokemon/{pokemon_id}", response_model=PokemonOut)
async def get_pokemon(pokemon_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single Pokémon by its national dex ID."""
    pokemon = await db.get(Pokemon, pokemon_id)
    if not pokemon:
        raise HTTPException(status_code=404, detail="Pokémon not found.")
    return await _pokemon_to_out(db, pokemon)


# ---------------------------------------------------------------------------
# Session routes
# ---------------------------------------------------------------------------
@router.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def start_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    try:
        session, pool_size = await create_session(
            db=db,
            filters=body.filters,
            target_remaining=body.target_remaining,
            user_id=current_user.id if current_user else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CreateSessionResponse(
        session_id=session.id,
        pool_size=pool_size,
        message=(
            f"Session created! {pool_size} Pokémon are in your pool. "
            f"Matchups will continue until {body.target_remaining} remain."
        ),
    )


@router.get("/sessions/history", response_model=list[SessionOut])
async def session_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all sessions for the currently authenticated user."""
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id)
        .order_by(Session.created_at.desc())
    )
    sessions = result.scalars().all()

    out = []
    for session in sessions:
        current_round = await get_current_round(db, session.id)
        active = await get_active_pokemon(db, session.id)
        pool_result = await db.execute(
            select(SessionPokemon).where(SessionPokemon.session_id == session.id)
        )
        pool_size = len(pool_result.scalars().all())
        out.append(SessionOut(
            id=session.id,
            status=session.status.value,
            target_remaining=session.target_remaining,
            current_round=current_round.round_number if current_round else None,
            active_count=len(active),
            pool_size=pool_size,
        ))
    return out


@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get the current state of a session."""
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    current_round = await get_current_round(db, session_id)
    active = await get_active_pokemon(db, session_id)

    result = await db.execute(
        select(SessionPokemon).where(SessionPokemon.session_id == session_id)
    )
    pool_size = len(result.scalars().all())

    return SessionOut(
        id=session.id,
        status=session.status.value,
        target_remaining=session.target_remaining,
        current_round=current_round.round_number if current_round else None,
        active_count=len(active),
        pool_size=pool_size,
    )


@router.get("/sessions/{session_id}/next", response_model=MatchupOut)
async def next_matchup(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get the next undecided matchup for a session."""
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.status != SessionStatus.active:
        raise HTTPException(
            status_code=400,
            detail=f"Session is {session.status.value}, no more matchups available."
        )

    matchup = await get_next_matchup(db, session_id)
    if not matchup:
        raise HTTPException(
            status_code=404,
            detail="No more matchups available. The session may be complete."
        )

    return await _matchup_to_out(db, matchup)


@router.post("/sessions/{session_id}/matchups/{matchup_id}", response_model=MatchupOut)
async def decide_matchup(
    session_id: UUID,
    matchup_id: UUID,
    body: SubmitPickRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit a pick for a matchup. winner_id must be one of the two Pokémon in the matchup."""
    try:
        matchup = await submit_pick(
            db=db,
            session_id=session_id,
            matchup_id=matchup_id,
            winner_id=body.winner_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return await _matchup_to_out(db, matchup)


@router.get("/sessions/{session_id}/results", response_model=ResultsResponse)
async def session_results(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get the final surviving Pokémon for a completed session."""
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.status != SessionStatus.completed:
        raise HTTPException(
            status_code=400,
            detail="Session is not yet complete."
        )

    winners = await get_results(db, session_id)
    return ResultsResponse(
        session_id=session_id,
        status=session.status.value,
        winners=[await _pokemon_to_out(db, p) for p in winners],
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def abandon_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Mark a session as abandoned."""
    from datetime import datetime, timezone
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.status != SessionStatus.active:
        raise HTTPException(
            status_code=400,
            detail=f"Session is already {session.status.value}."
        )
    session.status = SessionStatus.abandoned
    session.completed_at = datetime.now(timezone.utc)