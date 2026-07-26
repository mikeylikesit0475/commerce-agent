import os
import requests
from dotenv import load_dotenv

load_dotenv()

class PrestaShopClient:
    def __init__(self):
        self.url = os.getenv("PS_URL", "http://localhost:8080/api")
        self.key = os.getenv("WEBSERVICE_KEY")
        if not self.key:
            raise ValueError("WEBSERVICE_KEY must be set in .env")

    def get_products(self, query: str):
        """
        Searches products via the PrestaShop Webservice API.
        Filters locally by keyword in name or description for simplicity 
        as the WS API filter syntax is quite complex (XML/JSON queries).
        """
        try:
            # We fetch a batch of products. In a real app we'd use OData-like filters
            params = {
                "output_format": "JSON",
                "display": "full"
            }
            response = requests.get(f"{self.url}/products", auth=(self.key, ""), params=params, timeout=10)
            
            if response.status_code != 200:
                return {"error": f"Store returned status {response.status_code}"}

            data = response.json()
            products = data.get("products", [])
            
            # Filter by query keyword in name or description
            filtered = [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "price": p.get("price"),
                    "stock": p.get("quantity", 0), # Quantity is often separate or in stock_availables
                    "description": p.get("description_short") or p.get("description")
                }
                for p in products if query.lower() in (p.get("name", "").lower() or p.get("description_short", "").lower())
            ]
            
            return filtered if filtered else {"message": "No products found matching the query."}

        except Exception as e:
            return {"error": f"Could not connect to store: {str(e)}"}
