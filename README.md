# Code Comprehension Platform

A platform for assessing student code comprehension through automated analysis and AI-generated questions.

## Project Structure

See the scaffold structure for the complete organization of the codebase.

## Getting Started

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Configure your .env file
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env.local
# Configure your .env.local file
npm run dev
```

## Team Ownership

- **Member 1**: Backend platform (API, models, routers, services)
- **Member 2**: Analysis engine (code facts, runner, tracer, questions)
- **Member 3**: AI integration (question generation, evaluation, scoring)
- **Member 4**: Frontend (Next.js UI, student/teacher portals)

## College Assignments

Teachers create classes, add registered student accounts, and create assignments
for a class from the teacher portal. The assignment dashboard includes current
and past assignments. The assignment detail page shows the complete class roster,
including students who have not submitted, and displays marks only when a saved
evaluation score exists.

Students type code directly into the assignment editor. The backend runs the
existing language-specific structural analysis and sends the source code and
assignment instructions to the configured Agnes AI model for a code review
and private draft comprehension questions. Draft questions are never shown to
students until the teacher explicitly releases them. Submitted answers are
graded with the private expected answer and rubric; saved marks and per-answer
feedback are then visible to the student and the assignment's teacher.
The source submission is committed before external AI analysis starts, so an
AI provider outage does not discard student code. In that case the student is
told the code was saved and AI feedback/questions did not complete.
Open practice sessions generate private-to-the-student questions from the
submitted code, persist those questions and answers in the existing practice
tables, and ask the configured practice model to score each answer with
feedback. Student APIs never return the private expected answers or rubrics.
The student dashboard shows released question prompts only for that student.
Each released question also includes a short hint pointing to its referenced
code lines and encouraging the student to trace the relevant behavior; if no
lines were supplied, it gives a general code-reasoning hint. Hints never expose
the expected answer or grading rubric.
After answers are submitted and evaluated, the result sheet shows the persisted
answer marks and a code-understanding score out of 100, normalized from the
awarded points over the available points, plus per-answer feedback and code
improvement suggestions.

Questions are tied to a student's submitted code and start in `draft` state.
Student assignment
responses contain only released prompts and supported response fields; answer
keys and rubrics are never part of student schemas or responses. Students must
be class members to fetch assignment details, submit code, start an attempt, or
save answers. Submitted code cannot be changed after questions are released or
an attempt has started. Teachers must own the assignment to manage or inspect
it.

The workflow uses existing `assignments`, `exams`, `exam_slots`, `groups`,
`group_members`, `exam_questions`, `exam_attempts`, `answers`, and `scores`
tables; no database migration is required. Assignment instructions are stored
with the description in the existing description column to avoid changing the
schema.

Teacher student-detail views include the same saved code-understanding score
out of 100 and attempt aggregates shown to the student, alongside the per-answer
marks and evaluation feedback.

Supported languages use the adapters in `backend/analysis/languages`: Python,
C, C++, Java, JavaScript, and Go. Text-editor submissions are limited to 50,000
UTF-8 bytes. AI feedback, question generation, and grading require the
server-side `AGNES_API_KEY`, `AGNES_API_BASE_URL`, `MODEL_PRACTICE`, and
`MODEL_EXAM` settings. Code and answers are sent to the configured Agnes AI API
for these features; do not submit sensitive source
code or personal data unless permitted by your institution. The analysis
adapters do not execute submitted source, and the application only displays
marks returned by its configured AI grader and persisted in the database.

Teacher accounts are created only with the server-side `TEACHER_INVITE_CODE`;
an Atria email address alone never grants teacher access. Set a non-empty,
high-entropy invite code in the backend environment before enabling teacher
registration. Student registration remains available to non-college emails for
public practice; assignment access still requires explicit class membership.
Set `COOKIE_SECURE=true` when serving the backend over HTTPS; leave it false for
local HTTP development.

Key API routes:

- `GET/POST /api/teacher/groups` and `GET/POST /api/teacher/groups/{id}/members`
- `GET/POST /api/teacher/assignments`
- `GET /api/teacher/assignments/{id}` for class roster and saved marks
- `GET /api/teacher/assignments/{id}/students/{student_id}` for an authorized
  student submission and answers
- `POST /api/teacher/assignments/{id}/questions/release` to release all draft
  questions for the assignment
- `POST /api/teacher/assignments/{id}/questions` and
  `PATCH /api/teacher/assignments/{id}/questions/{question_id}/release`
- `GET /api/student/assignments` and `GET /api/student/assignments/{id}`
- `POST /api/student/submissions/code` for code entered in the editor (public
  practice or assigned code); public submissions also create saved practice
  sessions and AI-generated questions
- `GET /api/student/practice-sessions/{id}` for the owner's saved code,
  generated questions, answers, and scores
- `PUT /api/student/practice-sessions/{id}/questions/{question_id}/answer` to
  save and AI-grade an open-practice answer
- `POST /api/student/submissions` remains available for legacy multipart
  clients and uses the same AI analysis/review flow
- `POST /api/student/assignments/{id}/attempts`, `GET
  /api/student/assignments/{id}/attempt`, and attempt answer/submit routes

Focused workflow tests:

```bash
cd backend
PYTHONPATH=.. python -m pytest tests/api/test_assignment_workflow.py tests/api/test_submission_cache.py tests/analysis/test_multilanguage.py
```

On Windows PowerShell, set `$env:PYTHONPATH = (Resolve-Path ..).Path` before
running the same `python -m pytest` command.

## Documentation

See the `docs/` directory for detailed documentation on architecture, API, and components.
