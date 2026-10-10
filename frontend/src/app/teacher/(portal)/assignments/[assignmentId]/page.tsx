"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  Sparkles,
  UnlockKeyhole,
  Users,
} from "lucide-react";

import {
  ApiRequestError,
  apiRequest,
  AssignmentStudent,
  formatDate,
  TeacherAssignmentDetail,
  TeacherStudentDetail,
} from "@/lib/assignments";

export default function TeacherAssignmentDetailPage() {
  const params = useParams<{ assignmentId: string }>();
  const assignmentId = params.assignmentId;
  const [data, setData] = useState<TeacherAssignmentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [releasing, setReleasing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await apiRequest<TeacherAssignmentDetail>(
        `/teacher/assignments/${assignmentId}`,
      ));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load assignment details.");
    } finally {
      setLoading(false);
    }
  }, [assignmentId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function releaseQuestions() {
    setReleasing(true);
    setError("");
    setNotice("");
    try {
      let releasedQuestions: number;
      try {
        const result = await apiRequest<{ released_questions: number }>(
          `/teacher/assignments/${assignmentId}/questions/release`,
          { method: "POST" },
        );
        releasedQuestions = result.released_questions;
      } catch (err) {
        if (!(err instanceof ApiRequestError) || err.status !== 404 || !data) {
          throw err;
        }
        const studentDetails = await Promise.all(
          data.students
            .filter((student) => student.submission_id)
            .map((student) => apiRequest<TeacherStudentDetail>(
              `/teacher/assignments/${assignmentId}/students/${student.student_id}`,
            )),
        );
        const unreleased = studentDetails.flatMap((detail) =>
          detail.answers.filter((answer) => !answer.released),
        );
        await Promise.all(
          unreleased.map((question) => apiRequest(
            `/teacher/assignments/${assignmentId}/questions/${question.question_id}/release`,
            { method: "PATCH", body: JSON.stringify({ released: true }) },
          )),
        );
        releasedQuestions = unreleased.length;
      }
      setNotice(
        releasedQuestions
          ? `${releasedQuestions} question(s) released to the assigned students.`
          : "There are no draft questions to release yet. Questions are generated after students submit code.",
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not release questions.");
    } finally {
      setReleasing(false);
    }
  }

  if (loading) {
    return <main className="min-h-screen bg-canvas p-8 text-center text-muted">Loading assignment…</main>;
  }
  if (error || !data) {
    return (
      <main className="min-h-screen bg-canvas px-5 py-10 text-white">
        <Link href="/teacher/assignments" className="text-sm text-lime">← All assignments</Link>
        <p className="mt-6 text-red-200">{error || "Assignment not found."}</p>
      </main>
    );
  }

  const { assignment, students } = data;
  const draftQuestionCount = assignment.draft_questions ?? 0;
  const submitted = students.filter((student) => student.submission_id).length;
  const graded = students.filter((student) => student.score !== null).length;
  const scoredStudents = students.filter(
    (student) => student.score !== null && student.max_score !== null && student.max_score > 0,
  );
  const average = scoredStudents.length
    ? scoredStudents.reduce(
        (sum, student) => sum + ((student.score ?? 0) / (student.max_score ?? 1)) * 100,
        0,
      ) / scoredStudents.length
    : null;

  return (
    <main className="min-h-screen bg-canvas text-white">
      <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8">
        <Link
          href="/teacher/assignments"
          className="inline-flex items-center gap-2 text-sm text-muted hover:text-lime"
        >
          <ArrowLeft size={16} /> All assignments
        </Link>
        <header className="mt-7 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <p className="mb-3 text-xs tracking-[0.2em] text-lime">CLASS OVERVIEW</p>
            <h1 className="text-3xl font-semibold sm:text-4xl">{assignment.title}</h1>
            {assignment.description && <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">{assignment.description}</p>}
            {assignment.instructions && (
              <div className="mt-3 max-w-3xl rounded-lg border border-line bg-panel px-4 py-3 text-sm leading-6 text-zinc-300">
                <strong className="mr-2 text-white">Instructions:</strong>{assignment.instructions}
              </div>
            )}
            <p className="mt-3 text-xs text-muted">
              {assignment.group_name ?? "No class"} · Created {formatDate(assignment.created_at)}
              {assignment.due_at ? ` · Due ${formatDate(assignment.due_at)}` : " · No deadline"}
            </p>
          </div>
          <button
            onClick={() => void load()}
            className="rounded-lg border border-line px-4 py-2.5 text-sm hover:border-lime hover:text-lime"
          >
            Refresh
          </button>
        </header>

        <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Summary icon={<Users size={18} />} label="Assigned students" value={String(students.length)} />
          <Summary icon={<CheckCircle2 size={18} />} label="Code submitted" value={`${submitted} / ${students.length}`} />
          <Summary icon={<Clock3 size={18} />} label="Awaiting submission" value={String(students.length - submitted)} />
          <Summary icon={<CheckCircle2 size={18} />} label="Students with saved marks" value={String(graded)} />
        </section>

        <section className="mt-7 flex flex-col justify-between gap-5 rounded-2xl border border-lime/25 bg-panel p-5 sm:flex-row sm:items-center sm:p-6">
          <div className="flex items-start gap-3">
            <Sparkles className="mt-0.5 shrink-0 text-lime" size={20} />
            <div>
              <h2 className="font-semibold">Generated questions and student access</h2>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
                {draftQuestionCount
                  ? `${draftQuestionCount} draft question(s) are ready. Release makes them available to the students whose code generated them.`
                  : "Questions are drafted after a student submits code. Use this action to check for and release any questions ready for the class."}
                {` ${assignment.released_questions} already released.`}
              </p>
            </div>
          </div>
          <button
            onClick={() => void releaseQuestions()}
            disabled={releasing}
            title={draftQuestionCount === 0 ? "Questions are generated after a student submits code." : undefined}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-lime px-4 py-3 text-sm font-semibold text-black hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            <UnlockKeyhole size={16} />
            {releasing
              ? "Releasing…"
              : draftQuestionCount
                ? "Release questions to class"
                : "Check for questions and release"}
          </button>
        </section>
        {error && (
          <p role="alert" className="mt-4 rounded-lg border border-red-400/30 bg-red-400/5 px-4 py-3 text-sm text-red-200">
            {error}
          </p>
        )}
        {notice && (
          <p role="status" className="mt-4 rounded-lg border border-lime/30 bg-lime/5 px-4 py-3 text-sm text-lime">
            {notice}
          </p>
        )}

        <section className="mt-7 rounded-2xl border border-line bg-panel p-5 sm:p-6">
          <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
            <div>
              <h2 className="font-semibold">Recorded class marks</h2>
              <p className="mt-1 text-xs text-muted">
                Only saved evaluation scores are shown; no score is inferred for ungraded work.
              </p>
            </div>
            <p className="text-sm text-muted">
              {average === null ? "No saved marks yet" : `Average of graded students: ${average.toFixed(1)}%`}
            </p>
          </div>
          <div className="mt-5 space-y-4">
            {scoredStudents.length === 0 ? (
              <p className="rounded-lg border border-line bg-canvas p-4 text-sm text-muted">
                Class marks will appear here when evaluation scores have been saved.
              </p>
            ) : scoredStudents.map((student) => (
              <ScoreBar key={student.student_id} student={student} />
            ))}
          </div>
        </section>

        <section className="mt-7 overflow-hidden rounded-2xl border border-line bg-panel">
          <div className="border-b border-line px-5 py-5 sm:px-6">
            <h2 className="font-semibold">Every assigned student</h2>
            <p className="mt-1 text-xs text-muted">
              Pending submissions remain visible. Open a student to inspect the uploaded code, answers, and saved evaluation.
            </p>
          </div>
          {students.length === 0 ? (
            <p className="p-8 text-center text-sm text-muted">No students are currently in this class.</p>
          ) : (
            <div className="divide-y divide-line">
              {students.map((student) => (
                <StudentRow
                  key={student.student_id}
                  student={student}
                  assignmentId={assignmentId}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function StudentRow({
  student,
  assignmentId,
}: {
  student: AssignmentStudent;
  assignmentId: string;
}) {
  return (
    <Link
      href={`/teacher/assignments/${assignmentId}/students/${student.student_id}`}
      className="flex flex-col gap-3 px-5 py-4 transition hover:bg-white/[0.02] sm:flex-row sm:items-center sm:px-6"
    >
      <span className="min-w-0 flex-1">
        <span className="block font-medium">{student.full_name}</span>
        <span className="mt-1 block text-xs text-muted">{student.email}</span>
      </span>
      <span className="flex flex-wrap items-center gap-3 text-xs text-muted">
        <span>{student.submission_filename ?? "No submission"}</span>
        {student.submitted_at && <span>{formatDate(student.submitted_at)}</span>}
        <span>{student.answered_questions} answers</span>
        <span className={`rounded-full border px-2.5 py-1 ${
          student.status === "Completed" || student.status === "Submitted"
            ? "border-lime/30 text-lime"
            : "border-line text-muted"
        }`}>{student.status}</span>
        <ArrowUpRight size={15} className="text-lime" />
      </span>
    </Link>
  );
}

function ScoreBar({ student }: { student: AssignmentStudent }) {
  const percent = Math.min(
    100,
    Math.max(0, ((student.score ?? 0) / (student.max_score ?? 1)) * 100),
  );
  return (
    <div className="grid gap-2 sm:grid-cols-[180px_1fr_100px] sm:items-center">
      <p className="truncate text-sm">{student.full_name}</p>
      <div className="h-2 overflow-hidden rounded-full bg-canvas">
        <div className="h-full rounded-full bg-lime" style={{ width: `${percent}%` }} />
      </div>
      <p className="text-xs text-muted sm:text-right">
        {student.score} / {student.max_score} ({percent.toFixed(0)}%)
      </p>
    </div>
  );
}

function Summary({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <article className="rounded-xl border border-line bg-panel p-4">
      <div className="flex items-center gap-2 text-lime">{icon}<span className="text-xs text-muted">{label}</span></div>
      <p className="mt-3 text-2xl font-semibold">{value}</p>
    </article>
  );
}
