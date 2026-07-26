from unittest.mock import MagicMock, patch

from commerce_agent.prestashop_client import PrestaShopClient


def test_client_init_lazy_without_env():
    """Client initialization should not raise ValueError when WEBSERVICE_KEY is missing."""
    with patch.dict("os.environ", {}, clear=True):
        client = PrestaShopClient()
        assert client.key is None
        res = client.get_products("Electronics")
        assert "error" in res
        assert "WEBSERVICE_KEY" in res["error"]

def test_get_products_description_search_match():
    """Verify that keyword in product description (absent in name) returns product."""
    mock_products = {
        "products": [
            {
                "id": 1,
                "name": "Standard Gadget",
                "price": "49.990000",
                "description": "This is a fantastic high-tech gadget for audiophiles",
                "description_short": "Short summary"
            }
        ]
    }
    mock_stock = {
        "stock_availables": [
            {"id_product": 1, "quantity": 100}
        ]
    }

    client = PrestaShopClient(url="http://mock-store/api", key="MOCK_KEY")
    
    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "stock_availables" in url:
            resp.json.return_value = mock_stock
        else:
            resp.json.return_value = mock_products
        return resp

    with patch("requests.get", side_effect=mock_get):
        res = client.get_products("audiophiles")
        assert isinstance(res, list)
        assert len(res) == 1
        assert res[0]["name"] == "Standard Gadget"
        assert res[0]["stock"] == 100
