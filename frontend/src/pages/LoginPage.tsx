import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function formatError(err: unknown): string {
  if (typeof err === "object" && err !== null && "message" in err) {
    return String((err as Error).message);
  }
  return String(err);
}

export function LoginPage() {
  const { isAuthenticated, isLoading, login, register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isRegister) {
        await register(email, password);
      } else {
        await login(email, password);
      }
      navigate("/dashboard", { replace: true });
    } catch (e) {
      setError(formatError(e));
    } finally {
      setLoading(false);
    }
  }

  if (isLoading) return <div className="loading-spinner">Loading...</div>;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  return (
    <section className="card auth-card">
      <h2>{isRegister ? "Create Account" : "Login"}</h2>
      <p className="hint">Secure access to your forensic enhancement workspace.</p>
      <form onSubmit={handleSubmit} className="form-grid auth-form">
        <label htmlFor="email">Email</label>
        <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label htmlFor="password">Password</label>
        <input id="password" type="password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required />
        {isRegister ? <small className="hint">Use at least 8 characters for password.</small> : null}
        <button type="submit" disabled={loading}>
          {loading ? "Please wait..." : isRegister ? "Register" : "Login"}
        </button>
      </form>
      <button className="link-btn" onClick={() => setIsRegister((s) => !s)}>
        {isRegister ? "Use existing account" : "Create new account"}
      </button>
      {error ? <pre className="error">{error}</pre> : null}
    </section>
  );
}
