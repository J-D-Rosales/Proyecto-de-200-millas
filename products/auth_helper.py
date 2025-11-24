import os
import json
import boto3

VALIDAR_TOKEN_LAMBDA_NAME = os.environ.get("VALIDAR_TOKEN_LAMBDA_NAME", "ValidarTokenAcceso")

lambda_client = boto3.client('lambda')


def get_bearer_token(event):
    """
    Extrae el token del header Authorization (con o sin 'Bearer ')
    """
    headers = event.get("headers") or {}
    
    # Buscar el header Authorization (case-insensitive)
    auth_header = None
    for key, value in headers.items():
        if key.lower() == "authorization":
            auth_header = value
            break
    
    if not auth_header:
        return None
    
    # Si es string, procesar
    if isinstance(auth_header, str):
        auth_header = auth_header.strip()
        
        # Si tiene "Bearer ", extraer el token
        if auth_header.lower().startswith("bearer "):
            return auth_header.split(" ", 1)[1].strip()
        
        # Si no tiene "Bearer ", devolver el token directamente
        return auth_header
    
    return None


def validate_token_via_lambda(token: str):
    """
    Invoca el Lambda validador de token (ValidarTokenAcceso).
    
    Retorna:
        (valido: bool, error: str, rol: str)
    """
    if not token:
        return False, "Token requerido", None
    
    try:
        payload_string = json.dumps({"token": token})
        
        invoke_response = lambda_client.invoke(
            FunctionName=VALIDAR_TOKEN_LAMBDA_NAME,
            InvocationType='RequestResponse',
            Payload=payload_string.encode('utf-8')
        )
        
        response = json.loads(invoke_response['Payload'].read())
        
        # Verificar statusCode
        if response.get('statusCode') != 200:
            body = response.get('body', 'Token inválido')
            error_msg = body if isinstance(body, str) else json.dumps(body)
            return False, error_msg, None
        
        # Extraer rol de la respuesta
        rol = response.get('rol', 'Cliente')
        
        return True, None, rol
        
    except Exception as e:
        return False, f"Error al validar token: {str(e)}", None
