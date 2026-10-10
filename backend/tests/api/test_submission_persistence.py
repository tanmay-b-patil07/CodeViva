from sqlalchemy import select

from app.db.models import Profile
from app.db.session import get_db
from app.services.submissions import (
    calculate_code_hash,
    create_submission,
    find_cached_facts,
)


def test_submission_persistence_and_fact_cache():
    db = next(get_db())

    created_submission = None

    try:
        student = db.scalar(
            select(Profile).where(
                Profile.email == "student1@example.com"
            )
        )

        assert student is not None

        source = """def add(a, b):
    return a + b


print(add(2, 3))
"""

        code_hash = calculate_code_hash(source)

        fake_code_facts = {
            "language": "python",
            "code_hash": code_hash,
            "line_count": 6,
            "functions": [
                {
                    "name": "add",
                    "start_line": 1,
                    "end_line": 2,
                    "params": ["a", "b"],
                    "is_recursive": False,
                    "cyclomatic_complexity": 1,
                    "max_loop_depth": 0,
                    "calls": [],
                }
            ],
            "loops": [],
            "data_structures": [],
            "imports": [],
            "edge_case_inputs": [],
            "warnings": [],
        }

        # ---------------------------------------------------------
        # First submission
        # ---------------------------------------------------------

        created_submission = create_submission(
            db,
            student_id=student.id,
            filename="test_submission.py",
            code=source,
            assignment_id=None,
            code_facts=fake_code_facts,
            code_hash=code_hash,
        )

        assert created_submission.id is not None
        assert created_submission.student_id == student.id
        assert created_submission.assignment_id is None
        assert created_submission.filename == "test_submission.py"
        assert created_submission.code == source
        assert created_submission.code_hash == code_hash
        assert created_submission.code_facts == fake_code_facts

        # ---------------------------------------------------------
        # Cache lookup
        # ---------------------------------------------------------

        cached_facts = find_cached_facts(
            db,
            code_hash,
            student_id=student.id,
            assignment_id=None,
        )

        assert cached_facts == fake_code_facts

    finally:
        if created_submission is not None:
            db.delete(created_submission)
            db.commit()

        db.close()
