// MatchupScreen.jsx — Head-to-head battle UI with progress tracking.

import { useState, useEffect, useCallback } from "react";
import { getNextMatchup, submitPick, getSession } from "./api";
import { TypeBadge } from "./types.jsx";

function ProgressBar({ active, pool }) {
  const pct = pool > 0 ? Math.round(((pool - active) / pool) * 100) : 0;
  return (
    <div style={{ marginBottom: "1.5rem" }}>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        fontFamily: "var(--font-body)",
        fontSize: "0.75rem",
        fontWeight: 700,
        color: "var(--text-muted)",
        marginBottom: "6px",
        letterSpacing: "0.08em",
        textTransform: "uppercase",
      }}>
        <span>{active} remaining...</span>
        <span>{pct}% MOGGED</span>
      </div>
      <div style={{
        height: "8px",
        background: "var(--border)",
        borderRadius: "4px",
        overflow: "hidden",
      }}>
        <div style={{
          height: "100%",
          width: `${pct}%`,
          background: "var(--red)",
          borderRadius: "4px",
          transition: "width 0.5s ease",
        }} />
      </div>
    </div>
  );
}

function RoundBadge({ round }) {
  return (
    <div style={{
      display: "inline-block",
      background: "var(--red)",
      color: "#fff",
      fontFamily: "var(--font-body)",
      fontSize: "0.7rem",
      fontWeight: 800,
      letterSpacing: "0.15em",
      textTransform: "uppercase",
      padding: "4px 14px",
      borderRadius: "20px",
      marginBottom: "1.2rem",
    }}>
      Round {round}
    </div>
  );
}

function PokemonCard({ pokemon, onClick, disabled, winner, loser, shiny }) {
  const [hovered, setHovered] = useState(false);

  const borderColor = winner
    ? "#4caf50"
    : loser
    ? "#e53935"
    : hovered && !disabled
    ? "var(--red)"
    : "var(--border)";

  const scale = winner ? 1.03 : loser ? 0.97 : hovered && !disabled ? 1.02 : 1;

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        flex: 1,
        background: winner
          ? "rgba(76,175,80,0.08)"
          : loser
          ? "rgba(229,57,53,0.05)"
          : "var(--card-bg)",
        border: `2.5px solid ${borderColor}`,
        borderRadius: "16px",
        padding: "1.5rem 1rem",
        cursor: disabled ? "default" : "pointer",
        transform: `scale(${scale})`,
        transition: "all 0.18s ease",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "0.5rem",
        boxShadow: winner
          ? "0 4px 20px rgba(76,175,80,0.2)"
          : hovered && !disabled
          ? "0 4px 20px rgba(220,38,38,0.15)"
          : "0 2px 8px rgba(0,0,0,0.06)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Pokédex number */}
      <div style={{
        position: "absolute",
        top: "10px",
        right: "12px",
        fontFamily: "var(--font-body)",
        fontSize: "0.7rem",
        color: "var(--text-muted)",
        fontWeight: 700,
      }}>
        #{String(pokemon.id).padStart(3, "0")}
      </div>

      {/* Sprite */}
      <div style={{
        width: 110,
        height: 110,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        filter: loser ? "grayscale(0.8) opacity(0.5)" : "none",
        transition: "filter 0.3s ease",
      }}>
        {pokemon.sprite_url ? (
          <img
            src={shiny && pokemon.sprite_shiny_url 
              ? pokemon.sprite_shiny_url 
              : pokemon.sprite_url}
            alt={pokemon.display_name}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
              imageRendering: "pixelated",
            }}
          />
        ) : (
          <div style={{
            width: 80,
            height: 80,
            background: "var(--border)",
            borderRadius: "50%",
          }} />
        )}
      </div>

      {/* Name */}
      <div style={{
        fontFamily: "var(--font-display)",
        fontSize: "clamp(1rem, 3vw, 1.3rem)",
        color: loser ? "var(--text-muted)" : "var(--text)",
        textAlign: "center",
        lineHeight: 1.1,
      }}>
        {pokemon.display_name}
      </div>

      {/* Types */}
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center" }}>
        {pokemon.types.map((t) => (
          <TypeBadge key={t} type={t} />
        ))}
      </div>

      {/* Gen badge */}
      <div style={{
        fontFamily: "var(--font-body)",
        fontSize: "0.68rem",
        color: "var(--text-muted)",
        fontWeight: 600,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
      }}>
        Gen {pokemon.generation}
        {pokemon.is_legendary && " · Legendary"}
        {pokemon.is_mythical && " · Mythical"}
      </div>

      {/* Winner/loser overlay label */}
      {(winner || loser) && (
        <div style={{
          position: "absolute",
          bottom: "10px",
          left: "50%",
          transform: "translateX(-50%)",
          fontFamily: "var(--font-display)",
          fontSize: "0.8rem",
          color: winner ? "#4caf50" : "#e53935",
          letterSpacing: "0.1em",
        }}>
          {winner ? "✓ Winner" : "✗ Eliminated"}
        </div>
      )}
    </button>
  );
}

export default function MatchupScreen({ sessionId, poolSize, onComplete }) {
  const [matchup, setMatchup] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [picking, setPicking] = useState(false);
  const [decided, setDecided] = useState(null); // { winnerId, loserId }
  const [error, setError] = useState(null);
  const [shiny, setShiny] = useState(false);

  const fetchSession = useCallback(async () => {
    const s = await getSession(sessionId);
    setSession(s);
    return s;
  }, [sessionId]);

  const fetchNextMatchup = useCallback(async () => {
    setLoading(true);
    setDecided(null);
    setError(null);
    try {
      const s = await fetchSession();
      if (s.status !== "active") {
        onComplete(sessionId);
        return;
      }
      const m = await getNextMatchup(sessionId);
      setMatchup(m);
    } catch (e) {
      // 400 with session complete message
      if (e.message?.includes("complete") || e.message?.includes("no more")) {
        onComplete(sessionId);
      } else {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  }, [sessionId, fetchSession, onComplete]);

  useEffect(() => {
    fetchNextMatchup();
  }, [fetchNextMatchup]);

  async function handlePick(winnerId) {
    if (picking || decided) return;
    setPicking(true);
    const loserId =
      matchup.pokemon_a.id === winnerId
        ? matchup.pokemon_b.id
        : matchup.pokemon_a.id;

    setDecided({ winnerId, loserId });

    try {
      await submitPick(sessionId, matchup.id, winnerId);
      // Brief pause so the user can see the result before moving on
      await new Promise((r) => setTimeout(r, 900));
      await fetchNextMatchup();
    } catch (e) {
      setError(e.message);
    } finally {
      setPicking(false);
    }
  }

  if (error) {
    return (
      <div style={{ textAlign: "center", padding: "3rem", fontFamily: "var(--font-body)" }}>
        <div style={{ color: "var(--red)", marginBottom: "1rem" }}>{error}</div>
        <button onClick={fetchNextMatchup} style={{ color: "var(--red)", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}>
          Try again
        </button>
      </div>
    );
  }

  if (loading && !matchup) {
    return (
      <div style={{ textAlign: "center", padding: "4rem", fontFamily: "var(--font-display)", fontSize: "1.5rem", color: "var(--text-muted)" }}>
        Loading...
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 700, margin: "0 auto", padding: "1.5rem" }}>
      {/* Progress + round */}
      {session && (
        <>
          <ProgressBar active={session.active_count} pool={poolSize} />
          <div style={{ textAlign: "center" }}>
            {session.current_round && <RoundBadge round={session.current_round} />}
          </div>
        </>
      )}

      {/* VS header */}
      <div style={{
        textAlign: "center",
        fontFamily: "var(--font-display)",
        fontSize: "clamp(1rem, 3vw, 1.2rem)",
        color: "var(--text-muted)",
        marginBottom: "1rem",
        letterSpacing: "0.1em",
      }}>
        Which 'mon mogs the other?
      </div>

      {/* Shiny toggle */}
      <div style={{ textAlign: "center", marginBottom: "0.8rem" }}>
        <button
          onClick={() => setShiny(s => !s)}
          style={{
            background: shiny ? "#F8D030" : "var(--card-bg)",
            border: `2px solid ${shiny ? "#F8D030" : "var(--border)"}`,
            borderRadius: "20px",
            padding: "4px 14px",
            fontFamily: "var(--font-body)",
            fontSize: "0.72rem",
            fontWeight: 700,
            cursor: "pointer",
            color: shiny ? "#333" : "var(--text-muted)",
            letterSpacing: "0.08em",
            transition: "all 0.15s ease",
          }}
        >
          ✨ Shiny
        </button>
      </div>

      {/* Battle area */}
      {matchup && (
        <div style={{ display: "flex", gap: "1rem", alignItems: "stretch" }}>
          <PokemonCard
            pokemon={matchup.pokemon_a}
            onClick={() => handlePick(matchup.pokemon_a.id)}
            disabled={picking || !!decided}
            winner={decided?.winnerId === matchup.pokemon_a.id}
            loser={decided?.loserId === matchup.pokemon_a.id}
            shiny={shiny}
          />

          {/* VS divider */}
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}>
            <div style={{
              fontFamily: "var(--font-display)",
              fontSize: "clamp(1.5rem, 4vw, 2.2rem)",
              color: "var(--red)",
              opacity: decided ? 0.3 : 1,
              transition: "opacity 0.3s ease",
              textShadow: "0 2px 8px rgba(220,38,38,0.3)",
            }}>
              VS
            </div>
          </div>

          <PokemonCard
            pokemon={matchup.pokemon_b}
            onClick={() => handlePick(matchup.pokemon_b.id)}
            disabled={picking || !!decided}
            winner={decided?.winnerId === matchup.pokemon_b.id}
            loser={decided?.loserId === matchup.pokemon_b.id}
            shiny={shiny}
          />
        </div>
      )}

      {/* Hint */}
      {!decided && !loading && (
        <div style={{
          textAlign: "center",
          marginTop: "1.2rem",
          fontFamily: "var(--font-body)",
          fontSize: "0.78rem",
          color: "var(--text-muted)",
          letterSpacing: "0.05em",
        }}>
          Tap a card to pick your favourite
        </div>
      )}
    </div>
  );
}
