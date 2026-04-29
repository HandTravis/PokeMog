"""
test_routes.py — Integration tests for FastAPI routes.
Uses the async HTTP test client with a real test DB.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def create_test_session(client, filters=None, target=3):
    res = await client.post("/api/sessions", json={
        "target_remaining": target,
        "filters": filters or {},
    })
    assert res.status_code == 201
    return res.json()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
class TestHealth:
    async def test_health(self, client):
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Pokemon routes
# ---------------------------------------------------------------------------
class TestPokemonRoutes:
    async def test_list_pokemon(self, client, seeded_db):
        res = await client.get("/api/pokemon")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 13

    async def test_list_pokemon_filter_generation(self, client, seeded_db):
        res = await client.get("/api/pokemon?generation=1")
        assert res.status_code == 200
        assert len(res.json()) == 13

    async def test_list_pokemon_filter_legendary(self, client, seeded_db):
        res = await client.get("/api/pokemon?is_legendary=true")
        assert res.status_code == 200
        names = [p["name"] for p in res.json()]
        assert "articuno" in names
        assert "bulbasaur" not in names

    async def test_list_pokemon_filter_type(self, client, seeded_db):
        res = await client.get("/api/pokemon?type=fire")
        assert res.status_code == 200
        assert len(res.json()) == 4

    async def test_get_single_pokemon(self, client, seeded_db):
        res = await client.get("/api/pokemon/1")
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "bulbasaur"
        assert "grass" in data["types"]
        assert "poison" in data["types"]

    async def test_get_pokemon_not_found(self, client, seeded_db):
        res = await client.get("/api/pokemon/9999")
        assert res.status_code == 404

    async def test_pokemon_response_has_sprite(self, client, seeded_db):
        res = await client.get("/api/pokemon/1")
        data = res.json()
        assert data["sprite_url"] is not None


# ---------------------------------------------------------------------------
# Session routes
# ---------------------------------------------------------------------------
class TestSessionRoutes:
    async def test_create_session(self, client, seeded_db):
        res = await client.post("/api/sessions", json={
            "target_remaining": 3,
            "filters": {},
        })
        assert res.status_code == 201
        data = res.json()
        assert "session_id" in data
        assert data["pool_size"] == 13
        assert "13 Pokémon" in data["message"]

    async def test_create_session_with_filters(self, client, seeded_db):
        res = await client.post("/api/sessions", json={
            "target_remaining": 2,
            "filters": {"type": ["fire"]},
        })
        assert res.status_code == 201
        assert res.json()["pool_size"] == 4

    async def test_create_session_target_too_large(self, client, seeded_db):
        res = await client.post("/api/sessions", json={
            "target_remaining": 20,
            "filters": {},
        })
        assert res.status_code == 400
        assert "13" in res.json()["detail"]

    async def test_create_session_empty_pool(self, client, seeded_db):
        res = await client.post("/api/sessions", json={
            "target_remaining": 1,
            "filters": {"generation": ["9"]},
        })
        assert res.status_code == 400

    async def test_get_session(self, client, seeded_db):
        created = await create_test_session(client)
        session_id = created["session_id"]

        res = await client.get(f"/api/sessions/{session_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "active"
        assert data["active_count"] == 13
        assert data["current_round"] == 1

    async def test_get_session_not_found(self, client, seeded_db):
        res = await client.get("/api/sessions/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404

    async def test_abandon_session(self, client, seeded_db):
        created = await create_test_session(client)
        session_id = created["session_id"]

        res = await client.delete(f"/api/sessions/{session_id}")
        assert res.status_code == 204

        status_res = await client.get(f"/api/sessions/{session_id}")
        assert status_res.json()["status"] == "abandoned"

    async def test_abandon_already_abandoned(self, client, seeded_db):
        created = await create_test_session(client)
        session_id = created["session_id"]
        await client.delete(f"/api/sessions/{session_id}")

        res = await client.delete(f"/api/sessions/{session_id}")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# Matchup routes
# ---------------------------------------------------------------------------
class TestMatchupRoutes:
    async def test_get_next_matchup(self, client, seeded_db):
        created = await create_test_session(client)
        session_id = created["session_id"]

        res = await client.get(f"/api/sessions/{session_id}/next")
        assert res.status_code == 200
        data = res.json()
        assert "pokemon_a" in data
        assert "pokemon_b" in data
        assert data["winner_id"] is None
        assert data["pokemon_a"]["id"] != data["pokemon_b"]["id"]

    async def test_matchup_includes_sprite(self, client, seeded_db):
        created = await create_test_session(client)
        session_id = created["session_id"]

        res = await client.get(f"/api/sessions/{session_id}/next")
        data = res.json()
        assert data["pokemon_a"]["sprite_url"] is not None
        assert data["pokemon_b"]["sprite_url"] is not None

    async def test_matchup_includes_types(self, client, seeded_db):
        created = await create_test_session(client)
        session_id = created["session_id"]

        res = await client.get(f"/api/sessions/{session_id}/next")
        data = res.json()
        assert len(data["pokemon_a"]["types"]) >= 1
        assert len(data["pokemon_b"]["types"]) >= 1

    async def test_submit_pick(self, client, seeded_db):
        created = await create_test_session(client)
        session_id = created["session_id"]

        matchup_res = await client.get(f"/api/sessions/{session_id}/next")
        matchup = matchup_res.json()
        winner_id = matchup["pokemon_a"]["id"]
        matchup_id = matchup["id"]

        res = await client.post(
            f"/api/sessions/{session_id}/matchups/{matchup_id}",
            json={"winner_id": winner_id},
        )
        assert res.status_code == 200
        assert res.json()["winner_id"] == winner_id

    async def test_submit_invalid_winner(self, client, seeded_db):
        created = await create_test_session(client)
        session_id = created["session_id"]

        matchup_res = await client.get(f"/api/sessions/{session_id}/next")
        matchup_id = matchup_res.json()["id"]

        res = await client.post(
            f"/api/sessions/{session_id}/matchups/{matchup_id}",
            json={"winner_id": 9999},
        )
        assert res.status_code == 400

    async def test_submit_pick_twice(self, client, seeded_db):
        created = await create_test_session(client)
        session_id = created["session_id"]

        matchup_res = await client.get(f"/api/sessions/{session_id}/next")
        matchup = matchup_res.json()
        winner_id = matchup["pokemon_a"]["id"]
        matchup_id = matchup["id"]

        await client.post(
            f"/api/sessions/{session_id}/matchups/{matchup_id}",
            json={"winner_id": winner_id},
        )
        res = await client.post(
            f"/api/sessions/{session_id}/matchups/{matchup_id}",
            json={"winner_id": winner_id},
        )
        assert res.status_code == 400

    async def test_next_matchup_on_completed_session(self, client, seeded_db):
        """Fire types: pool of 4, target 3 — one pick completes the session."""
        res = await client.post("/api/sessions", json={
            "target_remaining": 3,
            "filters": {"type": ["fire"]},
        })
        session_id = res.json()["session_id"]

        matchup_res = await client.get(f"/api/sessions/{session_id}/next")
        matchup = matchup_res.json()
        await client.post(
            f"/api/sessions/{session_id}/matchups/{matchup['id']}",
            json={"winner_id": matchup["pokemon_a"]["id"]},
        )

        next_res = await client.get(f"/api/sessions/{session_id}/next")
        assert next_res.status_code == 400


# ---------------------------------------------------------------------------
# Results routes
# ---------------------------------------------------------------------------
class TestResultsRoutes:
    async def test_results_on_active_session(self, client, seeded_db):
        created = await create_test_session(client)
        session_id = created["session_id"]

        res = await client.get(f"/api/sessions/{session_id}/results")
        assert res.status_code == 400
        assert "not yet complete" in res.json()["detail"]

    async def test_results_after_completion(self, client, seeded_db):
        res = await client.post("/api/sessions", json={
            "target_remaining": 3,
            "filters": {"type": ["fire"]},
        })
        session_id = res.json()["session_id"]

        matchup_res = await client.get(f"/api/sessions/{session_id}/next")
        matchup = matchup_res.json()
        await client.post(
            f"/api/sessions/{session_id}/matchups/{matchup['id']}",
            json={"winner_id": matchup["pokemon_a"]["id"]},
        )

        results_res = await client.get(f"/api/sessions/{session_id}/results")
        assert results_res.status_code == 200
        data = results_res.json()
        assert data["status"] == "completed"
        assert len(data["winners"]) <= 3
        assert len(data["winners"]) >= 1

    async def test_results_winners_have_full_data(self, client, seeded_db):
        res = await client.post("/api/sessions", json={
            "target_remaining": 3,
            "filters": {"type": ["fire"]},
        })
        session_id = res.json()["session_id"]

        matchup_res = await client.get(f"/api/sessions/{session_id}/next")
        matchup = matchup_res.json()
        await client.post(
            f"/api/sessions/{session_id}/matchups/{matchup['id']}",
            json={"winner_id": matchup["pokemon_a"]["id"]},
        )

        results_res = await client.get(f"/api/sessions/{session_id}/results")
        winner = results_res.json()["winners"][0]
        assert "sprite_url" in winner
        assert "types" in winner
        assert "generation" in winner
