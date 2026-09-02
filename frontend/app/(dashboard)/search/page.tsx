"use client";

import { useState } from "react";
import Link from "next/link";
import { Search, SearchX, Sparkles, ArrowRight, ExternalLink } from "lucide-react";
import { searchApi, ApiError } from "@/lib/api";
import type { SearchHit } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonCardGrid } from "@/components/skeleton-card-grid";
import { Reveal } from "@/components/motion/reveal";

const EXAMPLES = [
  "Total amounts across invoices",
  "Vendor names in contracts",
  "Dates mentioned in reports",
  "Key terms in research papers",
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(q?: string) {
    const value = (q ?? query).trim();
    if (!value || loading) return;
    setLoading(true);
    setError(null);
    setSubmitted(value);
    try {
      const res = await searchApi.search(value);
      setHits(res.hits);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Search failed");
      setHits([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <Reveal>
        <PageHeader
          title="Semantic search"
          description="Find meaning across every document — invoices, contracts, reports, and more."
          icon={<Search className="size-5" />}
        />
      </Reveal>

      {/* Search box */}
      <Reveal delay={40}>
        <div className="mx-auto w-full max-w-2xl">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              onSubmit();
            }}
            className="group relative"
          >
            <Search className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by meaning… e.g. “which invoices mention ACME”"
              aria-label="Search query"
              className="h-14 rounded-2xl pl-12 pr-28 text-base shadow-md"
              autoFocus
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="absolute right-2 top-1/2 inline-flex h-10 -translate-y-1/2 items-center gap-1.5 rounded-xl bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition-[background-color,transform]
                hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50"
            >
              {loading ? <span className="size-4 animate-spin rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground" aria-label="Searching" /> : <Sparkles className="size-4" />}
              Search
            </button>
          </form>
          <div className="mt-3 flex flex-wrap justify-center gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => {
                  setQuery(ex);
                  onSubmit(ex);
                }}
                className="rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground shadow-sm transition-[color,border-color,transform] hover:border-primary/30 hover:text-foreground active:scale-95"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      </Reveal>

      {error && (
        <div role="alert" className="mx-auto w-full max-w-2xl rounded-lg border border-red-200 bg-red-50/60 px-3 py-2.5 text-sm text-red-700 dark:border-red-900">
          {error}
        </div>
      )}

      {loading && <SkeletonCardGrid count={4} />}

      {!loading && submitted && hits.length === 0 && !error && (
        <EmptyState
          icon={<SearchX className="size-5" />}
          title={`No semantic matches for “${submitted}”`}
          description="Try rephrasing the query or searching for a specific document in the Documents tab."
        />
      )}

      {!loading && hits.length > 0 && (
        <section className="space-y-3">
          <Reveal>
            <p className="text-sm text-muted-foreground">
              {hits.length} result{hits.length === 1 ? "" : "s"} for “{submitted}”
            </p>
          </Reveal>
          <div className="space-y-3">
            {hits.map((h, i) => (
              <Reveal key={`${h.document_id}-${h.page_number}-${h.chunk_index}`} delay={i * 45}>
                <HitCard hit={h} rank={i + 1} />
              </Reveal>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function HitCard({ hit, rank }: { hit: SearchHit; rank: number }) {
  const score = Math.round(hit.score * 100);
  return (
    <div className="group rounded-xl border border-border bg-card p-4 shadow-sm transition-[transform,box-shadow,border-color] hover:-translate-y-0.5 hover:border-primary/20 hover:shadow-card-hover">
      <div className="flex flex-wrap items-center gap-2">
        <span className="flex w-6 items-center justify-center rounded-md bg-muted text-xs font-semibold text-muted-foreground">
          {rank}
        </span>
        <Link
          href={`/documents/${hit.document_id}`}
          className="inline-flex items-center gap-1 font-medium text-foreground hover:text-primary"
        >
          <span className="truncate">{hit.document_filename}</span>
          <ExternalLink className="size-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
        </Link>
        <Badge variant="outline">Page {hit.page_number}</Badge>
        {hit.section && <Badge variant="secondary">{hit.section}</Badge>}
        <span className="ml-auto inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          similarity
          <span className="inline-flex h-1.5 w-16 overflow-hidden rounded-full bg-muted">
            <span
              className={`h-full rounded-full ${score >= 70 ? "bg-emerald-500" : score >= 45 ? "bg-amber-500" : "bg-red-400"}`}
              style={{ width: `${score}%` }}
            />
          </span>
          <span className="w-9 text-right font-medium text-foreground">{score}%</span>
        </span>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
        <MarkSnippet text={hit.snippet} highlight={hit.text} />
      </p>
      <Link
        href={`/documents/${hit.document_id}?tab=pages`}
        className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
      >
        Open page context
        <ArrowRight className="size-3" />
      </Link>
    </div>
  );
}

function MarkSnippet({ text, highlight }: { text: string; highlight: string }) {
  if (!highlight) return <>{text}</>;
  const needle = highlight.trim();
  if (!needle) return <>{text}</>;
  try {
    const parts = text.split(new RegExp(`(${escapeRegex(needle.slice(0, 60))})`, "gi"));
    if (parts.length === 1) return <>{text}</>;
    return (
      <>
        {parts.map((p, i) =>
          p.toLowerCase().includes(needle.slice(0, 60).toLowerCase()) && p.trim() ? (
            <mark key={i} className="rounded bg-amber-200/70 px-0.5 text-foreground dark:bg-amber-500/30">
              {p}
            </mark>
          ) : (
            <span key={i}>{p}</span>
          )
        )}
      </>
    );
  } catch {
    return <>{text}</>;
  }
}

function escapeRegex(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}