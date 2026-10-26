import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { ApiError, isLoggedIn, login } from "@/lib/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Sign in — GridOps" },
      { name: "description", content: "Sign in to the GridOps factory monitoring dashboard." },
      { property: "og:title", content: "Sign in — GridOps" },
      { property: "og:description", content: "Factory and sensor monitoring dashboard." },
    ],
  }),
  component: Login,
});

function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isLoggedIn()) navigate({ to: "/dashboard" });
  }, [navigate]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
      navigate({ to: "/dashboard" });
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "Felaktigt användarnamn eller lösenord."
          : err instanceof Error
            ? err.message
            : "Inloggningen misslyckades.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2">
          <div className="h-5 w-5 rounded-sm bg-primary" />
          <span className="text-sm font-semibold tracking-tight">GRIDOPS</span>
          <span className="text-xs text-muted-foreground">/ IoT Operations</span>
        </div>
        <form onSubmit={onSubmit} className="rounded-sm border bg-card p-6">
          <h1 className="text-base font-semibold">Sign in</h1>
          <p className="mt-1 text-xs text-muted-foreground">Use your account credentials.</p>
          <label className="mt-5 block text-xs font-medium">Username</label>
          <input
            className="mt-1 h-9 w-full rounded-sm border border-input bg-card px-2.5 text-sm outline-none focus:border-ring focus:ring-1 focus:ring-ring"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
          <label className="mt-4 block text-xs font-medium">Password</label>
          <input
            type="password"
            className="mt-1 h-9 w-full rounded-sm border border-input bg-card px-2.5 text-sm outline-none focus:border-ring focus:ring-1 focus:ring-ring"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          {error && (
            <p className="mt-3 rounded-sm border border-crit/40 bg-crit/5 px-2.5 py-1.5 text-xs text-crit">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="mt-5 h-9 w-full rounded-sm bg-primary text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
          <p className="mt-4 text-center text-xs text-muted-foreground">
            Need an account?{" "}
            <Link
              to="/register"
              className="font-medium text-foreground underline underline-offset-4"
            >
              Create one
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
