// ResultsScreen.jsx — Final survivors display.

import { useState, useEffect } from "react";
import { getResults } from "./api";
import { TypeBadge } from "./types.jsx";

function Confetti() {
  // Simple CSS confetti using pseudo-random positioned dots
  const pieces = Array.from({ length: 24 }, (_, i) => ({
    left: `${(i * 37 + 11) % 100}%`,
    top: `${(i * 53 + 7) % 60}%`,
    color: ["var(--red)", "#F8D030", "#78C850", "#6890F0", "#F85888"][i % 5],
    size: `${6 + (i % 4) * 3}px`,
    delay: `${(i * 0.15) % 1.5}s`,
  }));

  return (
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden" }}>
      {pieces.map((p, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: p.left,
            top: p.top,
            width: p.size,
            height: p.size,
            background: p.color,
            borderRadius: i % 3 === 0 ? "50%" : "2px",
            opacity: 0,
            animation: `confettiFall 1.2s ease forwards`,
            animationDelay: p.delay,
          }}
        />
      ))}
      <style>{`
        @keyframes confettiFall {
          0% { opacity: 0; transform: translateY(-20px) rotate(0deg); }
          30% { opacity: 1; }
          100% { opacity: 0; transform: translateY(80px) rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

function WinnerCard({ pokemon, rank }) {
  return (
    <div style={{
      background: "var(--card-bg)",
      border: "2.5px solid var(--border)",
      borderRadius: "16px",
      padding: "1.2rem 1rem",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: "0.4rem",
      position: "relative",
      animation: `riseIn 0.4s ease forwards`,
      animationDelay: `${rank * 0.07}s`,
      opacity: 0,
      boxShadow: "0 2px 12px rgba(0,0,0,0.07)",
    }}>
      <style>{`
        @keyframes riseIn {
          from { opacity: 0; transform: translateY(16px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Dex number */}
      <div style={{
        position: "absolute",
        top: 8,
        right: 10,
        fontFamily: "var(--font-body)",
        fontSize: "0.65rem",
        color: "var(--text-muted)",
        fontWeight: 700,
      }}>
        #{String(pokemon.id).padStart(3, "0")}
      </div>

      {/* Sprite */}
      <div style={{ width: 88, height: 88 }}>
        {pokemon.sprite_url ? (
          <img
            src={pokemon.sprite_url}
            alt={pokemon.display_name}
            style={{ width: "100%", height: "100%", objectFit: "contain", imageRendering: "pixelated" }}
          />
        ) : (
          <div style={{ width: 80, height: 80, background: "var(--border)", borderRadius: "50%" }} />
        )}
      </div>

      {/* Name */}
      <div style={{
        fontFamily: "var(--font-display)",
        fontSize: "1rem",
        color: "var(--text)",
        textAlign: "center",
        lineHeight: 1.1,
      }}>
        {pokemon.display_name}
      </div>

      {/* Types */}
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center" }}>
        {pokemon.types.map((t) => <TypeBadge key={t} type={t} />)}
      </div>

      {/* Gen */}
      <div style={{
        fontFamily: "var(--font-body)",
        fontSize: "0.65rem",
        color: "var(--text-muted)",
        fontWeight: 600,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
      }}>
        Gen {pokemon.generation}
        {pokemon.is_legendary && " · Legendary"}
        {pokemon.is_mythical && " · Mythical"}
      </div>
    </div>
  );
}

export default function ResultsScreen({ sessionId, onRestart }) {
  const [winners, setWinners] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetch() {
      try {
        const res = await getResults(sessionId);
        setWinners(res.winners);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, [sessionId]);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "4rem", fontFamily: "var(--font-display)", fontSize: "1.5rem", color: "var(--text-muted)" }}>
        Tallying results...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: "center", padding: "3rem", color: "var(--red)", fontFamily: "var(--font-body)" }}>
        {error}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "2rem 1.5rem", position: "relative" }}>
      <Confetti />

      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: "2rem" }}>
        <div style={{
          fontSize: "0.75rem",
          letterSpacing: "0.2em",
          textTransform: "uppercase",
          color: "var(--red)",
          fontFamily: "var(--font-body)",
          fontWeight: 800,
          marginBottom: "0.4rem",
        }}>
          Results
        </div>
        <h1 style={{
          fontFamily: "var(--font-display)",
          fontSize: "clamp(2rem, 6vw, 3rem)",
          color: "var(--text)",
          margin: 0,
          lineHeight: 1.1,
        }}>
          Your Favourites!
        </h1>
        <p style={{
          color: "var(--text-muted)",
          fontFamily: "var(--font-body)",
          fontSize: "0.9rem",
          marginTop: "0.6rem",
        }}>
          {winners.length} Pokémon survived your rankings.
        </p>
      </div>

      {/* Winners grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
        gap: "1rem",
        marginBottom: "2rem",
      }}>
        {winners.map((p, i) => (
          <WinnerCard key={p.id} pokemon={p} rank={i} />
        ))}
      </div>

      {/* Restart button */}
      <div style={{ textAlign: "center" }}>
        <button
          onClick={onRestart}
          style={{
            padding: "0.9rem 2.5rem",
            background: "var(--red)",
            color: "#fff",
            border: "none",
            borderRadius: "12px",
            fontFamily: "var(--font-display)",
            fontSize: "1.1rem",
            cursor: "pointer",
            boxShadow: "0 4px 0 #8b0000",
            transition: "transform 0.1s ease",
            letterSpacing: "0.05em",
          }}
          onMouseDown={(e) => { e.currentTarget.style.transform = "translateY(3px)"; e.currentTarget.style.boxShadow = "none"; }}
          onMouseUp={(e) => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = "0 4px 0 #8b0000"; }}
        >
          Rank Again
        </button>
      </div>
    </div>
  );
}
