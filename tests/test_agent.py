from unittest.mock import patch

from commerce_agent.agent import (
    create_router_agent,
    get_order_status,
    get_products,
    update_product_description,
)


def test_get_products_tool_formatting():
    mock_data = [
        {"id": 1, "name": "Electronics Product 1", "price": "100.000000", "stock": 50, "description": "High tech product"}
    ]
    with patch("commerce_agent.prestashop_client.PrestaShopClient.get_products", return_value=mock_data):
        res = get_products("Electronics")
        assert "Found matching products:" in res
        assert "Electronics Product 1" in res
        assert "$100.00" in res
        assert "Stock: 50" in res

def test_get_order_status_tool_formatting():
    mock_order = {
        "id": 12,
        "reference": "XYZREF",
        "status": "Payment accepted / Processing",
        "total_paid": "150.00",
        "date_add": "2026-07-25 12:00:00",
        "items": [{"name": "Electronics Product 1", "quantity": 2, "price": "75.00"}]
    }
    with patch("commerce_agent.prestashop_client.PrestaShopClient.get_order", return_value=mock_order):
        res = get_order_status("12")
        assert "Order #12" in res
        assert "XYZREF" in res
        assert "Payment accepted" in res
        assert "Electronics Product 1" in res

def test_update_product_description_draft_unconfirmed():
    mock_prod = {"id": 5, "name": "Test Mug", "description": "Old desc"}
    with patch("commerce_agent.prestashop_client.PrestaShopClient.get_product_by_id", return_value=mock_prod):
        res = update_product_description(5, "New awesome description", confirmed=False)
        assert "[DRAFT DESCRIPTION FOR REVIEW]" in res
        assert "New awesome description" in res
        assert "Please confirm" in res

def test_update_product_description_confirmed_writeback():
    mock_prod = {"id": 5, "name": "Test Mug", "description": "New awesome description"}
    with (
        patch("commerce_agent.prestashop_client.PrestaShopClient.get_product_by_id", return_value=mock_prod),
        patch("commerce_agent.prestashop_client.PrestaShopClient.update_product_description", return_value={"success": True})
    ):
        res = update_product_description(5, "New awesome description", confirmed=True)
        assert "[PRESTASHOP STORE UPDATED SUCCESSFULLY]" in res
        assert "New awesome description" in res

def test_create_router_agent_instantiation():
    agent = create_router_agent()
    assert agent.name == "CommerceRouterAgent"
    assert len(agent.tools) == 3
