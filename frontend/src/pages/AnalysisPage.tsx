import { useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useCase } from "../hooks/useCases";
import { useCreateAnalysis, useAnalysisResult } from "../hooks/useAnalysis";
import { filesApi } from "../api/client";
import { getErrorMessage } from "../api/client";

function useQueryParams() {
  const { search } = useLocation();
  return new URLSearchParams(search);
}

function ArtifactImage({ path, alt }: { path: string; alt: string }) {
  const [src, setSrc] = useState("");
  const [error, setError] = useState(false);
  useEffect(() => {
    let cancelled = false;
    let blobUrl: string | null = null;
    filesApi.getArtifactUrl(path).then((url) => {
      if (cancelled) { URL.revokeObjectURL(url); return; }
      blobUrl = url;
      setSrc(url);
    }).catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; if (blobUrl) URL.revokeObjectURL(blobUrl); };
  }, [path]);
  if (error) return <div className="hint">Failed to load image</div>;
  if (!src) return <div className="hint">Loading...</div>;
  return <img src={src} alt={alt} style={{ maxWidth: "100%", borderRadius: "8px" }} />;
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const lower = verdict.toLowerCase();
  const cls = lower.includes("potential") || lower.includes("significant")
    ? "error"
    : lower.includes("minor") || lower.includes("moderate")
      ? "warning-inline"
      : "success-inline";
  return <div className={cls}>{verdict}</div>;
}

export function AnalysisPage() {
  const { caseId } = useParams();
  const query = useQueryParams();
  const imageId = Number(query.get("imageId"));
  const caseNumericId = Number(caseId);

  const { data: caseData } = useCase(caseNumericId);
  const createAnalysis = useCreateAnalysis();
  const [analysisId, setAnalysisId] = useState<number | null>(null);
  const { data: result } = useAnalysisResult(analysisId);

  const imageName = caseData?.images.find((img) => img.id === imageId)
    ? String(caseData.images.find((img) => img.id === imageId)!.metadata_json.filename ?? "Image")
    : "Image";

  async function handleStart() {
    try {
      const res = await createAnalysis.mutateAsync({ case_id: caseNumericId, image_id: imageId });
      setAnalysisId(res.id);
    } catch { /* mutation error rendered via hook */ }
  }

  const r = result?.results_json;
  const isRunning = result?.status === "running" || result?.status === "queued";
  const isDone = result?.status === "completed";

  return (
    <section className="card panel">
      <h2>Forensic Analysis</h2>
      <p className="selected-pill">Image: {imageName}</p>

      {!analysisId ? (
        <div>
          <p className="hint">
            Run forensic analysis to detect tampering, evaluate authenticity, and check for image manipulation.
          </p>
          <button onClick={handleStart} disabled={createAnalysis.isPending}>
            {createAnalysis.isPending ? "Starting..." : "Start Forensic Analysis"}
          </button>
          {createAnalysis.error ? <pre className="error">{getErrorMessage(createAnalysis.error)}</pre> : null}
        </div>
      ) : null}

      {isRunning ? (
        <div className="selected-pill">
          Status: {result?.status}...
          <div className="progress-bar-container">
            <div className="progress-bar" style={{ width: "50%" }} />
          </div>
        </div>
      ) : null}

      {result?.error_message ? <pre className="error">{result.error_message}</pre> : null}

      {isDone && r ? (
        <div className="grid metrics-grid">
          {/* ELA */}
          <section className="card panel">
            <h3>Error Level Analysis (ELA)</h3>
            <VerdictBadge verdict={r.ela?.verdict ?? "N/A"} />
            {r.ela?.image_path ? <ArtifactImage path={r.ela.image_path} alt="ELA heatmap" /> : null}
            <div className="hint">
              Mean error: {r.ela?.mean_error ?? "N/A"} | Max error: {r.ela?.max_error ?? "N/A"} | Suspicious pixels: {((r.ela?.suspicious_pixel_ratio ?? 0) * 100).toFixed(2)}%
            </div>
          </section>

          {/* Copy-Move */}
          <section className="card panel">
            <h3>Copy-Move Forgery Detection</h3>
            <VerdictBadge verdict={r.copy_move?.verdict ?? "N/A"} />
            {r.copy_move?.image_path ? <ArtifactImage path={r.copy_move.image_path} alt="Copy-move detection" /> : null}
            <div className="hint">
              Keypoints: {r.copy_move?.total_keypoints ?? 0} | Suspicious matches: {r.copy_move?.suspicious_matches ?? 0}
            </div>
          </section>

          {/* Noise Analysis */}
          <section className="card panel">
            <h3>Noise Pattern Analysis</h3>
            <VerdictBadge verdict={r.noise?.verdict ?? "N/A"} />
            {r.noise?.image_path ? <ArtifactImage path={r.noise.image_path} alt="Noise heatmap" /> : null}
            <div className="hint">
              Noise CV: {r.noise?.coefficient_of_variation?.toFixed(4) ?? "N/A"} | Inconsistent blocks: {r.noise?.inconsistent_blocks ?? 0}/{r.noise?.total_blocks ?? 0}
            </div>
          </section>

          {/* Metadata */}
          <section className="card panel">
            <h3>Metadata &amp; EXIF Analysis</h3>
            <div>
              <strong>Format:</strong> {r.metadata?.format} | <strong>Size:</strong> {r.metadata?.size.width}x{r.metadata?.size.height} | <strong>Mode:</strong> {r.metadata?.mode}
            </div>
            {r.metadata?.flags.map((flag, i) => (
              <div key={i} className={flag.toLowerCase().includes("no ") || flag.toLowerCase().includes("editing") ? "warning-inline" : "hint"} style={{ marginTop: "0.5rem" }}>
                {flag}
              </div>
            ))}
            {r.metadata?.exif && Object.keys(r.metadata.exif).length > 0 ? (
              <details style={{ marginTop: "1rem" }}>
                <summary className="hint" style={{ cursor: "pointer" }}>View EXIF data ({Object.keys(r.metadata.exif).length} fields)</summary>
                <table className="metrics-table">
                  <tbody>
                    {Object.entries(r.metadata.exif).map(([key, val]) => (
                      <tr key={key}><td>{key}</td><td>{String(val)}</td></tr>
                    ))}
                  </tbody>
                </table>
              </details>
            ) : null}
            {r.metadata?.gps ? (
              <div className="hint" style={{ marginTop: "0.5rem" }}>
                <strong>GPS data found:</strong> {JSON.stringify(r.metadata.gps)}
              </div>
            ) : null}
          </section>
        </div>
      ) : null}
    </section>
  );
}
