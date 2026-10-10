"""Configuration and information-disclosure hardening regressions."""

import logging
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.auth import router as auth_module
from app.core.config import (
    DEFAULT_DATABASE_URL,
    DEVELOPMENT_JWT_SECRET,
    Settings,
    settings,
    validate_jwt_secret,
    validate_runtime_settings,
)
from app.core.errors import unhandled_exception_handler
from app.core.security import create_access_token, decode_access_token, hash_password
from app.db.models import Profile
from app.db.session import get_db
from app.main import app


def _settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "environment": "development",
        "jwt_secret": DEVELOPMENT_JWT_SECRET,
        "database_url": DEFAULT_DATABASE_URL,
        "allowed_origins": "http://localhost:3000",
        "cookie_secure": False,
        "teacher_invite_code": "choose-a-code",
    }
    values.update(overrides)
    return Settings(**values)


def _production_settings(**overrides) -> Settings:
    values = {
        "environment": "production",
        "jwt_secret": "phase16-unit-test-signing-key-not-a-real-credential",
        "database_url": "postgresql+psycopg://service:unit-test-only@db.example.invalid/codeviva",
        "allowed_origins": "https://app.example.invalid",
        "cookie_secure": True,
        "teacher_invite_code": "phase16-unit-test-invite-value",
    }
    values.update(overrides)
    return _settings(**values)


def test_development_and_test_settings_allow_documented_development_key():
    for environment in ("development", "test"):
        config = _settings(environment=environment)
        validate_runtime_settings(config)
        validate_jwt_secret(config.environment, config.jwt_secret)
    assert DEVELOPMENT_JWT_SECRET not in repr(_settings())


def test_runtime_requires_an_explicit_environment(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    config = Settings(_env_file=None, jwt_secret=DEVELOPMENT_JWT_SECRET)
    with pytest.raises(RuntimeError, match="ENVIRONMENT must be set explicitly"):
        validate_runtime_settings(config)


def test_production_rejects_missing_weak_and_development_jwt_keys():
    for secret in ("", "short", DEVELOPMENT_JWT_SECRET, "change-me"):
        config = _production_settings(jwt_secret=secret)
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            validate_runtime_settings(config)


def test_production_accepts_explicit_hardened_configuration():
    validate_runtime_settings(_production_settings())


def test_application_startup_rejects_production_development_defaults(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(RuntimeError, match="ALLOWED_ORIGINS"), TestClient(app):
        pass


def test_access_tokens_are_signed_and_weak_keys_cannot_sign(monkeypatch):
    user_id = uuid4()
    token = create_access_token(user_id, "student")
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "student"

    monkeypatch.setattr("app.core.security.settings.jwt_secret", "short")
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        create_access_token(user_id, "student")


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"allowed_origins": "*"}, "explicit origins"),
        ({"allowed_origins": "http://app.example.invalid"}, "HTTPS origins"),
        ({"allowed_origins": "https://localhost"}, "HTTPS origins"),
        ({"database_url": DEFAULT_DATABASE_URL}, "DATABASE_URL"),
        ({"cookie_secure": False}, "COOKIE_SECURE"),
        ({"teacher_invite_code": "choose-a-code"}, "TEACHER_INVITE_CODE"),
    ],
)
def test_production_rejects_unsafe_deployment_defaults(overrides, message):
    with pytest.raises(RuntimeError, match=message):
        validate_runtime_settings(_production_settings(**overrides))


def test_secure_cookie_setting_is_used_for_login_and_logout(monkeypatch):
    db = next(get_db())
    email = f"phase16-{uuid4().hex}@example.com"
    password = "phase16-only-test-password"
    user = Profile(
        email=email,
        password_hash=hash_password(password),
        full_name="Phase 16 Test User",
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    monkeypatch.setattr(auth_module.settings, "cookie_secure", True)
    client = TestClient(app)
    try:
        response = client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200
        login_cookie = response.headers["set-cookie"].lower()
        assert "secure" in login_cookie and "httponly" in login_cookie
        assert "access_token" not in response.json()
        assert password not in response.text

        logout = client.post("/api/auth/logout")
        logout_cookie = logout.headers["set-cookie"].lower()
        assert logout.status_code == 200
        assert "secure" in logout_cookie and "max-age=0" in logout_cookie
    finally:
        db.execute(delete(Profile).where(Profile.id == user.id))
        db.commit()
        db.close()


def test_unhandled_error_response_and_logs_omit_exception_details(caplog):
    test_app = FastAPI()
    test_app.add_exception_handler(Exception, unhandled_exception_handler)

    @test_app.get("/failure")
    def fail():
        raise RuntimeError("private evaluator payload and bearer-token-sentinel")

    caplog.set_level(logging.ERROR, logger="codeviva")
    response = TestClient(test_app, raise_server_exceptions=False).get("/failure")
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected server error occurred.",
        }
    }
    assert "private evaluator payload" not in response.text
    assert "bearer-token-sentinel" not in response.text
    assert "private evaluator payload" not in caplog.text
    assert "bearer-token-sentinel" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_database_utility_failure_does_not_print_connection_details(
    monkeypatch, capsys
):
    from scripts import db_tools

    class SessionStub:
        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(db_tools, "SessionLocal", SessionStub)

    def fail_seed(_db):
        raise RuntimeError("postgresql://user:private-sentinel@db.invalid/name")

    monkeypatch.setattr(db_tools, "seed_demo_data", fail_seed)
    assert db_tools.main(["seed-demo"]) == 1
    output = capsys.readouterr()
    assert "private-sentinel" not in output.err
    assert "postgresql://" not in output.err
    assert "RuntimeError" in output.err


def test_health_and_openapi_still_load():
    with TestClient(app) as client:
        health = client.get("/health")
        openapi = client.get("/openapi.json")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert openapi.status_code == 200
    paths = openapi.json()["paths"]
    assert "/api/auth/login" in paths
    assert "/api/student/slots" in paths
    assert "/api/teacher/results" in paths
    assert "/api/teacher/exams/{exam_id}/analytics" in paths
