import json
import os

COLLECTION_PATH = "200_millas proyecto.postman_collection.json"

BASE_URL_USERS = "https://wp4cigovo1.execute-api.us-east-1.amazonaws.com"
BASE_URL_PRODUCTS = "https://bd1dxxt4yh.execute-api.us-east-1.amazonaws.com"
BASE_URL_CLIENTES = "https://s371uf7p37.execute-api.us-east-1.amazonaws.com"

def update_url(url_obj, base_url):
    # url_obj is a dict with 'raw', 'protocol', 'host', 'path'
    # We replace 'host' and 'protocol' and update 'raw'
    
    # Parse base_url
    # e.g. https://xyz.execute-api.us-east-1.amazonaws.com
    protocol = base_url.split("://")[0]
    host_str = base_url.split("://")[1]
    host_parts = host_str.split(".")
    
    url_obj["protocol"] = protocol
    url_obj["host"] = host_parts
    
    # Reconstruct raw
    path_str = "/".join(url_obj["path"])
    url_obj["raw"] = f"{base_url}/{path_str}"
    return url_obj

def main():
    if not os.path.exists(COLLECTION_PATH):
        print(f"File {COLLECTION_PATH} not found.")
        return

    with open(COLLECTION_PATH, "r") as f:
        data = json.load(f)

    # Iterate items
    for folder in data.get("item", []):
        folder_name = folder.get("name")
        for request_item in folder.get("item", []):
            req = request_item.get("request", {})
            url_obj = req.get("url", {})
            path = url_obj.get("path", [])
            
            # Determine service based on path or folder
            new_base = None
            if "users" in path or "employees" in path:
                new_base = BASE_URL_USERS
            elif "productos" in path:
                new_base = BASE_URL_PRODUCTS
            elif "pedido" in path:
                new_base = BASE_URL_CLIENTES
            
            if new_base:
                req["url"] = update_url(url_obj, new_base)
                
            # Update Body Examples
            if request_item["name"] == "Register User":
                req["body"]["raw"] = json.dumps({
                    "nombre": "Test User",
                    "correo": "test_client_v2@200millas.com",
                    "contrasena": "password123",
                    "role": "Cliente"
                }, indent=2)
            elif request_item["name"] == "Login User":
                req["body"]["raw"] = json.dumps({
                    "correo": "test_client_v2@200millas.com",
                    "contrasena": "password123"
                }, indent=2)
            elif request_item["name"] == "Listar" and folder_name == "Products":
                req["body"]["raw"] = json.dumps({
                    "local_id": "LOCAL-005"
                }, indent=2)
            elif request_item["name"] == "Buscar Producto":
                req["body"]["raw"] = json.dumps({
                    "local_id": "LOCAL-005",
                    "nombre": "Ceviches 39"
                }, indent=2)

    with open(COLLECTION_PATH, "w") as f:
        json.dump(data, f, indent=4)
    
    print("Postman collection updated successfully.")

if __name__ == "__main__":
    main()
