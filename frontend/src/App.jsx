// App.jsx — Root component, global styles, and screen routing.

import { useState } from "react";
import { clearToken, isAuthenticated } from "./api";
import { LoginScreen, RegisterScreen } from "./AuthScreens";
import SetupScreen from "./SetupScreen";
import MatchupScreen from "./MatchupScreen";
import ResultsScreen from "./ResultsScreen";
import SessionHistoryScreen from "./SessionHistoryScreen";

// ---------------------------------------------------------------------------
// Global styles
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Screen states
// ---------------------------------------------------------------------------
const SCREENS = {
  LOGIN:    "login",
  REGISTER: "register",
  SETUP:    "setup",
  MATCHUP:  "matchup",
  RESULTS:  "results",
  HISTORY:  "history",
};

export default function App() {
  const [screen, setScreen] = useState(SCREENS.LOGIN);
  const [user, setUser] = useState(null);       // { email } or null for guests
  const [sessionId, setSessionId] = useState(null);
  const [poolSize, setPoolSize] = useState(0);

  // ---------------------------------------------------------------------------
  // Auth handlers
  // ---------------------------------------------------------------------------
  function handleAuthSuccess(userData) {
    setUser(userData);
    setScreen(SCREENS.HISTORY);
  }

  function handleGuest() {
    setUser(null);
    setScreen(SCREENS.SETUP);
  }

  function handleLogout() {
    clearToken();
    setUser(null);
    setSessionId(null);
    setPoolSize(0);
    setScreen(SCREENS.LOGIN);
  }

  // ---------------------------------------------------------------------------
  // Session handlers
  // ---------------------------------------------------------------------------
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
    // Authenticated users go to history, guests go to setup
    setScreen(user ? SCREENS.HISTORY : SCREENS.SETUP);
  }

  function handleResume(id, size) {
    setSessionId(id);
    setPoolSize(size);
    setScreen(SCREENS.MATCHUP);
  }

  // ---------------------------------------------------------------------------
  // Nav bar
  // ---------------------------------------------------------------------------
  function NavBar() {
    return (
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
        {/* Logo */}
        <div
          onClick={() => setScreen(user ? SCREENS.HISTORY : SCREENS.SETUP)}
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

        {/* Right side */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          {/* Quit button during matchup */}
          {screen === SCREENS.MATCHUP && (
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

          {/* User info + logout */}
          {user ? (
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
              <span style={{
                fontFamily: "var(--font-body)",
                fontSize: "0.75rem",
                color: "var(--text-muted)",
              }}>
                {user.email}
              </span>
              <button
                onClick={handleLogout}
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
                Log out
              </button>
            </div>
          ) : (
            // Guest — show login link unless already on auth screens
            ![SCREENS.LOGIN, SCREENS.REGISTER].includes(screen) && (
              <button
                onClick={() => setScreen(SCREENS.LOGIN)}
                style={{
                  background: "none",
                  border: "2px solid var(--red)",
                  borderRadius: "8px",
                  padding: "4px 12px",
                  fontFamily: "var(--font-body)",
                  fontSize: "0.75rem",
                  color: "var(--red)",
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                Log in
              </button>
            )
          )}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <>
      <style>{GLOBAL_STYLES}</style>
      <NavBar />

      <main style={{ minHeight: "calc(100vh - 52px)" }}>
        {screen === SCREENS.LOGIN && (
          <LoginScreen
            onSuccess={handleAuthSuccess}
            onSwitchToRegister={() => setScreen(SCREENS.REGISTER)}
            onContinueAsGuest={handleGuest}
          />
        )}

        {screen === SCREENS.REGISTER && (
          <RegisterScreen
            onSuccess={handleAuthSuccess}
            onSwitchToLogin={() => setScreen(SCREENS.LOGIN)}
            onContinueAsGuest={handleGuest}
          />
        )}

        {screen === SCREENS.HISTORY && (
          <SessionHistoryScreen
            onResume={handleResume}
            onStartNew={() => setScreen(SCREENS.SETUP)}
          />
        )}

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
