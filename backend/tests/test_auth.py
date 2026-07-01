import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_register_and_login():
    """Регистрация нового эксперта и вход."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        register_payload = {
            "phone": "+79009998877",
            "email": "pytest_expert@dompro.ru",
            "password": "Test123456",
        }
        reg = await client.post("/api/v1/auth/register", json=register_payload)
        if reg.status_code == 400 and "уже существует" in reg.text:
            pass
        else:
            assert reg.status_code == 201
            assert "access_token" in reg.json()

        login = await client.post(
            "/api/v1/auth/login",
            json={"login": register_payload["email"], "password": register_payload["password"]},
        )
        assert login.status_code == 200
        data = login.json()
        assert data["user"]["verification_status"] == "unverified"
        token = data["access_token"]

        me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me.status_code == 200
        assert me.json()["email"] == register_payload["email"]
