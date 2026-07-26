from unittest.mock import patch

from commerce_agent.agent import create_catalog_agent, get_products


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

def test_get_products_tool_error_handling():
    with patch("commerce_agent.prestashop_client.PrestaShopClient.get_products", return_value={"error": "Connection refused"}):
        res = get_products("Electronics")
        assert "Error accessing store: Connection refused" in res

def test_create_catalog_agent_instantiation():
    agent = create_catalog_agent()
    assert agent.name == "CatalogQnASEntry"
    assert len(agent.tools) == 1
