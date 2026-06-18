import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { ApiError } from "../api/types";

function formatError(err: unknown): string {
  if (typeof err === "object" && err !== null && "message" in err) {
    const apiErr = err as ApiError;
    if (apiErr.fieldErrors?.password) return apiErr.fieldErrors.password[0];
    if (apiErr.fieldErrors?.email) return apiErr.fieldErrors.email[0];
    return apiErr.message;
  }
  return String(err);
}

export function LoginPage() {
  const { login, register } = useAuth();
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
      navigate("/", { replace: true });
    } catch (e) {
      setError(formatError(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card auth-card">
      <h2>{isRegister ? "Create Account" : "Login"}</h2>
      <p className="hint">Secure access to your forensic enhancement workspace.</p>
      <form onSubmit={handleSubmit} className="form-grid auth-form">
        <label htmlFor="email">Email</label>
        <input id="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label htmlFor="password">Password</label>
        <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
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
