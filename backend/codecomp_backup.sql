--
-- PostgreSQL database dump
--

\restrict uWechg9nVobyuZQlEifSPYbh8SMLqg1AzFekPEqkavL45ghoIocokxHYVekZz8Q

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: answers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.answers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    attempt_id uuid NOT NULL,
    question_id uuid NOT NULL,
    answer_text text NOT NULL,
    saved_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.answers OWNER TO postgres;

--
-- Name: assignments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.assignments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    teacher_id uuid NOT NULL,
    title text NOT NULL,
    description text,
    language text DEFAULT 'python'::text NOT NULL,
    due_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.assignments OWNER TO postgres;

--
-- Name: attempt_results; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.attempt_results (
    attempt_id uuid NOT NULL,
    comprehension_index numeric,
    sub_scores jsonb,
    flag_oral_followup boolean,
    needs_review_count integer,
    computed_at timestamp with time zone DEFAULT now() NOT NULL,
    status text DEFAULT 'graded'::text NOT NULL,
    total_score numeric,
    max_score numeric,
    percentage numeric,
    graded_at timestamp with time zone,
    grading_error text,
    CONSTRAINT ck_attempt_results_status CHECK ((status = ANY (ARRAY['pending'::text, 'grading'::text, 'graded'::text, 'failed'::text])))
);


ALTER TABLE public.attempt_results OWNER TO postgres;

--
-- Name: exam_attempts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exam_attempts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    slot_id uuid NOT NULL,
    student_id uuid NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    deadline_at timestamp with time zone NOT NULL,
    submitted_at timestamp with time zone,
    auto_submitted boolean DEFAULT false NOT NULL
);


ALTER TABLE public.exam_attempts OWNER TO postgres;

--
-- Name: exam_questions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exam_questions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    exam_id uuid NOT NULL,
    slot_id uuid NOT NULL,
    student_id uuid NOT NULL,
    submission_id uuid NOT NULL,
    order_idx integer NOT NULL,
    type text NOT NULL,
    prompt text NOT NULL,
    line_refs jsonb NOT NULL,
    answer_format text NOT NULL,
    options jsonb,
    answer_key jsonb,
    rubric jsonb,
    max_score numeric NOT NULL,
    status text NOT NULL,
    question_hash text NOT NULL,
    CONSTRAINT ck_exam_questions_status CHECK ((status = ANY (ARRAY['generating'::text, 'draft'::text, 'approved'::text, 'failed'::text])))
);


ALTER TABLE public.exam_questions OWNER TO postgres;

--
-- Name: exam_slots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exam_slots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    exam_id uuid NOT NULL,
    group_id uuid,
    starts_at timestamp with time zone NOT NULL,
    ends_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_exam_slots_time_window CHECK ((ends_at > starts_at))
);


ALTER TABLE public.exam_slots OWNER TO postgres;

--
-- Name: exams; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exams (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    teacher_id uuid NOT NULL,
    assignment_id uuid NOT NULL,
    title text NOT NULL,
    duration_minutes integer NOT NULL,
    num_questions integer NOT NULL,
    auto_approve boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.exams OWNER TO postgres;

--
-- Name: group_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.group_members (
    group_id uuid NOT NULL,
    student_id uuid NOT NULL
);


ALTER TABLE public.group_members OWNER TO postgres;

--
-- Name: groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.groups (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    teacher_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.groups OWNER TO postgres;

--
-- Name: practice_answers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.practice_answers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    question_id uuid NOT NULL,
    answer_text text NOT NULL,
    is_correct boolean,
    score numeric,
    feedback text,
    answered_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.practice_answers OWNER TO postgres;

--
-- Name: practice_questions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.practice_questions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid NOT NULL,
    order_idx integer NOT NULL,
    type text NOT NULL,
    prompt text NOT NULL,
    line_refs jsonb NOT NULL,
    answer_format text NOT NULL,
    options jsonb,
    answer_key jsonb,
    explanation text,
    source text NOT NULL,
    question_hash text NOT NULL,
    CONSTRAINT ck_practice_questions_source CHECK ((source = ANY (ARRAY['deterministic'::text, 'llm'::text])))
);


ALTER TABLE public.practice_questions OWNER TO postgres;

--
-- Name: practice_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.practice_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    student_id uuid NOT NULL,
    submission_id uuid NOT NULL,
    status text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_practice_sessions_status CHECK ((status = ANY (ARRAY['generating'::text, 'ready'::text, 'failed'::text])))
);


ALTER TABLE public.practice_sessions OWNER TO postgres;

--
-- Name: profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.profiles (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    full_name text NOT NULL,
    role text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_profiles_role CHECK ((role = ANY (ARRAY['student'::text, 'teacher'::text])))
);


ALTER TABLE public.profiles OWNER TO postgres;

--
-- Name: scores; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.scores (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    answer_id uuid NOT NULL,
    score numeric NOT NULL,
    max_score numeric NOT NULL,
    evidence text NOT NULL,
    confidence numeric NOT NULL,
    needs_review boolean NOT NULL,
    feedback text NOT NULL
);


ALTER TABLE public.scores OWNER TO postgres;

--
-- Name: slot_students; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.slot_students (
    slot_id uuid NOT NULL,
    student_id uuid NOT NULL,
    submission_id uuid
);


ALTER TABLE public.slot_students OWNER TO postgres;

--
-- Name: submissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.submissions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    assignment_id uuid,
    student_id uuid NOT NULL,
    filename text NOT NULL,
    code text NOT NULL,
    code_hash text NOT NULL,
    code_facts jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.submissions OWNER TO postgres;

--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
a12b3c4d5e6f
\.


--
-- Data for Name: answers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.answers (id, attempt_id, question_id, answer_text, saved_at) FROM stdin;
\.


--
-- Data for Name: assignments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.assignments (id, teacher_id, title, description, language, due_at, created_at) FROM stdin;
9ad68d24-6cec-402c-8ce2-d20607879980	dfac2bf0-85b8-4239-a987-01fc739a7408	Manual Test Assignment 01	Temporary assignment for API testing	python	2026-10-09 07:49:00.181+05:30	2026-10-09 07:49:52.219901+05:30
1347d3fc-d0a3-4a27-a347-efba3e543a0c	dfac2bf0-85b8-4239-a987-01fc739a7408	Manual Test Assignment 01	Temporary assignment for API testing	python	2026-10-09 07:49:00.181+05:30	2026-10-09 07:53:28.453468+05:30
c6dde24f-e19e-45c5-b296-a93d53e86694	dfac2bf0-85b8-4239-a987-01fc739a7408	Python Fundamentals	Variables, functions, loops and basic data structures.	python	2026-10-20 18:00:00+05:30	2026-10-09 02:36:42.03126+05:30
f6c647be-4522-440b-b013-e08f5e2e2298	dfac2bf0-85b8-4239-a987-01fc739a7408	Loops Practice	Practice loop tracing.	python	\N	2026-10-09 02:37:05.735473+05:30
\.


--
-- Data for Name: attempt_results; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.attempt_results (attempt_id, comprehension_index, sub_scores, flag_oral_followup, needs_review_count, computed_at, status, total_score, max_score, percentage, graded_at, grading_error) FROM stdin;
\.


--
-- Data for Name: exam_attempts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.exam_attempts (id, slot_id, student_id, started_at, deadline_at, submitted_at, auto_submitted) FROM stdin;
\.


--
-- Data for Name: exam_questions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.exam_questions (id, exam_id, slot_id, student_id, submission_id, order_idx, type, prompt, line_refs, answer_format, options, answer_key, rubric, max_score, status, question_hash) FROM stdin;
\.


--
-- Data for Name: exam_slots; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.exam_slots (id, exam_id, group_id, starts_at, ends_at) FROM stdin;
\.


--
-- Data for Name: exams; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.exams (id, teacher_id, assignment_id, title, duration_minutes, num_questions, auto_approve, created_at) FROM stdin;
d3324abe-0b01-4934-95ad-923a58520f20	dfac2bf0-85b8-4239-a987-01fc739a7408	1347d3fc-d0a3-4a27-a347-efba3e543a0c	Manual Test Exam 01	10	5	t	2026-10-09 07:53:43.752573+05:30
\.


--
-- Data for Name: group_members; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.group_members (group_id, student_id) FROM stdin;
ef603ed7-c316-467e-a584-4f78a3a57e2a	e3c016cb-25b7-42a3-9a70-70adf457065b
\.


--
-- Data for Name: groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.groups (id, name, teacher_id, created_at) FROM stdin;
ef603ed7-c316-467e-a584-4f78a3a57e2a	Python Fundamentals	dfac2bf0-85b8-4239-a987-01fc739a7408	2026-10-09 02:19:56.462914+05:30
3f1b07b6-2f99-41a4-9305-cf6148042012	Manual Test Group 01	dfac2bf0-85b8-4239-a987-01fc739a7408	2026-10-09 07:46:08.695377+05:30
\.


--
-- Data for Name: practice_answers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.practice_answers (id, question_id, answer_text, is_correct, score, feedback, answered_at) FROM stdin;
\.


--
-- Data for Name: practice_questions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.practice_questions (id, session_id, order_idx, type, prompt, line_refs, answer_format, options, answer_key, explanation, source, question_hash) FROM stdin;
\.


--
-- Data for Name: practice_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.practice_sessions (id, student_id, submission_id, status, created_at) FROM stdin;
\.


--
-- Data for Name: profiles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.profiles (id, email, password_hash, full_name, role, created_at) FROM stdin;
e3c016cb-25b7-42a3-9a70-70adf457065b	student1@example.com	$argon2id$v=19$m=65536,t=3,p=4$E6LhjEUUqfDJ/iNc2lmrgA$fkShInMbNygPYeKomerCyWUw0bxtF5wdQ3JjMnA5PJk	Student One	student	2026-10-08 23:33:57.365782+05:30
1c8a886e-3008-4b69-b552-2beb264efc13	student2@example.com	$argon2id$v=19$m=65536,t=3,p=4$50AE+lmKSzyFWGlq+42uQQ$HebphLNfXBMYsn+s/Q6Iz8aFTIvXamn4a4igLadnGyk	Student Two	student	2026-10-08 23:35:46.983794+05:30
541a56a2-4014-41bc-b6dc-4c774dc22f32	teacher1@example.com	$argon2id$v=19$m=65536,t=3,p=4$riixxotBzzdnWGUelQ0j4g$HMkg54SCxWTpdI14oWhCuzBi3ARekrKnxyYPUSHCReo	Teacher One	teacher	2026-10-08 23:39:52.878812+05:30
dfac2bf0-85b8-4239-a987-01fc739a7408	teacher2@example.com	$argon2id$v=19$m=65536,t=3,p=4$nJGc9L67l8WTJqkXHpQLug$0gEBtpOlD9rSjXtD3vTnhtWjZwWSV5aQGsj+aKmKHEM	Teacher Two	teacher	2026-10-09 00:00:16.471085+05:30
6b15e859-e766-4108-82ed-468c4c9a1dda	teacher3@example.com	$argon2id$v=19$m=65536,t=3,p=4$pK8sm/tAtcEM8GwEwIbF8g$ZDOo11Ha0slPPrqVt5JkTTvQopuAz3EJsA5MHhV15pc	Teacher Three	teacher	2026-10-09 02:28:48.286114+05:30
cc4e3888-4329-4c3f-8034-76ead8cdb550	teacher4@example.com	$argon2id$v=19$m=65536,t=3,p=4$ajdaQB3t6j9Q2JZpk9tT5A$7MpWZJSamxYbIRNB2z+vzTbR2tm5hIeMT9Pq9vXlPF4	Teacher Four	teacher	2026-10-09 07:28:37.958658+05:30
0b371d22-c2e3-45db-8774-b7d3d74d9a5e	student3@example.com	$argon2id$v=19$m=65536,t=3,p=4$hue9257wag/coMblhK4XiA$0UhZheXH5Z7WI5kcORPQUmvo6kJOSsfA8EeNYZTxssY	Student Three	student	2026-10-09 07:41:37.483028+05:30
c15bf363-659a-40b8-8ca0-ebe3fe693008	student4@example.com	$argon2id$v=19$m=65536,t=3,p=4$yXOGEMbRqY3kf7arKXzC5Q$WoBC/DoIBWmJEe8iKv9LGeLpYyjHrwuKqNTrjCNlRxs	Student Four	student	2026-10-09 07:41:53.271407+05:30
\.


--
-- Data for Name: scores; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.scores (id, answer_id, score, max_score, evidence, confidence, needs_review, feedback) FROM stdin;
\.


--
-- Data for Name: slot_students; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.slot_students (slot_id, student_id, submission_id) FROM stdin;
\.


--
-- Data for Name: submissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.submissions (id, assignment_id, student_id, filename, code, code_hash, code_facts, created_at) FROM stdin;
\.


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: answers answers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT answers_pkey PRIMARY KEY (id);


--
-- Name: assignments assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assignments
    ADD CONSTRAINT assignments_pkey PRIMARY KEY (id);


--
-- Name: attempt_results attempt_results_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attempt_results
    ADD CONSTRAINT attempt_results_pkey PRIMARY KEY (attempt_id);


--
-- Name: exam_attempts exam_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_attempts
    ADD CONSTRAINT exam_attempts_pkey PRIMARY KEY (id);


--
-- Name: exam_questions exam_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_questions
    ADD CONSTRAINT exam_questions_pkey PRIMARY KEY (id);


--
-- Name: exam_slots exam_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_slots
    ADD CONSTRAINT exam_slots_pkey PRIMARY KEY (id);


--
-- Name: exams exams_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_pkey PRIMARY KEY (id);


--
-- Name: group_members group_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_pkey PRIMARY KEY (group_id, student_id);


--
-- Name: groups groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_pkey PRIMARY KEY (id);


--
-- Name: practice_answers practice_answers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.practice_answers
    ADD CONSTRAINT practice_answers_pkey PRIMARY KEY (id);


--
-- Name: practice_questions practice_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.practice_questions
    ADD CONSTRAINT practice_questions_pkey PRIMARY KEY (id);


--
-- Name: practice_sessions practice_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.practice_sessions
    ADD CONSTRAINT practice_sessions_pkey PRIMARY KEY (id);


--
-- Name: profiles profiles_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.profiles
    ADD CONSTRAINT profiles_email_key UNIQUE (email);


--
-- Name: profiles profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.profiles
    ADD CONSTRAINT profiles_pkey PRIMARY KEY (id);


--
-- Name: scores scores_answer_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_answer_id_key UNIQUE (answer_id);


--
-- Name: scores scores_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_pkey PRIMARY KEY (id);


--
-- Name: slot_students slot_students_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.slot_students
    ADD CONSTRAINT slot_students_pkey PRIMARY KEY (slot_id, student_id);


--
-- Name: submissions submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_pkey PRIMARY KEY (id);


--
-- Name: answers uq_answers_attempt_question; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT uq_answers_attempt_question UNIQUE (attempt_id, question_id);


--
-- Name: exam_attempts uq_exam_attempts_slot_student; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_attempts
    ADD CONSTRAINT uq_exam_attempts_slot_student UNIQUE (slot_id, student_id);


--
-- Name: ix_exam_questions_slot_student_order; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_exam_questions_slot_student_order ON public.exam_questions USING btree (slot_id, student_id, order_idx);


--
-- Name: ix_submissions_assignment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_submissions_assignment ON public.submissions USING btree (assignment_id);


--
-- Name: ix_submissions_student_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_submissions_student_created ON public.submissions USING btree (student_id, created_at DESC);


--
-- Name: answers answers_attempt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT answers_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.exam_attempts(id);


--
-- Name: answers answers_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.answers
    ADD CONSTRAINT answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.exam_questions(id);


--
-- Name: assignments assignments_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assignments
    ADD CONSTRAINT assignments_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.profiles(id);


--
-- Name: attempt_results attempt_results_attempt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attempt_results
    ADD CONSTRAINT attempt_results_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.exam_attempts(id);


--
-- Name: exam_attempts exam_attempts_slot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_attempts
    ADD CONSTRAINT exam_attempts_slot_id_fkey FOREIGN KEY (slot_id) REFERENCES public.exam_slots(id);


--
-- Name: exam_attempts exam_attempts_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_attempts
    ADD CONSTRAINT exam_attempts_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.profiles(id);


--
-- Name: exam_questions exam_questions_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_questions
    ADD CONSTRAINT exam_questions_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exams(id);


--
-- Name: exam_questions exam_questions_slot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_questions
    ADD CONSTRAINT exam_questions_slot_id_fkey FOREIGN KEY (slot_id) REFERENCES public.exam_slots(id);


--
-- Name: exam_questions exam_questions_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_questions
    ADD CONSTRAINT exam_questions_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.profiles(id);


--
-- Name: exam_questions exam_questions_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_questions
    ADD CONSTRAINT exam_questions_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.submissions(id);


--
-- Name: exam_slots exam_slots_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_slots
    ADD CONSTRAINT exam_slots_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exams(id);


--
-- Name: exam_slots exam_slots_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_slots
    ADD CONSTRAINT exam_slots_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);


--
-- Name: exams exams_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id);


--
-- Name: exams exams_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.profiles(id);


--
-- Name: group_members group_members_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.groups(id);


--
-- Name: group_members group_members_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.profiles(id);


--
-- Name: groups groups_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.groups
    ADD CONSTRAINT groups_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.profiles(id);


--
-- Name: practice_answers practice_answers_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.practice_answers
    ADD CONSTRAINT practice_answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.practice_questions(id);


--
-- Name: practice_questions practice_questions_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.practice_questions
    ADD CONSTRAINT practice_questions_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.practice_sessions(id);


--
-- Name: practice_sessions practice_sessions_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.practice_sessions
    ADD CONSTRAINT practice_sessions_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.profiles(id);


--
-- Name: practice_sessions practice_sessions_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.practice_sessions
    ADD CONSTRAINT practice_sessions_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.submissions(id);


--
-- Name: scores scores_answer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_answer_id_fkey FOREIGN KEY (answer_id) REFERENCES public.answers(id);


--
-- Name: slot_students slot_students_slot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.slot_students
    ADD CONSTRAINT slot_students_slot_id_fkey FOREIGN KEY (slot_id) REFERENCES public.exam_slots(id);


--
-- Name: slot_students slot_students_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.slot_students
    ADD CONSTRAINT slot_students_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.profiles(id);


--
-- Name: slot_students slot_students_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.slot_students
    ADD CONSTRAINT slot_students_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.submissions(id);


--
-- Name: submissions submissions_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id);


--
-- Name: submissions submissions_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.profiles(id);


--
-- PostgreSQL database dump complete
--

\unrestrict uWechg9nVobyuZQlEifSPYbh8SMLqg1AzFekPEqkavL45ghoIocokxHYVekZz8Q

