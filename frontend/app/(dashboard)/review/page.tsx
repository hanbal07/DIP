"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ClipboardCheck, ArrowRight, RefreshCw, Inbox } from "lucide-react";
import { documentsApi, ApiError, formatBytes } from "@/lib/api";
import type { DocumentListItem } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonCardGrid } from "@/components/skeleton-card-grid";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/motion/reveal";
import { DocumentTypeLabel } from "@/components/status-badge";

export default function ReviewPage() {
  const [items, setItems] = useState<DocumentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await documentsApi.list({
        page: 1,
        page_size: 50,
        review_status: "pending",
        sort: "created_at",
        order: "desc",
      });
      setItems(res.items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Loading failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Documents move into review when processing completes, so refresh periodically.
  useEffect(() => {
    const t = window.setInterval(load, 30000);
    return () => window.clearInterval(t);
  }, [load]);

  return (
    <div className="space-y-8">
      <Reveal>
        <PageHeader
          title="Needs review"
          description="Documents where model confidence was low. Verify extracted values to finalize."
          icon={<ClipboardCheck className="size-5" />}
          actions={
            <Button variant="outline" size="sm" onClick={load}>
              <RefreshCw className={loading ? "animate-spin-slow" : ""} />
              Refresh
            </Button>
          }
        />
      </Reveal>

      {error && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50/60 px-3 py-2.5 text-sm text-red-700 dark:border-red-900">
          {error} <button className="ml-2 font-medium underline underline-offset-2" onClick={load}>Retry</button>
        </div>
      )}

      {loading ? (
        <SkeletonCardGrid count={5} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Inbox className="size-5" />}
          title="All caught up"
          description="No documents are awaiting review right now. Completed low-confidence extractions will land here."
        />
      ) : (
        <div className="space-y-3">
          <Reveal>
            <p className="text-sm text-muted-foreground">
              {items.length} document{items.length === 1 ? "" : "s"} awaiting review
            </p>
          </Reveal>
          <div className="grid gap-3 sm:grid-cols-2">
            {items.map((d, i) => (
              <Reveal key={d.id} delay={i * 40}>
                <ReviewRow doc={d} />
              </Reveal>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ReviewRow({ doc }: { doc: DocumentListItem }) {
  return (
    <div className="group flex items-center gap-3 rounded-xl border border-border bg-card p-4 shadow-sm transition-[transform,box-shadow,border-color] hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-card-hover">
      <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-600 dark:bg-amber-500/15 dark:text-amber-400">
        <ClipboardCheck className="size-5" />
      </div>
      <div className="min-w-0 flex-1">
        <Link
          href={`/documents/${doc.id}?tab=extraction`}
          className="inline-flex max-w-full items-center gap-1 font-medium text-foreground hover:text-primary"
        >
          <span className="truncate">{doc.filename}</span>
        </Link>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="secondary">
            <DocumentTypeLabel type={doc.document_type} />
          </Badge>
          <span>{formatBytes(doc.file_size)}</span>
          {doc.page_count > 0 && <span>· {doc.page_count} pages</span>}
        </div>
      </div>
      <Link
        href={`/documents/${doc.id}?tab=extraction`}
        className="inline-flex size-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors group-hover:bg-primary group-hover:text-primary-foreground"
        aria-label={`Review ${doc.filename}`}
      >
        <ArrowRight className="size-4" />
      </Link>
    </div>
  );
}