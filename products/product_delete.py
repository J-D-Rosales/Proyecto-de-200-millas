import os, json, boto3
from decimal import Decimal

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]
PRODUCTS_BUCKET = os.environ.get("PRODUCTS_BUCKET")
VALIDAR_EMPLOYEE_TOKEN_ACCESS_FUNCTION = os.environ["VALIDAR_EMPLOYEE_TOKEN_ACCESS_FUNCTION"]

def _resp(code, body):
    return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False)}

def convert_decimal(obj):
    """Convierte objetos Decimal a float de manera recursiva."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal(i) for i in obj]
    return obj

def lambda_handler(event, context):
    print(event)
    
    # Inicio - Proteger el Lambda
    token = event['headers']['Authorization']
    lambda_client = boto3.client('lambda')    
    payload_string = '{ "token": "' + token +  '" }'
    invoke_response = lambda_client.invoke(FunctionName=VALIDAR_EMPLOYEE_TOKEN_ACCESS_FUNCTION,
                                           InvocationType='RequestResponse',
                                           Payload = payload_string)
    response = json.loads(invoke_response['Payload'].read())
    print(response)
    if response['statusCode'] == 403:
        return {
            'statusCode' : 403,
            'status' : 'Forbidden - Acceso No Autorizado'
        }
    # Fin - Proteger el Lambda   

    data = json.loads(event.get("body") or "{}")
    tenant_id = data.get("tenant_id")
    product_id = data.get("product_id")
    if not tenant_id:
        return _resp(400, {"error": "Falta tenant_id en el body"})
    if not product_id:
        return _resp(400, {"error": "Falta product_id en el body"})

    ddb = boto3.resource("dynamodb")
    s3 = boto3.client("s3")
    table = ddb.Table(PRODUCTS_TABLE)

    try:
        res = table.get_item(
            Key={"tenant_id": tenant_id, "product_id": product_id}
        )
        
        if "Item" not in res:
            return _resp(404, {"error": "Producto no encontrado"})

        product = res["Item"]
        image_key = product.get("image_url")

        if image_key:
            try:
                s3.delete_object(Bucket=PRODUCTS_BUCKET, Key=image_key)
                print(f"Imagen {image_key} eliminada de S3.")
            except Exception as e:
                print(f"Error al eliminar la imagen de S3: {str(e)}")
                return _resp(500, {"error": f"Error al eliminar la imagen de S3: {str(e)}"})

        res = table.delete_item(
            Key={"tenant_id": tenant_id, "product_id": product_id},
            ConditionExpression="attribute_exists(tenant_id) AND attribute_exists(product_id)",
            ReturnValues="ALL_OLD"
        )
    except ddb.meta.client.exceptions.ConditionalCheckFailedException:
        return _resp(404, {"error": "Producto no encontrado"})

    deleted_attributes = convert_decimal(res.get("Attributes"))
    return _resp(200, {"ok": True, "deleted": deleted_attributes})
