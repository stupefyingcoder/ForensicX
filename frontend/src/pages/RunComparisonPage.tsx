import { FormEvent, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useCase, useUploadImage } from "../hooks/useCases";
import { useCreateRun } from "../hooks/useRuns";
import { getErrorMessage } from "../api/client";

function useQueryParams() {
  const { search } = useLocation();
  return useMemo(() => new URLSearchParams(search), [search]);
}

export function RunComparisonPage() {
  const { caseId } = useParams();
  const query = useQueryParams();
  const imageId = Number(query.get("imageId"));
  const caseNumericId = Number(caseId);

  const { data: caseData } = useCase(caseNumericId);
  const createRun = useCreateRun();
  const uploadRef = useUploadImage(caseNumericId);

  const [includeRealesr, setIncludeRealesr] = useState(true);
  const [includeX4plus, setIncludeX4plus] = useState(false);
  const [includeBicubic, setIncludeBicubic] = useState(true);
  const [includeBsrgan, setIncludeBsrgan] = useState(false);
  const [referenceImageId, setReferenceImageId] = useState("");
  const [referenceText, setReferenceText] = useState("");
  const [preprocess, setPreprocess] = useState("auto");
  const [denoiseStrength, setDenoiseStrength] = useState(10);
  const [referenceUploadFiles, setReferenceUploadFiles] = useState<File[]>([]);
  const [uploadInputKey, setUploadInputKey] = useState(0);
  const [info, setInfo] = useState("");
  const [error, setError] = useState("");

  const imageOptions = useMemo(() => {
    return (caseData?.images ?? []).map((img) => ({
      id: img.id,
      label: String(img.metadata_json.filename ?? img.original_path),
    }));
  }, [caseData]);

  const selectedInputName = useMemo(() => {
    const match = (caseData?.images ?? []).find((img) => img.id === imageId);
    return match ? String(match.metadata_json.filename ?? match.original_path) : null;
  }, [caseData, imageId]);

  const selectedQualityIsInput = referenceImageId !== "" && Number(referenceImageId) === imageId;

  async function submit(event: FormEvent) {
    event.preventDefault();
    const models: string[] = [];
    if (includeRealesr) models.push("realesrgan");
    if (includeX4plus) models.push("realesrgan_x4plus");
    if (includeBicubic) models.push("bicubic");
    if (includeBsrgan) models.push("bsrgan");
    if (models.length === 0) {
      setError("Select at least one model.");
      return;
    }
    if (selectedQualityIsInput) {
      setError("Quality reference cannot be the same as input image.");
      return;
    }
    setError("");
    setInfo("");
    try {
      await createRun.mutateAsync({
        case_id: caseNumericId,
        image_id: imageId,
        models,
        scale: 4,
        reference_image_id: referenceImageId ? Number(referenceImageId) : null,
        reference_text: referenceText || null,
        preprocess,
        denoise_strength: denoiseStrength,
      });
    } catch { /* mutation error rendered via hook */ }
  }

  async function handleReferenceUpload(event: FormEvent) {
    event.preventDefault();
    if (referenceUploadFiles.length === 0) return;
    setError("");
    setInfo("");
    try {
      const uploaded = [];
      for (const file of referenceUploadFiles) {
        uploaded.push(await uploadRef.mutateAsync(file));
      }
      const lastUploaded = uploaded[uploaded.length - 1];
      if (lastUploaded) {
        setReferenceImageId(String(lastUploaded.id));
      }
      setReferenceUploadFiles([]);
      setUploadInputKey((v) => v + 1);
      setInfo(`Uploaded ${uploaded.length} reference image${uploaded.length === 1 ? "" : "s"}. The last upload is selected for quality metrics.`);
    } catch { /* mutation error rendered via hook */ }
  }

  return (
    <section className="card panel">
      <h2>Run Comparison</h2>
      {selectedInputName ? <p className="selected-pill">Selected image: {selectedInputName}</p> : null}
      <form onSubmit={submit} className="form-grid run-form">
        <label>Enhancement methods to compare</label>
        <small className="hint">
          Tick the methods you want to run on this image. Each one cleans up the picture in a
          different way — running several lets you compare the results side by side and judge which
          is the most trustworthy for this piece of evidence. We suggest always keeping{" "}
          <strong>Bicubic</strong> ticked as a neutral reference.
        </small>

        <div className="model-option">
          <label className="check-row">
            <input type="checkbox" checked={includeBicubic} onChange={(e) => setIncludeBicubic(e.target.checked)} /> Bicubic — plain enlargement (baseline)
          </label>
          <small className="hint">
            A simple resize with <strong>no AI</strong> — it just makes the image bigger without
            inventing anything. Use it as your honest reference point: any detail the AI methods
            show that Bicubic does not is <strong>AI-generated</strong> and must be treated with
            caution, not as real recovered evidence.
          </small>
        </div>

        <div className="model-option">
          <label className="check-row">
            <input type="checkbox" checked={includeRealesr} onChange={(e) => setIncludeRealesr(e.target.checked)} /> Real-ESRGAN — general clean-up (recommended)
          </label>
          <small className="hint">
            The best all-round first choice. Designed for everyday real-world evidence — CCTV
            stills, phone photos, screenshots and compressed or noisy images. Sharpens faces,
            text and object edges while reducing graininess. Fast.
          </small>
        </div>

        <div className="model-option">
          <label className="check-row">
            <input type="checkbox" checked={includeX4plus} onChange={(e) => setIncludeX4plus(e.target.checked)} /> Real-ESRGAN x4plus — high detail (slower)
          </label>
          <small className="hint">
            A heavier version that rebuilds finer detail on very low-resolution or heavily
            pixelated images. Reach for this when the standard Real-ESRGAN result still looks soft.
            Takes noticeably longer to run.
          </small>
        </div>

        <div className="model-option">
          <label className="check-row">
            <input type="checkbox" checked={includeBsrgan} onChange={(e) => setIncludeBsrgan(e.target.checked)} /> BSRGAN — heavy real-world damage
          </label>
          <small className="hint">
            Trained to undo several kinds of damage at once — blur, compression artefacts and
            sensor noise combined. Best for old, scanned, or badly compressed evidence. Heavier
            to run.
          </small>
        </div>

        <div className="model-option">
          <label className="check-row check-row-disabled">
            <input type="checkbox" checked={false} disabled /> SRGAN — currently unavailable
          </label>
          <small className="hint">
            Temporarily disabled: this model&rsquo;s file is not installed on the server. Ask your
            administrator to enable it.
          </small>
        </div>
        <label>Image preparation (before enhancement)</label>
        <select value={preprocess} onChange={(e) => setPreprocess(e.target.value)}>
          <option value="auto">Auto — check for blur and fix it if needed (recommended)</option>
          <option value="deblur">Always sharpen blur</option>
          <option value="none">None — enhance the image exactly as-is</option>
        </select>
        <small className="hint">
          A first pass that sharpens motion/out-of-focus blur <em>before</em> the enhancement
          methods run. <strong>Auto</strong> is recommended — it only sharpens when it actually
          detects blur, so a clear image is left untouched.
        </small>
        {preprocess !== "none" ? (
          <>
            <label>Noise removal strength: {denoiseStrength}</label>
            <input type="range" min={0} max={30} value={denoiseStrength} onChange={(e) => setDenoiseStrength(Number(e.target.value))} />
            <small className="hint">
              Controls how aggressively graininess/speckle is smoothed away. Higher numbers give a
              cleaner image but can erase fine detail (e.g. skin texture, small text). Default 10 is
              a safe balance — only raise it for very noisy footage.
            </small>
          </>
        ) : null}
        <label>Known text in the image (optional)</label>
        <input value={referenceText} onChange={(e) => setReferenceText(e.target.value)} placeholder="e.g. a number plate or sign you already know" />
        <small className="hint">
          If you already know some text that appears in the image — a number plate, a door sign, a
          serial number — type it here. The app then measures how accurately each method makes that
          text readable, giving you an objective score for which enhancement recovered the text best.
        </small>
        <label>Quality reference image (optional — unlocks the accuracy scores)</label>
        <select value={referenceImageId} onChange={(e) => setReferenceImageId(e.target.value)}>
          <option value="">None</option>
          {imageOptions.map((opt) => (<option key={opt.id} value={opt.id}>{opt.label}</option>))}
        </select>
        <small className="hint">
          <strong>What this is:</strong> a clearer, higher-quality picture of the <em>same</em>
          {" "}person, object or scene — for example a sharp reference mugshot, or a better photo of
          the same vehicle.
          <br />
          <strong>Why it matters:</strong> the numeric quality scores (PSNR, SSIM, LPIPS) work by
          comparing each enhanced result against a known-good &ldquo;correct answer&rdquo;. Without a
          reference, the app has nothing to measure against, so those scores stay blank and you can
          only judge the results by eye. Adding one turns the comparison from an opinion into
          objective, defensible numbers.
          <br />
          <strong>If you don&rsquo;t have one:</strong> that&rsquo;s fine — leave it as
          &ldquo;None&rdquo;. Enhancement still runs and you can compare the images visually; you
          just won&rsquo;t get the accuracy scores. (The reference is only a measuring stick — it is
          never mixed into the enhanced output.)
        </small>
        {selectedQualityIsInput ? (
          <div className="warning-inline">Selected quality reference is same as input. Pick another image.</div>
        ) : null}
        <button type="submit" disabled={selectedQualityIsInput || createRun.isPending}>
          {createRun.isPending ? "Starting..." : "Start Run"}
        </button>
      </form>

      <form onSubmit={handleReferenceUpload} className="form-grid top-gap">
        <label>Add a new quality reference image</label>
        <small className="hint">
          Upload a clearer photo of the same subject to use as the &ldquo;correct answer&rdquo; for
          the accuracy scores above. Once uploaded, the newest one is selected automatically.
        </small>
        <input
          key={uploadInputKey}
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => setReferenceUploadFiles(Array.from(e.target.files ?? []))}
        />
        <button type="submit" disabled={referenceUploadFiles.length === 0 || uploadRef.isPending}>
          {uploadRef.isPending ? "Uploading..." : `Upload ${referenceUploadFiles.length || ""} Reference Image${referenceUploadFiles.length === 1 ? "" : "s"}`.trim()}
        </button>
      </form>

      {createRun.data ? (
        <p className="success-inline">
          Run created successfully. <Link to={`/runs/${createRun.data.id}/metrics`}>View Metrics</Link>
        </p>
      ) : null}
      {info ? <div className="success-inline">{info}</div> : null}
      {error ? <pre className="error">{error}</pre> : null}
      {createRun.error ? <pre className="error">{getErrorMessage(createRun.error)}</pre> : null}
      {uploadRef.error ? <pre className="error">{getErrorMessage(uploadRef.error)}</pre> : null}
    </section>
  );
}
