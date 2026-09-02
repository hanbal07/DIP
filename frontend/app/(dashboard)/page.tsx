"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Files,
  CheckCircle2,
  Loader2,
  AlertTriangle,
  ClipboardCheck,
  Sparkles,
  Search,
  UploadCloud,
  RefreshCw,
  Activity,
} from "lucide-react";
import { documentsApi, healthApi, ApiError } from "@/lib/api";
import type { DocumentListResponse, DocumentListItem } from "@/lib/types";
import { UploadZone } from "@/components/upload-zone";
import { DocumentCard } from "@/components/document-card";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SkeletonCardGrid } from "@/components/skeleton-card-grid";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/motion/reveal";
import { useToast } from "@/components/ui/toast";

interface Counts {
  total: number;
  completed: number;
  processing: number;
  queued: number;
  failed: number;
  awaitingReview: number;
}

const EMPTY_COUNTS: Counts = {
  total: 0,
  completed: 0,
  processing: 0,
  queued: 0,
  failed: 0,
  awaitingReview: 0,
};

async function fetchCount(
  filters: Record<string, string | number | undefined>
): Promise<number> {
  const res = await documentsApi.list({ page: 1, page_size: 1, ...filters });
  return res.total;
}

export default function DashboardPage() {
  const { toast } = useToast();
  const [counts, setCounts] = useState<Counts>(EMPTY_COUNTS);
  const [recent, setRecent] = useState<DocumentListResponse | null>(null);
  const [inFlight, setInFlight] = useState<DocumentListItem[]>([]);
  const [health, setHealth] = useState<{ status: string; database: string; ai_mode: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DocumentListItem | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    try {
      const [total, completed, processing, queued, failed, awaitingReview, recentRes, inFlightRes] =
        await Promise.allSettled([
          fetchCount({}),
          fetchCount({ status: "completed" }),
          fetchCount({ status: "processing" }),
          fetchCount({ status: "pending" }),
          fetchCount({ status: "failed" }),
          fetchCount({ review_status: "pending" }),
          documentsApi.list({ page: 1, page_size: 6 }),
          documentsApi.list({ page: 1, page_size: 20, status: "processing" }),
        ]);

      const num = (r: PromiseSettledResult<number>) => (r.status === "fulfilled" ? r.value : 0);
      const doc = (r: PromiseSettledResult<DocumentListResponse>) =>
        r.status === "fulfilled" ? r.value : null;

      setCounts({
        total: num(total),
        completed: num(completed),
        processing: num(processing),
        queued: num(queued),
        failed: num(failed),
        awaitingReview: num(awaitingReview),
      });
      const recentData = doc(recentRes);
      setRecent(recentData);
      const inFlightData = doc(inFlightRes);
      setInFlight(inFlightData?.items ?? []);
      setError(total.status === "rejected" ? "Unable to load some dashboard data." : null);
    } catch {
      setError("Unable to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Lightweight periodic refresh so long-running jobs show up without manual reloads.
  useEffect(() => {
    const t = window.setInterval(load, 20000);
    return () => window.clearInterval(t);
  }, [load]);

  useEffect(() => {
    healthApi
      .health()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await documentsApi.del(deleteTarget.id);
      toast("success", "Document deleted");
      setDeleteTarget(null);
      load();
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  }

  const inProgress = counts.processing + counts.queued;

  return (
    <div className="space-y-8">
      <Reveal>
        <PageHeader
          title="Dashboard"
          description="Monitor your document pipeline: uploads, extraction, review, and AI assistance."
          icon={<Activity className="size-5" />}
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

      {/* KPI cards */}
      {loading ? (
        <SkeletonCardGrid count={5} />
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
          <Reveal delay={0}>
            <StatCard label="Total documents" value={counts.total} icon={<Files className="size-4" />} />
          </Reveal>
          <Reveal delay={40}>
            <StatCard
              label="Completed"
              value={counts.completed}
              tone="success"
              icon={<CheckCircle2 className="size-4" />}
            />
          </Reveal>
          <Reveal delay={80}>
            <StatCard
              label="In progress"
              value={inProgress}
              tone="info"
              icon={<Loader2 className="size-4" />}
              hint={counts.queued > 0 ? `${counts.queued} queued` : undefined}
            />
          </Reveal>
          <Reveal delay={120}>
            <StatCard
              label="Awaiting review"
              value={counts.awaitingReview}
              tone="warning"
              icon={<ClipboardCheck className="size-4" />}
              hint="Low-confidence extractions"
            />
          </Reveal>
          <Reveal delay={160}>
            <StatCard
              label="Failed"
              value={counts.failed}
              tone="destructive"
              icon={<AlertTriangle className="size-4" />}
            />
          </Reveal>
        </div>
      )}

      {/* Quick actions */}
      <Reveal>
        <div className="grid gap-3 sm:grid-cols-3">
          <QuickAction href="/documents" icon={<UploadCloud className="size-4" />} title="Upload document" description="Add files to the pipeline" />
          <QuickAction href="/search" icon={<Search className="size-4" />} title="Semantic search" description="Find meaning, not just keywords" />
          <QuickAction href="/ask" icon={<Sparkles className="size-4" />} title="Ask AI" description="Chat with your documents" />
        </div>
      </Reveal>

      {/* Upload + system */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Upload & process</CardTitle>
          </CardHeader>
          <CardContent>
            <UploadZone
              multi
              buttonLabel="Upload & process"
              onUploaded={() => load()}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!health ? (
              <Skeleton className="h-24" />
            ) : (
              <>
                <HealthRow label="API" value={health.status} ok={health.status === "ok"} />
                <HealthRow label="Database" value={health.database} ok={health.database === "ok"} />
                <HealthRow label="AI provider" value={health.ai_mode} ok={Boolean(health.ai_mode)} />
                <p className="border-t pt-3 text-xs leading-relaxed text-muted-foreground">
                  Uploaded documents are validated, OCR’d, classified, and extracted
                  in the background.
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* In-flight */}
      {!loading && inFlight.length > 0 && (
        <Reveal>
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground">Processing now</h2>
              <Link href="/documents" className="text-sm font-medium text-primary hover:underline">
                View all
              </Link>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {inFlight.map((d, i) => (
                <Reveal key={d.id} delay={i * 40}>
                  <div className="flex items-center gap-3 rounded-lg border border-border bg-card p-3 shadow-sm">
                    <Loader2 className="size-4 shrink-0 animate-spin-slow text-info" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{d.filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {d.status === "pending" ? "Queued" : "Processing"} · {d.page_count || "…"} pages
                      </p>
                    </div>
                  </div>
                </Reveal>
              ))}
            </div>
          </section>
        </Reveal>
      )}

      {/* Recent documents */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">Recent documents</h2>
          <Link href="/documents" className="text-sm font-medium text-primary hover:underline">
            View all
          </Link>
        </div>

        {loading ? (
          <SkeletonCardGrid count={3} />
        ) : recent && recent.items.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {recent.items.map((d, i) => (
              <Reveal key={d.id} delay={i * 45}>
                <DocumentCard doc={d} index={i} onDelete={setDeleteTarget} />
              </Reveal>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Files className="size-5" />}
            title="No documents yet"
            description="Upload your first document to start classifying, extracting, and searching."
            action={
              <Button asChild variant="outline">
                <Link href="/documents">
                  <UploadCloud className="size-4" />
                  Go to documents
                </Link>
              </Button>
            }
          />
        )}
      </section>

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

function QuickAction({
  href,
  icon,
  title,
  description,
}: {
  href: string;
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <Link
      href={href}
      className="group rounded-xl border border-border bg-card p-4 shadow-sm transition-[transform,box-shadow,border-color] duration-200 hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-card-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="flex items-center gap-3">
        <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">{title}</p>
          <p className="truncate text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
    </Link>
  );
}

function HealthRow({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="flex items-center gap-1.5 font-medium capitalize">
        <span
          className={`size-2 rounded-full ${
            ok ? "bg-emerald-500" : "bg-amber-500"
          }`}
          aria-hidden
        />
        {value}
      </span>
    </div>
  );
}