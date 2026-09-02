"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api";
import { LogIn } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      router.replace("/");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Unable to sign in";
      setError(message);
      toast("error", message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="shadow-lg shadow-foreground/5">
      <CardContent className="p-8">
        <div className="mb-6 space-y-1.5">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Sign in</h1>
          <p className="text-sm text-muted-foreground">
            Access your document intelligence workspace.
          </p>
        </div>

        {error && (
          <div role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50/60 px-3 py-2 text-sm text-red-700 dark:border-red-900">
            {error}
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="you@example.com"
            />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password">Password</Label>
            </div>
            <Input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="••••••••"
            />
          </div>
          <Button type="submit" className="w-full" disabled={loading || !email || !password}>
            {loading ? (
              <>
                <Spinner className="size-4" />
                Signing in…
              </>
            ) : (
              <>
                <LogIn className="size-4" />
                Sign in
              </>
            )}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          New here?{" "}
          <Link href="/register" className="font-medium text-primary hover:underline">
            Create an account
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}