import { createFileRoute, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { z } from "zod";
import { toast } from "sonner";
import { Loader2, ShieldCheck } from "lucide-react";

import { signInDemoUser } from "@/hooks/useAuth";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

// TODO: Replace this demo auth flow with real FastAPI + JWT + PostgreSQL authentication.

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Sign in — ClaimBridge" },
      {
        name: "description",
        content:
          "Sign in to verify, validate and prepare insurance claims before submission.",
      },
      { property: "og:title", content: "Sign in — ClaimBridge" },
      {
        property: "og:description",
        content: "Access your insurance claim verification dashboard.",
      },
    ],
  }),
  component: AuthPage,
});

const credentials = z.object({
  email: z.string().trim().email({ message: "Enter a valid email address" }).max(255),
  password: z.string().min(6, { message: "Password must be at least 6 characters" }).max(72),
});

function AuthPage() {
  const navigate = useNavigate();
  const { user, loading } = useAuth();
  const isRestoring = useRouterState({ select: (s) => s.isLoading });
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && user) navigate({ to: "/" });
  }, [loading, user, navigate]);

 async function onSubmit(event: React.FormEvent) {
  event.preventDefault();

  const parsed = credentials.safeParse({ email, password });

  if (!parsed.success) {
  toast.error(parsed.error.issues[0]?.message ?? "Invalid details");
  return;
}

if (mode === "signup") {
  if (!fullName.trim()) {
    toast.error("Please enter your full name");
    return;
  }

  if (password !== confirmPassword) {
    toast.error("Passwords do not match");
    return;
  }
}

setBusy(true);

  setBusy(true);

  try {
    const endpoint =
      mode === "signin"
        ? "http://127.0.0.1:8000/auth/login"
        : "http://127.0.0.1:8000/auth/register";

    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: parsed.data.email,
        password: parsed.data.password,
        ...(mode === "signup" && {
          full_name: fullName.trim(),
          role: "Coordinator",
        }),
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail || "Authentication failed"
      );
    }

    // Keep the existing frontend session mechanism for now.
    signInDemoUser(data.email);

    if (mode === "signup") {
      toast.success("Account created successfully.");
    } else {
      toast.success("Login successful.");
    }

    navigate({ to: "/" });
  } catch (err) {
    toast.error(
      err instanceof Error
        ? err.message
        : "Authentication failed"
    );
  } finally {
    setBusy(false);
  }
}

  async function onGoogle() {
    setBusy(true);
    try {
      signInDemoUser("google-demo@claimbridge.local");
      navigate({ to: "/" });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 flex items-center gap-3">
          <span className="flex size-11 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <ShieldCheck className="size-5" />
          </span>
          <div>
            <p className="font-display text-lg font-semibold">ClaimBridge</p>
            <p className="text-sm text-muted-foreground">
              Intelligent Insurance Claim Verification
            </p>
          </div>
        </div>

        <Card className="shadow-panel">
          <CardHeader>
            <CardTitle className="text-2xl">
              {mode === "signin" ? "Welcome back" : "Create your account"}
            </CardTitle>
            <CardDescription>
              {mode === "signin"
                ? "Sign in to your Hospital Insurance Coordinator workspace."
                : "Verify, validate and prepare insurance claims before submission."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <form onSubmit={onSubmit} className="space-y-4">
            {mode === "signup" && (
  <div className="space-y-2">
    <Label htmlFor="fullName">Full Name</Label>
    <Input
      id="fullName"
      type="text"
      autoComplete="name"
      value={fullName}
      maxLength={150}
      onChange={(e) => setFullName(e.target.value)}
      placeholder="Enter your full name"
      required
    />
  </div>
)}
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  maxLength={255}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@hospital.org"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete={mode === "signin" ? "current-password" : "new-password"}
                  value={password}
                  maxLength={72}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
              </div>

              {mode === "signup" && (
  <div className="space-y-2">
    <Label htmlFor="confirmPassword">Confirm Password</Label>
    <Input
      id="confirmPassword"
      type="password"
      autoComplete="new-password"
      value={confirmPassword}
      maxLength={72}
      onChange={(e) => setConfirmPassword(e.target.value)}
      placeholder="Re-enter your password"
      required
    />
  </div>
)}
              <Button type="submit" className="w-full" disabled={busy || isRestoring}>
                {busy ? <Loader2 className="size-4 animate-spin" /> : null}
                {mode === "signin" ? "Sign in" : "Create account"}
              </Button>
            </form>

            <div className="flex items-center gap-3">
              <span className="h-px flex-1 bg-border" />
              <span className="text-xs uppercase tracking-widest text-muted-foreground">or</span>
              <span className="h-px flex-1 bg-border" />
            </div>

            <Button variant="outline" className="w-full" onClick={onGoogle} disabled={busy}>
              Continue with Google
            </Button>

            <p className="text-center text-sm text-muted-foreground">
              {mode === "signin" ? "New here?" : "Already have an account?"}{" "}
              <button
                type="button"
                className="font-medium text-primary underline-offset-4 hover:underline"
                onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
              >
                {mode === "signin" ? "Create an account" : "Sign in"}
              </button>
            </p>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}