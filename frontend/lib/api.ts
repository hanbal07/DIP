// API client. In this frontend the auth token is stored in localStorage and sent via
// the Authorization header. Never logs tokens or document contents.

import type {
  ChatResponse,
  ConversationOut,
  DocumentDetail,
  DocumentListResponse,
  EntityRead,
  ExtractionRead,
  JobRead,
  MessageOut,
  PageRead,
  SearchResponse,
  TableRead,
  TaskResponse,
  Token,
  User,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const TOKEN_KEY = "dip_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = true
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = (body as { detail?: string }).detail || message;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(message, res.status);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

// ---------------------------------------------------------------------- auth
export const authApi = {
  register: (data: { email: string; password: string; full_name?: string }) =>
    request<Token>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }, false),
  login: (data: { email: string; password: string }) =>
    request<Token>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }, false),
  me: () => request<User>("/auth/me"),
  changePassword: (data: { current_password: string; new_password: string }) =>
    request<{ message: string }>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// ------------------------------------------------------------------ documents
export const documentsApi = {
  list: (params: Record<string, string | number | undefined> = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    });
    return request<DocumentListResponse>(`/documents?${qs.toString()}`);
  },
  get: (id: string) => request<DocumentDetail>(`/documents/${id}`),
  upload: (file: File, description?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (description) form.append("description", description);
    return request<TaskResponse>("/documents", { method: "POST", body: form });
  },
  del: (id: string) => request<{ message: string }>(`/documents/${id}`, { method: "DELETE" }),
  extraction: (id: string) => request<ExtractionRead>(`/documents/${id}/extraction`),
  review: (id: string, corrections: { field: string; value: unknown }[]) =>
    request<ExtractionRead>(`/documents/${id}/extraction/review`, {
      method: "PUT",
      body: JSON.stringify({ corrections }),
    }),
  pages: (id: string) => request<PageRead[]>(`/documents/${id}/pages`),
  entities: (id: string) => request<EntityRead[]>(`/documents/${id}/entities`),
  tables: (id: string) => request<TableRead[]>(`/documents/${id}/tables`),
  jobs: (id: string) => request<JobRead[]>(`/documents/${id}/jobs`),
  exportCsv: async (id: string) => {
    const token = getToken();
    const res = await fetch(`${API_URL}/documents/${id}/export/csv`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new ApiError("Export failed", res.status);
    return res.text();
  },
};

// -------------------------------------------------------------------- search
export const searchApi = {
  search: (q: string, documentId?: string, limit = 10) => {
    const qs = new URLSearchParams({ q, limit: String(limit) });
    if (documentId) qs.set("document_id", documentId);
    return request<SearchResponse>(`/search?${qs.toString()}`);
  },
};

// ---------------------------------------------------------------------- chat
export const chatApi = {
  chat: (data: {
    question: string;
    conversation_id?: string;
    document_ids?: string[];
  }) => request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify(data) }),
  conversations: () => request<ConversationOut[]>("/chat/conversations"),
  messages: (conversationId: string) =>
    request<MessageOut[]>(`/chat/conversations/${conversationId}/messages`),
  deleteConversation: (conversationId: string) =>
    request<{ message: string }>(`/chat/conversations/${conversationId}`, {
      method: "DELETE",
    }),
};

// ------------------------------------------------------------------- health
export const healthApi = {
  health: () =>
    request<{
      status: string;
      version: string;
      environment: string;
      database: string;
      redis: string;
      ai_mode: string;
    }>("/health", {}, false),
};

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export function formatPercent(v: number): string {
  return `${Math.round(v * 100)}%`;
}
