// SessionHistoryScreen.jsx — Shows a user's past sessions and their results.

import { useState, useEffect } from "react";
import { getUserSessions, getResults } from "./api";
import { TypeBadge } from "./types.jsx";

function StatusBadge({ status }) {
  const colors = {
    completed: { bg: "#e8f5e9", text: "#2e7d32", label: "Completed" },
    active:    { bg: "#fff8e1", text: "#f57f17", label: "In Progress" },
    abandoned: { bg: "#fafafa", text: "#9e9e9e", label: "Abandoned" },
  };
  const c = colors[status] ?? colors.abandoned;
  return (
    <span style={{
      background: c.bg,
      color: c.text,
      padding: "2px 10px",
      borderRadius: "20px",
      fontSize: "0.7rem",
      fontWeight: 700,
      letterSpacing: "0.08em",
      textTransform: "uppercase",
      fontFamily: "var(--font-body)",
    }}>
      {c.label}
    </span>
  );
}

function WinnerSprite({ pokemon }) {
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: "4px",
      width: 70,
    }}>
      {pokemon.sprite_url ? (
        <img
          src={pokemon.sprite_url}
          alt={pokemon.display_name}
          style={{ width: 56, height: 56, imageRendering: "pixelated", objectFit: "contain" }}
        />
      ) : (
        <div style={{ width: 56, height: 56, background: "var(--border)", borderRadius: "50%" }} />
      )}
      <div style={{
        fontFamily: "var(--font-body)",
        fontSize: "0.62rem",
        color: "var(--text-muted)",
        textAlign: "center",
        fontWeight: 600,
        lineHeight: 1.2,
      }}>
        {pokemon.display_name}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center" }}>
        {pokemon.types.map((t) => <TypeBadge key={t} type={t} />)}
      </div>
    </div>
  );
}

function SessionCard({ session, onResume }) {
  const [winners, setWinners] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);

  const rawDate = session.created_at ? new Date(session.created_at) : null;
  const date = rawDate && !isNaN(rawDate)
  ? rawDate.toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric",
    })
  : "Unknown date";

  async function handleExpand() {
    if (expanded) { setExpanded(false); return; }
    if (session.status !== "completed") { setExpanded(true); return; }
    setLoading(true);
    try {
      const res = await getResults(session.id);
      setWinners(res.winners);
      setExpanded(true);
    } catch {
      setExpanded(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      background: "var(--card-bg)",
      border: "2px solid var(--border)",
      borderRadius: "14px",
      marginBottom: "0.8rem",
      overflow: "hidden",
      transition: "border-color 0.15s ease",
    }}>
      {/* Header row */}
      <div
        onClick={handleExpand}
        style={{
          padding: "1rem 1.2rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
          gap: "1rem",
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.3rem" }}>
            <StatusBadge status={session.status} />
            <span style={{
              fontFamily: "var(--font-body)",
              fontSize: "0.75rem",
              color: "var(--text-muted)",
            }}>
              {date}
            </span>
          </div>
          <div style={{
            fontFamily: "var(--font-body)",
            fontSize: "0.82rem",
            color: "var(--text)",
            fontWeight: 600,
          }}>
            {session.pool_size} Pokémon · Top {session.target_remaining} goal
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.8rem" }}>
          {session.status === "active" && (
            <button
              onClick={(e) => { e.stopPropagation(); onResume(session.id, session.pool_size); }}
              style={{
                background: "var(--red)",
                color: "#fff",
                border: "none",
                borderRadius: "8px",
                padding: "5px 12px",
                fontFamily: "var(--font-body)",
                fontSize: "0.75rem",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Resume
            </button>
          )}
          <span style={{
            color: "var(--text-muted)",
            fontSize: "0.8rem",
            transform: expanded ? "rotate(180deg)" : "none",
            transition: "transform 0.2s ease",
            display: "inline-block",
          }}>
            ▼
          </span>
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div style={{
          borderTop: "2px solid var(--border)",
          padding: "1rem 1.2rem",
        }}>
          {loading && (
            <div style={{ fontFamily: "var(--font-body)", fontSize: "0.8rem", color: "var(--text-muted)" }}>
              Loading results...
            </div>
          )}
          {winners && winners.length > 0 && (
            <>
              <div style={{
                fontFamily: "var(--font-body)",
                fontSize: "0.7rem",
                fontWeight: 800,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "var(--red)",
                marginBottom: "0.8rem",
              }}>
                Your Top {winners.length}
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.8rem" }}>
                {winners.map((p) => <WinnerSprite key={p.id} pokemon={p} />)}
              </div>
            </>
          )}
          {session.status === "abandoned" && (
            <div style={{ fontFamily: "var(--font-body)", fontSize: "0.82rem", color: "var(--text-muted)" }}>
              This session was abandoned before completion.
            </div>
          )}
          {session.status === "active" && (
            <div style={{ fontFamily: "var(--font-body)", fontSize: "0.82rem", color: "var(--text-muted)" }}>
              {session.active_count} Pokémon remaining — resume to continue ranking.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function SessionHistoryScreen({ onResume, onStartNew }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetch() {
      try {
        const data = await getUserSessions();
        setSessions(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Header */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{
          fontSize: "0.7rem",
          letterSpacing: "0.2em",
          textTransform: "uppercase",
          color: "var(--red)",
          fontFamily: "var(--font-body)",
          fontWeight: 800,
          marginBottom: "0.4rem",
        }}>
          Your Rankings
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h1 style={{
            fontFamily: "var(--font-display)",
            fontSize: "clamp(1.4rem, 4vw, 2rem)",
            color: "var(--text)",
            margin: 0,
          }}>
            Session History
          </h1>
          <button
            onClick={onStartNew}
            style={{
              background: "var(--red)",
              color: "#fff",
              border: "none",
              borderRadius: "10px",
              padding: "0.6rem 1.2rem",
              fontFamily: "var(--font-body)",
              fontSize: "0.8rem",
              fontWeight: 700,
              cursor: "pointer",
              boxShadow: "0 3px 0 #8b0000",
            }}
          >
            + New Ranking
          </button>
        </div>
      </div>

      {/* Content */}
      {loading && (
        <div style={{ textAlign: "center", padding: "3rem", fontFamily: "var(--font-display)", fontSize: "1rem", color: "var(--text-muted)" }}>
          Loading...
        </div>
      )}

      {error && (
        <div style={{
          background: "#fff0f0",
          border: "2px solid var(--red)",
          borderRadius: "10px",
          padding: "0.8rem 1rem",
          color: "var(--red)",
          fontFamily: "var(--font-body)",
          fontSize: "0.85rem",
        }}>
          {typeof error === "string" ? error : "Failed to load sessions."}
        </div>
      )}

      {!loading && !error && sessions.length === 0 && (
        <div style={{
          textAlign: "center",
          padding: "3rem",
          background: "var(--card-bg)",
          border: "2px solid var(--border)",
          borderRadius: "16px",
        }}>
          <div style={{
            fontFamily: "var(--font-display)",
            fontSize: "1rem",
            color: "var(--text-muted)",
            marginBottom: "1rem",
          }}>
            No sessions yet
          </div>
          <button
            onClick={onStartNew}
            style={{
              background: "var(--red)",
              color: "#fff",
              border: "none",
              borderRadius: "10px",
              padding: "0.7rem 1.5rem",
              fontFamily: "var(--font-body)",
              fontSize: "0.85rem",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Start your first ranking
          </button>
        </div>
      )}

      {!loading && sessions.map((s) => (
        <SessionCard key={s.id} session={s} onResume={onResume} />
      ))}
    </div>
  );
}
