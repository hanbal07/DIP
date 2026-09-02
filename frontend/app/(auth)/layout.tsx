"use client";

import Link from "next/link";
import { FileSearch, ScanSearch, MessagesSquare, ShieldCheck } from "lucide-react";

const FEATURES = [
  {
    icon: ScanSearch,
    title: "Classify & extract",
    description: "Auto-detect document type, OCR scans, and pull structured fields.",
  },
  {
    icon: FileSearch,
    title: "Semantic search",
    description: "Find meaning across every document with embeddings.",
  },
  {
    icon: MessagesSquare,
    title: "Ask AI",
    description: "Chat with grounded, cited answers from your extracted content.",
  },
  {
    icon: ShieldCheck,
    title: "Private by design",
    description: "Per-user isolation, audit logging, and rate-limited APIs.",
  },
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      {/* Brand / value panel */}
      <div className="hidden w-[45%] flex-col justify-between bg-gradient-to-br from-primary via-primary/90 to-primary/70 p-10 text-primary-foreground lg:flex">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-xl bg-white/15 text-lg font-black backdrop-blur">
            D
          </div>
          <div>
            <p className="text-lg font-bold leading-tight">Document Intelligence</p>
            <p className="text-xs text-primary-foreground/70">Extract · Search · Ask</p>
          </div>
        </div>

        <div className="space-y-6">
          <h2 className="text-3xl font-bold leading-tight tracking-tight">
            Your documents, intelligently processed.
          </h2>
          <ul className="space-y-4">
            {FEATURES.map((f) => (
              <li key={f.title} className="flex items-start gap-3">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-white/15">
                  <f.icon className="size-4" />
                </span>
                <span>
                  <span className="block text-sm font-semibold">{f.title}</span>
                  <span className="block text-sm text-primary-foreground/75">{f.description}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-primary-foreground/60">
          FastAPI + pgvector · One-click Docker deployment
        </p>
      </div>

      {/* Form panel */}
      <div className="flex flex-1 items-center justify-center bg-muted/40 p-6">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center lg:hidden">
            <div className="mx-auto mb-3 flex size-12 items-center justify-center rounded-2xl bg-primary text-xl font-black text-primary-foreground">
              D
            </div>
            <h1 className="text-xl font-bold tracking-tight text-foreground">
              Document Intelligence Platform
            </h1>
          </div>
          <div className="animate-fade-in-up">{children}</div>
          <p className="mt-6 text-center text-xs text-muted-foreground">
            <Link href="/" className="hover:text-foreground hover:underline">
              Back to dashboard
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}