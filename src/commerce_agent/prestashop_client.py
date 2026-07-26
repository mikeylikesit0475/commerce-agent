import os
import re
from xml.sax import saxutils

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

    def get_order(self, order_id: str):
        """Fetches details for a specific order ID."""
        if not self.key:
            return {"error": "WEBSERVICE_KEY environment variable is not configured."}
        try:
            response = requests.get(f"{self.url}/orders/{order_id}", auth=(self.key, ""), params={"output_format": "JSON"}, timeout=10)
            if response.status_code == 404:
                return {"message": f"Order #{order_id} was not found."}
            if response.status_code != 200:
                return {"error": f"Store returned status {response.status_code}"}

            data = response.json()
            order = data.get("order", {})
            rows = order.get("associations", {}).get("order_rows", [])
            
            items = [
                {
                    "product_id": r.get("product_id"),
                    "name": r.get("product_name"),
                    "quantity": r.get("product_quantity"),
                    "price": r.get("product_price")
                }
                for r in rows
            ]

            state_map = {
                1: "Awaiting check payment",
                2: "Payment accepted / Processing",
                3: "Processing in progress",
                4: "Shipped",
                5: "Delivered",
                6: "Canceled"
            }
            raw_state = order.get("current_state")
            status_str = state_map.get(int(raw_state), f"Status code {raw_state}") if raw_state else "Unknown"

            return {
                "id": order.get("id"),
                "reference": order.get("reference"),
                "customer_id": order.get("id_customer"),
                "status": status_str,
                "total_paid": order.get("total_paid"),
                "date_add": order.get("date_add"),
                "items": items
            }
        except Exception as e:  # noqa: BLE001
            return {"error": f"Could not fetch order: {e!s}"}

    def get_product_by_id(self, product_id: int):
        """Fetches product details by product ID."""
        if not self.key:
            return {"error": "WEBSERVICE_KEY environment variable is not configured."}
        try:
            response = requests.get(f"{self.url}/products/{product_id}", auth=(self.key, ""), params={"output_format": "JSON"}, timeout=10)
            if response.status_code == 404:
                return {"message": f"Product ID {product_id} not found."}
            if response.status_code != 200:
                return {"error": f"Store returned status {response.status_code}"}

            data = response.json()
            p = data.get("product", {})
            stock_map = self.get_stock_availables()
            stock_qty = stock_map.get(int(product_id), 0)
            return {
                "id": p.get("id"),
                "name": p.get("name"),
                "price": p.get("price"),
                "stock": stock_qty,
                "description": p.get("description") or p.get("description_short")
            }
        except Exception as e:  # noqa: BLE001
            return {"error": f"Could not fetch product: {e!s}"}

    def update_product_description(self, product_id: int, new_description: str):
        """Updates product description via PrestaShop PUT API."""
        if not self.key:
            return {"error": "WEBSERVICE_KEY environment variable is not configured."}
        try:
            # 1. Fetch current product XML
            get_resp = requests.get(f"{self.url}/products/{product_id}", auth=(self.key, ""), params={"output_format": "XML"}, timeout=10)
            if get_resp.status_code != 200:
                return {"error": f"Could not fetch product XML for ID {product_id}"}

            xml_str = get_resp.text
            clean_desc = saxutils.escape(new_description)
            
            # Replace description XML content
            updated_xml = re.sub(
                r"<description>.*?</description>",
                f"<description><language id=\"1\">{clean_desc}</language></description>",
                xml_str,
                flags=re.DOTALL
            )
            
            headers = {"Content-Type": "application/xml", "Accept": "application/xml"}
            put_resp = requests.put(f"{self.url}/products/{product_id}", auth=(self.key, ""), data=updated_xml, headers=headers, timeout=10)
            
            if put_resp.status_code in (200, 201):
                return {"success": True, "product_id": product_id, "new_description": new_description}
            else:
                return {"error": f"Failed to update product description. Status: {put_resp.status_code}"}
        except Exception as e:  # noqa: BLE001
            return {"error": f"Could not update product description: {e!s}"}
