"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Files,
  Search,
  Sparkles,
  ClipboardCheck,
  Settings,
  LogOut,
  Menu,
  X,
  FileScan,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/tooltip";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, match: (p: string) => p === "/" },
  {
    href: "/documents",
    label: "Documents",
    icon: Files,
    match: (p: string) => p.startsWith("/documents"),
  },
  { href: "/search", label: "Search", icon: Search, match: (p: string) => p.startsWith("/search") },
  { href: "/ask", label: "Ask AI", icon: Sparkles, match: (p: string) => p.startsWith("/ask") },
  { href: "/review", label: "Review", icon: ClipboardCheck, match: (p: string) => p.startsWith("/review") },
  { href: "/settings", label: "Settings", icon: Settings, match: (p: string) => p.startsWith("/settings") },
];

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2.5" aria-label="DocIntelligence home">
      <span className="relative flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
        <FileScan className="size-4" />
        <span className="absolute inset-0 rounded-lg ring-1 ring-inset ring-white/20" />
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-semibold tracking-tight text-foreground">
          DocIntelligence
        </span>
        <span className="block text-[11px] leading-none text-muted-foreground">
          Document intelligence
        </span>
      </span>
    </Link>
  );
}

function NavItems({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="space-y-1" aria-label="Main">
      {NAV.map((item) => {
        const active = item.match(pathname);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-[background-color,color,transform] duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background",
              active
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-accent hover:text-foreground active:scale-[0.99]"
            )}
          >
            <item.icon className={cn("size-4 shrink-0", !active && "text-muted-foreground/80 group-hover:text-foreground")} />
            {item.label}
            {active && (
              <span className="ml-auto size-1.5 rounded-full bg-primary-foreground/70" aria-hidden />
            )}
          </Link>
        );
      })}
    </nav>
  );
}

function AccountArea({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth();
  const initials = (user?.full_name || user?.email || "?")
    .split(/[\s@]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join("");

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2.5 rounded-lg border border-border bg-card p-2.5 shadow-sm">
        <span
          aria-hidden
          className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary"
        >
          {initials || "U"}
        </span>
        <span className="min-w-0 flex-1 leading-tight">
          <span className="block truncate text-sm font-medium text-foreground">
            {user?.full_name || "Account"}
          </span>
          <span className="block truncate text-xs text-muted-foreground">{user?.email}</span>
        </span>
        <Tooltip content="Sign out" side="top">
          <button
            type="button"
            onClick={logout}
            aria-label="Sign out"
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <LogOut className="size-3.5" />
          </button>
        </Tooltip>
      </div>
      {onNavigate && (
        <Link
          href="/settings"
          onClick={onNavigate}
          className="block rounded-md px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Account & settings
        </Link>
      )}
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [drawerOpen, setDrawerOpen] = React.useState(false);

  React.useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  React.useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  // Close the drawer on Escape.
  React.useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setDrawerOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [drawerOpen]);

  if (loading || !user) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-muted-foreground">
        Loading workspace…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-border bg-card/70 backdrop-blur-sm lg:flex">
        <div className="flex h-16 items-center border-b border-border px-5">
          <Brand />
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-4">
          <NavItems pathname={pathname} />
        </div>
        <div className="border-t border-border p-3">
          <AccountArea />
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-card/80 px-4 backdrop-blur-sm lg:hidden">
        <Brand />
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          aria-label="Open navigation"
          className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Menu className="size-5" />
        </button>
      </header>

      {/* Mobile drawer */}
      <div
        aria-hidden={!drawerOpen}
        className={cn(
          "fixed inset-0 z-40 bg-slate-950/40 backdrop-blur-[2px] transition-opacity duration-200 lg:hidden",
          drawerOpen ? "opacity-100" : "pointer-events-none opacity-0"
        )}
        onClick={() => setDrawerOpen(false)}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col border-r border-border bg-card shadow-xl transition-transform duration-300 ease-out lg:hidden",
          drawerOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-14 items-center justify-between border-b border-border px-4">
          <Brand />
          <button
            type="button"
            onClick={() => setDrawerOpen(false)}
            aria-label="Close navigation"
            className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="size-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-4">
          <NavItems pathname={pathname} onNavigate={() => setDrawerOpen(false)} />
        </div>
        <div className="border-t border-border p-3">
          <AccountArea onNavigate={() => setDrawerOpen(false)} />
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
          {children}
        </main>
      </div>
    </div>
  );
}