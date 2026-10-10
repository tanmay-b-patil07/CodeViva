"""Seed or safely clear the fixed CodeViva synthetic demo dataset."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings, validate_runtime_settings
from app.db.session import SessionLocal
from app.services.demo_data import (
    DEMO_EMAILS,
    DEMO_PASSWORD,
    reset_demo_data,
    seed_demo_data,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "seed-demo", help="create or refresh the deterministic demo dataset"
    )
    reset = commands.add_parser(
        "reset-demo", help="delete only the deterministic demo dataset"
    )
    reset.add_argument(
        "--confirm-reset",
        action="store_true",
        help="required explicit destructive confirmation",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db = None
    try:
        validate_runtime_settings(settings)
        db = SessionLocal()
        if args.command == "seed-demo":
            if settings.environment.lower() not in {"development", "test"}:
                raise RuntimeError(
                    "Demo seeding is allowed only in development or test environments."
                )
            counts = seed_demo_data(db)
            print(
                f"Demo seed verified: created={counts['created']} reused={counts['reused']}."
            )
            print("Demo identities: " + ", ".join(DEMO_EMAILS.values()))
            print(f"Development-only password for all demo identities: {DEMO_PASSWORD}")
            return 0
        deleted = reset_demo_data(
            db,
            confirm_reset=args.confirm_reset,
            environment=settings.environment,
            allow_reset=settings.allow_database_reset,
        )
        print(
            f"Demo reset complete: deleted {deleted} demo rows; schema and Alembic history preserved."
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - avoid echoing driver details or credentials.
        if db is not None:
            db.rollback()
        print(
            f"Database utility failed ({type(exc).__name__}); details were withheld.",
            file=sys.stderr,
        )
        return 1
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    raise SystemExit(main())
