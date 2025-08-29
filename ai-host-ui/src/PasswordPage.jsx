import { useState } from "react";

export default function PasswordPage({ onSuccess }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  // Read expected password from Vite env variable prefixed with VITE_
  const expected = import.meta.env.VITE_APP_PASSWORD || "password";

  const handleSubmit = (e) => {
    e.preventDefault();
    if (password === expected) {
      localStorage.setItem("ai_ui_auth", "true");
      onSuccess();
    } else {
      setError("Incorrect password");
    }
  };

  return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#f3f4f6" }}>
      <form onSubmit={handleSubmit} style={{ width: 360, padding: 24, borderRadius: 8, background: "white", boxShadow: "0 6px 18px rgba(0,0,0,0.06)" }}>
        <h2 style={{ margin: "0 0 12px 0", fontSize: 20, color: "#111827" }}>Enter access password</h2>
        <p style={{ margin: "0 0 18px 0", color: "#6b7280" }}>This page is protected — enter the password to continue.</p>

        <input
          type="password"
          value={password}
          onChange={(e) => { setPassword(e.target.value); setError(""); }}
          placeholder="Password"
          style={{ width: "100%", padding: "10px 12px", borderRadius: 6, border: "1px solid #e5e7eb", marginBottom: 12 }}
        />

        {error && <div style={{ color: "#dc2626", marginBottom: 12 }}>{error}</div>}

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button type="submit" style={{ padding: "10px 14px", borderRadius: 6, background: "#2563eb", color: "white", border: "none", cursor: "pointer" }}>
            Unlock
          </button>
        </div>

        <div style={{ marginTop: 14, fontSize: 12, color: "#9ca3af" }}>
          Hint: Configure the password using the Vite env variable <code style={{ background: "#f9fafb", padding: '2px 6px', borderRadius: 4 }}>VITE_APP_PASSWORD</code> at build time.
        </div>
      </form>
    </div>
  );
}
