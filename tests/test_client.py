import pytest
from unittest.mock import MagicMock, patch
from commerce_agent.prestashop_client import PrestaShopClient

def test_get_products_parsing():
    # Mock the requests.get call to return a valid PrestaShop JSON response
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "products": [
                {
                    "id": "1",
                    "name": "Fancy Mug",
                    "price": "15.00",
                    "description_short": "A very fancy mug.",
                    "quantity": 10
                },
                {
                    "id": "2",
                    "name": "Plain Plate",
                    "price": "5.00",
                    "description_short": "Just a plate.",
                    "quantity": 5
                }
            ]
        }
        mock_get.return_value = mock_response

        client = PrestaShopClient() # Ensure .env is handled or values are mocked if needed
        
        # Test filtering for 'Mug'
        results = client.get_products("Mug")
        assert len(results) == 1
        assert results[0]["name"] == "Fancy Mug"

        # Test filtering for 'Plate'
        results = client.get_products("Plate")
        assert len(results) == 1
        assert results[0]["name"] == "Plain Plate"

        # Test no match
        results = client.get_products("Toaster")
        assert isinstance(results, dict)
        assert "No products found" in results["message"]

def test_get_products_connection_error():
    with patch('requests.get') as mock_get:
        mock_get.side_effect = Exception("Connection timeout")
        client = PrestaShopClient()
        results = client.get_products("Mug")
        assert isinstance(results, dict)
        assert "error" in results
        assert "Could not connect to store" in results["error"]
