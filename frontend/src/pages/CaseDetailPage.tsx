import { FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useCase, useUploadImage } from "../hooks/useCases";
import { getErrorMessage } from "../api/client";

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB

export function CaseDetailPage() {
  const { caseId } = useParams();
  const id = Number(caseId);
  const { data, isLoading, error: fetchError } = useCase(id);
  const upload = useUploadImage(id);
  const [files, setFiles] = useState<File[]>([]);
  const [uploadInputKey, setUploadInputKey] = useState(0);
  const [info, setInfo] = useState("");
  const [fileError, setFileError] = useState("");

  async function handleUpload(event: FormEvent) {
    event.preventDefault();
    if (files.length === 0) return;
    const oversized = files.find((file) => file.size > MAX_FILE_SIZE);
    if (oversized) {
      setFileError(`"${oversized.name}" is too large. Maximum size is 20MB.`);
      return;
    }
    setFileError("");
    setInfo("");
    try {
      const uploaded = [];
      for (const selectedFile of files) {
        uploaded.push(await upload.mutateAsync(selectedFile));
      }
      setFiles([]);
      setUploadInputKey((value) => value + 1);
      setInfo(`Uploaded ${uploaded.length} image${uploaded.length === 1 ? "" : "s"} successfully.`);
    } catch {
      // error available via upload.error
    }
  }

  if (isLoading) return <p className="hint">Loading case...</p>;

  return (
    <div className="grid case-grid">
      <section className="card panel">
        <h2>Case</h2>
        <p className="case-title">{data?.title}</p>
        <p className="muted">{data?.description}</p>
        <form onSubmit={handleUpload} className="form-grid">
          <label htmlFor="upload-image">Upload Images</label>
          <input
            key={uploadInputKey}
            id="upload-image"
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
          />
          <button type="submit" disabled={files.length === 0 || upload.isPending}>
            {upload.isPending ? "Uploading..." : `Upload ${files.length || ""}`.trim()}
          </button>
        </form>
      </section>
      <section className="card panel">
        <h2>Images</h2>
        <ul className="list">
          {data?.images.map((img) => (
            <li key={img.id}>
              <span className="item-name">{String(img.metadata_json.filename ?? img.original_path)}</span>
              <Link className="item-link" to={`/cases/${id}/run?imageId=${img.id}`}>Run Comparison</Link>
              <Link className="item-link" to={`/cases/${id}/analysis?imageId=${img.id}`}>Analyze</Link>
            </li>
          ))}
        </ul>
        {data && data.images.length === 0 ? <small className="hint">No images uploaded in this case yet.</small> : null}
        {info ? <div className="success-inline">{info}</div> : null}
        {fileError ? <pre className="error">{fileError}</pre> : null}
        {upload.error ? <pre className="error">{getErrorMessage(upload.error)}</pre> : null}
        {fetchError ? <pre className="error">{getErrorMessage(fetchError)}</pre> : null}
      </section>
    </div>
  );
}
