"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { FileText, Download, ArrowLeft, Loader2 } from "lucide-react";
import { documentsApi, chatApi, ApiError, formatBytes } from "@/lib/api";
import type {
  DocumentDetail,
  ExtractionRead,
  EntityRead,
  TableRead,
  PageRead,
  JobRead,
  ConversationOut,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { StatusBadge, ReviewBadge, DocumentTypeLabel } from "@/components/status-badge";
import {
  SummaryPanel,
  ExtractionPanel,
  EntitiesPanel,
  TablesPanel,
  ProcessingStatus,
  PagesPanel,
} from "@/components/doc-panels";
import { ChatPanel } from "@/components/chat-panel";
import { EmptyPane } from "@/components/empty-pane";
import { Reveal } from "@/components/motion/reveal";

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const docId = params.id;
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();

  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [extraction, setExtraction] = useState<ExtractionRead | null>(null);
  const [entities, setEntities] = useState<EntityRead[]>([]);
  const [tables, setTables] = useState<TableRead[]>([]);
  const [pages, setPages] = useState<PageRead[]>([]);
  const [jobs, setJobs] = useState<JobRead[]>([]);
  const [conversations, setConversations] = useState<ConversationOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const isProcessing = useRef(false);

  const load = useCallback(async () => {
    if (!docId) return;
    try {
      const d = await documentsApi.get(docId);
      setDoc(d);
      const [ex, en, tb, pg, jb, conv] = await Promise.allSettled([
        documentsApi.extraction(docId).catch(() => null),
        documentsApi.entities(docId).catch(() => []),
        documentsApi.tables(docId).catch(() => []),
        documentsApi.pages(docId).catch(() => []),
        documentsApi.jobs(docId).catch(() => []),
        chatApi.conversations().catch(() => []),
      ]);
      if (ex.status === "fulfilled") setExtraction(ex.value);
      if (en.status === "fulfilled") setEntities(en.value);
      if (tb.status === "fulfilled") setTables(tb.value);
      if (pg.status === "fulfilled") setPages(pg.value);
      if (jb.status === "fulfilled") setJobs(jb.value);
      if (conv.status === "fulfilled") setConversations(conv.value);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load document");
    }
  }, [docId]);

  useEffect(() => {
    load();
  }, [load]);

  // Poll while processing.
  useEffect(() => {
    if (!docId || !doc) return;
    if (!(doc.status === "processing" || doc.status === "pending")) return;
    isProcessing.current = true;
    const t = window.setInterval(async () => {
      try {
        const d = await documentsApi.get(docId);
        setDoc(d);
        if (d.status !== "processing" && d.status !== "pending") {
          window.clearInterval(t);
          isProcessing.current = false;
          load();
        }
      } catch {
        window.clearInterval(t);
        isProcessing.current = false;
      }
    }, 3000);
    return () => window.clearInterval(t);
  }, [docId, doc?.status, load, doc]);

  async function handleExport() {
    try {
      const csv = await documentsApi.exportCsv(docId);
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${doc?.filename ?? "document"}_tables.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Export failed");
    }
  }

  if (error && !doc) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => router.push("/documents")}>
          <ArrowLeft className="size-4" />
          Back to documents
        </Button>
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50/60 px-3 py-2.5 text-sm text-red-700 dark:border-red-900">
          {error}
        </div>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="mx-auto max-w-6xl space-y-4">
        <div className="flex items-center gap-3">
          <Skeleton className="size-6 rounded-lg" />
          <Skeleton className="h-8 w-1/2" />
        </div>
        <Skeleton className="h-24" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  const processing = doc.status === "processing" || doc.status === "pending";
  const activeJob =
    jobs.find(
      (j) => j.status === "processing" || j.status === "pending" || j.status === "retry"
    ) ?? jobs[0] ?? null;
  const initialTab = searchParams.get("tab") === "extraction" ? "extraction" : "overview";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Reveal>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <Button
              variant="ghost"
              size="sm"
              className="-ml-2 mb-1 gap-1 text-muted-foreground hover:text-foreground"
              onClick={() => router.push("/documents")}
            >
              <ArrowLeft className="size-4" />
              Documents
            </Button>
            <div className="flex items-center gap-2">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <FileText className="size-5" />
              </div>
              <h1 className="truncate text-xl font-bold tracking-tight text-foreground sm:text-2xl">
                {doc.filename}
              </h1>
            </div>
            <div className="mt-2.5 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <StatusBadge status={doc.status} />
              <Badge variant="secondary">
                <DocumentTypeLabel type={doc.document_type} />
              </Badge>
              <ReviewBadge reviewStatus={doc.review_status} />
              {doc.is_scanned && <Badge variant="info">Scanned</Badge>}
              <span className="text-xs">· {formatBytes(doc.file_size)}</span>
              <span className="text-xs">· {doc.page_count} {doc.page_count === 1 ? "page" : "pages"}</span>
              <span className="text-xs">· {new Date(doc.created_at).toLocaleString()}</span>
            </div>
          </div>
          {tables.length > 0 && (
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="size-3.5" />
              Export tables
            </Button>
          )}
        </div>
      </Reveal>

      {doc.error_message && (
        <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50/60 px-3 py-2.5 text-sm text-red-700 dark:border-red-900">
          <span>Processing failed: {doc.error_message}</span>
        </div>
      )}

      {processing && (
        <Reveal>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <Loader2 className="size-4 animate-spin text-info" />
                Processing document
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ProcessingStatus job={activeJob} />
            </CardContent>
          </Card>
        </Reveal>
      )}

      <Tabs defaultValue={initialTab} className="w-full">
        <TabsList className="flex flex-wrap justify-start overflow-x-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="extraction">
            Extracted info
            {extraction?.needs_review && <Badge variant="warning" className="ml-1.5">!</Badge>}
          </TabsTrigger>
          <TabsTrigger value="tables">
            Tables{extraction ? ` (${tables.length})` : ""}
          </TabsTrigger>
          <TabsTrigger value="entities">Entities</TabsTrigger>
          <TabsTrigger value="pages">Page text</TabsTrigger>
          <TabsTrigger value="chat">Chat</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Reveal>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <SummaryPanel summary={doc.summary} generated={doc.summary_is_generated} />
              </CardContent>
            </Card>
          </Reveal>
          <Reveal delay={60}>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Processing metadata</CardTitle>
              </CardHeader>
              <CardContent>
                {doc.processing_meta && Object.keys(doc.processing_meta).length > 0 ? (
                  <dl className="grid gap-2 sm:grid-cols-2">
                    {Object.entries(doc.processing_meta).map(([k, v]) => (
                      <div key={k} className="rounded-md border border-border bg-card/50 px-3 py-2 text-sm">
                        <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                          {k.replace(/_/g, " ")}
                        </dt>
                        <dd className="mt-0.5 text-foreground">{String(v)}</dd>
                      </div>
                    ))}
                  </dl>
                ) : (
                  <p className="text-sm text-muted-foreground">No metadata yet.</p>
                )}
              </CardContent>
            </Card>
          </Reveal>
        </TabsContent>

        <TabsContent value="extraction">
          <Card>
            <CardContent className="p-5">
              {extraction ? (
                <ExtractionPanel
                  extraction={extraction}
                  documentId={doc.id}
                  onReviewed={(e) => setExtraction(e)}
                />
              ) : (
                <EmptyPane
                  title={processing ? "Extraction in progress…" : "No structured extraction available"}
                  description={
                    processing
                      ? "The pipeline is analyzing this document now."
                      : "Extracted fields will appear here once processing completes."
                  }
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tables">
          <Card>
            <CardContent className="p-5">
              <TablesPanel tables={tables} onExport={handleExport} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="entities">
          <Card>
            <CardContent className="p-5">
              <EntitiesPanel entities={entities} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="pages">
          <Card>
            <CardContent className="p-5">
              <PagesPanel pages={pages} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="chat" className="h-[600px]">
          <Card className="h-full">
            <CardContent className="flex h-full flex-col p-4">
              <ChatPanel
                documentId={doc.id}
                conversations={conversations}
                onConversationCreated={(c) => setConversations((prev) => [c, ...prev])}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}