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
import { UserPlus } from "lucide-react";

export default function RegisterPage() {
  const { register } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      await register(email, password, fullName || undefined);
      router.replace("/");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Unable to create account";
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
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Create an account</h1>
          <p className="text-sm text-muted-foreground">
            Start processing documents in seconds.
          </p>
        </div>

        {error && (
          <div role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50/60 px-3 py-2 text-sm text-red-700 dark:border-red-900">
            {error}
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="fullName">Full name (optional)</Label>
            <Input
              id="fullName"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              autoComplete="name"
              placeholder="Jane Doe"
            />
          </div>
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
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              placeholder="At least 8 characters"
            />
          </div>
          <Button type="submit" className="w-full" disabled={loading || !email || password.length < 8}>
            {loading ? (
              <>
                <Spinner className="size-4" />
                Creating account…
              </>
            ) : (
              <>
                <UserPlus className="size-4" />
                Create account
              </>
            )}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          Already registered?{" "}
          <Link href="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}