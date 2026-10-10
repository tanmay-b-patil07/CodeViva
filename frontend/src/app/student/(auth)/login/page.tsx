
"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  BookOpen,
  Braces,
  CheckCircle2,
  Code2,
  Lightbulb,
  LoaderCircle,
} from "lucide-react";

export default function StudentLoginPage() {
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
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.message || data.detail || "Invalid email or password."
        );
      }

      if (data.role !== "student") {
        await fetch("/api/auth/logout", {
          method: "POST",
          credentials: "same-origin",
        });
        throw new Error("This account is not a student account.");
      }

      router.replace("/student");
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
    <main className="min-h-screen bg-canvas px-5 py-10 text-white sm:px-8 sm:py-14">
      <div className="mx-auto max-w-6xl">
        <Link
          href="/"
          className="inline-flex items-center gap-3 text-xl font-semibold tracking-tight"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-lime text-black">
            <Braces size={22} />
          </span>
          codeviva<span className="text-lime">.</span>
        </Link>

        <section className="grid items-center gap-10 py-10 sm:py-14 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:py-20">
          <div className="max-w-xl">
            <p className="mb-4 text-xs font-semibold tracking-[0.22em] text-lime">
              STUDENT WORKSPACE
            </p>
            <h1 className="text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
              Learn the code.
              <br />
              <span className="text-lime">Explain your thinking.</span>
            </h1>
            <p className="mt-5 max-w-lg text-base leading-7 text-gray-400">
              Pick up where your class left off, practice with code, and see
              feedback that helps you understand how your solutions work.
            </p>

            <div className="mt-9 grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
              <InfoItem
                icon={<BookOpen size={18} />}
                title="Your assigned work"
                description="Find class assignments and deadlines in one place."
              />
              <InfoItem
                icon={<Code2 size={18} />}
                title="Practice by coding"
                description="Write code in the workspace and review your feedback."
              />
              <InfoItem
                icon={<Lightbulb size={18} />}
                title="Questions when released"
                description="Answer assignment questions after your teacher opens them."
              />
            </div>
            <p className="mt-6 flex items-center gap-2 text-xs leading-5 text-gray-500">
              <CheckCircle2 size={15} className="shrink-0 text-lime" />
              Use the email address registered to your student account.
            </p>
          </div>

          <div className="w-full rounded-2xl border border-line bg-panel p-7 sm:p-9">
            <p className="mb-3 text-sm font-medium text-lime">STUDENT SIGN IN</p>
            <h2 className="text-3xl font-semibold tracking-tight">
              Welcome back.
            </h2>
            <p className="mt-2 text-sm text-gray-400">
              Sign in to continue your coding journey.
            </p>

            <form onSubmit={handleSubmit} className="mt-8 space-y-5">
              <div>
                <label
                  htmlFor="email"
                  className="mb-2 block text-sm text-gray-300"
                >
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
                <label
                  htmlFor="password"
                  className="mb-2 block text-sm text-gray-300"
                >
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
                <p
                  role="alert"
                  className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300"
                >
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
              New to CodeViva?{" "}
              <Link
                href="/student/register"
                className="font-medium text-lime hover:underline"
              >
                Create an account
              </Link>
            </p>
            <p className="mt-4 border-t border-line pt-4 text-center text-xs text-gray-500">
              Are you a teacher?{" "}
              <Link
                href="/teacher/login"
                className="font-medium text-gray-300 hover:text-lime"
              >
                Go to teacher sign in
              </Link>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}

function InfoItem({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <article className="flex gap-3 rounded-xl border border-line bg-panel/60 p-4">
      <span className="mt-0.5 text-lime">{icon}</span>
      <div>
        <h2 className="text-sm font-medium text-white">{title}</h2>
        <p className="mt-1 text-xs leading-5 text-gray-400">{description}</p>
      </div>
    </article>
  );
}
