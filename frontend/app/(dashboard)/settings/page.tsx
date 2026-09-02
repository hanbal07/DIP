"use client";

import { useEffect, useState } from "react";
import { Settings as SettingsIcon, KeyRound, Server, UserCircle, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { authApi, healthApi, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/page-header";
import { Reveal } from "@/components/motion/reveal";
import { Spinner } from "@/components/ui/spinner";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

interface Health {
  status: string;
  version: string;
  environment: string;
  database: string;
  redis: string;
  ai_mode: string;
}

export default function SettingsPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    healthApi.health().then(setHealth).catch(() => undefined);
  }, []);

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword.length < 8) {
      toast("error", "New password must be at least 8 characters");
      return;
    }
    setBusy(true);
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast("success", "Password updated");
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Failed to change password");
    } finally {
      setBusy(false);
    }
  }

  const initials =
    user?.full_name?.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase() ??
    user?.email?.[0]?.toUpperCase() ??
    "?";

  return (
    <div className="space-y-8">
      <Reveal>
        <PageHeader
          title="Settings"
          description="Manage your account, security, and review system status."
          icon={<SettingsIcon className="size-5" />}
        />
      </Reveal>

      <Reveal>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <UserCircle className="size-4 text-muted-foreground" />
              Account
            </CardTitle>
            <CardDescription>Your profile details.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <span className="flex size-14 items-center justify-center rounded-full bg-primary/10 text-lg font-bold text-primary">
                {initials}
              </span>
              <div className="min-w-0">
                <p className="truncate text-base font-semibold text-foreground">
                  {user?.full_name || "Unnamed user"}
                </p>
                <p className="truncate text-sm text-muted-foreground">{user?.email}</p>
              </div>
              <Badge variant="success" className="ml-auto shrink-0">Active</Badge>
            </div>
          </CardContent>
        </Card>
      </Reveal>

      <Reveal delay={50}>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <KeyRound className="size-4 text-muted-foreground" />
              Change password
            </CardTitle>
            <CardDescription>Use a strong password you don&apos;t reuse elsewhere.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={changePassword} className="max-w-md space-y-4">
              <div className="space-y-2">
                <Label htmlFor="current">Current password</Label>
                <Input
                  id="current"
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="new">New password</Label>
                <Input
                  id="new"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoComplete="new-password"
                  minLength={8}
                  required
                />
              </div>
              <Button type="submit" disabled={busy || !currentPassword || newPassword.length < 8}>
                {busy ? (
                  <>
                    <Spinner className="size-4" />
                    Updating…
                  </>
                ) : (
                  <>
                    <ShieldCheck className="size-4" />
                    Update password
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </Reveal>

      <Reveal delay={80}>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Server className="size-4 text-muted-foreground" />
              System
            </CardTitle>
            <CardDescription>Backend status from the health endpoint.</CardDescription>
          </CardHeader>
          <CardContent>
            {!health ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-4 w-2/5" />
              </div>
            ) : (
              <dl className="grid gap-3 text-sm sm:grid-cols-2">
                <HealthItem label="API" value={health.status} />
                <HealthItem label="Version" value={health.version} />
                <HealthItem label="Environment" value={health.environment} />
                <HealthItem label="Database" value={health.database} />
                <HealthItem label="Redis / jobs" value={health.redis} />
                <HealthItem label="AI mode" value={health.ai_mode} />
              </dl>
            )}
          </CardContent>
        </Card>
      </Reveal>
    </div>
  );
}

function HealthItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card/50 px-3 py-2.5">
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 flex items-center gap-1.5 font-medium capitalize text-foreground">
        <span className={`size-2 rounded-full ${value === "ok" ? "bg-emerald-500" : "bg-amber-500"}`} aria-hidden />
        {value}
      </dd>
    </div>
  );
}