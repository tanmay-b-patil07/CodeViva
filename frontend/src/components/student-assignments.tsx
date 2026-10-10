"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowRight, BookOpen, CheckCircle2, Clock3, RefreshCw } from "lucide-react";

import { apiRequest, formatDate, StudentAssignment } from "@/lib/assignments";

export function StudentAssignments({ title = "Your assignments" }: { title?: string }) {
  const [assignments, setAssignments] = useState<StudentAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setAssignments(await apiRequest<StudentAssignment[]>("/student/assignments"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load assignments.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className="mt-8 overflow-hidden rounded-2xl border border-[#2A2D27] bg-[#151713]">
      <div className="flex items-center justify-between gap-3 border-b border-[#2A2D27] px-5 py-5 sm:px-6">
        <div>
          <h2 className="font-semibold">{title}</h2>
          <p className="mt-1 text-xs text-zinc-500">
            Work assigned to you by your teachers. Questions stay hidden until released.
          </p>
        </div>
        <button
          onClick={() => void load()}
          aria-label="Refresh assignments"
          className="rounded-lg border border-[#2A2D27] p-2.5 text-zinc-400 hover:text-[#D5FF62]"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {loading ? (
        <p className="px-5 py-8 text-center text-sm text-zinc-500">Loading assignments…</p>
      ) : error ? (
        <p role="alert" className="m-5 rounded-lg border border-red-400/30 bg-red-400/5 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : assignments.length === 0 ? (
        <div className="px-5 py-10 text-center">
          <BookOpen className="mx-auto text-[#D5FF62]" size={22} />
          <p className="mt-3 text-sm text-zinc-300">No assignments have been assigned to you yet.</p>
          <p className="mt-1 text-xs text-zinc-500">Your teacher&apos;s assignments will appear here.</p>
        </div>
      ) : (
        <div className="divide-y divide-[#2A2D27]">
          {assignments.map((assignment) => (
            <Link
              key={assignment.id}
              href={`/student/assignments/${assignment.id}`}
              className="flex flex-col gap-3 px-5 py-4 transition hover:bg-white/[0.02] sm:flex-row sm:items-center sm:px-6"
            >
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#24281F] text-[#D5FF62]">
                {assignment.status === "Completed"
                  ? <CheckCircle2 size={18} />
                  : <Clock3 size={18} />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{assignment.title}</span>
                <span className="mt-1 block text-xs text-zinc-500">
                  {assignment.teacher_name} · {assignment.group_name} · Due {formatDate(assignment.due_at)}
                </span>
                {(assignment.questions ?? []).length > 0 && (
                  <ol className="mt-3 space-y-2 text-sm text-zinc-300">
                    {(assignment.questions ?? []).map((question) => (
                      <li key={question.id} className="rounded-lg border border-[#2A2D27] bg-[#10110F] p-3">
                        <p className="flex gap-2 whitespace-pre-wrap">
                          <span className="shrink-0 text-[#D5FF62]">Q{question.order_idx}.</span>
                          <span>{question.prompt}</span>
                        </p>
                        <p className="mt-2 pl-7 text-xs leading-5 text-[#D5FFB1]">
                          <span className="font-semibold text-[#D5FF62]">Hint: </span>
                          {question.hint}
                        </p>
                      </li>
                    ))}
                  </ol>
                )}
              </span>
              <span className="flex items-center gap-3 text-xs text-zinc-400">
                <span>{assignment.question_count ? `${assignment.question_count} questions released · Open to answer` : "Questions locked"}</span>
                <span className="rounded-full border border-[#414832] px-2.5 py-1">{assignment.status}</span>
                <ArrowRight size={15} className="text-[#D5FF62]" />
              </span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
