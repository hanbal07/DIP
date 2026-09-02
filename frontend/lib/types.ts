// Shared TypeScript types matching the backend Pydantic schemas.

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export type DocumentStatus =
  | "pending"
  | "uploaded"
  | "processing"
  | "completed"
  | "failed"
  | "needs_review"
  | "deleted";

export interface DocumentListItem {
  id: string;
  filename: string;
  content_type: string;
  file_size: number;
  document_type: string;
  status: DocumentStatus;
  review_status: string;
  page_count: number;
  is_scanned: boolean;
  text_method: string | null;
  title: string | null;
  created_at: string;
  processed_at: string | null;
  error_message: string | null;
}

export interface DocumentDetail extends DocumentListItem {
  summary: string | null;
  summary_is_generated: boolean;
  processing_meta: Record<string, unknown>;
}

export interface DocumentListResponse {
  items: DocumentListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface TaskResponse {
  document_id: string;
  job_id: string;
  status: string;
  message: string;
}

export interface JobRead {
  id: string;
  document_id: string;
  status: string;
  current_stage: string | null;
  stages: Record<string, { status: string; error?: string }>;
  attempts: number;
  max_attempts: number;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface PageRead {
  id: string;
  page_number: number;
  text: string;
  section: string | null;
  char_count: number;
  ocr_confidence: number;
  has_preview: boolean;
}

export interface EntityRead {
  id: string;
  entity_type: string;
  value: string;
  confidence: number;
  page_number: number | null;
  occurrences: number;
}

export interface TableRead {
  id: string;
  page_number: number;
  table_index: number;
  headers: string[];
  rows: string[][];
  confidence: number;
  source: string | null;
}

export interface ExtractionRead {
  id: string;
  document_id: string;
  schema_type: string;
  raw_data: Record<string, unknown>;
  corrected_data: Record<string, unknown>;
  confidence: number;
  needs_review: boolean;
  review_status: string;
  corrections: { field: string; from?: unknown; to?: unknown; by?: string }[];
  source_refs: Record<string, unknown>;
  reviewed_at: string | null;
}

export interface SearchHit {
  document_id: string;
  document_filename: string;
  page_number: number;
  chunk_index: number;
  section: string | null;
  text: string;
  score: number;
  snippet: string;
}

export interface SearchResponse {
  query: string;
  hits: SearchHit[];
  total: number;
}

export interface CitationOut {
  document_id: string;
  document_filename: string;
  page_number: number;
  snippet: string;
  score: number;
}

export interface ChatResponse {
  answer: string;
  conversation_id: string;
  question: string;
  citations: CitationOut[];
  has_sufficient_evidence: boolean;
  used_document_ids: string[];
  model?: string | null;
}

export interface MessageOut {
  id: string;
  role: string;
  content: string;
  created_at: string;
  citations: Record<string, unknown>[];
}

export interface ConversationOut {
  id: string;
  document_id: string | null;
  title: string | null;
  created_at: string;
  updated_at: string;
}
