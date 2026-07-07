from decimal import Decimal

import pytest

from tests.conftest import register_client, register_expert


@pytest.mark.asyncio
async def test_create_order_defaults_open(api_client):
    client_user = await register_client(api_client, "orders_create")
    resp = await api_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {client_user['token']}"},
        json={
            "title": "Проверка договора",
            "description": "Нужна проверка договора аренды",
            "category": "Юриспруденция",
            "budget": "5000.00",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "open"
    assert Decimal(data["budget"]) == Decimal("5000.00")


@pytest.mark.asyncio
async def test_orders_visibility_for_expert_and_client(api_client):
    client_a = await register_client(api_client, "orders_vis_a")
    client_b = await register_client(api_client, "orders_vis_b")
    expert = await register_expert(api_client, "orders_vis_expert")

    first = await api_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {client_a['token']}"},
        json={"title": "A-Order", "description": "Описание заказа A", "category": "Юрист"},
    )
    second = await api_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {client_b['token']}"},
        json={"title": "B-Order", "description": "Описание заказа B", "category": "Юрист"},
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    client_orders = await api_client.get(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {client_a['token']}"},
    )
    assert client_orders.status_code == 200, client_orders.text
    items = client_orders.json()["items"]
    assert any(item["id"] == first.json()["id"] for item in items)
    assert all(item["id"] != second.json()["id"] for item in items)

    expert_orders = await api_client.get(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {expert['token']}"},
    )
    assert expert_orders.status_code == 200, expert_orders.text
    expert_items = expert_orders.json()["items"]
    returned_ids = {item["id"] for item in expert_items}
    assert first.json()["id"] in returned_ids
    assert second.json()["id"] in returned_ids
    assert all(item["status"] == "open" for item in expert_items)


@pytest.mark.asyncio
async def test_only_owner_client_can_update_order_status(api_client):
    owner = await register_client(api_client, "orders_owner")
    outsider = await register_client(api_client, "orders_outsider")

    created = await api_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {owner['token']}"},
        json={"title": "Статусный заказ", "description": "Проверяем статусы заказа", "category": "Финансы"},
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["id"]

    forbidden_update = await api_client.put(
        f"/api/v1/orders/{order_id}/status",
        headers={"Authorization": f"Bearer {outsider['token']}"},
        json={"status": "in_progress"},
    )
    assert forbidden_update.status_code == 404

    for target_status in ("in_progress", "completed", "cancelled"):
        updated = await api_client.put(
            f"/api/v1/orders/{order_id}/status",
            headers={"Authorization": f"Bearer {owner['token']}"},
            json={"status": target_status},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["status"] == target_status
