from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_status_code():
    """Verify GET /api/health returns HTTP 200."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_check_payload():
    """Verify GET /api/health returns valid JSON with expected health structure."""
    response = client.get("/api/health")
    data = response.json()
    assert isinstance(data, dict)
    assert data.get("status") == "healthy"
    assert data.get("service") == "Nisaarthi Backend"
    assert "version" in data
