"""
test_seed.py — Tests for the PokéAPI seed script.
Mocks HTTP calls so tests run offline and fast.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select

from app.models import Pokemon, PokemonType
from app.seed import seed_pokemon, get_generation, get_evolution_stage


# ---------------------------------------------------------------------------
# Pure function tests (no DB needed)
# ---------------------------------------------------------------------------
class TestGetGeneration:
    def test_gen_1(self):
        assert get_generation(1) == 1
        assert get_generation(151) == 1

    def test_gen_2(self):
        assert get_generation(152) == 2
        assert get_generation(251) == 2

    def test_gen_3(self):
        assert get_generation(252) == 3

    def test_gen_9(self):
        assert get_generation(906) == 9
        assert get_generation(1025) == 9

    def test_boundary_values(self):
        assert get_generation(493) == 4
        assert get_generation(494) == 5


class TestGetEvolutionStage:
    def test_basic_pokemon(self):
        chain = {
            "species": {"name": "bulbasaur"},
            "evolves_to": [
                {
                    "species": {"name": "ivysaur"},
                    "evolves_to": [
                        {"species": {"name": "venusaur"}, "evolves_to": []}
                    ],
                }
            ],
        }
        assert get_evolution_stage(chain, "bulbasaur") == 1

    def test_stage_1_evolution(self):
        chain = {
            "species": {"name": "bulbasaur"},
            "evolves_to": [
                {
                    "species": {"name": "ivysaur"},
                    "evolves_to": [
                        {"species": {"name": "venusaur"}, "evolves_to": []}
                    ],
                }
            ],
        }
        assert get_evolution_stage(chain, "ivysaur") == 2

    def test_stage_2_evolution(self):
        chain = {
            "species": {"name": "bulbasaur"},
            "evolves_to": [
                {
                    "species": {"name": "ivysaur"},
                    "evolves_to": [
                        {"species": {"name": "venusaur"}, "evolves_to": []}
                    ],
                }
            ],
        }
        assert get_evolution_stage(chain, "venusaur") == 3

    def test_no_evolution(self):
        chain = {
            "species": {"name": "mew"},
            "evolves_to": [],
        }
        assert get_evolution_stage(chain, "mew") == 1

    def test_not_in_chain_returns_1(self):
        chain = {
            "species": {"name": "bulbasaur"},
            "evolves_to": [],
        }
        assert get_evolution_stage(chain, "pikachu") == 1


# ---------------------------------------------------------------------------
# Seed function tests (mock HTTP + real DB)
# ---------------------------------------------------------------------------
MOCK_POKEMON_DATA = {
    "name": "bulbasaur",
    "types": [
        {"slot": 1, "type": {"name": "grass"}},
        {"slot": 2, "type": {"name": "poison"}},
    ],
    "sprites": {
        "front_default": "https://example.com/bulbasaur.png",
        "front_shiny": "https://example.com/bulbasaur_shiny.png",
    },
}

MOCK_SPECIES_DATA = {
    "name": "bulbasaur",
    "is_legendary": False,
    "is_mythical": False,
    "evolution_chain": {"url": "https://pokeapi.co/api/v2/evolution-chain/1/"},
}

MOCK_EVOLUTION_CHAIN = {
    "chain": {
        "species": {"name": "bulbasaur"},
        "evolves_to": [
            {
                "species": {"name": "ivysaur"},
                "evolves_to": [
                    {"species": {"name": "venusaur"}, "evolves_to": []}
                ],
            }
        ],
    }
}
