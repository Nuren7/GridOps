import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";

import { ApiError, register } from "@/lib/api";

export const Route = createFileRoute("/register")({
  head: () => ({
    meta: [
      { title: "Create account — GridOps" },
      { name: "description", content: "Create a GridOps dashboard account." },
    ],
  }),
  component: Register,
});

function Register() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState(false);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register(username, password);
      setCreated(true);
      window.setTimeout(() => navigate({ to: "/" }), 2000);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 400
          ? "Användarnamnet är redan registrerat."
          : err instanceof Error
            ? err.message
            : "Registreringen misslyckades.",
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
          <h1 className="text-base font-semibold">Create account</h1>
          <p className="mt-1 text-xs text-muted-foreground">
            Register to access the factory dashboard.
          </p>
          <label htmlFor="username" className="mt-5 block text-xs font-medium">
            Username
          </label>
          <input
            id="username"
            className="mt-1 h-9 w-full rounded-sm border border-input bg-card px-2.5 text-sm outline-none focus:border-ring focus:ring-1 focus:ring-ring"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            required
          />
          <label htmlFor="password" className="mt-4 block text-xs font-medium">
            Password
          </label>
          <input
            id="password"
            type="password"
            className="mt-1 h-9 w-full rounded-sm border border-input bg-card px-2.5 text-sm outline-none focus:border-ring focus:ring-1 focus:ring-ring"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
            required
          />
          {error && (
            <p
              role="alert"
              className="mt-3 rounded-sm border border-crit/40 bg-crit/5 px-2.5 py-1.5 text-xs text-crit"
            >
              {error}
            </p>
          )}
          {created && (
            <p
              role="status"
              className="mt-3 rounded-sm border border-ok/40 bg-ok/5 px-2.5 py-1.5 text-xs text-ok"
            >
              Konto skapat!
            </p>
          )}
          <button
            type="submit"
            disabled={loading || created}
            className="mt-5 h-9 w-full rounded-sm bg-primary text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
          >
            {loading ? "Creating account…" : "Create account"}
          </button>
          <p className="mt-4 text-center text-xs text-muted-foreground">
            Already registered?{" "}
            <Link to="/" className="font-medium text-foreground underline underline-offset-4">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
