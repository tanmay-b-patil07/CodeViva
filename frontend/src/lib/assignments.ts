export type AssignmentStatus =
  | "Upcoming"
  | "Available"
  | "Submitted"
  | "Completed"
  | "Past due"
  | "Active";

export const SUPPORTED_CODE_LANGUAGES = [
  { id: "python", name: "Python", extensions: [".py"] },
  { id: "c", name: "C", extensions: [".c"] },
  { id: "cpp", name: "C++", extensions: [".cpp", ".cc", ".cxx"] },
  { id: "java", name: "Java", extensions: [".java"] },
  { id: "javascript", name: "JavaScript", extensions: [".js", ".mjs"] },
  { id: "go", name: "Go", extensions: [".go"] },
] as const;

export function codeFileAccept(language?: string): string {
  const selected = language
    ? SUPPORTED_CODE_LANGUAGES.find((item) => item.id === language)
    : undefined;
  if (language && !selected) return "";
  return selected
    ? selected.extensions.join(",")
    : SUPPORTED_CODE_LANGUAGES.flatMap((item) => item.extensions).join(",");
}

export function codeFileMatchesLanguage(
  filename: string,
  language: string,
): boolean {
  const selected = SUPPORTED_CODE_LANGUAGES.find((item) => item.id === language);
  return !!selected && selected.extensions.some((extension) =>
    filename.toLowerCase().endsWith(extension),
  );
}

export function codeLanguageForFilename(filename: string): string | null {
  return SUPPORTED_CODE_LANGUAGES.find((language) =>
    language.extensions.some((extension) =>
      filename.toLowerCase().endsWith(extension),
    ),
  )?.id ?? null;
}

export function defaultCodeExtension(language: string): string | null {
  return SUPPORTED_CODE_LANGUAGES.find((item) => item.id === language)
    ?.extensions[0] ?? null;
}

export interface TeacherGroup {
  id: string;
  name: string;
  teacher_id: string;
  created_at: string;
}

export interface TeacherAssignment {
  id: string;
  title: string;
  description: string | null;
  instructions: string | null;
  language: string;
  created_at: string;
  due_at: string | null;
  teacher_name: string;
  group_id: string | null;
  group_name: string | null;
  slot_id: string | null;
  student_count: number;
  released_questions: number;
  draft_questions: number;
  status: AssignmentStatus;
}

export interface StudentAssignment {
  id: string;
  title: string;
  description: string | null;
  instructions: string | null;
  language: string;
  created_at: string;
  due_at: string | null;
  teacher_name: string;
  group_name: string;
  slot_id: string;
  status: AssignmentStatus;
  submission_id: string | null;
  submission_filename: string | null;
  submitted_at: string | null;
  questions_released: boolean;
  question_count: number;
  questions: StudentQuestion[];
  code_review: CodeReview | null;
  ai_analysis_status: "pending" | "complete" | "failed" | null;
  ai_analysis_error: string | null;
}

export interface CodeReview {
  summary: string;
  code_suggestions: string[];
  understanding_suggestions: string[];
}

export interface AssignmentStudent {
  student_id: string;
  full_name: string;
  email: string;
  submission_id: string | null;
  submission_filename: string | null;
  submitted_at: string | null;
  status: AssignmentStatus;
  released_questions: number;
  answered_questions: number;
  score: number | null;
  max_score: number | null;
  graded_answers: number;
  submitted_attempt: boolean;
}

export interface TeacherAssignmentDetail {
  assignment: TeacherAssignment;
  students: AssignmentStudent[];
}

export interface TeacherAnswer {
  question_id: string;
  order_idx: number;
  prompt: string;
  released: boolean;
  answer_text: string | null;
  score: number | null;
  max_score: number;
  evidence: string | null;
  feedback: string | null;
  needs_review: boolean | null;
}

export interface TeacherStudentDetail {
  student: AssignmentStudent;
  submission_code: string | null;
  code_facts: Record<string, unknown> | null;
  ai_analysis_status: "pending" | "complete" | "failed" | null;
  ai_analysis_error: string | null;
  code_review: CodeReview | null;
  answers: TeacherAnswer[];
  attempt_result: {
    comprehension_index: number;
    sub_scores: Record<string, unknown>;
    flag_oral_followup: boolean;
    needs_review_count: number;
    computed_at: string;
  } | null;
}

export interface StudentQuestion {
  id: string;
  order_idx: number;
  type: string;
  prompt: string;
  hint: string;
  line_refs: Record<string, unknown>[];
  answer_format: string;
  options: string[] | null;
}

export interface StudentAssignmentDetail extends StudentAssignment {
  submission_code: string | null;
}

export interface StudentAttempt {
  id: string;
  slot_id: string;
  started_at: string;
  deadline_at: string;
  submitted_at: string | null;
  auto_submitted: boolean;
}

export interface StudentSavedAnswer {
  id: string;
  question_id: string;
  answer_text: string;
  saved_at: string;
  score: number | null;
  max_score: number | null;
  evidence: string | null;
  feedback: string | null;
  needs_review: boolean | null;
}

export interface StudentAttemptDetail {
  attempt: StudentAttempt;
  answers: StudentSavedAnswer[];
  attempt_result: {
    comprehension_index: number;
    needs_review_count: number;
    computed_at: string;
  } | null;
}

export class ApiRequestError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const isFormData =
    typeof FormData !== "undefined" && init.body instanceof FormData;
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`/api${path}`, {
    ...init,
    credentials: "same-origin",
    headers,
  });
  if (!response.ok) {
    const responseText = await response.text();
    let message = response.statusText || "The request failed.";
    if (responseText) {
      try {
        const payload: unknown = JSON.parse(responseText);
        if (
          typeof payload === "object" &&
          payload !== null &&
          "error" in payload &&
          typeof payload.error === "object" &&
          payload.error !== null &&
          "message" in payload.error &&
          typeof payload.error.message === "string"
        ) {
          message = payload.error.message;
        } else {
          message = responseText;
        }
      } catch {
        message = responseText;
      }
    }
    throw new ApiRequestError(message, response.status);
  }
  return (await response.json()) as T;
}

export function formatDate(value: string | null): string {
  if (!value) return "No deadline";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
