import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useRunStatus, useRunResults } from "../hooks/useRuns";
import { useRunProgress } from "../hooks/useRunProgress";
import { useCase } from "../hooks/useCases";
import { filesApi } from "../api/client";
import { DisclaimerBanner } from "../components/DisclaimerBanner";
import type { ImageAsset, RunMetric } from "../api/types";

function fmtMetric(value: number | null | undefined, digits = 4): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return value.toFixed(digits);
}

function ArtifactImage({ path, alt }: { path: string; alt: string }) {
  const [src, setSrc] = useState<string>("");
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
  return <img src={src} alt={alt} />;
}

function imageName(image: ImageAsset | undefined): string {
  if (!image) return "";
  return String(image.metadata_json.filename ?? image.original_path);
}

function configNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function CompareSlider({ beforePath, afterPath, title }: { beforePath: string; afterPath: string; title: string }) {
  const [position, setPosition] = useState(50);
  const [beforeSrc, setBeforeSrc] = useState("");
  const [afterSrc, setAfterSrc] = useState("");

  useEffect(() => {
    let cancelled = false;
    let revokeBefore: string | null = null;
    let revokeAfter: string | null = null;
    filesApi.getArtifactUrl(beforePath).then((url) => {
      if (cancelled) { URL.revokeObjectURL(url); return; }
      revokeBefore = url;
      setBeforeSrc(url);
    }).catch(() => {});
    filesApi.getArtifactUrl(afterPath).then((url) => {
      if (cancelled) { URL.revokeObjectURL(url); return; }
      revokeAfter = url;
      setAfterSrc(url);
    }).catch(() => {});
    return () => {
      cancelled = true;
      if (revokeBefore) URL.revokeObjectURL(revokeBefore);
      if (revokeAfter) URL.revokeObjectURL(revokeAfter);
    };
  }, [beforePath, afterPath]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowLeft") setPosition((p) => Math.max(0, p - 2));
    if (e.key === "ArrowRight") setPosition((p) => Math.min(100, p + 2));
  }

  if (!beforeSrc || !afterSrc) return <div className="hint">Loading comparison...</div>;

  return (
    <div>
      <small>{title}</small>
      <div className="compare-slider" style={{ ["--split" as string]: `${position}%` }}>
        <img src={beforeSrc} alt={`${title} baseline`} />
        <div className="compare-after">
          <img src={afterSrc} alt={`${title} enhanced`} />
        </div>
        <div className="compare-handle" />
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={position}
        onChange={(e) => setPosition(Number(e.target.value))}
        onKeyDown={handleKeyDown}
        className="compare-range"
        aria-label={`${title} comparison slider`}
      />
    </div>
  );
}

function hasQualityMetrics(m: RunMetric): boolean {
  return m.psnr !== null || m.lpips !== null || m.ssim !== null;
}

function MetricsTable({ metrics }: { metrics: RunMetric[] }) {
  const hasQuality = metrics.some(hasQualityMetrics);
  const hasOcr = metrics.some((m) => m.ocr_json.available);

  return (
    <div>
      {/* Quality Metrics Table */}
      {hasQuality ? (
        <>
          <div className="metric-section-label">QUALITY METRICS</div>
          <table className="metrics-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>PSNR</th>
                <th>SSIM</th>
                <th>LPIPS</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => (
                <tr key={m.model_name}>
                  <td className="model-name-cell">{m.model_name}</td>
                  <td className={m.psnr != null ? "metric-value" : "metric-na"}>{fmtMetric(m.psnr, 2)}</td>
                  <td className={m.ssim != null ? "metric-value" : "metric-na"}>{fmtMetric(m.ssim, 4)}</td>
                  <td className={m.lpips != null ? "metric-value" : "metric-na"}>{fmtMetric(m.lpips, 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <div className="metric-hint-box">
          <div className="metric-section-label">QUALITY METRICS</div>
          <span className="hint">Select a Quality Reference Image when creating the run to enable PSNR, SSIM, and LPIPS comparison.</span>
        </div>
      )}

      {/* OCR Results */}
      {hasOcr ? (
        <>
          <div className="metric-section-label" style={{ marginTop: "1.5rem" }}>OCR EXTRACTION</div>
          <table className="metrics-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Detected Text</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {metrics.filter((m) => m.ocr_json.available).map((m) => (
                <tr key={m.model_name}>
                  <td className="model-name-cell">{m.model_name}</td>
                  <td>{m.ocr_json.text?.trim() || "(no text detected)"}</td>
                  <td className="metric-value">{m.ocr_json.confidence != null ? `${m.ocr_json.confidence.toFixed(1)}%` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <div className="metric-hint-box" style={{ marginTop: "1.5rem" }}>
          <div className="metric-section-label">OCR EXTRACTION</div>
          <span className="hint">{metrics[0]?.ocr_json.note || "Install Tesseract OCR to enable text extraction from enhanced images."}</span>
        </div>
      )}

    </div>
  );
}

export function MetricsPage() {
  const { runId } = useParams();
  const id = Number(runId);

  if (!runId || isNaN(id) || id <= 0) {
    return <section className="card panel"><h2>Invalid run ID</h2></section>;
  }

  const { data: status } = useRunStatus(id);
  const isComplete = status?.status === "completed";
  const isFailed = status?.status === "failed";
  const { data: results } = useRunResults(id, isComplete);
  const { data: caseData } = useCase(status?.case_id ?? 0);

  useRunProgress(id);

  const inputImageId = configNumber(status?.config_json.image_id);
  const referenceImageId = configNumber(status?.config_json.reference_image_id);
  const inputImage = caseData?.images.find((img) => img.id === inputImageId);
  const referenceImage = caseData?.images.find((img) => img.id === referenceImageId);
  const bicubicOutput = results?.outputs.find((o) => o.model_name === "bicubic");

  return (
    <section className="card panel">
      <h2>Run Results</h2>
      <DisclaimerBanner />
      {status ? (
        <div className="selected-pill">
          Status: {status.status} ({status.progress}%)
          {!isComplete && !isFailed ? (
            <div className="progress-bar-container">
              <div className="progress-bar" style={{ width: `${status.progress}%` }} />
            </div>
          ) : null}
        </div>
      ) : (
        <p className="hint">Loading run status...</p>
      )}
      {status?.error_message ? <pre className="error">{status.error_message}</pre> : null}
      {results ? (
        <div className="grid metrics-grid">
          <section className="card panel">
            <h3>Enhanced Outputs</h3>
            <ul className="list">
              {results.outputs.map((o) => (
                <li key={o.model_name}>
                  <div className="model-name-cell">{o.model_name}</div>
                  <div className="artifact-grid comparison-grid">
                    {inputImage ? (
                      <div>
                        <small>Original: {imageName(inputImage)}</small>
                        <ArtifactImage path={inputImage.original_path} alt="original input" />
                      </div>
                    ) : null}
                    {referenceImage ? (
                      <div>
                        <small>Reference: {imageName(referenceImage)}</small>
                        <ArtifactImage path={referenceImage.original_path} alt="quality reference" />
                      </div>
                    ) : (
                      <div className="artifact-placeholder">
                        <small>Reference</small>
                        <span className="hint">No quality reference selected.</span>
                      </div>
                    )}
                    <div>
                      <small>Enhanced</small>
                      <ArtifactImage path={o.output_path} alt={`${o.model_name} output`} />
                    </div>
                    {bicubicOutput && o.model_name !== "bicubic" ? (
                      <CompareSlider
                        beforePath={bicubicOutput.output_path}
                        afterPath={o.output_path}
                        title={`${o.model_name} vs bicubic`}
                      />
                    ) : null}
                    {o.diff_path && o.model_name !== "bicubic" ? (
                      <div>
                        <small>Diff Map vs Bicubic</small>
                        <ArtifactImage path={o.diff_path} alt={`${o.model_name} diff`} />
                      </div>
                    ) : null}
                    {o.roi_compare_path && o.model_name !== "bicubic" ? (
                      <div>
                        <small>ROI Detail</small>
                        <ArtifactImage path={o.roi_compare_path} alt={`${o.model_name} roi compare`} />
                      </div>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          </section>
          <section className="card panel">
            <h3>Analysis</h3>
            <MetricsTable metrics={results.metrics} />
          </section>
        </div>
      ) : null}
    </section>
  );
}
