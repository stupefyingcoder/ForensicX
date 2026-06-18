import type {
  AnalysisRequest,
  AnalysisResult,
  ApiError,
  Case,
  CreateCaseRequest,
  CreateExperimentRequest,
  CreateRunRequest,
  Experiment,
  Export,
  GenerateReportRequest,
  ImageAsset,
  Run,
  RunResults,
  TokenResponse,
} from "./types";

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://127.0.0.1:8000/api";

const REQUEST_TIMEOUT_MS = 10_000;

// --- Auth error callback (set by AuthContext) ---

let onAuthError: (() => void) | null = null;

export function setAuthErrorHandler(handler: () => void) {
  onAuthError = handler;
}

// --- Token access (set by AuthContext) ---

let getToken: (() => string | null) | null = null;

export function setTokenGetter(getter: () => string | null) {
  getToken = getter;
}

// --- Error normalization ---

function isApiError(value: unknown): value is ApiError {
  return typeof value === "object" && value !== null && "status" in value && "message" in value;
}

export function getErrorMessage(err: unknown): string {
  if (isApiError(err)) return err.message;
  if (err instanceof Error) return err.message;
  return String(err);
}

async function parseError(response: Response): Promise<ApiError> {
  const status = response.status;
  try {
    const body = await response.json();
    // FastAPI validation errors
    if (Array.isArray(body.detail)) {
      const fieldErrors: Record<string, string[]> = {};
      let message = "Validation error";
      for (const err of body.detail) {
        const field = Array.isArray(err.loc) ? err.loc[err.loc.length - 1] : "unknown";
        const msg =
          err.type === "string_too_short"
            ? `Must be at least ${err.ctx?.min_length ?? "?"} characters`
            : (err.msg ?? "Invalid");
        fieldErrors[field] = fieldErrors[field] ?? [];
        fieldErrors[field].push(msg);
        message = msg;
      }
      return { status, message, fieldErrors };
    }
    // FastAPI string detail
    if (typeof body.detail === "string") {
      return { status, message: body.detail };
    }
    return { status, message: body.message ?? response.statusText };
  } catch {
    return { status, message: response.statusText || "Request failed" };
  }
}

// --- Core request method ---

type RequestOptions = {
  body?: unknown;
  formData?: FormData;
  timeout?: number;
};

async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), opts.timeout ?? REQUEST_TIMEOUT_MS);

  const headers: Record<string, string> = {};
  const token = getToken?.();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: opts.formData ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
      signal: controller.signal,
    });

    if (!response.ok) {
      const error = await parseError(response);
      if (error.status === 401 && onAuthError) onAuthError();
      throw error;
    }

    const text = await response.text();
    return text ? JSON.parse(text) : ({} as T);
  } catch (err) {
    if (isApiError(err)) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      throw { status: 0, message: "Request timed out" } satisfies ApiError;
    }
    throw { status: 0, message: String(err) } satisfies ApiError;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function requestBlob(path: string): Promise<string> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);

  const headers: Record<string, string> = {};
  const token = getToken?.();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  try {
    const response = await fetch(`${API_BASE}${path}`, { headers, signal: controller.signal });
    if (!response.ok) {
      const error = await parseError(response);
      if (error.status === 401 && onAuthError) onAuthError();
      throw error;
    }
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  } catch (err) {
    if (isApiError(err)) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      throw { status: 0, message: "Download timed out" } satisfies ApiError;
    }
    throw { status: 0, message: String(err) } satisfies ApiError;
  } finally {
    clearTimeout(timeoutId);
  }
}

// --- Auth ---

export const authApi = {
  register: (email: string, password: string) =>
    request<TokenResponse>("POST", "/auth/register", { body: { email, password } }),
  login: (email: string, password: string) =>
    request<TokenResponse>("POST", "/auth/login", { body: { email, password } }),
  logout: () => request<void>("POST", "/auth/logout"),
};

// --- Cases ---

export const casesApi = {
  list: () => request<Case[]>("GET", "/cases"),
  get: (id: number) => request<Case>("GET", `/cases/${id}`),
  create: (data: CreateCaseRequest) => request<Case>("POST", "/cases", { body: data }),
  uploadImage: (caseId: number, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<ImageAsset>("POST", `/cases/${caseId}/images`, { formData });
  },
};

// --- Runs ---

export const runsApi = {
  create: (data: CreateRunRequest) => request<Run>("POST", "/runs", { body: data }),
  getStatus: (id: number) => request<Run>("GET", `/runs/${id}`),
  getResults: (id: number) => request<RunResults>("GET", `/runs/${id}/results`),
};

// --- Experiments ---

export const experimentsApi = {
  create: (data: CreateExperimentRequest) =>
    request<Experiment>("POST", "/experiments/batch", { body: data }),
  getSummary: (id: number) => request<Experiment>("GET", `/experiments/${id}/summary`),
  getCsvBlob: (id: number) => requestBlob(`/experiments/${id}/csv`),
};

// --- Reports ---

export const reportsApi = {
  generate: (data: GenerateReportRequest) =>
    request<Export>("POST", "/reports/generate", { body: data }),
  getBlob: (id: number) => requestBlob(`/reports/${id}`),
};

// --- Analysis ---

export const analysisApi = {
  create: (data: AnalysisRequest) => request<AnalysisResult>("POST", "/analysis", { body: data }),
  get: (id: number) => request<AnalysisResult>("GET", `/analysis/${id}`),
};

// --- Files ---

export const filesApi = {
  getArtifactUrl: (path: string) =>
    requestBlob(`/files?path=${encodeURIComponent(path)}`),
};
