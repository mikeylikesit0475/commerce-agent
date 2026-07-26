import pytest
from commerce_agent.prestashop_client import PrestaShopClient


@pytest.mark.integration
def test_live_prestashop_update_product_description():
    client = PrestaShopClient()
    product_id = 20  # seeded Electronics Product 1

    # 1. Fetch original product info
    original_prod = client.get_product_by_id(product_id)
    assert "error" not in original_prod, f"Could not fetch product {product_id}: {original_prod}"
    original_desc = original_prod.get("description", "")

    test_desc = "Integration test description update for live PrestaShop API."

    try:
        # 2. Perform live PUT update
        res = client.update_product_description(product_id, test_desc)
        assert res.get("success") is True, f"PUT update failed: {res}"

        # 3. Verify description in store database via GET
        updated_prod = client.get_product_by_id(product_id)
        assert "error" not in updated_prod
        assert test_desc in updated_prod.get("description", "")

    finally:
        # 4. Revert description back to original
        if original_desc:
            client.update_product_description(product_id, original_desc)
