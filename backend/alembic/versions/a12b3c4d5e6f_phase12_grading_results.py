"""add Phase 12 grading result persistence

Revision ID: a12b3c4d5e6f
Revises: f931f3133048
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a12b3c4d5e6f"
down_revision: str | None = "f931f3133048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("attempt_results", "comprehension_index", nullable=True)
    op.alter_column("attempt_results", "sub_scores", nullable=True)
    op.alter_column("attempt_results", "flag_oral_followup", nullable=True)
    op.alter_column("attempt_results", "needs_review_count", nullable=True)
    op.add_column(
        "attempt_results",
        sa.Column("status", sa.Text(), nullable=False, server_default="graded"),
    )
    op.add_column(
        "attempt_results", sa.Column("total_score", sa.Numeric(), nullable=True)
    )
    op.add_column(
        "attempt_results", sa.Column("max_score", sa.Numeric(), nullable=True)
    )
    op.add_column(
        "attempt_results", sa.Column("percentage", sa.Numeric(), nullable=True)
    )
    op.add_column(
        "attempt_results",
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "attempt_results", sa.Column("grading_error", sa.Text(), nullable=True)
    )
    op.create_check_constraint(
        "ck_attempt_results_status",
        "attempt_results",
        "status IN ('pending', 'grading', 'graded', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_attempt_results_status", "attempt_results", type_="check")
    op.drop_column("attempt_results", "grading_error")
    op.drop_column("attempt_results", "graded_at")
    op.drop_column("attempt_results", "percentage")
    op.drop_column("attempt_results", "max_score")
    op.drop_column("attempt_results", "total_score")
    op.drop_column("attempt_results", "status")
    op.alter_column("attempt_results", "needs_review_count", nullable=False)
    op.alter_column("attempt_results", "flag_oral_followup", nullable=False)
    op.alter_column("attempt_results", "sub_scores", nullable=False)
    op.alter_column("attempt_results", "comprehension_index", nullable=False)
