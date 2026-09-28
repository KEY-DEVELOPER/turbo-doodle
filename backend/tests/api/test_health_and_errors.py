from typing import Any

from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import AppError
from app.main import create_app


class Payload(BaseModel):
    odds: str


def _client() -> TestClient:
    app = create_app()
    router = APIRouter(prefix="/_test")

    @router.get("/app-error")
    def app_error() -> None:
        raise AppError(
            "SYNTHETIC_MARKET_NOT_ALLOWED", "No synthetic benchmark", details={"books": 3}
        )

    @router.post("/validate")
    def validate(body: Payload) -> dict[str, Any]:
        return body.model_dump()

    @router.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail")

    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def _assert_error_shape(body: dict[str, Any], code: str) -> None:
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == code


def test_health() -> None:
    response = _client().get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_v1_router_is_mounted() -> None:
    paths = _client().get("/openapi.json").json()["paths"]
    assert "/health" in paths


def test_app_error_uses_standard_format() -> None:
    response = _client().get("/_test/app-error")
    assert response.status_code == 400
    body = response.json()
    _assert_error_shape(body, "SYNTHETIC_MARKET_NOT_ALLOWED")
    assert body["error"]["details"] == {"books": 3}


def test_not_found_uses_standard_format() -> None:
    response = _client().get("/v1/does-not-exist")
    assert response.status_code == 404
    _assert_error_shape(response.json(), "NOT_FOUND")


def test_validation_error_uses_standard_format() -> None:
    response = _client().post("/_test/validate", json={})
    assert response.status_code == 422
    body = response.json()
    _assert_error_shape(body, "VALIDATION_ERROR")
    assert body["error"]["details"]["errors"][0]["loc"] == ["body", "odds"]


def test_unhandled_error_does_not_leak_internals() -> None:
    response = _client().get("/_test/boom")
    assert response.status_code == 500
    body = response.json()
    _assert_error_shape(body, "INTERNAL_ERROR")
    assert "secret" not in response.text
