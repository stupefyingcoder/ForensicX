import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCases, useCreateCase } from "../hooks/useCases";
import { getErrorMessage } from "../api/client";

export function DashboardPage() {
  const navigate = useNavigate();
  const { data: cases, isLoading, error: fetchError } = useCases();
  const createCase = useCreateCase();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    try {
      const created = await createCase.mutateAsync({ title, description: description || undefined });
      setTitle("");
      setDescription("");
      navigate(`/cases/${created.id}`);
    } catch { /* mutation error rendered via hook */ }
  }

  return (
    <div className="grid dashboard-grid">
      <section className="card panel">
        <h2>Create Case</h2>
        <p className="hint">Group related evidence images into organized investigation cases.</p>
        <form onSubmit={handleCreate} className="form-grid">
          <label htmlFor="case-title">Title</label>
          <input id="case-title" value={title} onChange={(e) => setTitle(e.target.value)} required />
          <label htmlFor="case-desc">Description</label>
          <textarea id="case-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
          <button type="submit" disabled={createCase.isPending}>
            {createCase.isPending ? "Creating..." : "Create"}
          </button>
        </form>
        {createCase.error ? <pre className="error">{getErrorMessage(createCase.error)}</pre> : null}
      </section>

      <section className="card panel">
        <h2>Cases</h2>
        {isLoading ? <p className="hint">Loading cases...</p> : null}
        <ul className="list">
          {cases?.map((item) => (
            <li key={item.id}>
              <Link className="item-link" to={`/cases/${item.id}`}>{item.title}</Link>
              <span className="muted">{new Date(item.created_at).toLocaleString()}</span>
            </li>
          ))}
        </ul>
        {cases && cases.length === 0 ? <small className="hint">No cases yet. Create your first case to begin.</small> : null}
        {fetchError ? <pre className="error">{getErrorMessage(fetchError)}</pre> : null}
      </section>
    </div>
  );
}
