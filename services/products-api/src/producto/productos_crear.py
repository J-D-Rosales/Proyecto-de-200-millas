import os
import json
import base64
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError
from src.common.auth import get_token_from_headers, validate_token_and_get_claims

PRODUCTS_BUCKET = os.environ.get("PRODUCTS_BUCKET")
PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def _resp(code, body):
    return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False)}

def lambda_handler(event, context):
    token = get_token_from_headers(event)
    auth = validate_token_and_get_claims(token)
    if auth.get("statusCode") == 403:
        return _resp(403, {"error": "Acceso no autorizado"})

    body = json.loads(event.get("body") or "{}", parse_float=Decimal)
    tenant_id = body.get("tenant_id")
    product_id = body.get("product_id")
    if not tenant_id:
        return _resp(400, {"error": "Falta tenant_id en el body"})
    if not product_id:
        return _resp(400, {"error": "Falta product_id en el body"})

    image_data = body.get("image")
    image_url_or_key = None

    if image_data:
        try:
            bucket = PRODUCTS_BUCKET
            key = body["image"]["key"]
            file_b64 = body["image"]["file_base64"]
            content_type = body["image"]["content_type"]

            if not bucket:
                return _resp(400, {"error": "Falta 'bucket'"})
            if not key:
                return _resp(400, {"error": "Falta 'key'"})
            if not file_b64:
                return _resp(400, {"error": "'file_base64' es requerido"})

            try:
                file_bytes = base64.b64decode(file_b64)
            except Exception as e:
                return _resp(400, {"error": f"file_base64 inválido: {e}"})

            s3 = boto3.client("s3")
            put_kwargs = {"Bucket": bucket, "Key": key, "Body": file_bytes}
            if content_type:
                put_kwargs["ContentType"] = content_type

            resp = s3.put_object(**put_kwargs)
            etag = (resp.get("ETag") or "").strip('"')

            image_url_or_key = key

        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code == "AccessDenied":
                return _resp(403, {"error": "Acceso denegado al bucket"})
            if code == "NoSuchBucket":
                return _resp(400, {"error": f"El bucket {bucket} no existe"})
            return _resp(400, {"error": f"Error S3: {e}"})
        except Exception as e:
            return _resp(500, {"error": f"Error interno al subir la imagen: {e}"})

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)
    try:
        body["image_url"] = image_url_or_key
        table.put_item(
            Item=body,
            ConditionExpression="attribute_not_exists(tenant_id) AND attribute_not_exists(product_id)"
        )
    except ddb.meta.client.exceptions.ConditionalCheckFailedException:
        return _resp(409, {"error": "El producto ya existe"})

    return _resp(201, {"ok": True, "item": body})
