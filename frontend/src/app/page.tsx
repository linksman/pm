"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";

type User = {
  name?: string;
  email?: string;
  picture?: string | null;
};

function LoginPage({ error }: { error: string | null }) {
  const [demoOpen, setDemoOpen] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);

  const handleDemoSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setDemoError(null);
    setSubmitting(true);

    const response = await fetch("/api/auth/login", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (response.ok) {
      window.location.reload();
      return;
    }

    const data = await response.json();
    setDemoError(data.detail || "Invalid username or password.");
    setSubmitting(false);
  };

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-24 text-slate-900">
      <div className="mx-auto w-full max-w-md rounded-3xl border border-slate-200 bg-white p-10 shadow-lg">
        <h1 className="text-3xl font-semibold text-[var(--navy-dark)]">Kanban Studio</h1>
        <p className="mt-3 text-sm text-slate-500">
          Sign in to access your board.
        </p>

        {error ? (
          <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">
            Sign-in failed: {error.replace(/_/g, " ")}
          </p>
        ) : null}

        <div className="mt-8">
          <a
            href="/api/auth/google"
            className="flex w-full items-center justify-center gap-3 rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
          >
            <GoogleIcon />
            Sign in with Google
          </a>
        </div>

        <div className="mt-6">
          <button
            type="button"
            onClick={() => setDemoOpen((o) => !o)}
            className="w-full text-center text-xs text-slate-400 underline-offset-2 hover:text-slate-600 hover:underline"
          >
            {demoOpen ? "Hide demo login" : "Use demo credentials instead"}
          </button>

          {demoOpen ? (
            <form className="mt-4 space-y-4" onSubmit={handleDemoSubmit}>
              <div>
                <label className="block text-sm font-medium text-slate-700">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="mt-2 w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 focus:border-slate-500 focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-2 w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 focus:border-slate-500 focus:outline-none"
                  required
                />
              </div>
              {demoError ? <p className="text-sm text-red-600">{demoError}</p> : null}
              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-2xl bg-[var(--purple-secondary)] px-4 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
              >
                {submitting ? "Signing in..." : "Sign in"}
              </button>
            </form>
          ) : null}
        </div>
      </div>
    </main>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z"
        fill="#4285F4"
      />
      <path
        d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"
        fill="#34A853"
      />
      <path
        d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"
        fill="#FBBC05"
      />
      <path
        d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"
        fill="#EA4335"
      />
    </svg>
  );
}

export default function Home() {
  const [authStatus, setAuthStatus] = useState<"loading" | "authenticated" | "unauthenticated">("loading");
  const [user, setUser] = useState<User>({});
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const errorParam = params.get("auth_error");
    if (errorParam) {
      setAuthError(errorParam);
      window.history.replaceState({}, "", "/");
    }

    const check = async () => {
      try {
        const response = await fetch("/api/auth/me", { credentials: "include" });
        const data = await response.json();
        if (data.authenticated) {
          setUser({ name: data.name, email: data.email, picture: data.picture });
          setAuthStatus("authenticated");
        } else {
          setAuthStatus("unauthenticated");
        }
      } catch {
        setAuthStatus("unauthenticated");
      }
    };

    check();
  }, []);

  const logout = async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    setAuthStatus("unauthenticated");
    setUser({});
  };

  if (authStatus === "loading") {
    return (
      <main className="min-h-screen bg-slate-50 px-6 py-24 text-slate-900">
        <div className="mx-auto w-full max-w-md rounded-3xl border border-slate-200 bg-white p-10 shadow-lg text-center">
          <p className="text-sm text-slate-500">Checking authentication...</p>
        </div>
      </main>
    );
  }

  if (authStatus === "unauthenticated") {
    return <LoginPage error={authError} />;
  }

  return <KanbanBoard onLogout={logout} user={user} />;
}
