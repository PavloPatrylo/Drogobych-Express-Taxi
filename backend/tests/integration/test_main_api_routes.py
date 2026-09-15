import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_main_middleware_and_static_routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Test favicon endpoint
        resp_fav = await client.get("/favicon.ico")
        assert resp_fav.status_code == 204
        assert resp_fav.headers.get("ngrok-skip-browser-warning") == "true"

        # Test root endpoint
        resp_root = await client.get("/")
        assert resp_root.status_code == 200
        assert resp_root.headers.get("ngrok-skip-browser-warning") == "true"

        # Test app.js endpoint
        resp_js = await client.get("/app.js")
        assert resp_js.status_code == 200

        # Test API route 404 or 401
        resp_api = await client.get("/api/trips")
        assert resp_api.status_code in (200, 401, 403, 404)

        # Test Liveness probe
        resp_live = await client.get("/health/live")
        assert resp_live.status_code == 200
        assert resp_live.json().get("status") == "ok"

        # Test Readiness probe
        resp_ready = await client.get("/health/ready")
        assert resp_ready.status_code == 200
        assert resp_ready.json().get("status") == "ready"
        assert resp_ready.json().get("database") == "connected"

        # Test legacy /health endpoint (readiness backward compatibility)
        resp_health = await client.get("/health")
        assert resp_health.status_code == 200
        assert resp_health.json().get("status") == "ready"
