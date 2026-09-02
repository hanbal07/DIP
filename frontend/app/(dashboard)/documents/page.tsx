"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Files, Search, SearchX, UploadCloud, ArrowUpDown, X } from "lucide-react";
import { documentsApi, ApiError } from "@/lib/api";
import type { DocumentListResponse, DocumentListItem } from "@/lib/types";
import { DocumentCard } from "@/components/document-card";
import { UploadZone } from "@/components/upload-zone";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { PageHeader } from "@/components/page-header";
import { SkeletonCardGrid } from "@/components/skeleton-card-grid";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Reveal } from "@/components/motion/reveal";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 12;

const SORT_OPTIONS = [
  { value: "created_at", label: "Created date" },
  { value: "filename", label: "Filename" },
  { value: "document_type", label: "Document type" },
  { value: "status", label: "Status" },
  { value: "file_size", label: "File size" },
];

export default function DocumentsPage() {
  const { toast } = useToast();
  const [data, setData] = useState<DocumentListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [docType, setDocType] = useState("all");
  const [review, setReview] = useState("all");
  const [sort, setSort] = useState("created_at");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [refreshing, setRefreshing] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DocumentListItem | null>(null);
  const [deleting, setDeleting] = useState(false);
  const resultsRef = useRef<HTMLDivElement>(null);

  const load = useCallback(
    async (
      p: number,
      q: string,
      st: string,
      dt: string,
      rv: string,
      so: string,
      od: "asc" | "desc",
      silent = false
    ) => {
      if (!silent) setRefreshing(true);
      try {
        const res = await documentsApi.list({
          page: p,
          page_size: PAGE_SIZE,
          search: q || undefined,
          status: st !== "all" ? st : undefined,
          document_type: dt !== "all" ? dt : undefined,
          review_status: rv !== "all" ? rv : undefined,
          sort: so,
          order: od,
        });
        setData(res);
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Loading failed");
      } finally {
        setRefreshing(false);
      }
    },
    []
  );

  useEffect(() => {
    load(page, query, status, docType, review, sort, order);
  }, [page, query, status, docType, review, sort, order, load]);

  function applyAndLoad(next: Partial<{ q: string; st: string; dt: string; rv: string; so: string; od: "asc" | "desc" }>) {
    const merged = {
      q: query,
      st: status,
      dt: docType,
      rv: review,
      so: sort,
      od: order,
      ...next,
    };
    setQuery(merged.q);
    setStatus(merged.st);
    setDocType(merged.dt);
    setReview(merged.rv);
    setSort(merged.so);
    setOrder(merged.od);
    setPage(1);
  }

  function applySearch(e: React.FormEvent) {
    e.preventDefault();
    applyAndLoad({ q: search });
  }

  function clearFilters() {
    setSearch("");
    applyAndLoad({ q: "", st: "all", dt: "all", rv: "all", so: "created_at", od: "desc" });
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await documentsApi.del(deleteTarget.id);
      toast("success", "Document deleted");
      setDeleteTarget(null);
      load(page, query, status, docType, review, sort, order);
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const hasActiveFilters =
    query !== "" || status !== "all" || docType !== "all" || review !== "all" || sort !== "created_at" || order !== "desc";

  return (
    <div className="space-y-8">
      <Reveal>
        <PageHeader
          title="Documents"
          description="Upload, monitor, review, and manage every document in your workspace."
          icon={<Files className="size-5" />}
          actions={
            <a
              href="#upload"
              className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition-[background-color,box-shadow,transform] hover:bg-primary/90 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 active:scale-[0.98]"
            >
              <UploadCloud className="size-4" />
              Upload document
            </a>
          }
        />
      </Reveal>

      <Reveal>
        <Card id="upload">
          <CardHeader className="pb-3">
            <CardTitle>Upload & process</CardTitle>
          </CardHeader>
          <CardContent>
            <UploadZone
              multi
              buttonLabel="Upload & process"
              onUploaded={() => load(page, query, status, docType, review, sort, order)}
            />
          </CardContent>
        </Card>
      </Reveal>

      {/* Filters */}
      <Reveal>
        <Card>
          <CardContent className="space-y-3 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <form onSubmit={applySearch} className="relative min-w-[220px] flex-1 sm:max-w-xs">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search by filename…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9 pr-8"
                  aria-label="Search by filename"
                />
                {search && (
                  <button
                    type="button"
                    aria-label="Clear search"
                    onClick={() => {
                      setSearch("");
                      if (query) applyAndLoad({ q: "" });
                    }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-0.5 text-muted-foreground hover:text-foreground"
                  >
                    <X className="size-3.5" />
                  </button>
                )}
              </form>
              <Button type="submit" onClick={applySearch} variant="secondary">
                Search
              </Button>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Select value={status} onValueChange={(v) => applyAndLoad({ st: v })}>
                <SelectTrigger className="w-40" aria-label="Filter by status">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="pending">Queued</SelectItem>
                  <SelectItem value="processing">Processing</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>

              <Select value={docType} onValueChange={(v) => applyAndLoad({ dt: v })}>
                <SelectTrigger className="w-44" aria-label="Filter by document type">
                  <SelectValue placeholder="Document type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All types</SelectItem>
                  <SelectItem value="invoice">Invoice</SelectItem>
                  <SelectItem value="receipt">Receipt</SelectItem>
                  <SelectItem value="resume">Resume / CV</SelectItem>
                  <SelectItem value="contract">Contract</SelectItem>
                  <SelectItem value="report">Report</SelectItem>
                  <SelectItem value="research_paper">Research paper</SelectItem>
                  <SelectItem value="form">Form</SelectItem>
                  <SelectItem value="certificate">Certificate</SelectItem>
                  <SelectItem value="unknown">General</SelectItem>
                </SelectContent>
              </Select>

              <Select value={review} onValueChange={(v) => applyAndLoad({ rv: v })}>
                <SelectTrigger className="w-44" aria-label="Filter by review status">
                  <SelectValue placeholder="Review status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Review: all</SelectItem>
                  <SelectItem value="pending">Awaiting review</SelectItem>
                  <SelectItem value="reviewed">Reviewed</SelectItem>
                  <SelectItem value="not_required">Auto-verified</SelectItem>
                </SelectContent>
              </Select>

              <div className="flex items-center gap-1.5">
                <Select value={sort} onValueChange={(v) => applyAndLoad({ so: v })}>
                  <SelectTrigger className="w-40" aria-label="Sort by">
                    <SelectValue placeholder="Sort" />
                  </SelectTrigger>
                  <SelectContent>
                    {SORT_OPTIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value}>
                        {o.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  variant="outline"
                  size="icon"
                  aria-label={order === "desc" ? "Sort ascending" : "Sort descending"}
                  onClick={() => applyAndLoad({ od: order === "desc" ? "asc" : "desc" })}
                >
                  <ArrowUpDown className={cn("size-3.5 transition-transform", order === "asc" && "rotate-180")} />
                </Button>
              </div>

              {hasActiveFilters && (
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  <X className="size-3.5" />
                  Clear filters
                </Button>
              )}
            </div>

            {data && (
              <p className="text-xs text-muted-foreground">
                {data.total} document{data.total === 1 ? "" : "s"}
                {hasActiveFilters ? " matching filters" : " in workspace"}
              </p>
            )}
          </CardContent>
        </Card>
      </Reveal>

      {/* Results */}
      <div ref={resultsRef} className="space-y-4">
        {error && <ErrorBanner message={error} onRetry={() => load(page, query, status, docType, review, sort, order)} />}

        {refreshing && !data ? (
          <SkeletonCardGrid count={6} />
        ) : data && data.items.length > 0 ? (
          <Reveal reAnimate key={`${query}-${status}-${docType}-${review}-${sort}-${order}-${page}`}>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" key={page}>
              {data.items.map((d, i) => (
                <Reveal key={d.id} delay={i * 40}>
                  <DocumentCard doc={d} index={i} onDelete={setDeleteTarget} />
                </Reveal>
              ))}
            </div>
          </Reveal>
        ) : (
          <EmptyState
            icon={<SearchX className="size-5" />}
            title={hasActiveFilters ? "No matching documents" : "No documents yet"}
            description={
              hasActiveFilters
                ? "Try clearing the filters or changing your search query."
                : "Upload your first document and it will appear here with its status."
            }
            action={
              <Button variant="outline" onClick={clearFilters}>
                <X className="size-4" />
                Clear filters
              </Button>
            }
          />
        )}

        {data && data.total > 0 && (
          <div className="flex flex-col items-center justify-between gap-3 border-t border-border pt-4 sm:flex-row">
            <p className="text-sm text-muted-foreground">
              Page {page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                Previous
              </Button>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !deleting && setDeleteTarget(open ? deleteTarget : null)}
        title="Delete document?"
        description={
          deleteTarget
            ? `“${deleteTarget.filename}” and all of its extracted data, search index entries, and conversations will be permanently removed.`
            : ""
        }
        confirmLabel="Delete"
        destructive
        busy={deleting}
        onConfirm={confirmDelete}
      />
    </div>
  );
}

function ErrorBanner({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50/60 px-3 py-2.5 text-sm text-red-700 dark:border-red-900">
      <span>{message}</span>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Retry
      </Button>
    </div>
  );
}