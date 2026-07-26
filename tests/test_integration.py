import pytest
from commerce_agent.prestashop_client import PrestaShopClient

@pytest.mark.integration
def test_real_api_connectivity():
    """
    Smoke test to ensure the agent client can actually talk 
    to the live PrestaShop container.
    """
    client = PrestaShopClient()
    # Use a generic term that should return something given the seeded data
    results = client.get_products("a") 
    
    if isinstance(results, dict) and "error" in results:
        pytest.fail(f"API Error: {results['error']}")
    
    assert len(results) > 0, "Should find at least some products with search term 'a'"
    assert "name" in results[0], "Product object should contain a name"
