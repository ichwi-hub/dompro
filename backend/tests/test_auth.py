import pytest
from httpx import AsyncClient

from tests.conftest import register_client, register_expert, unique_identity


@pytest.mark.asyncio
async def test_register_and_login(api_client: AsyncClient):
    """Регистрация нового эксперта и вход."""
    identity = unique_identity("auth_flow")
    reg = await api_client.post("/api/v1/auth/register", json=identity)
    assert reg.status_code == 201, reg.text
    assert "access_token" in reg.json()

    login = await api_client.post(
        "/api/v1/auth/login",
        json={"login": identity["email"], "password": identity["password"]},
    )
    assert login.status_code == 200, login.text
    data = login.json()
    assert data["user"]["verification_status"] == "unverified"
    token = data["access_token"]

    me = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == identity["email"]
