from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.core.errors import unhandled_exception_handler
from app.main import app


client = TestClient(app)


def test_validation_error_shape():
    response = client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "123",
            "full_name": "",
        },
    )

    assert response.status_code == 422

    body = response.json()

    assert body == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
        }
    }