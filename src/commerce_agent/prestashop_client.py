import os

import requests
from dotenv import load_dotenv

load_dotenv()

class PrestaShopClient:
    def __init__(self, url=None, key=None):
        self.url = url or os.getenv("PS_URL", "http://localhost:8080/api")
        self._key = key

    @property
    def key(self):
        return self._key or os.getenv("WEBSERVICE_KEY")

    def get_stock_availables(self):
        """Fetches stock quantities mapped by product ID."""
        if not self.key:
            return {}
        try:
            params = {"output_format": "JSON", "display": "full"}
            response = requests.get(f"{self.url}/stock_availables", auth=(self.key, ""), params=params, timeout=5)
            if response.status_code != 200:
                return {}
            data = response.json()
            stock_list = data.get("stock_availables", [])
            stock_map = {}
            for item in stock_list:
                prod_id = item.get("id_product")
                qty = item.get("quantity", 0)
                if prod_id:
                    stock_map[int(prod_id)] = int(qty)
            return stock_map
        except Exception:  # noqa: BLE001
            return {}

    def get_products(self, query: str):
        """
        Searches products via the PrestaShop Webservice API.
        Filters locally by keyword in product name or description.
        """
        if not self.key:
            return {"error": "WEBSERVICE_KEY environment variable is not configured."}

        try:
            params = {
                "output_format": "JSON",
                "display": "full"
            }
            response = requests.get(f"{self.url}/products", auth=(self.key, ""), params=params, timeout=10)
            
            if response.status_code != 200:
                return {"error": f"Store returned status {response.status_code}"}

            data = response.json()
            products = data.get("products", [])
            stock_map = self.get_stock_availables()
            
            q = query.lower().strip()
            filtered = []
            for p in products:
                name_str = str(p.get("name", "")).lower()
                desc_str = (str(p.get("description", "")) + " " + str(p.get("description_short", ""))).lower()
                
                # Search matching in either name OR description
                if q in name_str or q in desc_str:
                    prod_id = p.get("id")
                    stock_qty = stock_map.get(int(prod_id), 0) if prod_id else 0
                    filtered.append({
                        "id": prod_id,
                        "name": p.get("name"),
                        "price": p.get("price"),
                        "stock": stock_qty,
                        "description": p.get("description_short") or p.get("description")
                    })

            return filtered if filtered else {"message": f"No products found matching '{query}'."}

        except Exception as e:  # noqa: BLE001
            return {"error": f"Could not connect to store: {e!s}"}
