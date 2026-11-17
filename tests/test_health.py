from fastapi.testclient import TestClient
import boto3

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_health_checks_demo_dynamodb_tables(monkeypatch):
    calls = []

    class FakeDynamoDB:
        def describe_table(self, *, TableName):
            calls.append(TableName)

    monkeypatch.setattr(settings, "dynamo_demo_enabled", True)
    monkeypatch.setattr(settings, "data_api_enabled", False)
    monkeypatch.setenv("DEMO_DATA_TABLE", "demo-data")
    monkeypatch.setenv("IDEMPOTENCY_TABLE", "demo-ledger")
    monkeypatch.setattr(boto3, "client", lambda service: FakeDynamoDB())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["checks"]["database"] == "ok"
    assert calls == ["demo-data", "demo-ledger"]


def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Get medical help" in response.text


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    # Should return Prometheus metrics format (plain text with # HELP and # TYPE)
    assert "# HELP" in response.text
    assert "# TYPE" in response.text
