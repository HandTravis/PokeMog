// App.jsx — Root component, global styles, and screen routing.

import { useState } from "react";
import SetupScreen from "./SetupScreen";
import MatchupScreen from "./MatchupScreen";
import ResultsScreen from "./ResultsScreen";

// Global styles injected once at the root
const GLOBAL_STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=DM+Sans:wght@400;600;700;800&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --red: #dc2626;
    --text: #1a1a2e;
    --text-muted: #6b7280;
    --bg: #f5f5f0;
    --card-bg: #ffffff;
    --border: #e5e7eb;
    --font-display: 'Press Start 2P', monospace;
    --font-body: 'DM Sans', sans-serif;
  }

  html, body, #root {
    min-height: 100vh;
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-body);
  }

  body {
    background-image:
      repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,0,0,0.012) 2px,
        rgba(0,0,0,0.012) 4px
      );
  }

  button { outline: none; }
  button:focus-visible { outline: 2px solid var(--red); outline-offset: 2px; }

  input[type=range] {
    -webkit-appearance: none;
    height: 6px;
    border-radius: 3px;
    background: var(--border);
    cursor: pointer;
  }
  input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--red);
    cursor: pointer;
    border: 2px solid #fff;
    box-shadow: 0 1px 4px rgba(0,0,0,0.2);
  }
`;

// Screen states
const SCREENS = {
  SETUP: "setup",
  MATCHUP: "matchup",
  RESULTS: "results",
};

export default function App() {
  const [screen, setScreen] = useState(SCREENS.SETUP);
  const [sessionId, setSessionId] = useState(null);
  const [poolSize, setPoolSize] = useState(0);

  function handleSessionStart(id, size) {
    setSessionId(id);
    setPoolSize(size);
    setScreen(SCREENS.MATCHUP);
  }

  function handleComplete(id) {
    setSessionId(id);
    setScreen(SCREENS.RESULTS);
  }

  function handleRestart() {
    setSessionId(null);
    setPoolSize(0);
    setScreen(SCREENS.SETUP);
  }

  return (
    <>
      <style>{GLOBAL_STYLES}</style>

      {/* Top nav bar */}
      <div style={{
        borderBottom: "2px solid var(--border)",
        background: "var(--card-bg)",
        padding: "0.7rem 1.5rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}>
        <div
          onClick={handleRestart}
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "0.6rem",
            color: "var(--red)",
            cursor: "pointer",
            letterSpacing: "0.05em",
            lineHeight: 1.4,
          }}
        >
          Pokémon<br />Ranker
        </div>

        {screen === SCREENS.MATCHUP && sessionId && (
          <button
            onClick={handleRestart}
            style={{
              background: "none",
              border: "2px solid var(--border)",
              borderRadius: "8px",
              padding: "4px 12px",
              fontFamily: "var(--font-body)",
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontWeight: 700,
            }}
          >
            ✕ Quit
          </button>
        )}
      </div>

      {/* Screen content */}
      <main style={{ minHeight: "calc(100vh - 52px)" }}>
        {screen === SCREENS.SETUP && (
          <SetupScreen onSessionStart={handleSessionStart} />
        )}
        {screen === SCREENS.MATCHUP && sessionId && (
          <MatchupScreen
            sessionId={sessionId}
            poolSize={poolSize}
            onComplete={handleComplete}
          />
        )}
        {screen === SCREENS.RESULTS && sessionId && (
          <ResultsScreen
            sessionId={sessionId}
            onRestart={handleRestart}
          />
        )}
      </main>
    </>
  );
}
