from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.security import AUTH_COOKIE_NAME, create_access_token
from app.db.models import (
    Assignment,
    Exam,
    ExamSlot,
    Group,
    GroupMember,
    Profile,
    SlotStudent,
)
from app.db.session import get_db
from app.main import app


def _auth_headers(user: Profile) -> dict[str, str]:
    token = create_access_token(user.id, user.role)
    return {"Cookie": f"{AUTH_COOKIE_NAME}={token}"}


def _test_users(db):
    users = {
        user.email: user
        for user in db.scalars(
            select(Profile).where(
                Profile.email.in_(
                    [
                        "teacher1@example.com",
                        "teacher2@example.com",
                        "student1@example.com",
                        "student2@example.com",
                    ]
                )
            )
        )
    }
    assert len(users) == 4
    return (
        users["teacher1@example.com"],
        users["teacher2@example.com"],
        users["student1@example.com"],
        users["student2@example.com"],
    )


def test_teacher_assignments_exams_slots_and_group_population():
    """Exercise Phase 8 ownership boundaries against the real test database."""
    db = next(get_db())
    marker = uuid4().hex
    assignment_ids = []
    exam_ids = []
    group_ids = []
    slot_ids = []

    try:
        teacher1, teacher2, student1, student2 = _test_users(db)
        teacher1_headers = _auth_headers(teacher1)
        teacher2_headers = _auth_headers(teacher2)
        student_headers = _auth_headers(student1)
        client = TestClient(app)

        # Assignment authentication, role guard, default language, and isolation.
        assert client.get("/api/teacher/assignments").status_code == 401
        assert (
            client.get(
                "/api/teacher/assignments", headers=student_headers
            ).status_code
            == 403
        )
        assignment_response = client.post(
            "/api/teacher/assignments",
            headers=teacher1_headers,
            json={"title": f"  Assignment {marker}  "},
        )
        assert assignment_response.status_code == 201
        assignment = assignment_response.json()
        assignment_ids.append(assignment["id"])
        assert assignment["title"] == f"Assignment {marker}"
        assert assignment["language"] == "python"

        other_assignment_response = client.post(
            "/api/teacher/assignments",
            headers=teacher2_headers,
            json={"title": f"Other assignment {marker}"},
        )
        assert other_assignment_response.status_code == 201
        other_assignment = other_assignment_response.json()
        assignment_ids.append(other_assignment["id"])

        teacher1_assignments = client.get(
            "/api/teacher/assignments", headers=teacher1_headers
        )
        assert teacher1_assignments.status_code == 200
        assert assignment["id"] in {item["id"] for item in teacher1_assignments.json()}
        assert other_assignment["id"] not in {
            item["id"] for item in teacher1_assignments.json()
        }

        # Exam ownership, role guard, anonymous access, and list isolation.
        assert client.get("/api/teacher/exams").status_code == 401
        assert client.get("/api/teacher/exams", headers=student_headers).status_code == 403
        forbidden_exam = client.post(
            "/api/teacher/exams",
            headers=teacher1_headers,
            json={
                "assignment_id": other_assignment["id"],
                "title": "Forbidden",
                "duration_minutes": 30,
                "num_questions": 5,
            },
        )
        assert forbidden_exam.status_code == 404
        invalid_exam = client.post(
            "/api/teacher/exams",
            headers=teacher1_headers,
            json={
                "assignment_id": assignment["id"],
                "title": "Invalid duration",
                "duration_minutes": 0,
                "num_questions": 5,
            },
        )
        assert invalid_exam.status_code == 422

        exam_response = client.post(
            "/api/teacher/exams",
            headers=teacher1_headers,
            json={
                "assignment_id": assignment["id"],
                "title": f"Exam {marker}",
                "duration_minutes": 30,
                "num_questions": 5,
            },
        )
        assert exam_response.status_code == 201
        exam = exam_response.json()
        exam_ids.append(exam["id"])
        assert exam["auto_approve"] is True

        other_exam_response = client.post(
            "/api/teacher/exams",
            headers=teacher2_headers,
            json={
                "assignment_id": other_assignment["id"],
                "title": f"Other exam {marker}",
                "duration_minutes": 45,
                "num_questions": 4,
            },
        )
        assert other_exam_response.status_code == 201
        other_exam = other_exam_response.json()
        exam_ids.append(other_exam["id"])
        teacher1_exams = client.get("/api/teacher/exams", headers=teacher1_headers)
        assert teacher1_exams.status_code == 200
        assert exam["id"] in {item["id"] for item in teacher1_exams.json()}
        assert other_exam["id"] not in {item["id"] for item in teacher1_exams.json()}

        # Groups are created through their existing API; memberships are fixture data.
        group_response = client.post(
            "/api/teacher/groups",
            headers=teacher1_headers,
            json={"name": f"Group {marker}"},
        )
        assert group_response.status_code == 201
        group = group_response.json()
        group_ids.append(group["id"])
        other_group_response = client.post(
            "/api/teacher/groups",
            headers=teacher2_headers,
            json={"name": f"Other group {marker}"},
        )
        assert other_group_response.status_code == 201
        other_group = other_group_response.json()
        group_ids.append(other_group["id"])
        db.add_all(
            [
                GroupMember(group_id=group["id"], student_id=student1.id),
                GroupMember(group_id=group["id"], student_id=student2.id),
            ]
        )
        db.commit()

        starts_at = datetime.now(timezone.utc) + timedelta(days=1)
        ends_at = starts_at + timedelta(minutes=30)
        slot_response = client.post(
            f"/api/teacher/exams/{exam['id']}/slots",
            headers=teacher1_headers,
            json={
                "group_id": group["id"],
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
            },
        )
        assert slot_response.status_code == 201
        slot = slot_response.json()
        slot_ids.append(slot["id"])

        members = db.scalars(
            select(SlotStudent).where(SlotStudent.slot_id == slot["id"])
        ).all()
        assert {member.student_id for member in members} == {student1.id, student2.id}
        assert all(member.submission_id is None for member in members)
        assert len(members) == 2

        invalid_window = client.post(
            f"/api/teacher/exams/{exam['id']}/slots",
            headers=teacher1_headers,
            json={
                "starts_at": ends_at.isoformat(),
                "ends_at": starts_at.isoformat(),
            },
        )
        assert invalid_window.status_code == 422
        assert invalid_window.json()["error"]["code"] == "VALIDATION_ERROR"
        assert (
            client.post(
                f"/api/teacher/exams/{other_exam['id']}/slots",
                headers=teacher1_headers,
                json={"starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()},
            ).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/teacher/exams/{exam['id']}/slots",
                headers=teacher1_headers,
                json={
                    "group_id": other_group["id"],
                    "starts_at": starts_at.isoformat(),
                    "ends_at": ends_at.isoformat(),
                },
            ).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/teacher/exams/{exam['id']}/slots",
                headers=student_headers,
                json={"starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()},
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/teacher/exams/{exam['id']}/slots",
                json={"starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()},
            ).status_code
            == 401
        )
    finally:
        if slot_ids:
            db.execute(delete(SlotStudent).where(SlotStudent.slot_id.in_(slot_ids)))
            db.execute(delete(ExamSlot).where(ExamSlot.id.in_(slot_ids)))
        if exam_ids:
            db.execute(delete(Exam).where(Exam.id.in_(exam_ids)))
        if group_ids:
            db.execute(delete(GroupMember).where(GroupMember.group_id.in_(group_ids)))
            db.execute(delete(Group).where(Group.id.in_(group_ids)))
        if assignment_ids:
            db.execute(delete(Assignment).where(Assignment.id.in_(assignment_ids)))
        db.commit()
        db.close()
