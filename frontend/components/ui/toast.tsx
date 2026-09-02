"use client";

import * as React from "react";
import { CheckCircle2, XCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastKind = "success" | "error" | "info";

interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
}

const ToastContext = React.createContext<{
  toast: (kind: ToastKind, message: string) => void;
} | null>(null);

let counter = 0;

const ICONS: Record<ToastKind, React.ReactNode> = {
  success: <CheckCircle2 className="size-4 shrink-0 text-emerald-600" />,
  error: <XCircle className="size-4 shrink-0 text-red-600" />,
  info: <Info className="size-4 shrink-0 text-sky-600" />,
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = React.useState<ToastItem[]>([]);

  const toast = React.useCallback((kind: ToastKind, message: string) => {
    const id = ++counter;
    setItems((prev) => [...prev.slice(-3), { id, kind, message }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div
        aria-live="polite"
        aria-label="Notifications"
        className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2 p-1"
      >
        {items.map((t) => (
          <div
            key={t.id}
            role="status"
            className={cn(
              "pointer-events-auto flex items-start gap-2.5 rounded-lg border bg-card/95 p-3 text-sm shadow-lg backdrop-blur-sm animate-toast-in",
              t.kind === "success" && "border-emerald-200",
              t.kind === "error" && "border-red-200",
              t.kind === "info" && "border-sky-200"
            )}
          >
            {ICONS[t.kind]}
            <span className="flex-1 text-card-foreground">{t.message}</span>
            <button
              type="button"
              aria-label="Dismiss notification"
              onClick={() =>
                setItems((prev) => prev.filter((i) => i.id !== t.id))
              }
              className="rounded-md p-0.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <X className="size-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}