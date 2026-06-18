// --- Error ---

export interface ApiError {
  status: number;
  message: string;
  fieldErrors?: Record<string, string[]>;
}

// --- Auth ---

export interface TokenResponse {
  access_token: string;
}

// --- Case ---

export interface ImageAsset {
  id: number;
  case_id: number;
  original_path: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface Case {
  id: number;
  title: string;
  description?: string | null;
  created_at: string;
  images: ImageAsset[];
}

export interface CreateCaseRequest {
  title: string;
  description?: string;
}

// --- Run ---

export interface ROI {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface CreateRunRequest {
  case_id: number;
  image_id: number;
  models: string[];
  scale: number;
  roi?: ROI | null;
  reference_image_id?: number | null;
  reference_text?: string | null;
  preprocess?: string;       // "auto" | "deblur" | "none"
  denoise_strength?: number; // 0-30, default 10
}

export interface Run {
  id: number;
  case_id: number;
  status: string;
  progress: number;
  config_json: Record<string, unknown>;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface RunOutput {
  model_name: string;
  output_path: string;
  diff_path?: string | null;
  roi_compare_path?: string | null;
}

export interface RunMetric {
  model_name: string;
  psnr?: number | null;
  lpips?: number | null;
  ssim?: number | null;
  ocr_json: {
    available?: boolean;
    text?: string;
    confidence?: number | null;
    normalized_edit_distance?: number | null;
    note?: string | null;
  };
  face_json: {
    available?: boolean;
    score?: number | null;
    note?: string | null;
  };
}

export interface RunResults {
  run: Run;
  outputs: RunOutput[];
  metrics: RunMetric[];
  disclaimer: string;
}

// --- Experiment ---

export interface CreateExperimentRequest {
  name: string;
  dataset_path: string;
  mode: string;
  models: string[];
  limit?: number;
  low_res_dir?: string;
  high_res_dir?: string;
}

export interface Experiment {
  id: number;
  name: string;
  dataset_path: string;
  status: string;
  config_json: Record<string, unknown>;
  summary_json: Record<string, unknown>;
  csv_path?: string | null;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

// --- Report ---

export interface GenerateReportRequest {
  case_id?: number | null;
  experiment_id?: number | null;
  title?: string;
}

export interface Export {
  id: number;
  type: string;
  source_id: number;
  file_path: string;
  created_at: string;
}

// --- Analysis ---

export interface AnalysisRequest {
  case_id: number;
  image_id: number;
}

export interface AnalysisResult {
  id: number;
  case_id: number;
  image_id: number;
  status: string;
  results_json: {
    ela?: {
      verdict: string;
      mean_error: number;
      max_error: number;
      suspicious_pixel_ratio: number;
      image_path?: string;
    };
    metadata?: {
      format: string;
      mode: string;
      size: { width: number; height: number };
      exif: Record<string, string>;
      flags: string[];
      gps?: Record<string, string>;
    };
    copy_move?: {
      verdict: string;
      total_keypoints: number;
      suspicious_matches: number;
      image_path?: string;
    };
    noise?: {
      verdict: string;
      mean_noise: number;
      coefficient_of_variation: number;
      inconsistent_blocks: number;
      total_blocks: number;
      image_path?: string;
    };
  } | null;
  error_message?: string | null;
}

// --- SSE ---

export interface RunProgressEvent {
  progress: number;
  status: string;
  message?: string;
}
