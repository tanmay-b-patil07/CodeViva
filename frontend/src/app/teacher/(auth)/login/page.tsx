
"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Code2, LoaderCircle } from "lucide-react";

export default function TeacherLoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.message || data.detail || "Invalid email or password."
        );
      }

      if (data.role !== "teacher") {
        await fetch("/api/auth/logout", {
          method: "POST",
          credentials: "same-origin",
        });
        throw new Error("This account is not a teacher account.");
      }

      router.replace("/teacher");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-5 py-12 text-white">
      <section className="w-full max-w-md">
        <Link
          href="/"
          className="mb-10 inline-flex items-center gap-3 text-xl font-semibold tracking-tight"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-lime text-black">
            <Code2 size={22} />
          </span>
          CodeViva
        </Link>

        <div className="rounded-2xl border border-line bg-panel p-7 sm:p-9">
          <p className="mb-3 text-sm font-medium text-lime">
            TEACHER PORTAL
          </p>

          <h1 className="text-3xl font-semibold tracking-tight">
            Welcome back.
          </h1>

          <p className="mt-2 text-sm text-gray-400">
            Sign in to manage your classes and assessments.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label htmlFor="email" className="mb-2 block text-sm text-gray-300">
                Email address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                className="w-full rounded-xl border border-line bg-canvas px-4 py-3 outline-none transition focus:border-lime"
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-2 block text-sm text-gray-300">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                className="w-full rounded-xl border border-line bg-canvas px-4 py-3 outline-none transition focus:border-lime"
              />
            </div>

            {error && (
              <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-lime px-4 py-3 font-semibold text-black transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <>
                  <LoaderCircle size={18} className="animate-spin" />
                  Signing in...
                </>
              ) : (
                <>
                  Sign in
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-400">
            Need a teacher account?{" "}
            <Link href="/teacher/register" className="font-medium text-lime hover:underline">
              Register
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}
