-- =============================================================
-- Pokémon Ranker DB Schema
-- =============================================================

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -------------------------------------------------------------
-- POKEMON
-- Core Pokémon data, seeded from PokéAPI
-- -------------------------------------------------------------
CREATE TABLE pokemon (
    id              INTEGER PRIMARY KEY,          -- National Pokédex number
    name            VARCHAR(100) NOT NULL UNIQUE,
    display_name    VARCHAR(100) NOT NULL,        -- Formatted name (e.g. "Mr. Mime")
    generation      SMALLINT NOT NULL,            -- 1–9
    is_legendary    BOOLEAN NOT NULL DEFAULT FALSE,
    is_mythical     BOOLEAN NOT NULL DEFAULT FALSE,
    evolution_stage SMALLINT NOT NULL DEFAULT 1, -- 1 = Basic, 2 = Stage 1, 3 = Stage 2+
    sprite_url      TEXT,                         -- Front default sprite
    sprite_shiny_url TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------------
-- POKEMON_TYPES
-- Many-to-many: a Pokémon can have 1 or 2 types
-- -------------------------------------------------------------
CREATE TYPE pokemon_type_enum AS ENUM (
    'normal','fire','water','electric','grass','ice',
    'fighting','poison','ground','flying','psychic',
    'bug','rock','ghost','dragon','dark','steel','fairy'
);

CREATE TABLE pokemon_types (
    pokemon_id  INTEGER NOT NULL REFERENCES pokemon(id) ON DELETE CASCADE,
    type        pokemon_type_enum NOT NULL,
    slot        SMALLINT NOT NULL CHECK (slot IN (1, 2)), -- primary or secondary
    PRIMARY KEY (pokemon_id, slot)
);

-- -------------------------------------------------------------
-- SESSIONS
-- One session = one ranking run by a user
-- -------------------------------------------------------------
CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    target_remaining SMALLINT NOT NULL DEFAULT 8,  -- How many survivors the user wants
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'completed', 'abandoned'))
);

-- -------------------------------------------------------------
-- SESSION_FILTERS
-- Which filters were applied when the session was created
-- -------------------------------------------------------------
CREATE TABLE session_filters (
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    filter_key      VARCHAR(50) NOT NULL,   -- e.g. 'generation', 'type', 'evolution_stage'
    filter_value    VARCHAR(50) NOT NULL,   -- e.g. '1', 'fire', '2'
    PRIMARY KEY (session_id, filter_key, filter_value)
);

-- -------------------------------------------------------------
-- SESSION_POKEMON
-- The pool of Pokémon participating in this session
-- -------------------------------------------------------------
CREATE TABLE session_pokemon (
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    pokemon_id      INTEGER NOT NULL REFERENCES pokemon(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'eliminated', 'winner')),
    round_eliminated SMALLINT,              -- Which round they were knocked out
    PRIMARY KEY (session_id, pokemon_id)
);

-- -------------------------------------------------------------
-- ROUNDS
-- Each pass through the pool is one round
-- -------------------------------------------------------------
CREATE TABLE rounds (
    id              SERIAL PRIMARY KEY,
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    round_number    SMALLINT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    UNIQUE (session_id, round_number)
);

-- -------------------------------------------------------------
-- MATCHUPS
-- Individual head-to-head comparisons
-- -------------------------------------------------------------
CREATE TABLE matchups (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    round_id        INTEGER NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    pokemon_a_id    INTEGER NOT NULL REFERENCES pokemon(id),
    pokemon_b_id    INTEGER NOT NULL REFERENCES pokemon(id),
    winner_id       INTEGER REFERENCES pokemon(id),  -- NULL until user picks
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at      TIMESTAMPTZ,
    CHECK (pokemon_a_id <> pokemon_b_id)
);

-- -------------------------------------------------------------
-- INDEXES
-- -------------------------------------------------------------
CREATE INDEX idx_pokemon_generation      ON pokemon(generation);
CREATE INDEX idx_pokemon_evolution_stage ON pokemon(evolution_stage);
CREATE INDEX idx_pokemon_legendary       ON pokemon(is_legendary);
CREATE INDEX idx_pokemon_mythical        ON pokemon(is_mythical);
CREATE INDEX idx_pokemon_types_type      ON pokemon_types(type);
CREATE INDEX idx_session_pokemon_session ON session_pokemon(session_id, status);
CREATE INDEX idx_matchups_round          ON matchups(round_id);
CREATE INDEX idx_matchups_session        ON matchups(session_id);
