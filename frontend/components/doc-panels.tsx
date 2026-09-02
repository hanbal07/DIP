"use client";

import { useState } from "react";
import {
  PencilLine,
  CheckCircle2,
  Sparkles,
  FileText,
  Table2,
  Users,
  Download,
  CircleAlert,
  Loader2,
} from "lucide-react";
import { documentsApi, formatPercent, ApiError } from "@/lib/api";
import type {
  ExtractionRead,
  EntityRead,
  TableRead,
  PageRead,
  JobRead,
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

// ------------------------------------------------------------------ summary

export function SummaryPanel({
  summary,
  generated,
}: {
  summary: string | null;
  generated: boolean;
}) {
  if (!summary) {
    return (
      <p className="text-sm text-muted-foreground">
        No summary available yet for this document.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      {generated && (
        <Badge variant="info">
          <Sparkles className="size-3" />
          AI-generated summary
        </Badge>
      )}
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">{summary}</p>
    </div>
  );
}

// ------------------------------------------------------------ extraction/review

export function ExtractionPanel({
  extraction,
  documentId,
  onReviewed,
}: {
  extraction: ExtractionRead;
  documentId: string;
  onReviewed?: (updated: ExtractionRead) => void;
}) {
  const { toast } = useToast();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const effective = { ...extraction.raw_data, ...extraction.corrected_data };
  const fields = Object.keys(extraction.raw_data);

  function startEdit() {
    const initial: Record<string, string> = {};
    for (const k of fields) {
      const v = effective[k];
      initial[k] = Array.isArray(v) ? JSON.stringify(v) : v == null ? "" : String(v);
    }
    setDraft(initial);
    setEditing(true);
  }

  async function saveReview() {
    setSaving(true);
    try {
      const corrections = fields
        .filter((f) => draft[f] !== (effective[f] == null ? "" : String(effective[f])))
        .map((f) => {
          const raw = draft[f];
          let parsed: unknown = raw;
          try {
            parsed = JSON.parse(raw);
          } catch {
            parsed = raw;
          }
          return { field: f, value: parsed };
        });
      const updated = await documentsApi.review(documentId, corrections);
      toast("success", corrections.length ? "Corrections saved" : "No changes to save");
      setEditing(false);
      onReviewed?.(updated);
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Review failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={extraction.needs_review ? "warning" : "success"}>
          {extraction.needs_review ? "Needs review" : "Reviewed"}
        </Badge>
        <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          Confidence
          <ConfidenceMeter value={extraction.confidence} />
        </span>
        {!editing && (
          <Button variant="outline" size="sm" onClick={startEdit} className="ml-auto">
            <PencilLine className="size-3.5" />
            Review / correct
          </Button>
        )}
      </div>

      {extraction.needs_review && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50/70 px-3 py-2.5 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300">
          <CircleAlert className="mt-0.5 size-3.5 shrink-0" />
          Model confidence was low for this document type. Please verify the extracted
          values — raw model output and human corrections are kept separately.
        </div>
      )}

      <dl className="grid gap-3 sm:grid-cols-2">
        {fields.map((f) => {
          const raw = extraction.raw_data[f];
          const corrected = extraction.corrected_data[f];
          const display = corrected !== undefined ? corrected : raw;
          const isCorrected = corrected !== undefined && corrected !== raw;
          return (
            <div key={f} className="rounded-lg border border-border bg-card p-3 shadow-sm transition-colors hover:border-foreground/15">
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {f.replace(/_/g, " ")}
              </dt>
              <dd className="mt-1 text-sm text-foreground">
                {Array.isArray(display)
                  ? display.map((x: unknown, i: number) => (
                      <span key={i} className="block">
                        {typeof x === "object" && x !== null ? JSON.stringify(x) : String(x)}
                      </span>
                    ))
                  : display == null ? (
                      <span className="italic text-muted-foreground">Not found</span>
                    ) : (
                      String(display)
                    )}
                {isCorrected && (
                  <Badge variant="success" className="ml-1.5 align-middle">
                    corrected
                  </Badge>
                )}
              </dd>
            </div>
          );
        })}
      </dl>

      {editing && (
        <div className="animate-fade-in space-y-3 rounded-lg border border-primary/25 bg-primary/[0.03] p-4">
          <p className="text-sm font-semibold text-foreground">Correct extracted values</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {fields.map((f) => (
              <label key={f} className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground">
                  {f.replace(/_/g, " ")}
                </span>
                <Input
                  value={draft[f] ?? ""}
                  onChange={(e) => setDraft((d) => ({ ...d, [f]: e.target.value }))}
                />
              </label>
            ))}
          </div>
          <div className="flex gap-2">
            <Button size="sm" onClick={saveReview} disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  <CheckCircle2 className="size-3.5" />
                  Save corrections
                </>
              )}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
        <span
          className={cn(
            "block h-full rounded-full transition-all duration-500",
            pct >= 80 ? "bg-emerald-500" : pct >= 55 ? "bg-amber-500" : "bg-red-500"
          )}
          style={{ width: `${pct}%` }}
        />
      </span>
      <span className="font-medium text-foreground">{formatPercent(value)}</span>
    </span>
  );
}

// ------------------------------------------------------------------ entities

export function EntitiesPanel({ entities }: { entities: EntityRead[] }) {
  if (!entities.length) {
    return (
      <EmptyState
        icon={<Users className="size-5" />}
        title="No entities detected"
        description="Entities like people, organizations, dates, and amounts will appear here after processing."
      />
    );
  }
  const grouped = entities.reduce<Record<string, EntityRead[]>>((acc, e) => {
    (acc[e.entity_type] ??= []).push(e);
    return acc;
  }, {});
  return (
    <div className="space-y-4">
      {Object.entries(grouped).map(([type, list]) => (
        <div key={type}>
          <div className="mb-1.5 flex items-center gap-2">
            <Badge variant="outline" className="uppercase">{type}</Badge>
            <span className="text-xs text-muted-foreground">{list.length}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {list.map((e) => (
              <span
                key={e.id}
                className="group flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1.5 text-sm shadow-sm transition-colors hover:border-foreground/20"
              >
                <span className="text-foreground">{e.value}</span>
                {e.confidence < 0.8 && (
                  <span className="text-amber-600 dark:text-amber-400">
                    {Math.round(e.confidence * 100)}%
                  </span>
                )}
                {e.page_number && (
                  <span className="text-xs text-muted-foreground">p{e.page_number}</span>
                )}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------- tables

export function TablesPanel({
  tables,
  onExport,
}: {
  tables: TableRead[];
  onExport?: () => void;
}) {
  if (!tables.length) {
    return (
      <EmptyState
        icon={<Table2 className="size-5" />}
        title="No tables detected"
        description="Extracted tables will appear here with pagination and confidence scores."
      />
    );
  }
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {tables.length} table{tables.length === 1 ? "" : "s"} detected
        </p>
        {onExport && (
          <Button variant="outline" size="sm" onClick={onExport}>
            <Download className="size-3.5" />
            Export CSV
          </Button>
        )}
      </div>
      {tables.map((t) => (
        <div key={t.id} className="animate-fade-in overflow-hidden rounded-lg border border-border shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-muted/40 px-3 py-2 text-sm">
            <span className="font-medium text-foreground">
              Table {t.table_index + 1} · page {t.page_number}
            </span>
            <ConfidenceMeter value={t.confidence} />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              {t.headers.length > 0 && (
                <thead>
                  <tr>
                    {t.headers.map((h, i) => (
                      <th key={i} className="border-b bg-muted/20 px-3 py-2 text-left font-semibold text-foreground">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
              )}
              <tbody>
                {t.rows.map((row, i) => (
                  <tr key={i} className="transition-colors hover:bg-muted/30">
                    {row.map((cell, j) => (
                      <td key={j} className="border-b px-3 py-2">{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

// ------------------------------------------------------------- processing status

const STAGE_LABELS: Record<string, string> = {
  queued: "Queued",
  validating: "Validating",
  inspecting: "Inspecting file",
  classifying: "Classifying type",
  pages: "Extracting pages",
  text_extraction: "Extracting text",
  ocr: "OCR",
  normalization: "Normalizing text",
  sections: "Detecting sections",
  tables: "Detecting tables",
  extraction: "Structured extraction",
  chunking: "Chunking",
  embedding: "Embedding",
  persist: "Persisting",
  completed: "Complete",
};

export function ProcessingStatus({ job }: { job: JobRead | null }) {
  if (!job) {
    return <p className="text-sm text-muted-foreground">No processing job.</p>;
  }
  const stageKeys = Object.keys(job.stages || {});
  const total = Math.max(stageKeys.length, 1);
  const done = stageKeys.filter((k) => job.stages[k]?.status === "completed").length;
  const pct = Math.round((done / total) * 100);
  const current = stageKeys.find((k) => job.stages[k]?.status === "running") ?? null;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <Badge variant="info">
          <Loader2 className="size-3 animate-spin" />
          {job.status}
        </Badge>
        <span className="text-muted-foreground">{done}/{total} stages · {pct}%</span>
      </div>
      <Progress value={pct} aria-label="Processing progress" />
      {current && (
        <p className="text-xs text-muted-foreground">
          Currently: <span className="font-medium text-foreground">{STAGE_LABELS[current] ?? current}</span>
        </p>
      )}
      {job.error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">
          {job.error}
        </p>
      )}
      <ul className="grid gap-1.5 sm:grid-cols-2">
        {stageKeys.map((k) => {
          const s = job.stages[k];
          return (
            <li
              key={k}
              className={cn(
                "flex items-center justify-between rounded-md border px-2.5 py-1.5 text-xs transition-colors",
                s?.status === "completed"
                  ? "border-emerald-200 bg-emerald-50/50 dark:border-emerald-900 dark:bg-emerald-950/30"
                  : s?.status === "failed"
                  ? "border-red-200 bg-red-50/50 dark:border-red-900 dark:bg-red-950/30"
                  : s?.status === "running"
                  ? "border-primary/30 bg-primary/5"
                  : "border-border bg-card"
              )}
            >
              <span className="text-muted-foreground">{STAGE_LABELS[k] ?? k}</span>
              {s?.status === "running" ? (
                <Loader2 className="size-3 animate-spin text-primary" />
              ) : (
                <Badge
                  variant={
                    s?.status === "completed"
                      ? "success"
                      : s?.status === "failed"
                      ? "destructive"
                      : "warning"
                  }
                >
                  {s?.status ?? "pending"}
                </Badge>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// --------------------------------------------------------------------- pages

export function PagesPanel({ pages }: { pages: PageRead[] }) {
  if (!pages.length) {
    return (
      <EmptyState
        icon={<FileText className="size-5" />}
        title="No page text"
        description="Extracted page text will appear here after processing."
      />
    );
  }
  return (
    <div className="space-y-4">
      {pages.map((p) => (
        <div key={p.id} className="animate-fade-in overflow-hidden rounded-lg border border-border shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-muted/40 px-3 py-2 text-sm">
            <span className="flex items-center gap-1.5 font-medium text-foreground">
              <FileText className="size-3.5 text-muted-foreground" />
              Page {p.page_number}
            </span>
            <div className="flex items-center gap-2">
              {p.section && <Badge variant="secondary">{p.section}</Badge>}
              {p.ocr_confidence > 0 && (
                <span className="text-xs text-muted-foreground">
                  OCR <ConfidenceMeter value={p.ocr_confidence} />
                </span>
              )}
            </div>
          </div>
          <div className="max-h-96 overflow-auto bg-card/60 p-3">
            {p.text ? (
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">{p.text}</p>
            ) : (
              <p className="text-sm italic text-muted-foreground">No text</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}