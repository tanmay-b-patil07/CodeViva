"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { ArrowRight, BookOpen, Plus, RefreshCw, Search } from "lucide-react";

import {
  apiRequest,
  formatDate,
  SUPPORTED_CODE_LANGUAGES,
  TeacherAssignment,
  TeacherGroup,
} from "@/lib/assignments";

export default function TeacherAssignmentsPage() {
  const [assignments, setAssignments] = useState<TeacherAssignment[]>([]);
  const [groups, setGroups] = useState<TeacherGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [groupId, setGroupId] = useState("");
  const [language, setLanguage] = useState<string>("python");
  const [deadline, setDeadline] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [assignmentData, groupData] = await Promise.all([
        apiRequest<TeacherAssignment[]>("/teacher/assignments"),
        apiRequest<TeacherGroup[]>("/teacher/groups"),
      ]);
      setAssignments(assignmentData);
      setGroups(groupData);
      setGroupId((current) => current || groupData[0]?.id || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load assignments.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function createAssignment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      await apiRequest<TeacherAssignment>("/teacher/assignments", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim() || null,
          instructions: instructions.trim() || null,
          group_id: groupId,
          due_at: deadline ? new Date(deadline).toISOString() : null,
          language,
        }),
      });
      setTitle("");
      setDescription("");
      setInstructions("");
      setDeadline("");
      setNotice("Assignment created and assigned to the selected class.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the assignment.");
    } finally {
      setSaving(false);
    }
  }

  const visibleAssignments = assignments.filter((assignment) =>
    `${assignment.title} ${assignment.group_name ?? ""}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );

  return (
    <main className="min-h-screen bg-canvas text-white">
      <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 sm:py-14">
        <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="mb-3 text-xs tracking-[0.2em] text-lime">TEACHER WORKSPACE</p>
            <h1 className="text-3xl font-semibold sm:text-4xl">Assignments</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
              Create class work, review the complete roster, and release each student&apos;s
              questions only when you are ready.
            </p>
          </div>
          <Link
            href="/teacher/groups"
            className="inline-flex w-fit items-center gap-2 rounded-lg border border-line px-4 py-2.5 text-sm text-white hover:border-lime hover:text-lime"
          >
            Manage classes <ArrowRight size={15} />
          </Link>
        </div>

        {error && <Notice tone="error">{error}</Notice>}
        {notice && <Notice tone="success">{notice}</Notice>}

        <section className="mb-8 rounded-2xl border border-line bg-panel p-5 sm:p-7">
          <div className="mb-5 flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-lime/10 text-lime">
              <Plus size={19} />
            </span>
            <div>
              <h2 className="font-semibold">Create an assignment</h2>
              <p className="mt-1 text-xs text-muted">
                Choose from the code-analysis adapters already supported by the backend.
              </p>
            </div>
          </div>
          <form onSubmit={createAssignment} className="grid gap-4 md:grid-cols-2">
            <label className="text-sm">
              Title
              <input
                required
                maxLength={200}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                className="mt-2 w-full rounded-lg border border-line bg-canvas px-3 py-2.5 text-sm outline-none focus:border-lime"
              />
            </label>
            <label className="text-sm">
              Assign to class
              <select
                required
                value={groupId}
                onChange={(event) => setGroupId(event.target.value)}
                disabled={!groups.length}
                className="mt-2 w-full rounded-lg border border-line bg-canvas px-3 py-2.5 text-sm outline-none focus:border-lime"
              >
                <option value="">Choose a class</option>
                {groups.map((group) => (
                  <option key={group.id} value={group.id}>{group.name}</option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              Code language
              <select
                value={language}
                onChange={(event) => setLanguage(event.target.value)}
                className="mt-2 w-full rounded-lg border border-line bg-canvas px-3 py-2.5 text-sm outline-none focus:border-lime"
              >
                {SUPPORTED_CODE_LANGUAGES.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} ({item.extensions.join(", ")})
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm md:col-span-2">
              Description
              <textarea
                rows={2}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                className="mt-2 w-full resize-y rounded-lg border border-line bg-canvas px-3 py-2.5 text-sm outline-none focus:border-lime"
              />
            </label>
            <label className="text-sm md:col-span-2">
              Instructions
              <textarea
                rows={3}
                maxLength={10_000}
                value={instructions}
                onChange={(event) => setInstructions(event.target.value)}
                className="mt-2 w-full resize-y rounded-lg border border-line bg-canvas px-3 py-2.5 text-sm outline-none focus:border-lime"
              />
            </label>
            <label className="text-sm">
              Deadline (optional)
              <input
                type="datetime-local"
                value={deadline}
                onChange={(event) => setDeadline(event.target.value)}
                className="mt-2 w-full rounded-lg border border-line bg-canvas px-3 py-2.5 text-sm outline-none focus:border-lime"
              />
            </label>
            <div className="flex items-end">
              <button
                disabled={saving || loading || !groups.length}
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-lime px-4 py-2.5 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-50 md:w-auto"
              >
                <Plus size={16} /> {saving ? "Creating…" : "Create assignment"}
              </button>
            </div>
          </form>
          {!loading && groups.length === 0 && (
            <p className="mt-4 text-sm text-amber-200">
              Create a class and add students before assigning work.{" "}
              <Link href="/teacher/groups" className="underline">Set up a class</Link>
            </p>
          )}
        </section>

        <section className="overflow-hidden rounded-2xl border border-line bg-panel">
          <div className="flex flex-col justify-between gap-4 border-b border-line p-5 sm:flex-row sm:items-center sm:px-6">
            <div>
              <h2 className="font-semibold">All assignments</h2>
              <p className="mt-1 text-xs text-muted">Current and past work created by you.</p>
            </div>
            <div className="flex gap-2">
              <label className="flex items-center gap-2 rounded-lg border border-line bg-canvas px-3">
                <Search size={15} className="text-muted" />
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search"
                  className="w-36 bg-transparent py-2 text-sm outline-none placeholder:text-muted"
                />
              </label>
              <button
                onClick={() => void load()}
                aria-label="Refresh assignments"
                className="rounded-lg border border-line p-2.5 text-muted hover:text-lime"
              >
                <RefreshCw size={16} />
              </button>
            </div>
          </div>
          {loading ? (
            <p className="p-8 text-center text-sm text-muted">Loading assignments…</p>
          ) : visibleAssignments.length === 0 ? (
            <p className="p-8 text-center text-sm text-muted">
              {assignments.length ? "No assignments match your search." : "No assignments have been created yet."}
            </p>
          ) : (
            <div className="divide-y divide-line">
              {visibleAssignments.map((assignment) => (
                <Link
                  key={assignment.id}
                  href={`/teacher/assignments/${assignment.id}`}
                  className="flex flex-col gap-4 px-5 py-5 transition hover:bg-white/[0.02] sm:flex-row sm:items-center sm:px-6"
                >
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-lime/10 text-lime">
                    <BookOpen size={18} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{assignment.title}</span>
                    <span className="mt-1 block text-xs text-muted">
                      {assignment.group_name ?? "No class"} · Created {formatDate(assignment.created_at)}
                      {assignment.due_at ? ` · Due ${formatDate(assignment.due_at)}` : ""}
                    </span>
                  </span>
                  <span className="flex items-center gap-4 text-xs text-muted">
                    <span>{assignment.student_count} students</span>
                    <span>{assignment.released_questions} released</span>
                    <span className="rounded-full border border-line px-2.5 py-1">{assignment.status}</span>
                    <ArrowRight size={16} className="text-lime" />
                  </span>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function Notice({
  tone,
  children,
}: {
  tone: "error" | "success";
  children: React.ReactNode;
}) {
  return (
    <p className={`mb-4 rounded-lg border px-4 py-3 text-sm ${
      tone === "error"
        ? "border-red-400/30 bg-red-400/5 text-red-200"
        : "border-lime/30 bg-lime/5 text-lime"
    }`}>
      {children}
    </p>
  );
}
