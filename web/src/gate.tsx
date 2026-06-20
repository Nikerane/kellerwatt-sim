import React, { useState } from "react";
import ReactDOM from "react-dom/client";

/**
 * Soft password gate for the simulator. The password lives in the bundle, so
 * this keeps out casual visitors — not a determined one. It blocks the app from
 * mounting (the simulator never renders into the DOM) until unlocked, and
 * remembers the unlock for the browser session.
 */
const PASSWORD = "kellerwatt";
const STORAGE_KEY = "kw_sim_unlocked";

function isUnlocked(): boolean {
  try {
    return sessionStorage.getItem(STORAGE_KEY) === "yes";
  } catch {
    return false;
  }
}

function Gate({ onUnlock }: { onUnlock: () => void }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value === PASSWORD) {
      try {
        sessionStorage.setItem(STORAGE_KEY, "yes");
      } catch {
        /* sessionStorage unavailable — proceed for this view only */
      }
      onUnlock();
    } else {
      setError(true);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--gk-hearth, #1F3A34)",
        color: "var(--gk-bone, #F5F1EA)",
        fontFamily: "var(--gk-font-sans, Inter, sans-serif)",
        padding: "24px",
      }}
    >
      <div style={{ width: "100%", maxWidth: "380px" }}>
        <p
          style={{
            fontFamily: "var(--gk-font-mono, monospace)",
            fontSize: "11px",
            letterSpacing: "0.22em",
            textTransform: "uppercase",
            color: "var(--gk-ember, #E89B4F)",
            margin: "0 0 16px",
          }}
        >
          Private
        </p>
        <h1
          style={{
            fontFamily: "var(--gk-font-serif, Fraunces, serif)",
            fontWeight: 500,
            fontSize: "32px",
            lineHeight: 1.1,
            letterSpacing: "-0.02em",
            color: "var(--gk-bone, #F5F1EA)",
            margin: "0 0 12px",
          }}
        >
          KellerWatt Simulator
        </h1>
        <p
          style={{
            fontSize: "15px",
            lineHeight: 1.5,
            color: "rgba(245, 241, 234, 0.72)",
            margin: "0 0 28px",
          }}
        >
          This tool is private. Enter the access password to continue.
        </p>
        <form onSubmit={submit}>
          <input
            type="password"
            value={value}
            autoFocus
            aria-label="Access password"
            placeholder="Password"
            onChange={(e) => {
              setValue(e.target.value);
              setError(false);
            }}
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "14px 16px",
              fontSize: "15px",
              fontFamily: "var(--gk-font-sans, Inter, sans-serif)",
              color: "var(--gk-bone, #F5F1EA)",
              background: "rgba(245, 241, 234, 0.06)",
              border: error
                ? "1px solid var(--gk-clay, #D98A7A)"
                : "1px solid rgba(245, 241, 234, 0.22)",
              borderRadius: "12px",
              outline: "none",
            }}
          />
          {error && (
            <p
              style={{
                color: "var(--gk-clay, #D98A7A)",
                fontSize: "13px",
                margin: "10px 2px 0",
              }}
            >
              Incorrect password. Try again.
            </p>
          )}
          <button
            type="submit"
            style={{
              width: "100%",
              marginTop: "16px",
              padding: "14px 20px",
              fontSize: "15px",
              fontWeight: 500,
              fontFamily: "var(--gk-font-sans, Inter, sans-serif)",
              color: "#3A1F08",
              background: "var(--gk-ember, #E89B4F)",
              border: "none",
              borderRadius: "12px",
              cursor: "pointer",
            }}
          >
            Unlock
          </button>
        </form>
      </div>
    </div>
  );
}

/**
 * Render `appNode` into #root, but only after the gate is unlocked. Shares a
 * single React root so the gate swaps cleanly into the app on success.
 */
export function withGate(appNode: React.ReactNode): void {
  const root = ReactDOM.createRoot(document.getElementById("root")!);
  const renderApp = () =>
    root.render(<React.StrictMode>{appNode}</React.StrictMode>);

  if (isUnlocked()) {
    renderApp();
  } else {
    root.render(<Gate onUnlock={renderApp} />);
  }
}
