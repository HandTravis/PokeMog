// AuthScreens.jsx — Login and Register screens.
// Both share the same layout, just different fields and API calls.

import { useState } from "react";
import { login, register, setToken } from "./api";

function AuthForm({ title, subtitle, onSuccess, onSwitch, switchLabel, switchPrompt, children, onSubmit, loading, error }) {
  return (
    <div style={{ maxWidth: 420, margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: "2rem" }}>
        <div style={{
          fontSize: "0.7rem",
          letterSpacing: "0.2em",
          textTransform: "uppercase",
          color: "var(--red)",
          fontFamily: "var(--font-body)",
          fontWeight: 800,
          marginBottom: "0.4rem",
        }}>
          Pokémon Ranker
        </div>
        <h1 style={{
          fontFamily: "var(--font-display)",
          fontSize: "clamp(1.4rem, 4vw, 2rem)",
          color: "var(--text)",
          margin: 0,
          lineHeight: 1.2,
        }}>
          {title}
        </h1>
        {subtitle && (
          <p style={{
            color: "var(--text-muted)",
            fontFamily: "var(--font-body)",
            fontSize: "0.85rem",
            marginTop: "0.6rem",
          }}>
            {subtitle}
          </p>
        )}
      </div>

      {/* Form card */}
      <div style={{
        background: "var(--card-bg)",
        border: "2px solid var(--border)",
        borderRadius: "16px",
        padding: "1.5rem",
        marginBottom: "1rem",
      }}>
        {children}

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

        {/* Submit button */}
        <button
          onClick={onSubmit}
          disabled={loading}
          style={{
            width: "100%",
            padding: "0.9rem",
            background: loading ? "var(--border)" : "var(--red)",
            color: "#fff",
            border: "none",
            borderRadius: "12px",
            fontFamily: "var(--font-display)",
            fontSize: "0.9rem",
            cursor: loading ? "not-allowed" : "pointer",
            boxShadow: loading ? "none" : "0 4px 0 #8b0000",
            transition: "transform 0.1s ease",
            letterSpacing: "0.05em",
          }}
          onMouseDown={(e) => { if (!loading) { e.currentTarget.style.transform = "translateY(3px)"; e.currentTarget.style.boxShadow = "none"; }}}
          onMouseUp={(e) => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = loading ? "none" : "0 4px 0 #8b0000"; }}
        >
          {loading ? "Please wait..." : title}
        </button>
      </div>

      {/* Switch link */}
      <div style={{
        textAlign: "center",
        fontFamily: "var(--font-body)",
        fontSize: "0.85rem",
        color: "var(--text-muted)",
      }}>
        {switchPrompt}{" "}
        <span
          onClick={onSwitch}
          style={{ color: "var(--red)", cursor: "pointer", fontWeight: 700 }}
        >
          {switchLabel}
        </span>
      </div>
    </div>
  );
}

function InputField({ label, type, value, onChange, placeholder }) {
  return (
    <div style={{ marginBottom: "1rem" }}>
      <label style={{
        display: "block",
        fontFamily: "var(--font-body)",
        fontSize: "0.72rem",
        fontWeight: 800,
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        color: "var(--red)",
        marginBottom: "0.4rem",
      }}>
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        style={{
          width: "100%",
          padding: "0.7rem 0.9rem",
          background: "var(--bg)",
          border: "2px solid var(--border)",
          borderRadius: "10px",
          fontFamily: "var(--font-body)",
          fontSize: "0.9rem",
          color: "var(--text)",
          outline: "none",
          boxSizing: "border-box",
          transition: "border-color 0.15s ease",
        }}
        onFocus={(e) => { e.target.style.borderColor = "var(--red)"; }}
        onBlur={(e) => { e.target.style.borderColor = "var(--border)"; }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Login Screen
// ---------------------------------------------------------------------------
export function LoginScreen({ onSuccess, onSwitchToRegister, onContinueAsGuest }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit() {
    if (!email || !password) {
      setError("Please enter your email and password.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await login(email, password);
      setToken(res.access_token);
      onSuccess({ email });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthForm
      title="Log In"
      subtitle="Welcome back! Log in to track your sessions."
      onSubmit={handleSubmit}
      onSwitch={onSwitchToRegister}
      switchPrompt="Don't have an account?"
      switchLabel="Register"
      loading={loading}
      error={error}
    >
      <InputField
        label="Email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
      />
      <InputField
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="••••••••"
      />
      {/* Guest option */}
      <div style={{
        textAlign: "center",
        marginBottom: "1rem",
        fontFamily: "var(--font-body)",
        fontSize: "0.8rem",
        color: "var(--text-muted)",
      }}>
        <span
          onClick={onContinueAsGuest}
          style={{ cursor: "pointer", textDecoration: "underline" }}
        >
          Continue as guest
        </span>
      </div>
    </AuthForm>
  );
}

// ---------------------------------------------------------------------------
// Register Screen
// ---------------------------------------------------------------------------
export function RegisterScreen({ onSuccess, onSwitchToLogin, onContinueAsGuest }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit() {
    if (!email || !password || !confirm) {
      setError("Please fill in all fields.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await register(email, password);
      setToken(res.access_token);
      onSuccess({ email: res.user.email });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthForm
      title="Register"
      subtitle="Create an account to save and revisit your rankings."
      onSubmit={handleSubmit}
      onSwitch={onSwitchToLogin}
      switchPrompt="Already have an account?"
      switchLabel="Log in"
      loading={loading}
      error={error}
    >
      <InputField
        label="Email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
      />
      <InputField
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Minimum 8 characters"
      />
      <InputField
        label="Confirm Password"
        type="password"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
        placeholder="••••••••"
      />
      {/* Guest option */}
      <div style={{
        textAlign: "center",
        marginBottom: "1rem",
        fontFamily: "var(--font-body)",
        fontSize: "0.8rem",
        color: "var(--text-muted)",
      }}>
        <span
          onClick={onContinueAsGuest}
          style={{ cursor: "pointer", textDecoration: "underline" }}
        >
          Continue as guest
        </span>
      </div>
    </AuthForm>
  );
}
