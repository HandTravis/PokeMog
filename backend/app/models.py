"""
models.py — SQLAlchemy ORM models for PokéRanker.

Mirrors the schema in db/schema.sql exactly.
Import Base into your Alembic env.py for migrations.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class PokemonTypeEnum(str, enum.Enum):
    normal   = "normal"
    fire     = "fire"
    water    = "water"
    electric = "electric"
    grass    = "grass"
    ice      = "ice"
    fighting = "fighting"
    poison   = "poison"
    ground   = "ground"
    flying   = "flying"
    psychic  = "psychic"
    bug      = "bug"
    rock     = "rock"
    ghost    = "ghost"
    dragon   = "dragon"
    dark     = "dark"
    steel    = "steel"
    fairy    = "fairy"


class SessionStatus(str, enum.Enum):
    active    = "active"
    completed = "completed"
    abandoned = "abandoned"


class PokemonStatus(str, enum.Enum):
    active     = "active"
    eliminated = "eliminated"
    winner     = "winner"


# ---------------------------------------------------------------------------
# Pokemon
# ---------------------------------------------------------------------------
class Pokemon(Base):
    __tablename__ = "pokemon"

    id               = Column(Integer, primary_key=True)   # National Dex number
    name             = Column(String(100), nullable=False, unique=True)
    display_name     = Column(String(100), nullable=False)
    generation       = Column(SmallInteger, nullable=False)
    is_legendary     = Column(Boolean, nullable=False, default=False)
    is_mythical      = Column(Boolean, nullable=False, default=False)
    evolution_stage  = Column(SmallInteger, nullable=False, default=1)
    sprite_url       = Column(Text)
    sprite_shiny_url = Column(Text)
    created_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    types            = relationship("PokemonType", back_populates="pokemon", cascade="all, delete-orphan")
    session_entries  = relationship("SessionPokemon", back_populates="pokemon")
    matchups_as_a    = relationship("Matchup", foreign_keys="Matchup.pokemon_a_id", back_populates="pokemon_a")
    matchups_as_b    = relationship("Matchup", foreign_keys="Matchup.pokemon_b_id", back_populates="pokemon_b")
    matchups_won     = relationship("Matchup", foreign_keys="Matchup.winner_id", back_populates="winner")

    def __repr__(self):
        return f"<Pokemon #{self.id} {self.display_name}>"


# ---------------------------------------------------------------------------
# PokemonType
# ---------------------------------------------------------------------------
class PokemonType(Base):
    __tablename__ = "pokemon_types"

    pokemon_id = Column(Integer, ForeignKey("pokemon.id", ondelete="CASCADE"), primary_key=True)
    type       = Column(Enum(PokemonTypeEnum, name="pokemon_type_enum"), nullable=False)
    slot       = Column(SmallInteger, primary_key=True)

    __table_args__ = (
        CheckConstraint("slot IN (1, 2)", name="ck_pokemon_types_slot"),
    )

    # Relationships
    pokemon = relationship("Pokemon", back_populates="types")

    def __repr__(self):
        return f"<PokemonType pokemon_id={self.pokemon_id} type={self.type} slot={self.slot}>"


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
class Session(Base):
    __tablename__ = "sessions"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at      = Column(DateTime(timezone=True))
    target_remaining  = Column(SmallInteger, nullable=False, default=8)
    status            = Column(
                            Enum(SessionStatus, name="session_status_enum"),
                            nullable=False,
                            default=SessionStatus.active,
                        )

    # Relationships
    filters           = relationship("SessionFilter", back_populates="session", cascade="all, delete-orphan")
    pokemon_entries   = relationship("SessionPokemon", back_populates="session", cascade="all, delete-orphan")
    rounds            = relationship("Round", back_populates="session", cascade="all, delete-orphan", order_by="Round.round_number")
    matchups          = relationship("Matchup", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session id={self.id} status={self.status}>"


# ---------------------------------------------------------------------------
# SessionFilter
# ---------------------------------------------------------------------------
class SessionFilter(Base):
    __tablename__ = "session_filters"

    session_id   = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    filter_key   = Column(String(50), primary_key=True)
    filter_value = Column(String(50), primary_key=True)

    # Relationships
    session = relationship("Session", back_populates="filters")

    def __repr__(self):
        return f"<SessionFilter session_id={self.session_id} {self.filter_key}={self.filter_value}>"


# ---------------------------------------------------------------------------
# SessionPokemon
# ---------------------------------------------------------------------------
class SessionPokemon(Base):
    __tablename__ = "session_pokemon"

    session_id       = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    pokemon_id       = Column(Integer, ForeignKey("pokemon.id"), primary_key=True)
    status           = Column(
                           Enum(PokemonStatus, name="pokemon_status_enum"),
                           nullable=False,
                           default=PokemonStatus.active,
                       )
    round_eliminated = Column(SmallInteger)

    # Relationships
    session = relationship("Session", back_populates="pokemon_entries")
    pokemon = relationship("Pokemon", back_populates="session_entries")

    def __repr__(self):
        return f"<SessionPokemon session_id={self.session_id} pokemon_id={self.pokemon_id} status={self.status}>"


# ---------------------------------------------------------------------------
# Round
# ---------------------------------------------------------------------------
class Round(Base):
    __tablename__ = "rounds"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    session_id   = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    round_number = Column(SmallInteger, nullable=False)
    started_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("session_id", "round_number", name="uq_rounds_session_round"),
    )

    # Relationships
    session  = relationship("Session", back_populates="rounds")
    matchups = relationship("Matchup", back_populates="round", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Round id={self.id} session_id={self.session_id} round={self.round_number}>"


# ---------------------------------------------------------------------------
# Matchup
# ---------------------------------------------------------------------------
class Matchup(Base):
    __tablename__ = "matchups"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id     = Column(Integer, ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False)
    session_id   = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    pokemon_a_id = Column(Integer, ForeignKey("pokemon.id"), nullable=False)
    pokemon_b_id = Column(Integer, ForeignKey("pokemon.id"), nullable=False)
    winner_id    = Column(Integer, ForeignKey("pokemon.id"))
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at   = Column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("pokemon_a_id <> pokemon_b_id", name="ck_matchups_different_pokemon"),
    )

    # Relationships
    round     = relationship("Round", back_populates="matchups")
    session   = relationship("Session", back_populates="matchups")
    pokemon_a = relationship("Pokemon", foreign_keys=[pokemon_a_id], back_populates="matchups_as_a")
    pokemon_b = relationship("Pokemon", foreign_keys=[pokemon_b_id], back_populates="matchups_as_b")
    winner    = relationship("Pokemon", foreign_keys=[winner_id], back_populates="matchups_won")

    def __repr__(self):
        return f"<Matchup id={self.id} a={self.pokemon_a_id} b={self.pokemon_b_id} winner={self.winner_id}>"