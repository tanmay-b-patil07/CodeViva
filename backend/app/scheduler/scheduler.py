"""Lifecycle-managed APScheduler instance for exam pre-generation."""

from datetime import timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.scheduler.jobs import run_attempt_auto_submit, run_generation_discovery

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone=timezone.utc)
        _scheduler.add_job(
            run_generation_discovery,
            trigger="interval",
            minutes=1,
            id="exam-question-generation-discovery",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        _scheduler.add_job(
            run_attempt_auto_submit,
            trigger="interval",
            minutes=1,
            id="exam-attempt-auto-submit",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
    return _scheduler


def start_scheduler() -> BackgroundScheduler:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
    return scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        if _scheduler.running:
            _scheduler.shutdown(wait=False)
        _scheduler = None
