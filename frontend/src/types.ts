export interface Segment {
  start: number;
  end: number;
  text: string;
}

export interface JobError {
  code: string;
  message: string;
}

export interface Job {
  id: string;
  status: "queued" | "processing" | "completed" | "failed";
  created_at: string;
  completed_at?: string;
  file_name: string;
  file_size: number;
  model: string;
  language: string;
  detected_language?: string;
  progress: number;
  duration_seconds?: number;
  segments?: Segment[];
  error?: JobError;
}

export type ModelOption = "tiny" | "base" | "small";
