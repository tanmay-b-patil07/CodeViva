
"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Code2, LoaderCircle } from "lucide-react";

export default function TeacherRegisterPage() {
  const router = useRouter();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (password.length < 8 || password.length > 128) {
      setError("Password must be between 8 and 128 characters.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch("/api/auth/register-teacher", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          full_name: fullName.trim(),
          email: email.trim(),
          password,
          invite_code: inviteCode.trim(),
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const message =
          typeof data?.error?.message === "string"
            ? data.error.message
            : typeof data?.message === "string"
              ? data.message
              : typeof data?.detail === "string"
                ? data.detail
                : "Unable to create your teacher account.";
        throw new Error(message);
      }

      router.push("/teacher/login?registered=1");
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
        <Link href="/" className="mb-10 inline-flex items-center gap-3 text-xl font-semibold">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-lime text-black">
            <Code2 size={22} />
          </span>
          CodeViva
        </Link>

        <div className="rounded-2xl border border-line bg-panel p-7 sm:p-9">
          <p className="mb-3 text-sm font-medium text-lime">TEACHER PORTAL</p>
          <h1 className="text-3xl font-semibold tracking-tight">Join as a teacher.</h1>
          <p className="mt-2 text-sm text-gray-400">
            Create your account to manage classes and assessments.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label htmlFor="fullName" className="mb-2 block text-sm text-gray-300">
                Full name
              </label>
              <input
                id="fullName"
                autoComplete="name"
                required
                maxLength={200}
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Your full name"
                className="w-full rounded-xl border border-line bg-canvas px-4 py-3 outline-none focus:border-lime"
              />
            </div>

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
                className="w-full rounded-xl border border-line bg-canvas px-4 py-3 outline-none focus:border-lime"
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-2 block text-sm text-gray-300">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                minLength={8}
                maxLength={128}
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="At least 8 characters"
                className="w-full rounded-xl border border-line bg-canvas px-4 py-3 outline-none focus:border-lime"
              />
            </div>

            <div>
              <label htmlFor="inviteCode" className="mb-2 block text-sm text-gray-300">
                Teacher invite code
              </label>
              <input
                id="inviteCode"
                type="password"
                autoComplete="off"
                required
                maxLength={200}
                value={inviteCode}
                onChange={(event) => setInviteCode(event.target.value)}
                placeholder="Enter your invite code"
                className="w-full rounded-xl border border-line bg-canvas px-4 py-3 outline-none focus:border-lime"
              />
              <p className="mt-2 text-xs text-gray-500">
                Use the code provided by your CodeViva administrator.
              </p>
            </div>

            {error && (
              <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-lime px-4 py-3 font-semibold text-black hover:opacity-90 disabled:opacity-60"
            >
              {loading ? (
                <>
                  <LoaderCircle size={18} className="animate-spin" />
                  Creating account...
                </>
              ) : (
                <>
                  Create teacher account
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-400">
            Already registered?{" "}
            <Link href="/teacher/login" className="font-medium text-lime hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}
