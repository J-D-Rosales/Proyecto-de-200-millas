import urllib.request
import urllib.error
import json
import sys

# Configuration
BASE_URL_USERS = "https://wp4cigovo1.execute-api.us-east-1.amazonaws.com"
BASE_URL_PRODUCTS = "https://bd1dxxt4yh.execute-api.us-east-1.amazonaws.com"
BASE_URL_CLIENTES = "https://s371uf7p37.execute-api.us-east-1.amazonaws.com"

ADMIN_EMAIL = "admin@200millas.com"
ADMIN_PASS = "admin123"

CLIENT_EMAIL = "laura.lopez@hotmail.com"
CLIENT_PASS = "cli_1ac3c48c9b"

results = []

def log_result(name, method, url, status, req_body, resp_body, success):
    results.append({
        "name": name,
        "method": method,
        "url": url,
        "status": status,
        "request_body": req_body,
        "response_body": resp_body,
        "success": success
    })
    print(f"[{'PASS' if success else 'FAIL'}] {name} ({status})")

def make_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    
    if data is not None:
        json_data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    else:
        json_data = None

    req = urllib.request.Request(url, data=json_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            body = response.read().decode('utf-8')
            try:
                json_body = json.loads(body)
            except:
                json_body = body
            return status, json_body
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            json_body = json.loads(body)
        except:
            json_body = body
        return e.code, json_body
    except Exception as e:
        return "ERR", str(e)

def test_login(email, password, role_name):
    url = f"{BASE_URL_USERS}/users/login"
    payload = {"correo": email, "contrasena": password}
    status, body = make_request(url, "POST", payload)
    success = status == 200 and isinstance(body, dict) and "token" in body
    log_result(f"Login {role_name}", "POST", url, status, payload, body, success)
    return body.get("token") if success else None

def test_get_me(token, role_name):
    url = f"{BASE_URL_USERS}/users/me"
    headers = {"Authorization": token}
    status, body = make_request(url, "GET", None, headers)
    success = status == 200
    log_result(f"Get Me ({role_name})", "GET", url, status, None, body, success)

def test_list_products():
    url = f"{BASE_URL_PRODUCTS}/productos/list"
    payload = {"local_id": "LOCAL-005"}
    status, body = make_request(url, "POST", payload)
    success = status == 200
    
    # Truncate long list for report
    report_body = body
    if isinstance(body, dict) and "contents" in body and len(body["contents"]) > 2:
        report_body = body.copy()
        report_body["contents"] = body["contents"][:2] + ["... (truncated)"]
        
    log_result("List Products", "POST", url, status, payload, report_body, success)

def test_get_product():
    url = f"{BASE_URL_PRODUCTS}/productos/id"
    payload = {"local_id": "LOCAL-005", "nombre": "Ceviches 1"}
    status, body = make_request(url, "POST", payload)
    success = status == 200
    log_result("Get Product ID", "POST", url, status, payload, body, success)

def test_create_pedido(token):
    url = f"{BASE_URL_CLIENTES}/pedido/create"
    headers = {"Authorization": token}
    payload = {
        "tenant_id": "TENANT-001",
        "local_id": "LOCAL-005",
        "usuario_correo": CLIENT_EMAIL,
        "direccion": "Av. Test 123",
        "costo": 50.0,
        "estado": "procesando",
        "productos": [
            {"nombre": "Ceviches 1", "cantidad": 2}
        ]
    }
    status, body = make_request(url, "POST", payload, headers)
    success = status == 201
    log_result("Create Pedido", "POST", url, status, payload, body, success)
    if success and isinstance(body, dict):
        return body.get("pedido", {}).get("pedido_id")
    return None

def test_get_pedido_status(token, pedido_id):
    if not pedido_id:
        print("Skipping Get Pedido Status (no pedido_id)")
        return
    url = f"{BASE_URL_CLIENTES}/pedido/status?tenant_id=TENANT-001&pedido_id={pedido_id}"
    headers = {"Authorization": token}
    status, body = make_request(url, "GET", None, headers)
    success = status == 200
    log_result("Get Pedido Status", "GET", url, status, None, body, success)

def test_confirmar_pedido(token, pedido_id):
    if not pedido_id:
        print("Skipping Confirmar Pedido (no pedido_id)")
        return
    url = f"{BASE_URL_CLIENTES}/pedido/confirmar"
    headers = {"Authorization": token}
    payload = {"tenant_id": "TENANT-001", "pedido_id": pedido_id}
    status, body = make_request(url, "POST", payload, headers)
    success = status == 200
    log_result("Confirmar Pedido", "POST", url, status, payload, body, success)

def test_register(email, password, role="Cliente"):
    url = f"{BASE_URL_USERS}/users/register"
    payload = {
        "nombre": "Test User",
        "correo": email,
        "contrasena": password,
        "role": role
    }
    status, body = make_request(url, "POST", payload)
    success = status in [201, 200] # 200 if already exists
    log_result(f"Register {role}", "POST", url, status, payload, body, success)

def main():
    print("Starting tests...")
    
    # 1. Register & Login Client
    test_client_email = "test_client_v2@200millas.com"
    test_client_pass = "password123"
    
    test_register(test_client_email, test_client_pass, "Cliente")
    client_token = test_login(test_client_email, test_client_pass, "Client")
    
    if client_token:
        test_get_me(client_token, "Client")
    
    # 2. Products
    # List first to get a valid product
    url_list = f"{BASE_URL_PRODUCTS}/productos/list"
    payload_list = {"local_id": "LOCAL-005"}
    status, body = make_request(url_list, "POST", payload_list)
    success_list = status == 200
    
    report_body = body
    if isinstance(body, dict) and "contents" in body and len(body["contents"]) > 2:
        report_body = body.copy()
        report_body["contents"] = body["contents"][:2] + ["... (truncated)"]
    log_result("List Products", "POST", url_list, status, payload_list, report_body, success_list)
    
    valid_product = None
    if success_list and isinstance(body, dict) and "contents" in body and len(body["contents"]) > 0:
        valid_product = body["contents"][0]
    
    # Get Product ID using valid data
    if valid_product:
        url_id = f"{BASE_URL_PRODUCTS}/productos/id"
        # Use keys from the listed product
        payload_id = {
            "local_id": valid_product.get("local_id"),
            "nombre": valid_product.get("nombre")
        }
        status_id, body_id = make_request(url_id, "POST", payload_id)
        log_result("Get Product ID", "POST", url_id, status_id, payload_id, body_id, status_id == 200)
    else:
        print("Skipping Get Product ID (no product found in list)")
    
    # 3. Orders
    if client_token and valid_product:
        # Create order with valid product
        url_create = f"{BASE_URL_CLIENTES}/pedido/create"
        headers = {"Authorization": client_token}
        payload_create = {
            "tenant_id": "TENANT-001",
            "local_id": valid_product.get("local_id", "LOCAL-005"),
            "usuario_correo": test_client_email,
            "direccion": "Av. Test 123",
            "costo": 50.0,
            "estado": "procesando",
            "productos": [
                {"nombre": valid_product.get("nombre", "Ceviches 1"), "cantidad": 2}
            ]
        }
        status_create, body_create = make_request(url_create, "POST", payload_create, headers)
        success_create = status_create == 201
        log_result("Create Pedido", "POST", url_create, status_create, payload_create, body_create, success_create)
        
        pedido_id = None
        if success_create and isinstance(body_create, dict):
            pedido_id = body_create.get("pedido", {}).get("pedido_id")
            
        if pedido_id:
            test_get_pedido_status(client_token, pedido_id)
            test_confirmar_pedido(client_token, pedido_id)
    
    # Save results to JSON for processing
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("Tests completed. Results saved to test_results.json")

if __name__ == "__main__":
    main()
