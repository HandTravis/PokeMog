// SetupScreen.jsx — Filter picker and session creation screen.

import { useState } from "react";
import { createSession } from "./api";

const GENERATIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9];
const TYPES = [
  "normal","fire","water","electric","grass","ice",
  "fighting","poison","ground","flying","psychic",
  "bug","rock","ghost","dragon","dark","steel","fairy",
];
const TYPE_COLORS = {
  normal:"#A8A878", fire:"#F08030", water:"#6890F0", electric:"#F8D030",
  grass:"#78C850", ice:"#98D8D8", fighting:"#C03028", poison:"#A040A0",
  ground:"#E0C068", flying:"#A890F0", psychic:"#F85888", bug:"#A8B820",
  rock:"#B8A038", ghost:"#705898", dragon:"#7038F8", dark:"#705848",
  steel:"#B8B8D0", fairy:"#EE99AC",
};

function ToggleChip({ label, active, onClick, color }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? (color ?? "var(--red)") : "transparent",
        color: active ? "#fff" : "var(--text-muted)",
        border: `2px solid ${active ? (color ?? "var(--red)") : "var(--border)"}`,
        borderRadius: "20px",
        padding: "4px 14px",
        fontSize: "0.78rem",
        fontWeight: 700,
        cursor: "pointer",
        letterSpacing: "0.05em",
        textTransform: "uppercase",
        transition: "all 0.15s ease",
        fontFamily: "var(--font-body)",
      }}
    >
      {label}
    </button>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: "1.8rem" }}>
      <div style={{
        fontSize: "0.7rem",
        fontWeight: 800,
        letterSpacing: "0.15em",
        textTransform: "uppercase",
        color: "var(--red)",
        marginBottom: "0.6rem",
        fontFamily: "var(--font-body)",
      }}>
        {title}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
        {children}
      </div>
    </div>
  );
}

export default function SetupScreen({ onSessionStart }) {
  const [generations, setGenerations] = useState([]);
  const [types, setTypes] = useState([]);
  const [stages, setStages] = useState([]);
  const [legendary, setLegendary] = useState(null); // null = any, true/false
  const [mythical, setMythical] = useState(null);
  const [target, setTarget] = useState(8);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  function toggle(arr, setArr, val) {
    setArr(arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val]);
  }

  async function handleStart() {
    setLoading(true);
    setError(null);
    try {
      const filters = {};
      if (generations.length) filters.generation = generations.map(String);
      if (types.length) filters.type = types;
      if (stages.length) filters.evolution_stage = stages.map(String);
      if (legendary !== null) filters.is_legendary = [String(legendary)];
      if (mythical !== null) filters.is_mythical = [String(mythical)];

      const res = await createSession(filters, target);
      onSessionStart(res.session_id, res.pool_size, res.message);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: "2.5rem" }}>
        <div style={{
          fontSize: "0.75rem",
          letterSpacing: "0.2em",
          textTransform: "uppercase",
          color: "var(--red)",
          fontFamily: "var(--font-body)",
          fontWeight: 800,
          marginBottom: "0.4rem",
        }}>
          A Pokémon Ranking Game
        </div>
        <h1 style={{
          fontFamily: "var(--font-display)",
          fontSize: "clamp(2rem, 6vw, 3.2rem)",
          color: "var(--text)",
          margin: 0,
          lineHeight: 1.1,
        }}>
          Poké<br />MOGGED!
        </h1>
        <p style={{
          color: "var(--text-muted)",
          fontFamily: "var(--font-body)",
          fontSize: "0.9rem",
          marginTop: "0.8rem",
        }}>
          Pick your filters, then decide head-to-head until your favourites MOG to the top.
        </p>
      </div>

      {/* Filters */}
      <div style={{
        background: "var(--card-bg)",
        border: "2px solid var(--border)",
        borderRadius: "16px",
        padding: "1.5rem",
        marginBottom: "1.5rem",
      }}>
        <Section title="Generation">
          {GENERATIONS.map((g) => (
            <ToggleChip
              key={g}
              label={`Gen ${g}`}
              active={generations.includes(g)}
              onClick={() => toggle(generations, setGenerations, g)}
            />
          ))}
        </Section>

        <Section title="Type">
          {TYPES.map((t) => (
            <ToggleChip
              key={t}
              label={t}
              active={types.includes(t)}
              onClick={() => toggle(types, setTypes, t)}
              color={TYPE_COLORS[t]}
            />
          ))}
        </Section>

        <Section title="Evolution Stage">
          {[["1", "Basic"], ["2", "Stage 1"], ["3", "Stage 2+"]].map(([val, label]) => (
            <ToggleChip
              key={val}
              label={label}
              active={stages.includes(Number(val))}
              onClick={() => toggle(stages, setStages, Number(val))}
            />
          ))}
        </Section>

        <Section title="Special">
          <ToggleChip
            label="Legendary"
            active={legendary === true}
            onClick={() => setLegendary(legendary === true ? null : true)}
          />
          <ToggleChip
            label="No Legendaries"
            active={legendary === false}
            onClick={() => setLegendary(legendary === false ? null : false)}
          />
          <ToggleChip
            label="Mythical"
            active={mythical === true}
            onClick={() => setMythical(mythical === true ? null : true)}
          />
          <ToggleChip
            label="No Mythicals"
            active={mythical === false}
            onClick={() => setMythical(mythical === false ? null : false)}
          />
        </Section>
      </div>

      {/* Target remaining */}
      <div style={{
        background: "var(--card-bg)",
        border: "2px solid var(--border)",
        borderRadius: "16px",
        padding: "1.5rem",
        marginBottom: "1.5rem",
      }}>
        <div style={{
          fontSize: "0.7rem",
          fontWeight: 800,
          letterSpacing: "0.15em",
          textTransform: "uppercase",
          color: "var(--red)",
          marginBottom: "0.8rem",
          fontFamily: "var(--font-body)",
        }}>
          How Many Survivors?
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <input
            type="range"
            min={1}
            max={20}
            value={target}
            onChange={(e) => setTarget(Number(e.target.value))}
            style={{ flex: 1, accentColor: "var(--red)" }}
          />
          <div style={{
            fontFamily: "var(--font-display)",
            fontSize: "2rem",
            color: "var(--text)",
            minWidth: "2.5rem",
            textAlign: "center",
          }}>
            {target}
          </div>
        </div>
        <div style={{
          fontSize: "0.8rem",
          color: "var(--text-muted)",
          fontFamily: "var(--font-body)",
          marginTop: "0.4rem",
        }}>
          Matchups continue until {target} Pokémon remain.
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          background: "#fff0f0",
          border: "2px solid var(--red)",
          borderRadius: "10px",
          padding: "0.8rem 1rem",
          color: "var(--red)",
          fontFamily: "var(--font-body)",
          fontSize: "0.85rem",
          marginBottom: "1rem",
        }}>
          {error}
        </div>
      )}

      {/* Start button */}
      <button
        onClick={handleStart}
        disabled={loading}
        style={{
          width: "100%",
          padding: "1rem",
          background: loading ? "var(--border)" : "var(--red)",
          color: "#fff",
          border: "none",
          borderRadius: "12px",
          fontFamily: "var(--font-display)",
          fontSize: "1.2rem",
          cursor: loading ? "not-allowed" : "pointer",
          letterSpacing: "0.05em",
          transition: "transform 0.1s ease, background 0.2s ease",
          boxShadow: loading ? "none" : "0 4px 0 #8b0000",
          transform: loading ? "none" : "translateY(0)",
        }}
        onMouseDown={(e) => { if (!loading) e.currentTarget.style.transform = "translateY(3px)"; e.currentTarget.style.boxShadow = "none"; }}
        onMouseUp={(e) => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = loading ? "none" : "0 4px 0 #8b0000"; }}
      >
        {loading ? "Building pool..." : "Start Ranking!"}
      </button>
    </div>
  );
}
